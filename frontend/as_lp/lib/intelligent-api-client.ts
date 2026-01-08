/**
 * AstraGuard AI Intelligent API Client
 *
 * Features intelligent rate limiting and throttling based on system health
 * Provides graceful degradation and user feedback
 */

import { logger } from './logger';

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  headers: Headers;
}

export interface RateLimitConfig {
  maxRequestsPerMinute: number;
  maxConcurrentRequests: number;
  backoffMultiplier: number;
  maxBackoffTime: number;
  healthCheckInterval: number;
}

export interface SystemHealth {
  cpuUsage: number;
  memoryUsage: number;
  activeConnections: number;
  anomalyScore: number;
  status: 'healthy' | 'degraded' | 'critical';
}

export class IntelligentApiClient {
  private baseUrl: string;
  private config: RateLimitConfig;
  private requestQueue: Array<{
    request: () => Promise<any>;
    resolve: (value: any) => void;
    reject: (error: any) => void;
    priority: number;
  }> = [];
  private activeRequests = 0;
  private requestCounts = new Map<string, number>();
  private lastRequestTimes = new Map<string, number>();
  private backoffUntil = 0;
  private systemHealth: SystemHealth | null = null;
  private healthCheckTimer: ReturnType<typeof setInterval> | null = null;

  constructor(baseUrl = '/api', config: Partial<RateLimitConfig> = {}) {
    this.baseUrl = baseUrl;
    this.config = {
      maxRequestsPerMinute: 60,
      maxConcurrentRequests: 5,
      backoffMultiplier: 2,
      maxBackoffTime: 30000, // 30 seconds
      healthCheckInterval: 10000, // 10 seconds
      ...config,
    };

    this.startHealthMonitoring();
  }

  private startHealthMonitoring() {
    this.healthCheckTimer = setInterval(async () => {
      try {
        await this.updateSystemHealth();
      } catch (error) {
        logger.warn('Failed to update system health', error);
      }
    }, this.config.healthCheckInterval);
  }

  private async updateSystemHealth(): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/health/state`);
      if (response.ok) {
        const healthData = await response.json();
        this.systemHealth = {
          cpuUsage: healthData.cpu_usage || 0,
          memoryUsage: healthData.memory_usage || 0,
          activeConnections: healthData.active_connections || 0,
          anomalyScore: healthData.anomaly_score || 0,
          status: this.determineHealthStatus(healthData),
        };

        // Adjust rate limits based on system health
        this.adjustRateLimits();
      }
    } catch (error) {
      logger.warn('Health check failed', error);
      // Assume degraded state if health check fails
      this.systemHealth = {
        cpuUsage: 80,
        memoryUsage: 80,
        activeConnections: 100,
        anomalyScore: 0.7,
        status: 'degraded',
      };
    }
  }

  private determineHealthStatus(healthData: any): 'healthy' | 'degraded' | 'critical' {
    const cpuUsage = healthData.cpu_usage || 0;
    const memoryUsage = healthData.memory_usage || 0;
    const anomalyScore = healthData.anomaly_score || 0;

    if (cpuUsage > 90 || memoryUsage > 90 || anomalyScore > 0.8) {
      return 'critical';
    } else if (cpuUsage > 70 || memoryUsage > 70 || anomalyScore > 0.5) {
      return 'degraded';
    }
    return 'healthy';
  }

  private adjustRateLimits(): void {
    if (!this.systemHealth) return;

    const { status } = this.systemHealth;
    let multiplier = 1;

    switch (status) {
      case 'healthy':
        multiplier = 1;
        break;
      case 'degraded':
        multiplier = 0.5; // Reduce to 50% capacity
        break;
      case 'critical':
        multiplier = 0.2; // Reduce to 20% capacity
        break;
    }

    this.config.maxRequestsPerMinute = Math.floor(60 * multiplier);
    this.config.maxConcurrentRequests = Math.floor(5 * multiplier);

    logger.info(`Adjusted rate limits based on system health: ${status}`, {
      maxRequestsPerMinute: this.config.maxRequestsPerMinute,
      maxConcurrentRequests: this.config.maxConcurrentRequests,
    });
  }

  private getRequestKey(endpoint: string): string {
    return endpoint.split('?')[0]; // Remove query parameters
  }

  private isRateLimited(endpoint: string): boolean {
    const key = this.getRequestKey(endpoint);
    const now = Date.now();
    const windowStart = now - 60000; // 1 minute window

    // Clean old entries
    for (const [k, time] of this.lastRequestTimes) {
      if (time < windowStart) {
        this.lastRequestTimes.delete(k);
        this.requestCounts.delete(k);
      }
    }

    const currentCount = this.requestCounts.get(key) || 0;
    return currentCount >= this.config.maxRequestsPerMinute;
  }

  private recordRequest(endpoint: string): void {
    const key = this.getRequestKey(endpoint);
    const now = Date.now();

    this.lastRequestTimes.set(key, now);
    this.requestCounts.set(key, (this.requestCounts.get(key) || 0) + 1);
  }

  private async waitForBackoff(): Promise<void> {
    const now = Date.now();
    if (now < this.backoffUntil) {
      const waitTime = this.backoffUntil - now;
      logger.warn(`Backing off for ${waitTime}ms due to rate limiting`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
  }

  private async processQueue(): Promise<void> {
    if (this.requestQueue.length === 0 || this.activeRequests >= this.config.maxConcurrentRequests) {
      return;
    }

    // Sort by priority (higher priority first)
    this.requestQueue.sort((a, b) => b.priority - a.priority);

    const { request, resolve, reject } = this.requestQueue.shift()!;
    this.activeRequests++;

    try {
      const response = await request();
      resolve(response);
    } catch (error) {
      reject(error);
    } finally {
      this.activeRequests--;
      // Process next request in queue
      setTimeout(() => this.processQueue(), 0);
    }
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {},
    priority = 1
  ): Promise<ApiResponse<T>> {
    const fullUrl = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;

    // Check rate limits
    if (this.isRateLimited(fullUrl)) {
      const error = new Error('Rate limit exceeded. Please try again later.');
      error.name = 'RateLimitError';
      throw error;
    }

    // Wait for backoff if needed
    await this.waitForBackoff();

    return new Promise((resolve, reject) => {
      const request = async (): Promise<ApiResponse<T>> => {
        try {
          logger.debug(`Making API request to ${fullUrl}`);
          this.recordRequest(fullUrl);

          const response = await fetch(fullUrl, {
            ...options,
            headers: {
              'Content-Type': 'application/json',
              ...options.headers,
            },
          });

          if (response.status === 429) {
            // Rate limited by server
            const retryAfter = response.headers.get('Retry-After');
            const backoffTime = Math.min(
              (retryAfter ? parseInt(retryAfter) * 1000 : 1000) * this.config.backoffMultiplier,
              this.config.maxBackoffTime
            );
            this.backoffUntil = Date.now() + backoffTime;
            throw new Error('Server rate limit exceeded. Backing off...');
          }

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const data = await response.json();
          return {
            data,
            status: response.status,
            headers: response.headers,
          };
        } catch (error) {
          logger.error(`API request failed: ${fullUrl}`, error);
          throw error;
        }
      };

      // Add to queue if at capacity
      if (this.activeRequests >= this.config.maxConcurrentRequests) {
        this.requestQueue.push({ request: () => request(), resolve, reject, priority });
        logger.debug(`Request queued. Queue length: ${this.requestQueue.length}`);
      } else {
        // Process immediately
        this.processQueue();
        request().then(resolve).catch(reject);
      }
    });
  }

  // Public API methods
  async get<T>(endpoint: string, priority = 1): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(endpoint, { method: 'GET' }, priority);
  }

  async post<T>(endpoint: string, data: any, priority = 1): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    }, priority);
  }

  async put<T>(endpoint: string, data: any, priority = 1): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    }, priority);
  }

  async delete<T>(endpoint: string, priority = 1): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(endpoint, { method: 'DELETE' }, priority);
  }

  // Health monitoring
  getSystemHealth(): SystemHealth | null {
    return this.systemHealth;
  }

  getQueueLength(): number {
    return this.requestQueue.length;
  }

  getActiveRequests(): number {
    return this.activeRequests;
  }

  // Cleanup
  destroy(): void {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
  }
}

// Export singleton instance
export const apiClient = new IntelligentApiClient();

// Cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    apiClient.destroy();
  });
}