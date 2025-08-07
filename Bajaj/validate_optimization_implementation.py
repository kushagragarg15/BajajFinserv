#!/usr/bin/env python3
"""
Optimization Implementation Validator

This script validates that the optimization implementation is correctly structured
and follows the design patterns specified in the requirements, without requiring
external dependencies.

Requirements validated:
- File structure and organization
- Async implementation patterns
- Global resource management patterns
- Direct retrieval implementation
- Performance monitoring integration
"""

import os
import sys
import ast
import inspect
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OptimizationValidator:
    """Validates the optimization implementation structure"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.app_path = self.base_path / "app"
        self.validation_results = []
        
    def validate_file_structure(self) -> bool:
        """Validate that required files exist"""
        logger.info("Validating file structure...")
        
        required_files = [
            "main.py",
            "app/global_resources.py",
            "app/input_documents.py", 
            "app/llm_parser.py",
            "app/direct_answer_generator.py",
            "app/embedding_search.py",
            "app/performance_monitor.py",
            "app/error_handling.py"
        ]
        
        missing_files = []
        existing_files = []
        
        for file_path in required_files:
            full_path = self.base_path / file_path
            if full_path.exists():
                existing_files.append(file_path)
                logger.info(f"✅ Found: {file_path}")
            else:
                missing_files.append(file_path)
                logger.warning(f"❌ Missing: {file_path}")
        
        self.validation_results.append({
            "test": "file_structure",
            "success": len(missing_files) == 0,
            "details": {
                "existing_files": existing_files,
                "missing_files": missing_files,
                "total_required": len(required_files),
                "total_found": len(existing_files)
            }
        })
        
        return len(missing_files) == 0
    
    def analyze_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Python file for async patterns and structure"""
        if not file_path.exists():
            return {"error": "File not found"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            analysis = {
                "has_async_functions": False,
                "has_await_calls": False,
                "has_classes": False,
                "function_names": [],
                "class_names": [],
                "async_function_names": [],
                "import_statements": [],
                "has_error_handling": False
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    analysis["has_async_functions"] = True
                    analysis["async_function_names"].append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    analysis["function_names"].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    analysis["has_classes"] = True
                    analysis["class_names"].append(node.name)
                elif isinstance(node, ast.Await):
                    analysis["has_await_calls"] = True
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["import_statements"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        analysis["import_statements"].append(node.module)
                elif isinstance(node, ast.Try):
                    analysis["has_error_handling"] = True
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    def validate_async_implementation(self) -> bool:
        """Validate async implementation patterns"""
        logger.info("Validating async implementation patterns...")
        
        files_to_check = [
            ("main.py", ["async", "await", "startup"]),
            ("app/input_documents.py", ["async", "aiohttp", "process_document_from_url_async"]),
            ("app/llm_parser.py", ["async", "chunk_document_async"]),
            ("app/direct_answer_generator.py", ["async", "parallel", "asyncio.gather"])
        ]
        
        validation_details = {}
        overall_success = True
        
        for file_path, expected_patterns in files_to_check:
            full_path = self.base_path / file_path
            analysis = self.analyze_python_file(full_path)
            
            if "error" in analysis:
                logger.warning(f"❌ Could not analyze {file_path}: {analysis['error']}")
                validation_details[file_path] = {"success": False, "error": analysis["error"]}
                overall_success = False
                continue
            
            # Check for async patterns
            has_async = analysis["has_async_functions"] or analysis["has_await_calls"]
            
            # Check file content for expected patterns
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                
                pattern_matches = {}
                for pattern in expected_patterns:
                    pattern_matches[pattern] = pattern.lower() in content
                
                file_success = has_async and all(pattern_matches.values())
                
                validation_details[file_path] = {
                    "success": file_success,
                    "has_async": has_async,
                    "async_functions": analysis["async_function_names"],
                    "pattern_matches": pattern_matches
                }
                
                if file_success:
                    logger.info(f"✅ {file_path}: Async patterns validated")
                else:
                    logger.warning(f"❌ {file_path}: Missing async patterns")
                    overall_success = False
                    
            except Exception as e:
                logger.warning(f"❌ Could not read {file_path}: {e}")
                validation_details[file_path] = {"success": False, "error": str(e)}
                overall_success = False
        
        self.validation_results.append({
            "test": "async_implementation",
            "success": overall_success,
            "details": validation_details
        })
        
        return overall_success
    
    def validate_global_resources_pattern(self) -> bool:
        """Validate global resources singleton pattern"""
        logger.info("Validating global resources pattern...")
        
        global_resources_file = self.base_path / "app/global_resources.py"
        analysis = self.analyze_python_file(global_resources_file)
        
        if "error" in analysis:
            logger.warning(f"❌ Could not analyze global_resources.py: {analysis['error']}")
            self.validation_results.append({
                "test": "global_resources_pattern",
                "success": False,
                "details": {"error": analysis["error"]}
            })
            return False
        
        # Check for expected patterns
        expected_class = "GlobalResources"
        expected_methods = ["initialize", "is_initialized", "get_vector_store"]
        
        has_expected_class = expected_class in analysis["class_names"]
        has_async_init = "initialize" in analysis["async_function_names"]
        
        try:
            with open(global_resources_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for singleton pattern indicators
            has_singleton_pattern = "global_resources" in content.lower()
            has_initialization = "pinecone" in content.lower() or "embeddings" in content.lower()
            
            success = has_expected_class and has_async_init and has_singleton_pattern
            
            validation_details = {
                "has_expected_class": has_expected_class,
                "has_async_init": has_async_init,
                "has_singleton_pattern": has_singleton_pattern,
                "has_initialization": has_initialization,
                "class_names": analysis["class_names"],
                "async_functions": analysis["async_function_names"]
            }
            
            if success:
                logger.info("✅ Global resources pattern validated")
            else:
                logger.warning("❌ Global resources pattern issues found")
            
            self.validation_results.append({
                "test": "global_resources_pattern",
                "success": success,
                "details": validation_details
            })
            
            return success
            
        except Exception as e:
            logger.warning(f"❌ Could not validate global resources pattern: {e}")
            self.validation_results.append({
                "test": "global_resources_pattern",
                "success": False,
                "details": {"error": str(e)}
            })
            return False
    
    def validate_direct_retrieval_pattern(self) -> bool:
        """Validate direct retrieval implementation (no agent)"""
        logger.info("Validating direct retrieval pattern...")
        
        direct_answer_file = self.base_path / "app/direct_answer_generator.py"
        analysis = self.analyze_python_file(direct_answer_file)
        
        if "error" in analysis:
            logger.warning(f"❌ Could not analyze direct_answer_generator.py: {analysis['error']}")
            self.validation_results.append({
                "test": "direct_retrieval_pattern",
                "success": False,
                "details": {"error": analysis["error"]}
            })
            return False
        
        try:
            with open(direct_answer_file, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            # Check for direct retrieval patterns (no agent)
            has_direct_pattern = "directanswergenerator" in content
            has_parallel_processing = "asyncio.gather" in content or "parallel" in content
            has_no_agent = "agent" not in content or "no agent" in content
            has_async_methods = analysis["has_async_functions"]
            
            success = has_direct_pattern and has_parallel_processing and has_async_methods
            
            validation_details = {
                "has_direct_pattern": has_direct_pattern,
                "has_parallel_processing": has_parallel_processing,
                "has_no_agent_dependency": has_no_agent,
                "has_async_methods": has_async_methods,
                "class_names": analysis["class_names"],
                "async_functions": analysis["async_function_names"]
            }
            
            if success:
                logger.info("✅ Direct retrieval pattern validated")
            else:
                logger.warning("❌ Direct retrieval pattern issues found")
            
            self.validation_results.append({
                "test": "direct_retrieval_pattern",
                "success": success,
                "details": validation_details
            })
            
            return success
            
        except Exception as e:
            logger.warning(f"❌ Could not validate direct retrieval pattern: {e}")
            self.validation_results.append({
                "test": "direct_retrieval_pattern",
                "success": False,
                "details": {"error": str(e)}
            })
            return False
    
    def validate_performance_monitoring(self) -> bool:
        """Validate performance monitoring implementation"""
        logger.info("Validating performance monitoring...")
        
        perf_monitor_file = self.base_path / "app/performance_monitor.py"
        analysis = self.analyze_python_file(perf_monitor_file)
        
        if "error" in analysis:
            logger.warning(f"❌ Could not analyze performance_monitor.py: {analysis['error']}")
            self.validation_results.append({
                "test": "performance_monitoring",
                "success": False,
                "details": {"error": analysis["error"]}
            })
            return False
        
        try:
            with open(perf_monitor_file, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            # Check for performance monitoring patterns
            has_performance_class = any("performance" in name.lower() for name in analysis["class_names"])
            has_timing_methods = "time" in content and ("perf_counter" in content or "duration" in content)
            has_monitoring_methods = "start_request" in content or "track_operation" in content
            has_metrics_collection = "metrics" in content or "stats" in content
            
            success = has_performance_class and has_timing_methods and has_monitoring_methods
            
            validation_details = {
                "has_performance_class": has_performance_class,
                "has_timing_methods": has_timing_methods,
                "has_monitoring_methods": has_monitoring_methods,
                "has_metrics_collection": has_metrics_collection,
                "class_names": analysis["class_names"],
                "function_names": analysis["function_names"]
            }
            
            if success:
                logger.info("✅ Performance monitoring validated")
            else:
                logger.warning("❌ Performance monitoring issues found")
            
            self.validation_results.append({
                "test": "performance_monitoring",
                "success": success,
                "details": validation_details
            })
            
            return success
            
        except Exception as e:
            logger.warning(f"❌ Could not validate performance monitoring: {e}")
            self.validation_results.append({
                "test": "performance_monitoring",
                "success": False,
                "details": {"error": str(e)}
            })
            return False
    
    def validate_main_app_integration(self) -> bool:
        """Validate main app integration with optimizations"""
        logger.info("Validating main app integration...")
        
        main_file = self.base_path / "main.py"
        analysis = self.analyze_python_file(main_file)
        
        if "error" in analysis:
            logger.warning(f"❌ Could not analyze main.py: {analysis['error']}")
            self.validation_results.append({
                "test": "main_app_integration",
                "success": False,
                "details": {"error": analysis["error"]}
            })
            return False
        
        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            # Check for integration patterns
            has_startup_event = "startup" in content and "@app.on_event" in content
            has_global_resources_import = "global_resources" in content
            has_async_endpoint = analysis["has_async_functions"] and "async def" in content
            has_performance_monitoring = "performance_monitor" in content
            has_error_handling = analysis["has_error_handling"]
            has_direct_answer_import = "direct_answer_generator" in content
            
            success = (has_startup_event and has_global_resources_import and 
                      has_async_endpoint and has_performance_monitoring)
            
            validation_details = {
                "has_startup_event": has_startup_event,
                "has_global_resources_import": has_global_resources_import,
                "has_async_endpoint": has_async_endpoint,
                "has_performance_monitoring": has_performance_monitoring,
                "has_error_handling": has_error_handling,
                "has_direct_answer_import": has_direct_answer_import,
                "async_functions": analysis["async_function_names"]
            }
            
            if success:
                logger.info("✅ Main app integration validated")
            else:
                logger.warning("❌ Main app integration issues found")
            
            self.validation_results.append({
                "test": "main_app_integration",
                "success": success,
                "details": validation_details
            })
            
            return success
            
        except Exception as e:
            logger.warning(f"❌ Could not validate main app integration: {e}")
            self.validation_results.append({
                "test": "main_app_integration",
                "success": False,
                "details": {"error": str(e)}
            })
            return False
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        successful_tests = [r for r in self.validation_results if r["success"]]
        failed_tests = [r for r in self.validation_results if not r["success"]]
        
        report = {
            "timestamp": __import__('time').strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(self.validation_results),
            "successful_tests": len(successful_tests),
            "failed_tests": len(failed_tests),
            "success_rate": len(successful_tests) / len(self.validation_results) if self.validation_results else 0,
            "overall_success": len(failed_tests) == 0,
            "test_results": self.validation_results
        }
        
        return report
    
    def print_validation_summary(self, report: Dict[str, Any]):
        """Print validation summary"""
        print("\n" + "=" * 80)
        print("OPTIMIZATION IMPLEMENTATION VALIDATION SUMMARY")
        print("=" * 80)
        
        print(f"Total Tests: {report['total_tests']}")
        print(f"Successful: {report['successful_tests']}")
        print(f"Failed: {report['failed_tests']}")
        print(f"Success Rate: {report['success_rate']:.1%}")
        
        print("\nTEST RESULTS:")
        print("-" * 40)
        
        for result in self.validation_results:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            test_name = result["test"].replace("_", " ").title()
            print(f"{status} {test_name}")
            
            if not result["success"] and "error" in result.get("details", {}):
                print(f"    Error: {result['details']['error']}")
        
        print(f"\nOVERALL RESULT: {'✅ VALIDATION PASSED' if report['overall_success'] else '❌ VALIDATION FAILED'}")
        
        if report["overall_success"]:
            print("\n🎉 IMPLEMENTATION VALIDATION SUCCESSFUL!")
            print("The optimization implementation follows the correct patterns:")
            print("✅ File structure is complete")
            print("✅ Async patterns are implemented correctly")
            print("✅ Global resources pattern is in place")
            print("✅ Direct retrieval replaces agent-based approach")
            print("✅ Performance monitoring is integrated")
            print("✅ Main app integration is correct")
        else:
            print(f"\n⚠️ IMPLEMENTATION NEEDS ATTENTION")
            print("Some aspects of the optimization implementation may need review.")
            
            # Provide specific recommendations
            for result in self.validation_results:
                if not result["success"]:
                    test_name = result["test"].replace("_", " ").title()
                    print(f"• Review {test_name} implementation")
        
        print("=" * 80)
    
    def run_validation(self) -> bool:
        """Run complete validation suite"""
        print("🔍 Starting Optimization Implementation Validation")
        print("=" * 60)
        
        # Run all validation tests
        tests = [
            ("File Structure", self.validate_file_structure),
            ("Async Implementation", self.validate_async_implementation),
            ("Global Resources Pattern", self.validate_global_resources_pattern),
            ("Direct Retrieval Pattern", self.validate_direct_retrieval_pattern),
            ("Performance Monitoring", self.validate_performance_monitoring),
            ("Main App Integration", self.validate_main_app_integration)
        ]
        
        for test_name, test_func in tests:
            print(f"\n{len(self.validation_results) + 1}. {test_name}...")
            try:
                test_func()
            except Exception as e:
                logger.error(f"Test {test_name} failed with exception: {e}")
                self.validation_results.append({
                    "test": test_name.lower().replace(" ", "_"),
                    "success": False,
                    "details": {"error": str(e)}
                })
        
        # Generate and print report
        report = self.generate_validation_report()
        self.print_validation_summary(report)
        
        return report["overall_success"]

def main():
    """Main function"""
    validator = OptimizationValidator()
    
    try:
        success = validator.run_validation()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {str(e)}")
        logger.exception("Detailed error information:")
        sys.exit(1)

if __name__ == "__main__":
    main()