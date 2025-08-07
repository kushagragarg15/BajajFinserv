#!/usr/bin/env python3
"""
Performance Validation Test Suite

This script validates the performance improvements implemented in the response-time-optimization spec.
It tests response times, functionality correctness, and concurrent request handling.

Requirements tested:
- 1.1: Response time under 5 seconds maximum
- 1.2: Consistent response times across multiple requests  
- 1.3: Accuracy above 0% due to acceptable response times
"""

import asyncio
import aiohttp
import time
import json
import statistics
import sys
import os
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Container for individual test results"""
    test_name: str
    success: bool
    response_time: float
    error_message: str = ""
    response_data: Dict[Any, Any] = None

@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    median_response_time: float
    std_deviation: float
    success_rate: float
    total_requests: int
    successful_requests: int
    failed_requests: int

class PerformanceValidator:
    """Main class for validating performance improvements"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key or "Bearer 04882ff997f04a7548a2640b6ac4ca31bb61a48594229f92000cc82b4e6dbd3d"
        self.test_results: List[TestResult] = []
        
        # Test data - using a publicly accessible PDF for testing
        self.test_document_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        self.test_questions = [
            "What is the main topic of this document?",
            "What are the key points mentioned?",
            "Can you summarize the content?",
            "What is the purpose of this document?",
            "Are there any specific recommendations?"
        ]
        
        # Performance targets based on requirements
        self.target_response_time = 5.0  # seconds (Requirement 1.1)
        self.acceptable_success_rate = 0.95  # 95% success rate
        
    async def check_server_health(self) -> bool:
        """Check if the server is running and healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health", timeout=10) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        logger.info(f"Server health check: {health_data.get('overall_status', 'unknown')}")
                        return health_data.get('overall_status') == 'healthy'
                    else:
                        logger.error(f"Health check failed with status: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    async def make_api_request(self, session: aiohttp.ClientSession, request_data: Dict) -> Tuple[float, Dict]:
        """Make a single API request and measure response time"""
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}
        
        start_time = time.perf_counter()
        try:
            async with session.post(
                f"{self.base_url}/api/v1/hackrx/run",
                json=request_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)  # 30 second timeout
            ) as response:
                response_time = time.perf_counter() - start_time
                
                if response.status == 200:
                    response_data = await response.json()
                    return response_time, response_data
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            response_time = time.perf_counter() - start_time
            raise Exception(f"Request failed after {response_time:.3f}s: {str(e)}")
    
    async def test_single_request_performance(self) -> TestResult:
        """Test single request performance (Requirement 1.1)"""
        logger.info("Testing single request performance...")
        
        request_data = {
            "documents": self.test_document_url,
            "questions": self.test_questions[:3]  # Use 3 questions for single request test
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                response_time, response_data = await self.make_api_request(session, request_data)
                
                # Validate response structure
                if "answers" not in response_data:
                    raise Exception("Response missing 'answers' field")
                
                if len(response_data["answers"]) != len(request_data["questions"]):
                    raise Exception(f"Expected {len(request_data['questions'])} answers, got {len(response_data['answers'])}")
                
                # Check if response time meets target
                meets_target = response_time <= self.target_response_time
                
                logger.info(f"Single request completed in {response_time:.3f}s (target: {self.target_response_time}s)")
                
                return TestResult(
                    test_name="single_request_performance",
                    success=meets_target,
                    response_time=response_time,
                    response_data=response_data,
                    error_message="" if meets_target else f"Response time {response_time:.3f}s exceeds target {self.target_response_time}s"
                )
                
        except Exception as e:
            logger.error(f"Single request test failed: {str(e)}")
            return TestResult(
                test_name="single_request_performance",
                success=False,
                response_time=0.0,
                error_message=str(e)
            )
    
    async def test_multiple_requests_consistency(self, num_requests: int = 5) -> List[TestResult]:
        """Test consistency across multiple requests (Requirement 1.2)"""
        logger.info(f"Testing consistency across {num_requests} requests...")
        
        request_data = {
            "documents": self.test_document_url,
            "questions": self.test_questions[:2]  # Use 2 questions for consistency test
        }
        
        results = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(num_requests):
                try:
                    logger.info(f"Making request {i+1}/{num_requests}")
                    response_time, response_data = await self.make_api_request(session, request_data)
                    
                    # Validate response
                    success = (
                        "answers" in response_data and
                        len(response_data["answers"]) == len(request_data["questions"]) and
                        response_time <= self.target_response_time
                    )
                    
                    results.append(TestResult(
                        test_name=f"consistency_request_{i+1}",
                        success=success,
                        response_time=response_time,
                        response_data=response_data,
                        error_message="" if success else f"Request {i+1} failed validation"
                    ))
                    
                    logger.info(f"Request {i+1} completed in {response_time:.3f}s")
                    
                    # Small delay between requests to avoid overwhelming the server
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Request {i+1} failed: {str(e)}")
                    results.append(TestResult(
                        test_name=f"consistency_request_{i+1}",
                        success=False,
                        response_time=0.0,
                        error_message=str(e)
                    ))
        
        return results
    
    async def test_concurrent_requests(self, num_concurrent: int = 3) -> List[TestResult]:
        """Test concurrent request handling (Requirement 1.3 - scalability)"""
        logger.info(f"Testing {num_concurrent} concurrent requests...")
        
        request_data = {
            "documents": self.test_document_url,
            "questions": self.test_questions[:2]  # Use 2 questions for concurrent test
        }
        
        async def make_concurrent_request(session: aiohttp.ClientSession, request_id: int) -> TestResult:
            try:
                logger.info(f"Starting concurrent request {request_id}")
                response_time, response_data = await self.make_api_request(session, request_data)
                
                success = (
                    "answers" in response_data and
                    len(response_data["answers"]) == len(request_data["questions"]) and
                    response_time <= self.target_response_time * 2  # Allow 2x target for concurrent requests
                )
                
                logger.info(f"Concurrent request {request_id} completed in {response_time:.3f}s")
                
                return TestResult(
                    test_name=f"concurrent_request_{request_id}",
                    success=success,
                    response_time=response_time,
                    response_data=response_data,
                    error_message="" if success else f"Concurrent request {request_id} failed validation"
                )
                
            except Exception as e:
                logger.error(f"Concurrent request {request_id} failed: {str(e)}")
                return TestResult(
                    test_name=f"concurrent_request_{request_id}",
                    success=False,
                    response_time=0.0,
                    error_message=str(e)
                )
        
        # Execute concurrent requests
        async with aiohttp.ClientSession() as session:
            tasks = [make_concurrent_request(session, i+1) for i in range(num_concurrent)]
            results = await asyncio.gather(*tasks)
        
        return list(results)
    
    async def test_functionality_correctness(self) -> TestResult:
        """Test that the async implementation maintains functionality correctness"""
        logger.info("Testing functionality correctness...")
        
        request_data = {
            "documents": self.test_document_url,
            "questions": ["What type of document is this?", "What is the main content?"]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                response_time, response_data = await self.make_api_request(session, request_data)
                
                # Validate response structure and content
                if "answers" not in response_data:
                    raise Exception("Response missing 'answers' field")
                
                answers = response_data["answers"]
                if len(answers) != len(request_data["questions"]):
                    raise Exception(f"Expected {len(request_data['questions'])} answers, got {len(answers)}")
                
                # Check that answers are not empty and contain meaningful content
                for i, answer in enumerate(answers):
                    if not answer or len(answer.strip()) < 10:
                        raise Exception(f"Answer {i+1} is too short or empty: '{answer}'")
                
                logger.info("Functionality correctness test passed")
                logger.info(f"Sample answers: {answers[:1]}")  # Log first answer for verification
                
                return TestResult(
                    test_name="functionality_correctness",
                    success=True,
                    response_time=response_time,
                    response_data=response_data
                )
                
        except Exception as e:
            logger.error(f"Functionality correctness test failed: {str(e)}")
            return TestResult(
                test_name="functionality_correctness",
                success=False,
                response_time=0.0,
                error_message=str(e)
            )
    
    def calculate_performance_metrics(self, results: List[TestResult]) -> PerformanceMetrics:
        """Calculate performance metrics from test results"""
        successful_results = [r for r in results if r.success and r.response_time > 0]
        response_times = [r.response_time for r in successful_results]
        
        if not response_times:
            return PerformanceMetrics(
                avg_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                median_response_time=0.0,
                std_deviation=0.0,
                success_rate=0.0,
                total_requests=len(results),
                successful_requests=0,
                failed_requests=len(results)
            )
        
        return PerformanceMetrics(
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            median_response_time=statistics.median(response_times),
            std_deviation=statistics.stdev(response_times) if len(response_times) > 1 else 0.0,
            success_rate=len(successful_results) / len(results),
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(results) - len(successful_results)
        )
    
    def print_performance_report(self, metrics: PerformanceMetrics, test_category: str):
        """Print detailed performance report"""
        print(f"\n{'='*60}")
        print(f"PERFORMANCE REPORT: {test_category.upper()}")
        print(f"{'='*60}")
        print(f"Total Requests:      {metrics.total_requests}")
        print(f"Successful:          {metrics.successful_requests}")
        print(f"Failed:              {metrics.failed_requests}")
        print(f"Success Rate:        {metrics.success_rate:.1%}")
        print(f"")
        print(f"RESPONSE TIME METRICS:")
        print(f"Average:             {metrics.avg_response_time:.3f}s")
        print(f"Minimum:             {metrics.min_response_time:.3f}s")
        print(f"Maximum:             {metrics.max_response_time:.3f}s")
        print(f"Median:              {metrics.median_response_time:.3f}s")
        print(f"Std Deviation:       {metrics.std_deviation:.3f}s")
        print(f"")
        print(f"TARGET ANALYSIS:")
        print(f"Target Response Time: {self.target_response_time:.1f}s")
        target_met = metrics.avg_response_time <= self.target_response_time
        print(f"Target Met:          {'✅ YES' if target_met else '❌ NO'}")
        if not target_met:
            improvement_needed = metrics.avg_response_time - self.target_response_time
            print(f"Improvement Needed:  {improvement_needed:.3f}s")
        print(f"{'='*60}")
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive performance validation suite"""
        print("🚀 Starting Comprehensive Performance Validation")
        print(f"Target Response Time: {self.target_response_time}s")
        print(f"API Endpoint: {self.base_url}")
        print("="*60)
        
        # Check server health first
        print("1. Checking server health...")
        if not await self.check_server_health():
            print("❌ Server health check failed. Please ensure the server is running.")
            return {"status": "failed", "error": "Server not healthy"}
        
        print("✅ Server is healthy")
        
        validation_results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_response_time": self.target_response_time,
            "tests": {}
        }
        
        # Test 1: Single Request Performance (Requirement 1.1)
        print("\n2. Testing single request performance...")
        single_result = await self.test_single_request_performance()
        self.test_results.append(single_result)
        validation_results["tests"]["single_request"] = {
            "success": single_result.success,
            "response_time": single_result.response_time,
            "error": single_result.error_message
        }
        
        if single_result.success:
            print(f"✅ Single request test passed ({single_result.response_time:.3f}s)")
        else:
            print(f"❌ Single request test failed: {single_result.error_message}")
        
        # Test 2: Multiple Requests Consistency (Requirement 1.2)
        print("\n3. Testing multiple requests consistency...")
        consistency_results = await self.test_multiple_requests_consistency(5)
        self.test_results.extend(consistency_results)
        
        consistency_metrics = self.calculate_performance_metrics(consistency_results)
        self.print_performance_report(consistency_metrics, "Consistency Test")
        
        validation_results["tests"]["consistency"] = {
            "metrics": {
                "avg_response_time": consistency_metrics.avg_response_time,
                "success_rate": consistency_metrics.success_rate,
                "total_requests": consistency_metrics.total_requests
            },
            "target_met": consistency_metrics.avg_response_time <= self.target_response_time
        }
        
        # Test 3: Concurrent Requests (Requirement 1.3)
        print("\n4. Testing concurrent request handling...")
        concurrent_results = await self.test_concurrent_requests(3)
        self.test_results.extend(concurrent_results)
        
        concurrent_metrics = self.calculate_performance_metrics(concurrent_results)
        self.print_performance_report(concurrent_metrics, "Concurrent Test")
        
        validation_results["tests"]["concurrent"] = {
            "metrics": {
                "avg_response_time": concurrent_metrics.avg_response_time,
                "success_rate": concurrent_metrics.success_rate,
                "total_requests": concurrent_metrics.total_requests
            },
            "target_met": concurrent_metrics.avg_response_time <= (self.target_response_time * 2)
        }
        
        # Test 4: Functionality Correctness
        print("\n5. Testing functionality correctness...")
        functionality_result = await self.test_functionality_correctness()
        self.test_results.append(functionality_result)
        validation_results["tests"]["functionality"] = {
            "success": functionality_result.success,
            "response_time": functionality_result.response_time,
            "error": functionality_result.error_message
        }
        
        if functionality_result.success:
            print(f"✅ Functionality test passed ({functionality_result.response_time:.3f}s)")
        else:
            print(f"❌ Functionality test failed: {functionality_result.error_message}")
        
        # Overall Assessment
        print("\n" + "="*60)
        print("OVERALL VALIDATION RESULTS")
        print("="*60)
        
        all_metrics = self.calculate_performance_metrics(self.test_results)
        overall_success = (
            all_metrics.success_rate >= self.acceptable_success_rate and
            all_metrics.avg_response_time <= self.target_response_time
        )
        
        validation_results["overall"] = {
            "success": overall_success,
            "metrics": {
                "avg_response_time": all_metrics.avg_response_time,
                "success_rate": all_metrics.success_rate,
                "total_tests": all_metrics.total_requests
            }
        }
        
        print(f"Overall Success Rate: {all_metrics.success_rate:.1%}")
        print(f"Overall Avg Response Time: {all_metrics.avg_response_time:.3f}s")
        print(f"Target Achievement: {'✅ PASSED' if overall_success else '❌ FAILED'}")
        
        if overall_success:
            print("\n🎉 VALIDATION SUCCESSFUL!")
            print("The response-time optimization implementation meets all requirements:")
            print("✅ Response times are under 5 seconds")
            print("✅ Functionality works correctly with async implementation")
            print("✅ System handles concurrent requests properly")
        else:
            print("\n⚠️ VALIDATION NEEDS ATTENTION")
            print("Some requirements are not fully met. Review the detailed results above.")
        
        return validation_results

async def main():
    """Main function to run performance validation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance Validation Test Suite")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API server")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--output", help="Output file for results (JSON format)")
    
    args = parser.parse_args()
    
    validator = PerformanceValidator(base_url=args.url, api_key=args.api_key)
    
    try:
        results = await validator.run_comprehensive_validation()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {args.output}")
        
        # Exit with appropriate code
        sys.exit(0 if results.get("overall", {}).get("success", False) else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())