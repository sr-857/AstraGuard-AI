/**
 * React Hook for Intelligent API Rate Limiting
 *
 * Provides user feedback and graceful degradation during rate limiting
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient, ApiResponse, SystemHealth } from './intelligent-api-client';
import { logger } from './logger';

export interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  rateLimited: boolean;
  systemHealth: SystemHealth | null;
  queueLength: number;
  retryAfter: number;
}

export interface UseApiOptions {
  priority?: number;
  retryOnRateLimit?: boolean;
  maxRetries?: number;
  onRateLimit?: () => void;
  onSystemDegraded?: (health: SystemHealth) => void;
}

export function useIntelligentApi<T = any>(options: UseApiOptions = {}) {
  const {
    priority = 1,
    retryOnRateLimit = true,
    maxRetries = 3,
    onRateLimit,
    onSystemDegraded,
  } = options;

  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
    rateLimited: false,
    systemHealth: null,
    queueLength: 0,
    retryAfter: 0,
  });

  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);

  // Update system health and queue status
  useEffect(() => {
    const updateStatus = () => {
      const health = apiClient.getSystemHealth();
      const queueLength = apiClient.getQueueLength();

      setState((prev: UseApiState<T>) => ({
        ...prev,
        systemHealth: health,
        queueLength,
      }));

      // Notify about system degradation
      if (health && health.status !== 'healthy' && onSystemDegraded) {
        onSystemDegraded(health);
      }
    };

    // Update immediately and then every 2 seconds
    updateStatus();
    const interval = setInterval(updateStatus, 2000);

    return () => clearInterval(interval);
  }, [onSystemDegraded]);

  const executeRequest = useCallback(async (
    requestFn: () => Promise<ApiResponse<T>>
  ): Promise<T | null> => {
    setState((prev: UseApiState<T>) => ({
      ...prev,
      loading: true,
      error: null,
      rateLimited: false,
    }));

    try {
      const response = await requestFn();
      setState((prev: UseApiState<T>) => ({
        ...prev,
        data: response.data,
        loading: false,
        error: null,
        rateLimited: false,
      }));
      retryCountRef.current = 0; // Reset retry count on success
      return response.data;
    } catch (error: any) {
      logger.error('API request failed', error);

      let errorMessage = 'An unexpected error occurred';
      let isRateLimited = false;
      let retryAfter = 0;

      if (error.name === 'RateLimitError') {
        errorMessage = 'Too many requests. Please wait before trying again.';
        isRateLimited = true;
        retryAfter = 60; // 1 minute default
        onRateLimit?.();
      } else if (error.message?.includes('Rate limit exceeded')) {
        errorMessage = 'Server is busy. Please try again in a moment.';
        isRateLimited = true;
        retryAfter = 30; // 30 seconds
        onRateLimit?.();
      } else if (error.message?.includes('HTTP')) {
        errorMessage = error.message;
      }

      setState((prev: UseApiState<T>) => ({
        ...prev,
        loading: false,
        error: errorMessage,
        rateLimited: isRateLimited,
        retryAfter,
      }));

      // Auto-retry on rate limit if enabled
      if (isRateLimited && retryOnRateLimit && retryCountRef.current < maxRetries) {
        retryCountRef.current++;
        const retryDelay = retryAfter * 1000 * Math.pow(2, retryCountRef.current - 1); // Exponential backoff

        logger.info(`Retrying request in ${retryDelay}ms (attempt ${retryCountRef.current}/${maxRetries})`);

        retryTimeoutRef.current = setTimeout(() => {
          executeRequest(requestFn);
        }, retryDelay);
      }

      return null;
    }
  }, [retryOnRateLimit, maxRetries, onRateLimit]);

  const get = useCallback((endpoint: string) => {
    return executeRequest(() => apiClient.get<T>(endpoint, priority));
  }, [executeRequest, priority]);

  const post = useCallback((endpoint: string, data: any) => {
    return executeRequest(() => apiClient.post<T>(endpoint, data, priority));
  }, [executeRequest, priority]);

  const put = useCallback((endpoint: string, data: any) => {
    return executeRequest(() => apiClient.put<T>(endpoint, data, priority));
  }, [executeRequest, priority]);

  const del = useCallback((endpoint: string) => {
    return executeRequest(() => apiClient.delete<T>(endpoint, priority));
  }, [executeRequest, priority]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, []);

  return {
    ...state,
    get,
    post,
    put,
    delete: del,
  };
}

// Hook for displaying rate limit notifications
export function useRateLimitNotifications() {
  const [notifications, setNotifications] = useState<Array<{
    id: string;
    message: string;
    type: 'warning' | 'error' | 'info';
    timestamp: number;
  }>>([]);

  const addNotification = useCallback((message: string, type: 'warning' | 'error' | 'info' = 'warning') => {
    const id = Date.now().toString();
    setNotifications(prev => [...prev, { id, message, type, timestamp: Date.now() }]);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  }, []);

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev: typeof notifications) => prev.filter(n => n.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications((prev: typeof notifications) => []);
  }, []);

  return {
    notifications,
    addNotification,
    removeNotification,
    clearAll,
  };
}

// Hook for system health monitoring
export function useSystemHealth() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now());

  useEffect(() => {
    const updateHealth = () => {
      const currentHealth = apiClient.getSystemHealth();
      setHealth(currentHealth);
      setLastUpdate(Date.now());
    };

    updateHealth();
    const interval = setInterval(updateHealth, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, []);

  const getHealthStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-500';
      case 'degraded': return 'text-yellow-500';
      case 'critical': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getHealthStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return '🟢';
      case 'degraded': return '🟡';
      case 'critical': return '🔴';
      default: return '⚪';
    }
  };

  return {
    health,
    lastUpdate,
    getHealthStatusColor,
    getHealthStatusIcon,
  };
 * Intelligent API Hook for federated learning
 * Simplified version for demo purposes
 */

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

export function useIntelligentApi() {
  const get = async (endpoint: string): Promise<ApiResponse> => {
    try {
      // Mock API call for demo
      console.log(`GET ${endpoint}`);

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));

      // Mock responses based on endpoint
      if (endpoint.includes('/federated-learning/status')) {
        return {
          success: true,
          data: {
            currentRound: 5,
            participants: ['node-1', 'node-2', 'node-3'],
            globalAccuracy: 0.87
          }
        };
      }

      if (endpoint.includes('/federated-learning/participants')) {
        return {
          success: true,
          data: {
            participants: ['node-1', 'node-2', 'node-3', 'node-4', 'node-5']
          }
        };
      }

      if (endpoint.includes('/federated-learning/metrics')) {
        return {
          success: true,
          data: {
            metrics: [
              { round: 1, localAccuracy: 0.65, globalAccuracy: 0.62 },
              { round: 2, localAccuracy: 0.72, globalAccuracy: 0.68 },
              { round: 3, localAccuracy: 0.78, globalAccuracy: 0.74 },
              { round: 4, localAccuracy: 0.83, globalAccuracy: 0.79 },
              { round: 5, localAccuracy: 0.87, globalAccuracy: 0.82 }
            ]
          }
        };
      }

      if (endpoint.includes('/federated-learning/model')) {
        return {
          success: true,
          data: {
            weights: [
              [0.15, 0.25, 0.35, 0.45],
              [-0.05, -0.15, -0.25, -0.35],
              [0.08, -0.08, 0.12, -0.12],
              [0.32, -0.22, 0.14, -0.44]
            ]
          }
        };
      }

      return { success: false, error: 'Unknown endpoint' };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'API error' };
    }
  };

  const post = async (endpoint: string, data: any): Promise<ApiResponse> => {
    try {
      console.log(`POST ${endpoint}`, data);

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 800));

      // Mock responses
      if (endpoint.includes('/federated-learning/update')) {
        return {
          success: true,
          data: {
            participants: ['node-1', 'node-2', 'node-3', 'node-4', 'node-5'],
            accepted: true,
            round: 6
          }
        };
      }

      return { success: false, error: 'Unknown endpoint' };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'API error' };
    }
  };

  return { get, post };
}