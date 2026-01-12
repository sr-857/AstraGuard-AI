"""
Resource monitoring utilities for AstraGuard-AI.

Monitors system resources (CPU, memory, disk) to detect exhaustion
before it causes failures. Integrates with health monitoring system.

Features:
- Real-time CPU and memory usage tracking
- Configurable warning/critical thresholds
- Resource usage history for diagnostics
- Integration with health monitor
- Automatic alerts when thresholds exceeded
- Non-blocking CPU monitoring
"""

import psutil
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

# Import centralized secrets management
from core.secrets import get_secret

logger = logging.getLogger(__name__)


class ResourceStatus(str, Enum):
    """Resource health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ResourceMetrics:
    """
    Snapshot of system resource metrics.
    
    Attributes:
        cpu_percent: CPU utilization percentage (0-100)
        memory_percent: Memory utilization percentage (0-100)
        memory_available_mb: Available memory in megabytes
        disk_usage_percent: Disk usage percentage (0-100)
        process_memory_mb: Memory used by current process
        timestamp: When metrics were collected
    """
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_usage_percent: float
    process_memory_mb: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'cpu_percent': round(self.cpu_percent, 2),
            'memory_percent': round(self.memory_percent, 2),
            'memory_available_mb': round(self.memory_available_mb, 2),
            'disk_usage_percent': round(self.disk_usage_percent, 2),
            'process_memory_mb': round(self.process_memory_mb, 2),
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ResourceThresholds:
    """
    Configurable thresholds for resource monitoring.
    
    Attributes:
        cpu_warning: CPU % to trigger warning (default: 70%)
        cpu_critical: CPU % to trigger critical alert (default: 90%)
        memory_warning: Memory % for warning (default: 75%)
        memory_critical: Memory % for critical alert (default: 90%)
        disk_warning: Disk % for warning (default: 80%)
        disk_critical: Disk % for critical alert (default: 95%)
    """
    cpu_warning: float = 70.0
    cpu_critical: float = 90.0
    memory_warning: float = 75.0
    memory_critical: float = 90.0
    disk_warning: float = 80.0
    disk_critical: float = 95.0


class ResourceMonitor:
    """
    Monitor system resource utilization.
    
    Tracks CPU, memory, and disk usage with configurable thresholds.
    Maintains history for trend analysis and diagnostics.
    """
    
    def __init__(
        self,
        thresholds: Optional[ResourceThresholds] = None,
        history_size: int = 100,
        monitoring_enabled: bool = True
    ):
        """
        Initialize resource monitor.
        
        Args:
            thresholds: Custom threshold configuration (uses defaults if None)
            history_size: Number of metric snapshots to retain
            monitoring_enabled: Whether monitoring is active
        """
        self.thresholds = thresholds or ResourceThresholds()
        self.history_size = history_size
        self.monitoring_enabled = monitoring_enabled
        
        self._metrics_history: List[ResourceMetrics] = []
        self._process = psutil.Process()
        
        logger.info(
            f"ResourceMonitor initialized: "
            f"cpu_warning={self.thresholds.cpu_warning}%, "
            f"memory_warning={self.thresholds.memory_warning}%"
        )
    
    def get_current_metrics(self) -> ResourceMetrics:
        """
        Collect current resource metrics.
        
        Uses interval=0 for CPU to ensure non-blocking operation.
        
        Returns:
            ResourceMetrics snapshot of current system state
        """
        if not self.monitoring_enabled:
            return ResourceMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                process_memory_mb=0.0
            )
        
        try:
            # CPU usage (interval=0 for non-blocking return)
            # This returns usage since last call, which is ideal for periodic monitoring
            cpu_percent = psutil.cpu_percent(interval=0)
            # CPU usage (1 second interval for accuracy)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            
            # Process memory
            process_info = self._process.memory_info()
            process_memory_mb = process_info.rss / (1024 * 1024)
            
            metrics = ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                process_memory_mb=process_memory_mb,
                timestamp=datetime.now()
            )
            
            # Add to history
            self._add_to_history(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting resource metrics: {e}")
            return ResourceMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                process_memory_mb=0.0
            )
    
    def _add_to_history(self, metrics: ResourceMetrics):
        """Add metrics to history, maintaining size limit"""
        self._metrics_history.append(metrics)
        
        # Trim history if exceeded size
        if len(self._metrics_history) > self.history_size:
            self._metrics_history = self._metrics_history[-self.history_size:]
    
    def check_resource_health(self) -> Dict[str, str]:
        """
        Check if resources are within safe limits.
        
        Returns:
            Dictionary with status for each resource type:
            {
                'cpu': 'healthy' | 'warning' | 'critical',
                'memory': 'healthy' | 'warning' | 'critical',
                'disk': 'healthy' | 'warning' | 'critical',
                'overall': 'healthy' | 'warning' | 'critical'
            }
        """
        metrics = self.get_current_metrics()
        
        status = {
            'cpu': ResourceStatus.HEALTHY,
            'memory': ResourceStatus.HEALTHY,
            'disk': ResourceStatus.HEALTHY,
            'overall': ResourceStatus.HEALTHY
        }
        
        # Check CPU
        if metrics.cpu_percent >= self.thresholds.cpu_critical:
            status['cpu'] = ResourceStatus.CRITICAL
            logger.warning(
                f"CPU critical: {metrics.cpu_percent:.1f}% "
                f"(threshold: {self.thresholds.cpu_critical}%)"
            )
        elif metrics.cpu_percent >= self.thresholds.cpu_warning:
            status['cpu'] = ResourceStatus.WARNING
            logger.info(
                f"CPU warning: {metrics.cpu_percent:.1f}% "
                f"(threshold: {self.thresholds.cpu_warning}%)"
            )
        
        # Check Memory
        if metrics.memory_percent >= self.thresholds.memory_critical:
            status['memory'] = ResourceStatus.CRITICAL
            logger.warning(
                f"Memory critical: {metrics.memory_percent:.1f}% "
                f"(threshold: {self.thresholds.memory_critical}%)"
            )
        elif metrics.memory_percent >= self.thresholds.memory_warning:
            status['memory'] = ResourceStatus.WARNING
            logger.info(
                f"Memory warning: {metrics.memory_percent:.1f}% "
                f"(threshold: {self.thresholds.memory_warning}%)"
            )
        
        # Check Disk
        if metrics.disk_usage_percent >= self.thresholds.disk_critical:
            status['disk'] = ResourceStatus.CRITICAL
            logger.warning(
                f"Disk critical: {metrics.disk_usage_percent:.1f}% "
                f"(threshold: {self.thresholds.disk_critical}%)"
            )
        elif metrics.disk_usage_percent >= self.thresholds.disk_warning:
            status['disk'] = ResourceStatus.WARNING
        
        # Determine overall status (worst status wins)
        if any(s == ResourceStatus.CRITICAL for s in status.values()):
            status['overall'] = ResourceStatus.CRITICAL
        elif any(s == ResourceStatus.WARNING for s in status.values()):
            status['overall'] = ResourceStatus.WARNING
        
        return {k: v.value for k, v in status.items()}
    
    def is_resource_available(self, min_cpu_free: float = 10.0, min_memory_mb: float = 100.0) -> bool:
        """
        Check if sufficient resources are available for operations.
        
        Args:
            min_cpu_free: Minimum free CPU percentage required
            min_memory_mb: Minimum free memory in MB required
        
        Returns:
            True if resources are available, False otherwise
        """
        metrics = self.get_current_metrics()
        
        cpu_free = 100.0 - metrics.cpu_percent
        memory_available = metrics.memory_available_mb
        
        if cpu_free < min_cpu_free:
            logger.warning(
                f"Insufficient CPU: {cpu_free:.1f}% free (need {min_cpu_free}%)"
            )
            return False
        
        if memory_available < min_memory_mb:
            logger.warning(
                f"Insufficient memory: {memory_available:.1f}MB free (need {min_memory_mb}MB)"
            )
            return False
        
        return True
    
    def get_metrics_summary(self, duration_minutes: int = 5) -> Dict:
        """
        Get statistical summary of recent metrics.
        
        Args:
            duration_minutes: Look back window in minutes
        
        Returns:
            Dictionary with min/max/avg for each metric
        """
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_metrics = [
            m for m in self._metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {'error': 'No metrics available'}
        
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        
        return {
            'timeframe_minutes': duration_minutes,
            'samples': len(recent_metrics),
            'cpu': {
                'min': min(cpu_values),
                'max': max(cpu_values),
                'avg': sum(cpu_values) / len(cpu_values)
            },
            'memory': {
                'min': min(memory_values),
                'max': max(memory_values),
                'avg': sum(memory_values) / len(memory_values)
            },
            'current': self.get_current_metrics().to_dict()
        }
    
    def get_history(self, count: Optional[int] = None) -> List[Dict]:
        """
        Get recent metrics history.
        
        Args:
            count: Number of recent entries (None for all)
        
        Returns:
            List of metric dictionaries
        """
        history = self._metrics_history[-count:] if count else self._metrics_history
        return [m.to_dict() for m in history]


# Singleton instance and lock for thread safety
_resource_monitor: Optional[ResourceMonitor] = None
_resource_monitor_lock = threading.Lock()


def get_resource_monitor() -> ResourceMonitor:
    """
    Get global resource monitor singleton.

    Initializes with configuration from environment variables if not already created.
    Thread-safe using double-checked locking pattern.

    Returns:
        ResourceMonitor singleton instance
    """
    global _resource_monitor

    # First check without lock for performance
    if _resource_monitor is None:
        with _resource_monitor_lock:
            # Double-check pattern: check again inside lock
            if _resource_monitor is None:
                import os

                # Load configuration from environment
                thresholds = ResourceThresholds(
                    cpu_warning=get_secret('resource_cpu_warning'),
                    cpu_critical=get_secret('resource_cpu_critical'),
                    memory_warning=get_secret('resource_memory_warning'),
                    memory_critical=get_secret('resource_memory_critical'),
                )

                monitoring_enabled = get_secret('resource_monitoring_enabled')

                _resource_monitor = ResourceMonitor(
                    thresholds=thresholds,
                    monitoring_enabled=monitoring_enabled
                )

    return _resource_monitor
