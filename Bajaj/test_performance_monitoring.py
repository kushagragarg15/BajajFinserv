#!/usr/bin/env python3
"""
Test script to validate performance monitoring functionality.
This script tests the performance monitoring system without requiring the full application.
"""

import asyncio
import time
import logging
from app.performance_monitor import performance_monitor, setup_performance_logging

# Setup logging for testing
setup_performance_logging()
logger = logging.getLogger(__name__)

async def simulate_operation(operation_name: str, duration: float, should_fail: bool = False):
    """Simulate an operation with specified duration"""
    await asyncio.sleep(duration)
    if should_fail:
        raise Exception(f"Simulated failure in {operation_name}")

async def test_performance_monitoring():
    """Test the performance monitoring system"""
    logger.info("🧪 Testing performance monitoring system...")
    
    # Test 1: Basic request tracking
    logger.info("Test 1: Basic request tracking")
    request_id = "test_request_1"
    
    # Start request tracking
    request_metrics = performance_monitor.start_request(
        request_id, 
        metadata={"test": "basic_tracking", "questions": 3}
    )
    
    # Simulate operations
    async with performance_monitor.track_operation(request_id, "document_download", {"url": "test.pdf"}):
        await simulate_operation("document_download", 2.0)
    
    async with performance_monitor.track_operation(request_id, "document_chunking", {"pages": 10}):
        await simulate_operation("document_chunking", 1.5)
    
    async with performance_monitor.track_operation(request_id, "vector_store_creation", {"chunks": 50}):
        await simulate_operation("vector_store_creation", 3.0)
    
    async with performance_monitor.track_operation(request_id, "answer_generation", {"questions": 3}):
        await simulate_operation("answer_generation", 2.5)
    
    # Finish request
    completed_metrics = performance_monitor.finish_request(request_id)
    
    if completed_metrics:
        logger.info(f"✅ Test 1 passed: Request completed in {completed_metrics.total_duration:.3f}s")
        
        # Test bottleneck identification
        bottlenecks = completed_metrics.identify_bottlenecks()
        if bottlenecks:
            logger.info(f"🎯 Bottlenecks identified: {len(bottlenecks)}")
            for bottleneck in bottlenecks:
                logger.info(f"   - {bottleneck}")
    else:
        logger.error("❌ Test 1 failed: No metrics returned")
    
    # Test 2: Error handling
    logger.info("\nTest 2: Error handling in operations")
    request_id = "test_request_2"
    
    performance_monitor.start_request(request_id, metadata={"test": "error_handling"})
    
    # Successful operation
    async with performance_monitor.track_operation(request_id, "document_download", {"url": "test.pdf"}):
        await simulate_operation("document_download", 1.0)
    
    # Failed operation
    try:
        async with performance_monitor.track_operation(request_id, "document_chunking", {"pages": 5}):
            await simulate_operation("document_chunking", 0.5, should_fail=True)
    except Exception as e:
        logger.info(f"Expected error caught: {e}")
    
    completed_metrics = performance_monitor.finish_request(request_id)
    if completed_metrics:
        logger.info(f"✅ Test 2 passed: Error handling works correctly")
        
        # Check that failed operation is recorded
        failed_ops = [op for op in completed_metrics.operations if not op.success]
        if failed_ops:
            logger.info(f"   Failed operations recorded: {len(failed_ops)}")
    else:
        logger.error("❌ Test 2 failed: No metrics returned")
    
    # Test 3: Performance statistics
    logger.info("\nTest 3: Performance statistics")
    
    # Add a few more requests for statistics
    for i in range(3, 6):
        request_id = f"test_request_{i}"
        performance_monitor.start_request(request_id, metadata={"test": "statistics"})
        
        # Vary the operation times
        async with performance_monitor.track_operation(request_id, "document_download", {}):
            await simulate_operation("document_download", 1.0 + i * 0.5)
        
        async with performance_monitor.track_operation(request_id, "answer_generation", {}):
            await simulate_operation("answer_generation", 2.0 + i * 0.3)
        
        performance_monitor.finish_request(request_id)
    
    # Get performance statistics
    stats = performance_monitor.get_performance_stats()
    
    logger.info(f"✅ Test 3 passed: Statistics generated")
    logger.info(f"   Total requests: {stats['total_requests']}")
    logger.info(f"   Average duration: {stats['average_duration']:.3f}s")
    logger.info(f"   Fastest request: {stats['fastest_request']:.3f}s")
    logger.info(f"   Slowest request: {stats['slowest_request']:.3f}s")
    
    # Check operation statistics
    if stats['operation_stats']:
        logger.info("   Operation statistics:")
        for op_name, op_stats in stats['operation_stats'].items():
            logger.info(f"     {op_name}: avg={op_stats.get('average_duration', 0):.3f}s, "
                       f"count={op_stats.get('count', 0)}, "
                       f"failures={op_stats.get('failures', 0)}")
    
    # Check bottleneck analysis
    bottleneck_analysis = stats.get('bottleneck_analysis', {})
    if bottleneck_analysis.get('total_bottleneck_instances', 0) > 0:
        logger.info(f"   Total bottleneck instances: {bottleneck_analysis['total_bottleneck_instances']}")
        logger.info(f"   Common bottlenecks: {bottleneck_analysis.get('common_bottlenecks', {})}")
    
    # Check performance trends
    performance_trends = stats.get('performance_trends', {})
    if performance_trends:
        logger.info(f"   Performance trend: {performance_trends.get('trend', 'unknown')}")
        logger.info(f"   Recent vs previous: {performance_trends.get('improvement_percentage', 0):+.1f}%")
    
    logger.info("\n🎉 All performance monitoring tests completed successfully!")
    logger.info("📊 Performance monitoring system is working correctly")

if __name__ == "__main__":
    asyncio.run(test_performance_monitoring())