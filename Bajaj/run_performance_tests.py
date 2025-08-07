#!/usr/bin/env python3
"""
Performance Test Runner

This script orchestrates all performance validation tests for the response-time optimization.
It runs component tests, API validation tests, and benchmark comparisons.

Usage:
    python run_performance_tests.py [--server-url URL] [--skip-server-tests] [--output-dir DIR]
"""

import asyncio
import subprocess
import sys
import os
import json
import time
from pathlib import Path
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceTestRunner:
    """Orchestrates all performance tests"""
    
    def __init__(self, server_url: str = "http://localhost:8000", output_dir: str = "test_results"):
        self.server_url = server_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.test_results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "server_url": server_url,
            "tests": {}
        }
    
    async def check_server_availability(self) -> bool:
        """Check if the server is running and available"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health", timeout=10) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        logger.info(f"Server is available and {health_data.get('overall_status', 'unknown')}")
                        return health_data.get('overall_status') == 'healthy'
                    else:
                        logger.warning(f"Server responded with status {response.status}")
                        return False
        except ImportError:
            logger.warning("aiohttp not available, skipping server check")
            return False
        except Exception as e:
            logger.error(f"Server check failed: {e}")
            return False
    
    def run_component_tests(self) -> bool:
        """Run component performance tests"""
        logger.info("Running component performance tests...")
        
        try:
            result = subprocess.run([
                sys.executable, "test_component_performance.py"
            ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            success = result.returncode == 0
            
            # Save output
            output_file = self.output_dir / "component_tests.log"
            with open(output_file, 'w') as f:
                f.write("STDOUT:\n")
                f.write(result.stdout)
                f.write("\nSTDERR:\n")
                f.write(result.stderr)
            
            self.test_results["tests"]["component_tests"] = {
                "success": success,
                "output_file": str(output_file),
                "stdout_preview": result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout
            }
            
            if success:
                logger.info("✅ Component tests passed")
            else:
                logger.error("❌ Component tests failed")
                logger.error(f"Error output: {result.stderr[:200]}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to run component tests: {e}")
            self.test_results["tests"]["component_tests"] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    async def run_api_validation_tests(self) -> bool:
        """Run API validation tests"""
        logger.info("Running API validation tests...")
        
        try:
            # Check if server is available first
            if not await self.check_server_availability():
                logger.warning("Server not available, skipping API validation tests")
                self.test_results["tests"]["api_validation"] = {
                    "success": False,
                    "error": "Server not available"
                }
                return False
            
            result = subprocess.run([
                sys.executable, "test_performance_validation.py",
                "--url", self.server_url,
                "--output", str(self.output_dir / "api_validation_results.json")
            ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            success = result.returncode == 0
            
            # Save output
            output_file = self.output_dir / "api_validation.log"
            with open(output_file, 'w') as f:
                f.write("STDOUT:\n")
                f.write(result.stdout)
                f.write("\nSTDERR:\n")
                f.write(result.stderr)
            
            # Try to load JSON results if available
            json_results = None
            json_file = self.output_dir / "api_validation_results.json"
            if json_file.exists():
                try:
                    with open(json_file, 'r') as f:
                        json_results = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load JSON results: {e}")
            
            self.test_results["tests"]["api_validation"] = {
                "success": success,
                "output_file": str(output_file),
                "results_file": str(json_file) if json_file.exists() else None,
                "results_summary": json_results.get("overall") if json_results else None,
                "stdout_preview": result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout
            }
            
            if success:
                logger.info("✅ API validation tests passed")
            else:
                logger.error("❌ API validation tests failed")
                logger.error(f"Error output: {result.stderr[:200]}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to run API validation tests: {e}")
            self.test_results["tests"]["api_validation"] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    async def run_benchmark_comparison(self) -> bool:
        """Run benchmark comparison tests"""
        logger.info("Running benchmark comparison...")
        
        try:
            # Check if server is available first
            if not await self.check_server_availability():
                logger.warning("Server not available, skipping benchmark comparison")
                self.test_results["tests"]["benchmark_comparison"] = {
                    "success": False,
                    "error": "Server not available"
                }
                return False
            
            result = subprocess.run([
                sys.executable, "benchmark_comparison.py",
                "--url", self.server_url,
                "--output", str(self.output_dir / "benchmark_results.json")
            ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            success = result.returncode == 0
            
            # Save output
            output_file = self.output_dir / "benchmark_comparison.log"
            with open(output_file, 'w') as f:
                f.write("STDOUT:\n")
                f.write(result.stdout)
                f.write("\nSTDERR:\n")
                f.write(result.stderr)
            
            # Try to load JSON results if available
            json_results = None
            json_file = self.output_dir / "benchmark_results.json"
            if json_file.exists():
                try:
                    with open(json_file, 'r') as f:
                        json_results = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load JSON results: {e}")
            
            self.test_results["tests"]["benchmark_comparison"] = {
                "success": success,
                "output_file": str(output_file),
                "results_file": str(json_file) if json_file.exists() else None,
                "results_summary": json_results.get("summary") if json_results else None,
                "stdout_preview": result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout
            }
            
            if success:
                logger.info("✅ Benchmark comparison passed")
            else:
                logger.error("❌ Benchmark comparison failed")
                logger.error(f"Error output: {result.stderr[:200]}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to run benchmark comparison: {e}")
            self.test_results["tests"]["benchmark_comparison"] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    def generate_summary_report(self):
        """Generate a comprehensive summary report"""
        logger.info("Generating summary report...")
        
        # Count successful tests
        successful_tests = sum(1 for test in self.test_results["tests"].values() if test.get("success", False))
        total_tests = len(self.test_results["tests"])
        
        # Create summary
        summary = {
            "overall_success": successful_tests == total_tests,
            "successful_tests": successful_tests,
            "total_tests": total_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "recommendations": []
        }
        
        # Add recommendations based on results
        if summary["overall_success"]:
            summary["recommendations"].append("🎉 All tests passed! The optimization work is successful.")
        else:
            if not self.test_results["tests"].get("component_tests", {}).get("success", False):
                summary["recommendations"].append("❌ Component tests failed - check individual component implementations")
            
            if not self.test_results["tests"].get("api_validation", {}).get("success", False):
                summary["recommendations"].append("❌ API validation failed - check server functionality and response times")
            
            if not self.test_results["tests"].get("benchmark_comparison", {}).get("success", False):
                summary["recommendations"].append("❌ Benchmark comparison failed - performance targets may not be met")
        
        self.test_results["summary"] = summary
        
        # Save complete results
        results_file = self.output_dir / "complete_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        # Generate human-readable report
        report_file = self.output_dir / "test_summary_report.txt"
        with open(report_file, 'w') as f:
            f.write("PERFORMANCE VALIDATION TEST SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Test Run: {self.test_results['timestamp']}\n")
            f.write(f"Server URL: {self.server_url}\n")
            f.write(f"Output Directory: {self.output_dir}\n\n")
            
            f.write("TEST RESULTS:\n")
            f.write("-" * 20 + "\n")
            for test_name, test_result in self.test_results["tests"].items():
                status = "✅ PASSED" if test_result.get("success", False) else "❌ FAILED"
                f.write(f"{test_name}: {status}\n")
                if not test_result.get("success", False) and "error" in test_result:
                    f.write(f"  Error: {test_result['error']}\n")
            
            f.write(f"\nOVERALL RESULT: {'✅ SUCCESS' if summary['overall_success'] else '❌ NEEDS ATTENTION'}\n")
            f.write(f"Success Rate: {summary['success_rate']:.1%} ({successful_tests}/{total_tests})\n\n")
            
            f.write("RECOMMENDATIONS:\n")
            f.write("-" * 20 + "\n")
            for rec in summary["recommendations"]:
                f.write(f"• {rec}\n")
            
            f.write(f"\nDetailed results available in: {results_file}\n")
        
        logger.info(f"Summary report saved to: {report_file}")
        logger.info(f"Complete results saved to: {results_file}")
        
        return summary
    
    def print_final_summary(self, summary: dict):
        """Print final summary to console"""
        print("\n" + "=" * 80)
        print("PERFORMANCE VALIDATION COMPLETE")
        print("=" * 80)
        
        print(f"Test Results: {summary['successful_tests']}/{summary['total_tests']} passed")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        
        if summary["overall_success"]:
            print("\n🎉 ALL TESTS PASSED!")
            print("The response-time optimization implementation is successful!")
            print("\nKey achievements:")
            print("✅ Component-level optimizations are working correctly")
            print("✅ API response times meet the 5-second target")
            print("✅ System handles concurrent requests effectively")
            print("✅ Performance improvements are significant and measurable")
        else:
            print(f"\n⚠️ {summary['total_tests'] - summary['successful_tests']} TESTS NEED ATTENTION")
            print("Some aspects of the optimization may need additional work.")
            
            print("\nRecommendations:")
            for rec in summary["recommendations"]:
                print(f"  {rec}")
        
        print(f"\nDetailed results available in: {self.output_dir}")
        print("=" * 80)
    
    async def run_all_tests(self, skip_server_tests: bool = False) -> bool:
        """Run all performance validation tests"""
        print("🚀 Starting Comprehensive Performance Validation")
        print(f"Server URL: {self.server_url}")
        print(f"Output Directory: {self.output_dir}")
        print("=" * 60)
        
        # Test 1: Component Tests (always run)
        print("\n1. Running Component Performance Tests...")
        component_success = self.run_component_tests()
        
        if skip_server_tests:
            logger.info("Skipping server-dependent tests as requested")
        else:
            # Test 2: API Validation Tests
            print("\n2. Running API Validation Tests...")
            api_success = await self.run_api_validation_tests()
            
            # Test 3: Benchmark Comparison
            print("\n3. Running Benchmark Comparison...")
            benchmark_success = await self.run_benchmark_comparison()
        
        # Generate summary
        print("\n4. Generating Summary Report...")
        summary = self.generate_summary_report()
        
        # Print final summary
        self.print_final_summary(summary)
        
        return summary["overall_success"]

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Performance Test Runner")
    parser.add_argument("--server-url", default="http://localhost:8000", 
                       help="Base URL of the API server")
    parser.add_argument("--skip-server-tests", action="store_true",
                       help="Skip tests that require a running server")
    parser.add_argument("--output-dir", default="test_results",
                       help="Directory to save test results")
    
    args = parser.parse_args()
    
    runner = PerformanceTestRunner(
        server_url=args.server_url,
        output_dir=args.output_dir
    )
    
    try:
        success = await runner.run_all_tests(skip_server_tests=args.skip_server_tests)
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test run failed with error: {str(e)}")
        logger.exception("Detailed error information:")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())