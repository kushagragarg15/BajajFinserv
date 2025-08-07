#!/usr/bin/env python3
"""
Test script for comprehensive error handling and timeout functionality.
This script validates that all error handling mechanisms work correctly.
"""

import asyncio
import logging
import sys
import os
from typing import List

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.error_handling import (
    TimeoutConfig, CustomExceptions, ErrorHandler, FallbackMechanisms,
    timeout_handler, retry_handler, http_session_with_timeout, HealthChecker
)

# Configure logging for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorHandlingTests:
    """Test suite for error handling functionality"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0
    
    async def run_all_tests(self):
        """Run all error handling tests"""
        logger.info("Starting comprehensive error handling tests...")
        
        # Test timeout handlers
        await self.test_timeout_handler()
        await self.test_retry_handler()
        
        # Test custom exceptions
        await self.test_custom_exceptions()
        
        # Test HTTP session with timeout
        await self.test_http_session_timeout()
        
        # Test fallback mechanisms
        await self.test_fallback_mechanisms()
        
        # Test health checker
        await self.test_health_checker()
        
        # Test error handler
        await self.test_error_handler()
        
        # Print results
        self.print_test_results()
    
    def assert_test(self, condition: bool, test_name: str, message: str = ""):
        """Assert a test condition and track results"""
        self.total_tests += 1
        if condition:
            self.passed_tests += 1
            logger.info(f"✅ PASS: {test_name}")
        else:
            self.failed_tests += 1
            logger.error(f"❌ FAIL: {test_name} - {message}")
    
    async def test_timeout_handler(self):
        """Test timeout handler decorator"""
        logger.info("Testing timeout handler...")
        
        @timeout_handler(0.1, "test_operation")
        async def quick_operation():
            await asyncio.sleep(0.05)
            return "success"
        
        @timeout_handler(0.1, "test_operation")
        async def slow_operation():
            await asyncio.sleep(0.2)
            return "should_timeout"
        
        # Test successful operation
        try:
            result = await quick_operation()
            self.assert_test(result == "success", "timeout_handler_success")
        except Exception as e:
            self.assert_test(False, "timeout_handler_success", str(e))
        
        # Test timeout operation
        try:
            await slow_operation()
            self.assert_test(False, "timeout_handler_timeout", "Should have timed out")
        except CustomExceptions.TimeoutError as e:
            self.assert_test(
                e.operation == "test_operation" and e.timeout == 0.1,
                "timeout_handler_timeout"
            )
        except Exception as e:
            self.assert_test(False, "timeout_handler_timeout", f"Wrong exception: {e}")
    
    async def test_retry_handler(self):
        """Test retry handler decorator"""
        logger.info("Testing retry handler...")
        
        self.retry_attempts = 0
        
        @retry_handler(max_retries=2, backoff_factor=0.01, exceptions=(ValueError,))
        async def failing_operation():
            self.retry_attempts += 1
            if self.retry_attempts < 3:
                raise ValueError("Temporary failure")
            return "success_after_retries"
        
        @retry_handler(max_retries=2, backoff_factor=0.01, exceptions=(ValueError,))
        async def always_failing_operation():
            raise ValueError("Always fails")
        
        # Test successful retry
        try:
            self.retry_attempts = 0
            result = await failing_operation()
            self.assert_test(
                result == "success_after_retries" and self.retry_attempts == 3,
                "retry_handler_success"
            )
        except Exception as e:
            self.assert_test(False, "retry_handler_success", str(e))
        
        # Test max retries exceeded
        try:
            await always_failing_operation()
            self.assert_test(False, "retry_handler_max_retries", "Should have failed after retries")
        except ValueError:
            self.assert_test(True, "retry_handler_max_retries")
        except Exception as e:
            self.assert_test(False, "retry_handler_max_retries", f"Wrong exception: {e}")
    
    async def test_custom_exceptions(self):
        """Test custom exception classes"""
        logger.info("Testing custom exceptions...")
        
        # Test TimeoutError
        timeout_error = CustomExceptions.TimeoutError("test_op", 5.0)
        self.assert_test(
            timeout_error.operation == "test_op" and timeout_error.timeout == 5.0,
            "custom_timeout_error"
        )
        
        # Test ExternalServiceError
        service_error = CustomExceptions.ExternalServiceError("test_service", "test_error")
        self.assert_test(
            service_error.service == "test_service" and service_error.error == "test_error",
            "custom_service_error"
        )
        
        # Test ResourceInitializationError
        init_error = CustomExceptions.ResourceInitializationError("test_resource", "init_failed")
        self.assert_test(
            init_error.resource == "test_resource" and init_error.error == "init_failed",
            "custom_init_error"
        )
        
        # Test DocumentProcessingError
        doc_error = CustomExceptions.DocumentProcessingError("test_operation", "doc_failed")
        self.assert_test(
            doc_error.operation == "test_operation" and doc_error.error == "doc_failed",
            "custom_doc_error"
        )
        
        # Test VectorStoreError
        vector_error = CustomExceptions.VectorStoreError("test_vector_op", "vector_failed")
        self.assert_test(
            vector_error.operation == "test_vector_op" and vector_error.error == "vector_failed",
            "custom_vector_error"
        )
    
    async def test_http_session_timeout(self):
        """Test HTTP session with timeout configuration"""
        logger.info("Testing HTTP session timeout...")
        
        try:
            async with http_session_with_timeout() as session:
                # Test that session is created successfully
                self.assert_test(session is not None, "http_session_creation")
                
                # Test timeout configuration
                timeout = session.timeout
                self.assert_test(
                    timeout.total == TimeoutConfig.HTTP_TOTAL_TIMEOUT,
                    "http_session_timeout_config"
                )
        except Exception as e:
            self.assert_test(False, "http_session_creation", str(e))
    
    async def test_fallback_mechanisms(self):
        """Test fallback mechanisms"""
        logger.info("Testing fallback mechanisms...")
        
        # Test document processing fallback
        fallback_doc = await FallbackMechanisms.fallback_document_processing("test_url")
        self.assert_test(
            isinstance(fallback_doc, str) and len(fallback_doc) > 0,
            "fallback_document_processing"
        )
        
        # Test answer generation fallback
        fallback_answer = await FallbackMechanisms.fallback_answer_generation("test_question")
        self.assert_test(
            isinstance(fallback_answer, str) and len(fallback_answer) > 0,
            "fallback_answer_generation"
        )
        
        # Test vector search fallback
        fallback_search = await FallbackMechanisms.fallback_vector_search("test_query")
        self.assert_test(
            isinstance(fallback_search, str) and len(fallback_search) > 0,
            "fallback_vector_search"
        )
        
        # Test fallback response generation
        fallback_response = FallbackMechanisms.get_fallback_response("test_op", "test_error")
        self.assert_test(
            isinstance(fallback_response, dict) and fallback_response.get("fallback_used") is True,
            "fallback_response_generation"
        )
    
    async def test_health_checker(self):
        """Test health checker functionality"""
        logger.info("Testing health checker...")
        
        async def healthy_service():
            await asyncio.sleep(0.01)
            return True
        
        async def unhealthy_service():
            raise Exception("Service unavailable")
        
        async def timeout_service():
            await asyncio.sleep(15)  # Will timeout
            return True
        
        # Test healthy service
        health_result = await HealthChecker.check_external_service_health(
            "test_healthy", healthy_service
        )
        self.assert_test(
            health_result["status"] == "healthy" and "response_time" in health_result,
            "health_checker_healthy"
        )
        
        # Test unhealthy service
        health_result = await HealthChecker.check_external_service_health(
            "test_unhealthy", unhealthy_service
        )
        self.assert_test(
            health_result["status"] == "unhealthy" and "error" in health_result,
            "health_checker_unhealthy"
        )
        
        # Test timeout service
        health_result = await HealthChecker.check_external_service_health(
            "test_timeout", timeout_service
        )
        self.assert_test(
            health_result["status"] == "timeout",
            "health_checker_timeout"
        )
    
    async def test_error_handler(self):
        """Test error handler functionality"""
        logger.info("Testing error handler...")
        
        # Test safe execute with fallback - success case
        async def primary_success():
            return "primary_result"
        
        async def fallback_function():
            return "fallback_result"
        
        result = await ErrorHandler.safe_execute_with_fallback(
            primary_success, fallback_function, "test_operation"
        )
        self.assert_test(result == "primary_result", "error_handler_primary_success")
        
        # Test safe execute with fallback - fallback case
        async def primary_failure():
            raise Exception("Primary failed")
        
        result = await ErrorHandler.safe_execute_with_fallback(
            primary_failure, fallback_function, "test_operation"
        )
        self.assert_test(result == "fallback_result", "error_handler_fallback_success")
        
        # Test request error handling
        timeout_error = CustomExceptions.TimeoutError("test_op", 5.0)
        http_exception = ErrorHandler.handle_request_error(timeout_error, "test_request")
        self.assert_test(
            http_exception.status_code == 504,
            "error_handler_timeout_conversion"
        )
        
        service_error = CustomExceptions.ExternalServiceError("test_service", "error")
        http_exception = ErrorHandler.handle_request_error(service_error, "test_request")
        self.assert_test(
            http_exception.status_code == 502,
            "error_handler_service_error_conversion"
        )
    
    def print_test_results(self):
        """Print final test results"""
        logger.info("=" * 60)
        logger.info("ERROR HANDLING TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {self.total_tests}")
        logger.info(f"Passed: {self.passed_tests}")
        logger.info(f"Failed: {self.failed_tests}")
        
        if self.failed_tests == 0:
            logger.info("🎉 ALL TESTS PASSED!")
        else:
            logger.error(f"❌ {self.failed_tests} TESTS FAILED")
        
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        logger.info(f"Success Rate: {success_rate:.1f}%")


async def main():
    """Main test function"""
    print("🧪 Starting Error Handling and Timeout Tests")
    print("=" * 60)
    
    # Run tests
    test_suite = ErrorHandlingTests()
    await test_suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if test_suite.failed_tests == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())