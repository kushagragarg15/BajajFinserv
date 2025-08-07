# Performance Testing Suite

This directory contains a comprehensive performance testing suite for validating the response-time optimization implementation. The tests verify that the system meets the requirements specified in the optimization spec.

## Test Requirements Covered

- **Requirement 1.1**: Response time under 5 seconds maximum
- **Requirement 1.2**: Consistent response times across multiple requests  
- **Requirement 1.3**: Accuracy above 0% due to acceptable response times (scalability)

## Test Scripts Overview

### 1. `run_performance_tests.py` (Main Test Runner)
**Purpose**: Orchestrates all performance validation tests
**Usage**: 
```bash
python run_performance_tests.py [--server-url URL] [--skip-server-tests] [--output-dir DIR]
```

**Features**:
- Runs all test suites in sequence
- Generates comprehensive summary reports
- Saves detailed results in JSON and text formats
- Provides overall pass/fail assessment

**Example**:
```bash
# Run all tests with default settings
python run_performance_tests.py

# Run tests against a different server
python run_performance_tests.py --server-url http://localhost:8080

# Run only component tests (no server required)
python run_performance_tests.py --skip-server-tests

# Save results to custom directory
python run_performance_tests.py --output-dir my_test_results
```

### 2. `test_performance_validation.py` (API Validation)
**Purpose**: Tests the live API for performance and functionality
**Usage**:
```bash
python test_performance_validation.py [--url URL] [--api-key KEY] [--output FILE]
```

**Tests Performed**:
- Single request performance (< 5s target)
- Multiple request consistency
- Concurrent request handling
- Functionality correctness validation

**Example**:
```bash
# Test local server
python test_performance_validation.py

# Test with custom API key and save results
python test_performance_validation.py --api-key "Bearer your-key" --output results.json
```

### 3. `test_component_performance.py` (Component Testing)
**Purpose**: Tests individual optimized components without requiring a running server
**Usage**:
```bash
python test_component_performance.py
```

**Components Tested**:
- Global resources initialization
- Async document processing
- Direct answer generation
- Performance monitoring

### 4. `benchmark_comparison.py` (Before/After Comparison)
**Purpose**: Compares current performance against baseline (pre-optimization) metrics
**Usage**:
```bash
python benchmark_comparison.py [--url URL] [--output FILE]
```

**Comparisons Made**:
- Response time improvements
- Success rate improvements
- Scalability improvements
- Overall performance gains

## Prerequisites

### Required Dependencies
Make sure you have all required packages installed:
```bash
pip install -r requirements.txt
```

### For API Tests (Server Required)
1. Start the optimized server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. Verify server health:
   ```bash
   curl http://localhost:8000/health
   ```

### For Component Tests Only
No server required - tests individual components directly.

## Running the Tests

### Quick Start (Recommended)
```bash
# Run all tests with the main test runner
python run_performance_tests.py
```

This will:
1. Run component tests
2. Check server availability
3. Run API validation tests
4. Run benchmark comparison
5. Generate comprehensive reports

### Individual Test Execution

#### Component Tests Only (No Server Required)
```bash
python test_component_performance.py
```

#### API Validation (Server Required)
```bash
# Start server first
uvicorn main:app --host 0.0.0.0 --port 8000

# In another terminal
python test_performance_validation.py
```

#### Benchmark Comparison (Server Required)
```bash
python benchmark_comparison.py
```

## Understanding Test Results

### Success Criteria

**Component Tests**:
- ✅ All components initialize successfully
- ✅ Async operations work correctly
- ✅ Direct answer generation functions properly

**API Validation**:
- ✅ Average response time < 5 seconds
- ✅ Success rate > 95%
- ✅ Concurrent requests handled properly

**Benchmark Comparison**:
- ✅ Significant improvement over baseline (>50% faster)
- ✅ Success rate improved from 0% to >95%
- ✅ Response time reduced from >50s to <5s

### Output Files

The test runner creates several output files:

```
test_results/
├── complete_test_results.json      # Complete test data in JSON format
├── test_summary_report.txt         # Human-readable summary
├── component_tests.log             # Component test output
├── api_validation.log              # API validation output
├── api_validation_results.json     # API test results
├── benchmark_comparison.log        # Benchmark output
└── benchmark_results.json          # Benchmark data
```

### Interpreting Results

**Overall Success**: All tests pass and performance targets are met
- Response times consistently under 5 seconds
- High success rate (>95%)
- Significant performance improvement over baseline

**Partial Success**: Some improvements but targets not fully met
- May need additional optimization
- Check individual test logs for specific issues

**Failure**: Performance targets not met
- Review component test results
- Check server logs for errors
- Verify optimization implementation

## Troubleshooting

### Common Issues

**Server Connection Errors**:
```
❌ Cannot connect to server at http://localhost:8000
```
- Ensure server is running: `uvicorn main:app --host 0.0.0.0 --port 8000`
- Check server health: `curl http://localhost:8000/health`
- Verify port is not blocked by firewall

**Import Errors**:
```
ImportError: No module named 'app.global_resources'
```
- Ensure you're running from the Bajaj directory
- Check that all optimization components are implemented
- Verify Python path includes the app directory

**Timeout Errors**:
```
Request timeout: Processing took longer than expected
```
- Server may not be fully optimized
- Check server logs for bottlenecks
- Verify global resources are initialized

**Performance Target Misses**:
```
❌ Response time 7.3s exceeds target 5.0s
```
- Review optimization implementation
- Check for remaining bottlenecks
- Consider additional performance tuning

### Getting Help

1. **Check Logs**: Review detailed log files in the output directory
2. **Component Tests**: Run component tests first to isolate issues
3. **Server Health**: Use `/health` endpoint to check server status
4. **Performance Analysis**: Use `/performance/analysis` endpoint for insights

## Performance Targets

Based on the optimization requirements:

| Metric | Before Optimization | Target | Current |
|--------|-------------------|---------|---------|
| Response Time | >50 seconds | <5 seconds | Measured by tests |
| Success Rate | 0% (timeouts) | >95% | Measured by tests |
| Concurrent Handling | Failed | Working | Measured by tests |

## Test Data

The tests use a publicly available PDF document for consistency:
- URL: `https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf`
- Questions: Predefined set of test questions
- Expected: Meaningful answers within time limits

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Performance Tests
  run: |
    python run_performance_tests.py --skip-server-tests
    # Add server startup and full tests if needed
```

## Contributing

When adding new performance tests:

1. Follow the existing test structure
2. Include proper error handling and timeouts
3. Add meaningful assertions and metrics
4. Update this README with new test descriptions
5. Ensure tests are deterministic and reliable