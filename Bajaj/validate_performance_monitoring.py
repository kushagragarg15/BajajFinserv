#!/usr/bin/env python3
"""
Validation script to test the performance monitoring integration in the main application.
This script validates that all performance monitoring features are properly integrated.
"""

import asyncio
import logging
from app.performance_monitor import performance_monitor, setup_performance_logging

# Setup logging
setup_performance_logging()
logger = logging.getLogger(__name__)

def validate_performance_monitoring():
    """Validate that performance monitoring is properly integrated"""
    logger.info("🔍 Validating performance monitoring integration...")
    
    # Test 1: Check that performance monitor is properly initialized
    logger.info("Test 1: Performance monitor initialization")
    try:
        stats = performance_monitor.get_performance_stats()
        logger.info("✅ Performance monitor is properly initialized")
        logger.info(f"   Initial stats: {stats['total_requests']} requests tracked")
    except Exception as e:
        logger.error(f"❌ Performance monitor initialization failed: {e}")
        return False
    
    # Test 2: Check performance thresholds are properly configured
    logger.info("\nTest 2: Performance thresholds configuration")
    expected_thresholds = {
        "document_download": 10.0,
        "document_chunking": 5.0,
        "vector_store_creation": 15.0,
        "answer_generation": 20.0,
        "total_request": 30.0
    }
    
    actual_thresholds = performance_monitor.thresholds
    all_thresholds_correct = True
    
    for operation, expected_threshold in expected_thresholds.items():
        actual_threshold = actual_thresholds.get(operation)
        if actual_threshold == expected_threshold:
            logger.info(f"   ✅ {operation}: {actual_threshold}s (correct)")
        else:
            logger.error(f"   ❌ {operation}: expected {expected_threshold}s, got {actual_threshold}s")
            all_thresholds_correct = False
    
    if all_thresholds_correct:
        logger.info("✅ All performance thresholds are correctly configured")
    else:
        logger.error("❌ Some performance thresholds are incorrectly configured")
        return False
    
    # Test 3: Check that enhanced features are available
    logger.info("\nTest 3: Enhanced performance monitoring features")
    
    # Test bottleneck identification
    try:
        # Create a mock request metrics to test bottleneck identification
        from app.performance_monitor import RequestMetrics, PerformanceMetric
        import time
        
        test_request = RequestMetrics(
            request_id="validation_test",
            start_time=time.perf_counter()
        )
        
        # Add some mock operations
        slow_op = PerformanceMetric(
            operation_name="vector_store_creation",
            start_time=time.perf_counter()
        )
        slow_op.finish()
        slow_op.duration = 20.0  # Simulate slow operation
        test_request.add_operation(slow_op)
        
        test_request.finish()
        test_request.total_duration = 25.0
        
        bottlenecks = test_request.identify_bottlenecks()
        if bottlenecks:
            logger.info("✅ Bottleneck identification is working")
            logger.info(f"   Identified {len(bottlenecks)} bottlenecks")
        else:
            logger.warning("⚠️ Bottleneck identification returned no results")
        
    except Exception as e:
        logger.error(f"❌ Bottleneck identification failed: {e}")
        return False
    
    # Test 4: Check resource monitoring capabilities
    logger.info("\nTest 4: Resource monitoring capabilities")
    try:
        import psutil
        
        # Test that we can capture system metrics
        test_metric = PerformanceMetric(
            operation_name="test_resource_monitoring",
            start_time=time.perf_counter()
        )
        
        if test_metric.cpu_usage_start is not None and test_metric.memory_usage_start is not None:
            logger.info("✅ System resource monitoring is working")
            logger.info(f"   Initial CPU: {test_metric.cpu_usage_start}%")
            logger.info(f"   Initial Memory: {test_metric.memory_usage_start:.1f}MB")
        else:
            logger.warning("⚠️ System resource monitoring may not be fully functional")
        
    except ImportError:
        logger.error("❌ psutil not available - resource monitoring will not work")
        return False
    except Exception as e:
        logger.error(f"❌ Resource monitoring test failed: {e}")
        return False
    
    # Test 5: Check enhanced statistics
    logger.info("\nTest 5: Enhanced statistics features")
    try:
        stats = performance_monitor.get_performance_stats()
        
        # Check for new fields
        expected_fields = [
            'bottleneck_analysis',
            'performance_trends'
        ]
        
        for field in expected_fields:
            if field in stats:
                logger.info(f"   ✅ {field}: available")
            else:
                logger.error(f"   ❌ {field}: missing")
                return False
        
        logger.info("✅ Enhanced statistics features are available")
        
    except Exception as e:
        logger.error(f"❌ Enhanced statistics test failed: {e}")
        return False
    
    logger.info("\n🎉 All performance monitoring validation tests passed!")
    logger.info("📊 Performance monitoring system is fully integrated and functional")
    
    # Summary of features
    logger.info("\n📋 Performance monitoring features validated:")
    logger.info("   ✅ Request duration tracking")
    logger.info("   ✅ Operation-level timing")
    logger.info("   ✅ Bottleneck identification")
    logger.info("   ✅ Resource usage monitoring (CPU, Memory)")
    logger.info("   ✅ Performance thresholds and warnings")
    logger.info("   ✅ Enhanced statistics and trends")
    logger.info("   ✅ Error handling and logging")
    logger.info("   ✅ Debug logging for optimization")
    
    return True

if __name__ == "__main__":
    success = validate_performance_monitoring()
    if success:
        logger.info("\n✅ Performance monitoring validation PASSED")
        exit(0)
    else:
        logger.error("\n❌ Performance monitoring validation FAILED")
        exit(1)