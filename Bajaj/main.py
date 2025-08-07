# main.py
import sys
import os
import asyncio
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, HttpUrl
from typing import List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Import the modularized components
from app.input_documents import process_document_from_url_async
from app.llm_parser import chunk_document_async
from app.global_resources import global_resources
from app.direct_answer_generator import DirectAnswerGenerator
from app.error_handling import (
    TimeoutConfig, CustomExceptions, ErrorHandler, 
    timeout_handler, FallbackMechanisms
)
from app.performance_monitor import (
    performance_monitor, setup_performance_logging, timed_operation
)

# --- Configuration & Initialization ---
load_dotenv()

# Setup performance monitoring logging
setup_performance_logging()

app = FastAPI(
    title="Intelligent Query-Retrieval System",
    description="An API for processing documents and answering questions using LLMs and vector search.",
    version="1.0.0"
)

# --- Startup Event Handler ---
@app.on_event("startup")
async def startup_event():
    """
    Initialize global resources during application startup with comprehensive error handling.
    This ensures all expensive operations happen once at startup,
    not per request, significantly improving response times.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    startup_start_time = time.perf_counter()
    
    try:
        logger.info("[Startup] 🚀 Initializing global resources...")
        logger.info("[Startup] Performance target: < 5s response time per request")
        
        # Initialize with timeout and timing
        initialization_start = time.perf_counter()
        await asyncio.wait_for(
            global_resources.initialize(),
            timeout=120.0  # 2 minute timeout for startup
        )
        initialization_duration = time.perf_counter() - initialization_start
        
        logger.info(f"[Startup] ✅ Global resources initialized in {initialization_duration:.3f}s")
        
        # Verify all resources are properly initialized
        if not global_resources.is_initialized():
            raise CustomExceptions.ResourceInitializationError(
                "startup",
                "Failed to initialize all global resources"
            )
        
        # Perform health check with timing
        health_check_start = time.perf_counter()
        health_status = await global_resources.health_check()
        health_check_duration = time.perf_counter() - health_check_start
        
        logger.info(f"[Startup] Health check completed in {health_check_duration:.3f}s")
        
        if health_status["overall_status"] != "healthy":
            logger.warning(f"[Startup] ⚠️ Health check warnings: {health_status}")
        else:
            logger.info("[Startup] ✅ All components healthy")
        
        total_startup_time = time.perf_counter() - startup_start_time
        logger.info(f"[Startup] 🎉 Application ready! Total startup time: {total_startup_time:.3f}s")
        
        # Log optimization status
        logger.info("[Startup] 📊 Optimization features enabled:")
        logger.info("[Startup]   ✅ Global resource initialization (eliminates per-request setup)")
        logger.info("[Startup]   ✅ Async operations (non-blocking I/O)")
        logger.info("[Startup]   ✅ Parallel question processing")
        logger.info("[Startup]   ✅ Direct retrieval (no agent overhead)")
        logger.info("[Startup]   ✅ Performance monitoring and bottleneck detection")
        
    except asyncio.TimeoutError:
        startup_duration = time.perf_counter() - startup_start_time
        logger.critical(f"[Startup] ❌ Startup timeout after {startup_duration:.3f}s - application initialization took too long")
        raise CustomExceptions.TimeoutError("startup", 120.0)
    except Exception as e:
        startup_duration = time.perf_counter() - startup_start_time
        logger.critical(f"[Startup] ❌ Failed to initialize global resources after {startup_duration:.3f}s: {str(e)}")
        # This will prevent the application from starting if resources can't be initialized
        ErrorHandler.handle_startup_error(e, "startup")

# --- API Key Authentication ---
API_KEY_NAME = "Authorization"
API_KEY_HEADER = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
EXPECTED_BEARER_TOKEN = "Bearer 04882ff997f04a7548a2640b6ac4ca31bb61a48594229f92000cc82b4e6dbd3d"

async def get_api_key(api_key_header: str = Security(API_KEY_HEADER)):
    if api_key_header == EXPECTED_BEARER_TOKEN:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )

# --- Pydantic Models for API ---
class SubmissionRequest(BaseModel):
    documents: HttpUrl = Field(..., description="URL to the PDF document to be processed.")
    questions: List[str] = Field(..., description="A list of natural language questions about the document.")

class SubmissionResponse(BaseModel):
    answers: List[str] = Field(..., description="A list of answers corresponding to the questions asked.")

# --- API Endpoint ---
@app.post(
    "/api/v1/hackrx/run",
    response_model=SubmissionResponse,
    summary="Run Document Query Submission",
    tags=["Query System"]
)
@timeout_handler(TimeoutConfig.HTTP_TOTAL_TIMEOUT, "api_request")
async def run_submission(
    request: SubmissionRequest,
    api_key: str = Depends(get_api_key)
):
    import logging
    logger = logging.getLogger(__name__)
    
    request_id = str(id(request))  # Simple request ID for tracking
    logger.info(f"[Request {request_id}] Starting document query submission")
    
    # Start performance monitoring for this request
    request_metrics = performance_monitor.start_request(
        request_id, 
        metadata={
            "num_questions": len(request.questions),
            "document_url": str(request.documents)
        }
    )
    
    try:
        # Verify global resources are initialized
        if not global_resources.is_initialized():
            logger.error(f"[Request {request_id}] Global resources not initialized")
            raise HTTPException(
                status_code=503, 
                detail="Service unavailable: Global resources not initialized"
            )
        
        # Validate request
        if not request.questions or len(request.questions) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one question is required"
            )
        
        if len(request.questions) > 10:  # Reasonable limit
            raise HTTPException(
                status_code=400,
                detail="Too many questions (maximum 10 allowed)"
            )
        
        logger.info(f"[Request {request_id}] Processing {len(request.questions)} questions")
        
        # Step 1: Input Documents (async) with timeout and performance tracking
        logger.info(f"[Request {request_id}] Step 1: Processing document")
        async with performance_monitor.track_operation(request_id, "document_download", {"url": str(request.documents)}):
            raw_text = await asyncio.wait_for(
                process_document_from_url_async(str(request.documents)),
                timeout=TimeoutConfig.DOCUMENT_DOWNLOAD_TIMEOUT
            )

        # Step 2: LLM Parser (Chunking) (async) with timeout and performance tracking
        logger.info(f"[Request {request_id}] Step 2: Chunking document")
        async with performance_monitor.track_operation(request_id, "document_chunking", {"pages": len(raw_text)}):
            texts = await asyncio.wait_for(
                chunk_document_async(raw_text),
                timeout=TimeoutConfig.DOCUMENT_PROCESSING_TIMEOUT
            )

        # Step 3: Embedding Search (using pre-initialized resources) with timeout and performance tracking
        logger.info(f"[Request {request_id}] Step 3: Creating vector store")
        async with performance_monitor.track_operation(request_id, "vector_store_creation", {"chunks": len(texts)}):
            vector_store = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    global_resources.get_vector_store,
                    texts
                ),
                timeout=TimeoutConfig.VECTOR_STORE_CREATE_TIMEOUT
            )

        # Step 4: Direct answer generation with parallel processing and timeout and performance tracking
        logger.info(f"[Request {request_id}] Step 4: Generating answers")
        async with performance_monitor.track_operation(request_id, "answer_generation", {"questions": len(request.questions)}):
            answer_generator = DirectAnswerGenerator()
            answers = await asyncio.wait_for(
                answer_generator.answer_questions_parallel(vector_store, request.questions),
                timeout=TimeoutConfig.LLM_GENERATION_TIMEOUT * len(request.questions)
            )
        
        logger.info(f"[Request {request_id}] Successfully completed processing")
        
        # Finish performance monitoring and log summary
        request_metrics = performance_monitor.finish_request(request_id)
        
        # Log performance improvement metrics
        if request_metrics and request_metrics.total_duration:
            if request_metrics.total_duration < 5.0:
                logger.info(f"[Performance] ✅ Target achieved! Request completed in {request_metrics.total_duration:.3f}s (< 5s target)")
            elif request_metrics.total_duration < 10.0:
                logger.warning(f"[Performance] ⚠️ Close to target: Request completed in {request_metrics.total_duration:.3f}s (target: < 5s)")
            else:
                logger.error(f"[Performance] ❌ Target missed: Request completed in {request_metrics.total_duration:.3f}s (target: < 5s)")
            
            # Log detailed timing breakdown for analysis
            logger.info(f"[Performance] Detailed timing breakdown:")
            for op in request_metrics.operations:
                if op.duration:
                    percentage = (op.duration / request_metrics.total_duration) * 100
                    logger.info(f"[Performance]   {op.operation_name}: {op.duration:.3f}s ({percentage:.1f}%)")
        
        # Log bottleneck analysis
        if request_metrics:
            bottlenecks = request_metrics.identify_bottlenecks()
            if bottlenecks:
                logger.warning(f"[Performance] 🎯 Optimization opportunities identified:")
                for bottleneck in bottlenecks:
                    if bottleneck["type"] == "slowest_operation":
                        logger.warning(f"[Performance]   Focus on: {bottleneck['operation']} (consumes {bottleneck['percentage_of_total']}% of total time)")
                    elif bottleneck["type"] == "threshold_exceeded":
                        logger.warning(f"[Performance]   Optimize: {bottleneck['operation']} (exceeds threshold by {bottleneck['excess']}s)")
            else:
                logger.info(f"[Performance] ✅ No significant bottlenecks detected")
        
        return SubmissionResponse(answers=answers)

    except HTTPException as e:
        logger.warning(f"[Request {request_id}] HTTP exception: {e.detail}")
        raise e
    except asyncio.TimeoutError:
        logger.error(f"[Request {request_id}] Request timeout")
        raise HTTPException(
            status_code=504,
            detail="Request timeout: Processing took longer than expected"
        )
    except CustomExceptions.TimeoutError as e:
        logger.error(f"[Request {request_id}] Operation timeout: {e.operation}")
        raise ErrorHandler.handle_request_error(e, "api_request")
    except CustomExceptions.ExternalServiceError as e:
        logger.error(f"[Request {request_id}] External service error: {e.service}")
        raise ErrorHandler.handle_request_error(e, "api_request")
    except CustomExceptions.DocumentProcessingError as e:
        logger.error(f"[Request {request_id}] Document processing error: {e.operation}")
        raise ErrorHandler.handle_request_error(e, "api_request")
    except CustomExceptions.VectorStoreError as e:
        logger.error(f"[Request {request_id}] Vector store error: {e.operation}")
        raise ErrorHandler.handle_request_error(e, "api_request")
    except Exception as e:
        logger.error(f"[Request {request_id}] Unexpected error: {str(e)}")
        # Finish performance monitoring even on error
        request_metrics = performance_monitor.finish_request(request_id)
        
        # Log performance data even for failed requests for debugging
        if request_metrics and request_metrics.total_duration:
            logger.error(f"[Performance] Failed request duration: {request_metrics.total_duration:.3f}s")
            logger.error(f"[Performance] Operations completed before failure:")
            for op in request_metrics.operations:
                if op.duration:
                    status = "✅" if op.success else "❌"
                    logger.error(f"[Performance]   {status} {op.operation_name}: {op.duration:.3f}s")
        
        raise ErrorHandler.handle_request_error(e, "api_request")

@app.get("/", tags=["Health Check"])
async def read_root():
    return {"status": "ok", "message": "Intelligent Query-Retrieval System is running."}

@app.get("/performance", tags=["Performance"])
async def get_performance_stats():
    """
    Get comprehensive performance statistics and metrics.
    Returns detailed performance data for monitoring and optimization.
    """
    try:
        stats = performance_monitor.get_performance_stats()
        return {
            "status": "success",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "performance_stats": stats
        }
    except Exception as e:
        logger.error(f"[Performance] Error getting performance stats: {str(e)}")
        return {
            "status": "error",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.get("/performance/analysis", tags=["Performance"])
async def get_performance_analysis():
    """
    Get detailed performance analysis with bottleneck identification and optimization recommendations.
    Returns actionable insights for performance improvements.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        stats = performance_monitor.get_performance_stats()
        
        # Generate optimization recommendations
        recommendations = []
        
        # Check overall performance
        avg_duration = stats.get("average_duration", 0)
        if avg_duration > 5.0:
            recommendations.append({
                "priority": "high",
                "category": "overall_performance",
                "issue": f"Average response time ({avg_duration:.2f}s) exceeds 5s target",
                "recommendation": "Focus on optimizing the slowest operations identified in bottleneck analysis"
            })
        
        # Analyze operation performance
        operation_stats = stats.get("operation_stats", {})
        for op_name, op_stats in operation_stats.items():
            threshold_violation_rate = op_stats.get("threshold_violation_rate", 0)
            if threshold_violation_rate > 20:  # More than 20% of operations exceed threshold
                recommendations.append({
                    "priority": "medium",
                    "category": "operation_optimization",
                    "issue": f"{op_name} exceeds threshold in {threshold_violation_rate:.1f}% of cases",
                    "recommendation": f"Optimize {op_name} implementation or increase resources"
                })
            
            # Check for memory issues
            avg_memory_delta = op_stats.get("average_memory_delta", 0)
            if avg_memory_delta > 100:  # More than 100MB average increase
                recommendations.append({
                    "priority": "medium",
                    "category": "memory_optimization",
                    "issue": f"{op_name} uses {avg_memory_delta:.1f}MB memory on average",
                    "recommendation": f"Investigate memory usage in {op_name} and implement memory optimization"
                })
        
        # Check bottleneck patterns
        bottleneck_analysis = stats.get("bottleneck_analysis", {})
        common_bottlenecks = bottleneck_analysis.get("common_bottlenecks", {})
        
        for bottleneck_key, count in common_bottlenecks.items():
            if count > 3:  # Recurring bottleneck
                recommendations.append({
                    "priority": "high",
                    "category": "bottleneck_resolution",
                    "issue": f"Recurring bottleneck: {bottleneck_key} ({count} occurrences)",
                    "recommendation": "This is a consistent performance issue that should be prioritized for optimization"
                })
        
        # Performance trends analysis
        performance_trends = stats.get("performance_trends", {})
        if performance_trends.get("trend") == "degrading":
            improvement_pct = performance_trends.get("improvement_percentage", 0)
            recommendations.append({
                "priority": "high",
                "category": "performance_regression",
                "issue": f"Performance is degrading ({improvement_pct:+.1f}% change)",
                "recommendation": "Investigate recent changes that may have caused performance regression"
            })
        
        return {
            "status": "success",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "performance_analysis": {
                "overall_health": "good" if avg_duration < 5.0 else "needs_attention" if avg_duration < 10.0 else "poor",
                "target_achievement": {
                    "target_response_time": 5.0,
                    "current_average": round(avg_duration, 3),
                    "target_met": avg_duration < 5.0,
                    "improvement_needed": max(0, round(avg_duration - 5.0, 3))
                },
                "recommendations": recommendations,
                "detailed_stats": stats
            }
        }
        
    except Exception as e:
        logger.error(f"[Performance] Error getting performance analysis: {str(e)}")
        return {
            "status": "error",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Comprehensive health check endpoint with detailed component status and performance metrics.
    Returns detailed status of each component with response times.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("[Health] Starting comprehensive health check")
        
        # Perform comprehensive health check with timeout
        health_status = await asyncio.wait_for(
            global_resources.health_check(),
            timeout=30.0  # 30 second timeout for health check
        )
        
        # Add additional system information
        health_status.update({
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "timeout_config": {
                "http_timeout": TimeoutConfig.HTTP_TOTAL_TIMEOUT,
                "llm_timeout": TimeoutConfig.LLM_GENERATION_TIMEOUT,
                "vector_store_timeout": TimeoutConfig.VECTOR_STORE_SEARCH_TIMEOUT,
                "document_timeout": TimeoutConfig.DOCUMENT_DOWNLOAD_TIMEOUT
            }
        })
        
        # Determine HTTP status code
        status_code = 200 if health_status["overall_status"] == "healthy" else 503
        
        logger.info(f"[Health] Health check completed: {health_status['overall_status']}")
        return health_status
        
    except asyncio.TimeoutError:
        logger.error("[Health] Health check timeout")
        return {
            "status": "timeout",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "error": "Health check timed out",
            "overall_status": "unhealthy",
            "components": {
                "pinecone": {"status": "unknown", "error": "timeout"},
                "embeddings": {"status": "unknown", "error": "timeout"},
                "llm": {"status": "unknown", "error": "timeout"}
            },
            "initialized": False
        }
    except Exception as e:
        logger.error(f"[Health] Health check error: {str(e)}")
        return {
            "status": "error",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "error": str(e),
            "overall_status": "unhealthy",
            "components": {
                "pinecone": {"status": "error", "error": str(e)},
                "embeddings": {"status": "error", "error": str(e)},
                "llm": {"status": "error", "error": str(e)}
            },
            "initialized": global_resources.is_initialized() if global_resources else False
        }