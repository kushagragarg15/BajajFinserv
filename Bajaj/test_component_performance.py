#!/usr/bin/env python3
"""
Component Performance Test Suite

This script tests individual components of the optimized system to validate
performance improvements at the component level.

Requirements tested:
- 2.1, 2.2, 2.3: Global resource initialization efficiency
- 4.1, 4.2, 4.3: Direct retrieval vs agent-based approach
- 6.1, 6.2: Async operations performance
"""

import asyncio
import time
import sys
import os
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ComponentTestResult:
    """Container for component test results"""
    component_name: str
    operation: str
    success: bool
    duration: float
    error_message: str = ""
    metadata: Dict[str, Any] = None

class ComponentPerformanceTester:
    """Test individual components for performance"""
    
    def __init__(self):
        self.test_results: List[ComponentTestResult] = []
        
    async def test_global_resources_initialization(self) -> ComponentTestResult:
        """Test global resources initialization performance"""
        logger.info("Testing global resources initialization...")
        
        try:
            # Import here to avoid issues if modules aren't available
            from global_resources import global_resources
            
            start_time = time.perf_counter()
            
            # Test initialization
            await global_resources.initialize()
            
            duration = time.perf_counter() - start_time
            
            # Verify initialization
            is_initialized = global_resources.is_initialized()
            
            logger.info(f"Global resources initialization took {duration:.3f}s")
            
            return ComponentTestResult(
                component_name="global_resources",
                operation="initialization",
                success=is_initialized,
                duration=duration,
                metadata={"initialized": is_initialized}
            )
            
        except ImportError as e:
            logger.warning(f"Could not import global_resources: {e}")
            return ComponentTestResult(
                component_name="global_resources",
                operation="initialization",
                success=False,
                duration=0.0,
                error_message=f"Import error: {e}"
            )
        except Exception as e:
            logger.error(f"Global resources initialization failed: {e}")
            return ComponentTestResult(
                component_name="global_resources",
                operation="initialization",
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def test_async_document_processing(self) -> List[ComponentTestResult]:
        """Test async document processing components"""
        logger.info("Testing async document processing...")
        
        results = []
        test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        
        # Test async document download
        try:
            from input_documents import process_document_from_url_async
            
            start_time = time.perf_counter()
            documents = await process_document_from_url_async(test_url)
            duration = time.perf_counter() - start_time
            
            success = documents is not None and len(documents) > 0
            
            logger.info(f"Async document download took {duration:.3f}s")
            
            results.append(ComponentTestResult(
                component_name="input_documents",
                operation="async_download",
                success=success,
                duration=duration,
                metadata={"document_count": len(documents) if documents else 0}
            ))
            
            # Test async document chunking if download succeeded
            if success:
                try:
                    from llm_parser import chunk_document_async
                    
                    start_time = time.perf_counter()
                    chunks = await chunk_document_async(documents)
                    duration = time.perf_counter() - start_time
                    
                    chunk_success = chunks is not None and len(chunks) > 0
                    
                    logger.info(f"Async document chunking took {duration:.3f}s")
                    
                    results.append(ComponentTestResult(
                        component_name="llm_parser",
                        operation="async_chunking",
                        success=chunk_success,
                        duration=duration,
                        metadata={"chunk_count": len(chunks) if chunks else 0}
                    ))
                    
                except ImportError as e:
                    logger.warning(f"Could not import llm_parser: {e}")
                    results.append(ComponentTestResult(
                        component_name="llm_parser",
                        operation="async_chunking",
                        success=False,
                        duration=0.0,
                        error_message=f"Import error: {e}"
                    ))
                except Exception as e:
                    logger.error(f"Async chunking failed: {e}")
                    results.append(ComponentTestResult(
                        component_name="llm_parser",
                        operation="async_chunking",
                        success=False,
                        duration=0.0,
                        error_message=str(e)
                    ))
            
        except ImportError as e:
            logger.warning(f"Could not import input_documents: {e}")
            results.append(ComponentTestResult(
                component_name="input_documents",
                operation="async_download",
                success=False,
                duration=0.0,
                error_message=f"Import error: {e}"
            ))
        except Exception as e:
            logger.error(f"Async document processing failed: {e}")
            results.append(ComponentTestResult(
                component_name="input_documents",
                operation="async_download",
                success=False,
                duration=0.0,
                error_message=str(e)
            ))
        
        return results
    
    async def test_direct_answer_generation(self) -> ComponentTestResult:
        """Test direct answer generation performance"""
        logger.info("Testing direct answer generation...")
        
        try:
            from direct_answer_generator import DirectAnswerGenerator
            
            # Create a mock vector store for testing
            class MockVectorStore:
                def similarity_search(self, query: str, k: int = 4):
                    # Return mock documents
                    class MockDocument:
                        def __init__(self, content: str):
                            self.page_content = content
                            self.metadata = {}
                    
                    return [
                        MockDocument("This is a test document about performance optimization."),
                        MockDocument("The system has been optimized for faster response times."),
                        MockDocument("Async operations improve overall system performance."),
                        MockDocument("Direct retrieval eliminates agent overhead.")
                    ]
            
            mock_vector_store = MockVectorStore()
            test_questions = [
                "What is this document about?",
                "How has the system been optimized?",
                "What improves performance?"
            ]
            
            answer_generator = DirectAnswerGenerator()
            
            start_time = time.perf_counter()
            
            # Test parallel question processing
            answers = await answer_generator.answer_questions_parallel(
                mock_vector_store, 
                test_questions
            )
            
            duration = time.perf_counter() - start_time
            
            success = (
                answers is not None and 
                len(answers) == len(test_questions) and
                all(answer and len(answer.strip()) > 0 for answer in answers)
            )
            
            logger.info(f"Direct answer generation took {duration:.3f}s for {len(test_questions)} questions")
            
            return ComponentTestResult(
                component_name="direct_answer_generator",
                operation="parallel_generation",
                success=success,
                duration=duration,
                metadata={
                    "question_count": len(test_questions),
                    "answer_count": len(answers) if answers else 0,
                    "avg_time_per_question": duration / len(test_questions) if test_questions else 0
                }
            )
            
        except ImportError as e:
            logger.warning(f"Could not import direct_answer_generator: {e}")
            return ComponentTestResult(
                component_name="direct_answer_generator",
                operation="parallel_generation",
                success=False,
                duration=0.0,
                error_message=f"Import error: {e}"
            )
        except Exception as e:
            logger.error(f"Direct answer generation failed: {e}")
            return ComponentTestResult(
                component_name="direct_answer_generator",
                operation="parallel_generation",
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def test_performance_monitoring(self) -> ComponentTestResult:
        """Test performance monitoring components"""
        logger.info("Testing performance monitoring...")
        
        try:
            from performance_monitor import performance_monitor
            
            start_time = time.perf_counter()
            
            # Test performance monitoring functionality
            request_id = "test_request_123"
            
            # Start request monitoring
            request_metrics = performance_monitor.start_request(
                request_id,
                metadata={"test": True}
            )
            
            # Simulate some operations
            async with performance_monitor.track_operation(request_id, "test_operation", {"test": True}):
                await asyncio.sleep(0.1)  # Simulate work
            
            # Finish request monitoring
            final_metrics = performance_monitor.finish_request(request_id)
            
            # Get performance stats
            stats = performance_monitor.get_performance_stats()
            
            duration = time.perf_counter() - start_time
            
            success = (
                final_metrics is not None and
                stats is not None and
                final_metrics.total_duration is not None
            )
            
            logger.info(f"Performance monitoring test took {duration:.3f}s")
            
            return ComponentTestResult(
                component_name="performance_monitor",
                operation="monitoring_test",
                success=success,
                duration=duration,
                metadata={
                    "has_metrics": final_metrics is not None,
                    "has_stats": stats is not None,
                    "tracked_duration": final_metrics.total_duration if final_metrics else None
                }
            )
            
        except ImportError as e:
            logger.warning(f"Could not import performance_monitor: {e}")
            return ComponentTestResult(
                component_name="performance_monitor",
                operation="monitoring_test",
                success=False,
                duration=0.0,
                error_message=f"Import error: {e}"
            )
        except Exception as e:
            logger.error(f"Performance monitoring test failed: {e}")
            return ComponentTestResult(
                component_name="performance_monitor",
                operation="monitoring_test",
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    def print_component_results(self):
        """Print detailed component test results"""
        print("\n" + "="*80)
        print("COMPONENT PERFORMANCE TEST RESULTS")
        print("="*80)
        
        successful_tests = [r for r in self.test_results if r.success]
        failed_tests = [r for r in self.test_results if not r.success]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Successful: {len(successful_tests)}")
        print(f"Failed: {len(failed_tests)}")
        print(f"Success Rate: {len(successful_tests)/len(self.test_results)*100:.1f}%")
        
        print("\nSUCCESSFUL TESTS:")
        print("-" * 40)
        for result in successful_tests:
            print(f"✅ {result.component_name}.{result.operation}: {result.duration:.3f}s")
            if result.metadata:
                for key, value in result.metadata.items():
                    print(f"   {key}: {value}")
        
        if failed_tests:
            print("\nFAILED TESTS:")
            print("-" * 40)
            for result in failed_tests:
                print(f"❌ {result.component_name}.{result.operation}: {result.error_message}")
        
        print("\nPERFORMANCE ANALYSIS:")
        print("-" * 40)
        
        # Analyze performance by component
        components = {}
        for result in successful_tests:
            if result.component_name not in components:
                components[result.component_name] = []
            components[result.component_name].append(result.duration)
        
        for component, durations in components.items():
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            print(f"{component}:")
            print(f"  Average: {avg_duration:.3f}s")
            print(f"  Range: {min_duration:.3f}s - {max_duration:.3f}s")
        
        print("="*80)
    
    async def run_component_tests(self) -> Dict[str, Any]:
        """Run all component performance tests"""
        print("🔧 Starting Component Performance Tests")
        print("="*60)
        
        # Test 1: Global Resources Initialization
        print("1. Testing global resources initialization...")
        global_resources_result = await self.test_global_resources_initialization()
        self.test_results.append(global_resources_result)
        
        # Test 2: Async Document Processing
        print("2. Testing async document processing...")
        doc_processing_results = await self.test_async_document_processing()
        self.test_results.extend(doc_processing_results)
        
        # Test 3: Direct Answer Generation
        print("3. Testing direct answer generation...")
        answer_gen_result = await self.test_direct_answer_generation()
        self.test_results.append(answer_gen_result)
        
        # Test 4: Performance Monitoring
        print("4. Testing performance monitoring...")
        perf_monitor_result = await self.test_performance_monitoring()
        self.test_results.append(perf_monitor_result)
        
        # Print results
        self.print_component_results()
        
        # Return summary
        successful_tests = [r for r in self.test_results if r.success]
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(self.test_results),
            "successful_tests": len(successful_tests),
            "failed_tests": len(self.test_results) - len(successful_tests),
            "success_rate": len(successful_tests) / len(self.test_results) if self.test_results else 0,
            "overall_success": len(successful_tests) == len(self.test_results)
        }

async def main():
    """Main function to run component tests"""
    tester = ComponentPerformanceTester()
    
    try:
        results = await tester.run_component_tests()
        
        if results["overall_success"]:
            print("\n🎉 ALL COMPONENT TESTS PASSED!")
            print("The optimized components are working correctly.")
        else:
            print(f"\n⚠️ {results['failed_tests']} COMPONENT TESTS FAILED")
            print("Some components may need attention.")
        
        return results["overall_success"]
        
    except Exception as e:
        print(f"\n❌ Component testing failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)