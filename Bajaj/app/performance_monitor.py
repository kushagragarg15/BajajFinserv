# performance_monitor.py
import time
import asyncio
import logging
import functools
import psutil
import os
from typing import Dict, List, Optional, Any, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import threading

@dataclass
class PerformanceMetric:
    """Data class to store performance metrics for operations"""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    cpu_usage_start: Optional[float] = None
    memory_usage_start: Optional[float] = None
    cpu_usage_end: Optional[float] = None
    memory_usage_end: Optional[float] = None
    
    def __post_init__(self):
        """Capture initial system metrics"""
        try:
            process = psutil.Process()
            self.cpu_usage_start = process.cpu_percent()
            self.memory_usage_start = process.memory_info().rss / 1024 / 1024  # MB
        except Exception:
            # Ignore errors in system monitoring to not affect main functionality
            pass
    
    def finish(self, success: bool = True, error_message: Optional[str] = None):
        """Mark the operation as finished and calculate duration"""
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error_message = error_message
        
        # Capture final system metrics
        try:
            process = psutil.Process()
            self.cpu_usage_end = process.cpu_percent()
            self.memory_usage_end = process.memory_info().rss / 1024 / 1024  # MB
        except Exception:
            # Ignore errors in system monitoring
            pass
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """Get resource usage metrics for this operation"""
        return {
            "cpu_usage_start": self.cpu_usage_start,
            "cpu_usage_end": self.cpu_usage_end,
            "memory_usage_start": self.memory_usage_start,
            "memory_usage_end": self.memory_usage_end,
            "memory_delta": (
                self.memory_usage_end - self.memory_usage_start 
                if self.memory_usage_end and self.memory_usage_start 
                else None
            )
        }

@dataclass
class RequestMetrics:
    """Data class to store comprehensive request metrics"""
    request_id: str
    start_time: float
    end_time: Optional[float] = None
    total_duration: Optional[float] = None
    operations: List[PerformanceMetric] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    system_metrics_start: Dict[str, Any] = field(default_factory=dict)
    system_metrics_end: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Capture initial system metrics for the request"""
        self.system_metrics_start = self._capture_system_metrics()
    
    def _capture_system_metrics(self) -> Dict[str, Any]:
        """Capture current system metrics"""
        try:
            process = psutil.Process()
            return {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "open_files": len(process.open_files()),
                "threads": process.num_threads(),
                "timestamp": time.perf_counter()
            }
        except Exception:
            return {"error": "Failed to capture system metrics"}
    
    def add_operation(self, operation: PerformanceMetric):
        """Add an operation metric to this request"""
        self.operations.append(operation)
    
    def finish(self):
        """Mark the request as finished and calculate total duration"""
        self.end_time = time.perf_counter()
        self.total_duration = self.end_time - self.start_time
        self.system_metrics_end = self._capture_system_metrics()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics for this request"""
        return {
            "request_id": self.request_id,
            "total_duration": round(self.total_duration or 0, 3),
            "operations": [
                {
                    "name": op.operation_name,
                    "duration": round(op.duration or 0, 3),
                    "success": op.success,
                    "error": op.error_message,
                    "metadata": op.metadata,
                    "resource_usage": op.get_resource_usage()
                }
                for op in self.operations
            ],
            "metadata": self.metadata,
            "system_metrics": {
                "start": self.system_metrics_start,
                "end": self.system_metrics_end,
                "memory_delta": (
                    self.system_metrics_end.get("memory_mb", 0) - 
                    self.system_metrics_start.get("memory_mb", 0)
                    if "memory_mb" in self.system_metrics_end and "memory_mb" in self.system_metrics_start
                    else None
                )
            }
        }
    
    def identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify potential bottlenecks in the request processing"""
        bottlenecks = []
        
        if not self.operations:
            return bottlenecks
        
        # Find the slowest operation
        slowest_op = max(self.operations, key=lambda op: op.duration or 0)
        if slowest_op.duration and slowest_op.duration > 0:
            bottlenecks.append({
                "type": "slowest_operation",
                "operation": slowest_op.operation_name,
                "duration": round(slowest_op.duration, 3),
                "percentage_of_total": round((slowest_op.duration / self.total_duration) * 100, 1) if self.total_duration else 0
            })
        
        # Find operations that took longer than their thresholds
        thresholds = {
            "document_download": 10.0,
            "document_chunking": 5.0,
            "vector_store_creation": 15.0,
            "answer_generation": 20.0
        }
        
        for op in self.operations:
            if op.duration and op.operation_name in thresholds:
                threshold = thresholds[op.operation_name]
                if op.duration > threshold:
                    bottlenecks.append({
                        "type": "threshold_exceeded",
                        "operation": op.operation_name,
                        "duration": round(op.duration, 3),
                        "threshold": threshold,
                        "excess": round(op.duration - threshold, 3)
                    })
        
        # Check for memory usage spikes
        for op in self.operations:
            resource_usage = op.get_resource_usage()
            memory_delta = resource_usage.get("memory_delta")
            if memory_delta and memory_delta > 100:  # More than 100MB increase
                bottlenecks.append({
                    "type": "memory_spike",
                    "operation": op.operation_name,
                    "memory_increase_mb": round(memory_delta, 2)
                })
        
        return bottlenecks

class PerformanceMonitor:
    """
    Comprehensive performance monitoring system for tracking request durations,
    operation timings, and identifying bottlenecks.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._active_requests: Dict[str, RequestMetrics] = {}
        self._completed_requests: List[RequestMetrics] = []
        self._lock = threading.Lock()
        self._max_completed_requests = 100  # Keep last 100 requests for analysis
        
        # Performance thresholds for warnings (in seconds)
        self.thresholds = {
            "document_download": 10.0,
            "document_chunking": 5.0,
            "vector_store_creation": 15.0,
            "answer_generation": 20.0,
            "total_request": 30.0
        }
    
    def start_request(self, request_id: str, metadata: Optional[Dict[str, Any]] = None) -> RequestMetrics:
        """Start tracking a new request"""
        with self._lock:
            request_metrics = RequestMetrics(
                request_id=request_id,
                start_time=time.perf_counter(),
                metadata=metadata or {}
            )
            self._active_requests[request_id] = request_metrics
            
            self.logger.info(f"[Performance] Started tracking request {request_id}")
            return request_metrics
    
    def finish_request(self, request_id: str) -> Optional[RequestMetrics]:
        """Finish tracking a request and log performance summary"""
        with self._lock:
            request_metrics = self._active_requests.pop(request_id, None)
            if not request_metrics:
                self.logger.warning(f"[Performance] Request {request_id} not found in active requests")
                return None
            
            request_metrics.finish()
            self._completed_requests.append(request_metrics)
            
            # Keep only the last N requests to prevent memory growth
            if len(self._completed_requests) > self._max_completed_requests:
                self._completed_requests = self._completed_requests[-self._max_completed_requests:]
            
            # Log performance summary
            self._log_request_summary(request_metrics)
            return request_metrics
    
    def _log_request_summary(self, request_metrics: RequestMetrics):
        """Log a comprehensive performance summary for a request"""
        summary = request_metrics.get_summary()
        total_duration = summary["total_duration"]
        
        # Determine log level based on performance
        if total_duration > self.thresholds.get("total_request", 30.0):
            log_level = logging.WARNING
            status = "SLOW"
        elif total_duration > self.thresholds.get("total_request", 30.0) * 0.7:
            log_level = logging.INFO
            status = "ACCEPTABLE"
        else:
            log_level = logging.INFO
            status = "FAST"
        
        self.logger.log(
            log_level,
            f"[Performance] Request {request_metrics.request_id} completed in {total_duration}s [{status}]"
        )
        
        # Log system resource usage summary
        system_metrics = summary.get("system_metrics", {})
        if system_metrics.get("memory_delta"):
            memory_delta = system_metrics["memory_delta"]
            if abs(memory_delta) > 50:  # Log significant memory changes
                self.logger.info(
                    f"[Performance] Memory usage change: {memory_delta:+.1f}MB"
                )
        
        # Log detailed operation breakdown
        self.logger.info(f"[Performance] Operation breakdown for {request_metrics.request_id}:")
        for op in summary["operations"]:
            duration = op["duration"]
            op_name = op["name"]
            threshold = self.thresholds.get(op_name, 5.0)
            
            if duration > threshold:
                self.logger.warning(
                    f"[Performance]   🐌 {op_name}: {duration}s (SLOW - threshold: {threshold}s)"
                )
            elif duration > threshold * 0.7:
                self.logger.info(
                    f"[Performance]   ⚠️  {op_name}: {duration}s (acceptable)"
                )
            else:
                self.logger.info(
                    f"[Performance]   ✅ {op_name}: {duration}s (fast)"
                )
            
            # Log resource usage for slow operations
            if duration > threshold:
                resource_usage = op.get("resource_usage", {})
                memory_delta = resource_usage.get("memory_delta")
                if memory_delta and abs(memory_delta) > 10:
                    self.logger.debug(
                        f"[Performance]     💾 Memory delta: {memory_delta:+.1f}MB"
                    )
            
            # Log any errors
            if not op["success"] and op["error"]:
                self.logger.error(f"[Performance]     ❌ Error: {op['error']}")
            
            # Log metadata if present
            if op["metadata"]:
                self.logger.debug(f"[Performance]     📊 Metadata: {op['metadata']}")
        
        # Identify and log bottlenecks
        bottlenecks = request_metrics.identify_bottlenecks()
        if bottlenecks:
            self.logger.warning(f"[Performance] Bottlenecks identified for {request_metrics.request_id}:")
            for bottleneck in bottlenecks:
                if bottleneck["type"] == "slowest_operation":
                    self.logger.warning(
                        f"[Performance]   🎯 Slowest: {bottleneck['operation']} "
                        f"({bottleneck['duration']}s, {bottleneck['percentage_of_total']}% of total)"
                    )
                elif bottleneck["type"] == "threshold_exceeded":
                    self.logger.warning(
                        f"[Performance]   ⏰ Threshold exceeded: {bottleneck['operation']} "
                        f"({bottleneck['duration']}s, {bottleneck['excess']}s over threshold)"
                    )
                elif bottleneck["type"] == "memory_spike":
                    self.logger.warning(
                        f"[Performance]   💾 Memory spike: {bottleneck['operation']} "
                        f"(+{bottleneck['memory_increase_mb']}MB)"
                    )
    
    @asynccontextmanager
    async def track_operation(self, request_id: str, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """Context manager for tracking individual operations within a request"""
        operation = PerformanceMetric(
            operation_name=operation_name,
            start_time=time.perf_counter(),
            metadata=metadata or {}
        )
        
        self.logger.debug(f"[Performance] Starting operation '{operation_name}' for request {request_id}")
        
        # Log detailed start information for debugging
        if operation.cpu_usage_start is not None and operation.memory_usage_start is not None:
            self.logger.debug(
                f"[Performance] Initial resources - CPU: {operation.cpu_usage_start:.1f}%, "
                f"Memory: {operation.memory_usage_start:.1f}MB"
            )
        
        try:
            yield operation
            operation.finish(success=True)
            
            # Enhanced completion logging with resource usage
            duration_msg = f"[Performance] Completed operation '{operation_name}' in {operation.duration:.3f}s"
            
            # Add resource usage information for debugging
            resource_usage = operation.get_resource_usage()
            if resource_usage.get("memory_delta"):
                memory_delta = resource_usage["memory_delta"]
                if abs(memory_delta) > 5:  # Log memory changes > 5MB
                    duration_msg += f" (Memory: {memory_delta:+.1f}MB)"
            
            self.logger.debug(duration_msg)
            
            # Log warning for unexpectedly slow operations
            threshold = self.thresholds.get(operation_name, 5.0)
            if operation.duration > threshold:
                self.logger.warning(
                    f"[Performance] ⚠️ Operation '{operation_name}' exceeded threshold: "
                    f"{operation.duration:.3f}s > {threshold}s"
                )
                
        except Exception as e:
            operation.finish(success=False, error_message=str(e))
            self.logger.error(
                f"[Performance] Failed operation '{operation_name}' after {operation.duration:.3f}s: {str(e)}"
            )
            raise
        finally:
            # Add operation to request metrics
            with self._lock:
                if request_id in self._active_requests:
                    self._active_requests[request_id].add_operation(operation)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        with self._lock:
            if not self._completed_requests:
                return {
                    "total_requests": 0,
                    "average_duration": 0,
                    "fastest_request": 0,
                    "slowest_request": 0,
                    "operation_stats": {},
                    "bottleneck_analysis": {},
                    "performance_trends": {}
                }
            
            durations = [req.total_duration for req in self._completed_requests if req.total_duration]
            
            # Calculate operation statistics
            operation_stats = {}
            bottleneck_counts = {}
            
            for request in self._completed_requests:
                # Analyze bottlenecks
                bottlenecks = request.identify_bottlenecks()
                for bottleneck in bottlenecks:
                    key = f"{bottleneck['type']}_{bottleneck.get('operation', 'unknown')}"
                    bottleneck_counts[key] = bottleneck_counts.get(key, 0) + 1
                
                # Process operations
                for op in request.operations:
                    if op.operation_name not in operation_stats:
                        operation_stats[op.operation_name] = {
                            "count": 0,
                            "total_duration": 0,
                            "failures": 0,
                            "durations": [],
                            "memory_deltas": [],
                            "threshold_violations": 0
                        }
                    
                    stats = operation_stats[op.operation_name]
                    stats["count"] += 1
                    if op.duration:
                        stats["total_duration"] += op.duration
                        stats["durations"].append(op.duration)
                        
                        # Check threshold violations
                        threshold = self.thresholds.get(op.operation_name, 5.0)
                        if op.duration > threshold:
                            stats["threshold_violations"] += 1
                    
                    if not op.success:
                        stats["failures"] += 1
                    
                    # Track memory usage
                    resource_usage = op.get_resource_usage()
                    memory_delta = resource_usage.get("memory_delta")
                    if memory_delta is not None:
                        stats["memory_deltas"].append(memory_delta)
            
            # Calculate averages and percentiles for operations
            for op_name, stats in operation_stats.items():
                if stats["durations"]:
                    stats["average_duration"] = stats["total_duration"] / len(stats["durations"])
                    stats["min_duration"] = min(stats["durations"])
                    stats["max_duration"] = max(stats["durations"])
                    
                    # Calculate percentiles
                    sorted_durations = sorted(stats["durations"])
                    n = len(sorted_durations)
                    stats["p50"] = sorted_durations[n // 2] if n > 0 else 0
                    stats["p95"] = sorted_durations[int(n * 0.95)] if n > 0 else 0
                    stats["p99"] = sorted_durations[int(n * 0.99)] if n > 0 else 0
                    
                    # Calculate threshold violation rate
                    stats["threshold_violation_rate"] = (
                        stats["threshold_violations"] / stats["count"] * 100
                        if stats["count"] > 0 else 0
                    )
                
                # Calculate memory statistics
                if stats["memory_deltas"]:
                    stats["average_memory_delta"] = sum(stats["memory_deltas"]) / len(stats["memory_deltas"])
                    stats["max_memory_delta"] = max(stats["memory_deltas"])
                    stats["min_memory_delta"] = min(stats["memory_deltas"])
                
                # Remove raw data to keep response size manageable
                del stats["durations"]
                del stats["memory_deltas"]
            
            # Performance trends (last 10 requests vs previous)
            performance_trends = {}
            if len(self._completed_requests) >= 10:
                recent_requests = self._completed_requests[-10:]
                older_requests = self._completed_requests[-20:-10] if len(self._completed_requests) >= 20 else []
                
                if older_requests:
                    recent_avg = sum(req.total_duration for req in recent_requests if req.total_duration) / len(recent_requests)
                    older_avg = sum(req.total_duration for req in older_requests if req.total_duration) / len(older_requests)
                    
                    performance_trends = {
                        "recent_average": round(recent_avg, 3),
                        "previous_average": round(older_avg, 3),
                        "improvement_percentage": round(((older_avg - recent_avg) / older_avg) * 100, 1) if older_avg > 0 else 0,
                        "trend": "improving" if recent_avg < older_avg else "degrading"
                    }
            
            return {
                "total_requests": len(self._completed_requests),
                "active_requests": len(self._active_requests),
                "average_duration": round(sum(durations) / len(durations), 3) if durations else 0,
                "fastest_request": round(min(durations), 3) if durations else 0,
                "slowest_request": round(max(durations), 3) if durations else 0,
                "operation_stats": operation_stats,
                "bottleneck_analysis": {
                    "common_bottlenecks": bottleneck_counts,
                    "total_bottleneck_instances": sum(bottleneck_counts.values())
                },
                "performance_trends": performance_trends,
                "thresholds": self.thresholds
            }

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def timed_operation(operation_name: str, log_level: int = logging.INFO):
    """
    Decorator for timing function/method execution with automatic logging.
    
    Args:
        operation_name: Name of the operation for logging
        log_level: Logging level for the timing information
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            logger = logging.getLogger(func.__module__)
            
            try:
                logger.log(log_level, f"[Timer] Starting {operation_name}")
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start_time
                logger.log(log_level, f"[Timer] Completed {operation_name} in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                logger.error(f"[Timer] Failed {operation_name} after {duration:.3f}s: {str(e)}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            logger = logging.getLogger(func.__module__)
            
            try:
                logger.log(log_level, f"[Timer] Starting {operation_name}")
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start_time
                logger.log(log_level, f"[Timer] Completed {operation_name} in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                logger.error(f"[Timer] Failed {operation_name} after {duration:.3f}s: {str(e)}")
                raise
        
        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def setup_performance_logging():
    """
    Configure logging for performance monitoring with appropriate formatters and handlers.
    """
    # Create performance-specific logger
    perf_logger = logging.getLogger("performance")
    perf_logger.setLevel(logging.DEBUG)
    
    # Create formatter for performance logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler if not already present
    if not perf_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        perf_logger.addHandler(console_handler)
    
    # Set up root logger for general application logging
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    logging.getLogger(__name__).info("[Performance] Performance monitoring logging configured")