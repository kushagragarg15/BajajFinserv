# app/error_handling.py
import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar, Union
from functools import wraps
from contextlib import asynccontextmanager
import aiohttp
from fastapi import HTTPException

# Configure logging for error tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variable for generic function decoration
T = TypeVar('T')

# Timeout configurations for different operations
class TimeoutConfig:
    """Centralized timeout configuration for all external API calls"""
    
    # HTTP request timeouts
    HTTP_CONNECT_TIMEOUT = 10.0  # Connection timeout in seconds
    HTTP_READ_TIMEOUT = 30.0     # Read timeout in seconds
    HTTP_TOTAL_TIMEOUT = 60.0    # Total request timeout in seconds
    
    # Pinecone operation timeouts
    PINECONE_CONNECT_TIMEOUT = 15.0
    PINECONE_OPERATION_TIMEOUT = 45.0
    
    # LLM operation timeouts
    LLM_GENERATION_TIMEOUT = 30.0
    LLM_EMBEDDING_TIMEOUT = 20.0
    
    # Document processing timeouts
    DOCUMENT_DOWNLOAD_TIMEOUT = 120.0  # Large PDFs may take time
    DOCUMENT_PROCESSING_TIMEOUT = 60.0
    
    # Vector store operation timeouts
    VECTOR_STORE_CREATE_TIMEOUT = 90.0
    VECTOR_STORE_SEARCH_TIMEOUT = 30.0


class CustomExceptions:
    """Custom exception classes for different types of failures"""
    
    class TimeoutError(Exception):
        """Raised when an operation times out"""
        def __init__(self, operation: str, timeout: float):
            self.operation = operation
            self.timeout = timeout
            super().__init__(f"Operation '{operation}' timed out after {timeout} seconds")
    
    class ExternalServiceError(Exception):
        """Raised when external service calls fail"""
        def __init__(self, service: str, error: str):
            self.service = service
            self.error = error
            super().__init__(f"External service '{service}' error: {error}")
    
    class ResourceInitializationError(Exception):
        """Raised when global resources fail to initialize"""
        def __init__(self, resource: str, error: str):
            self.resource = resource
            self.error = error
            super().__init__(f"Failed to initialize resource '{resource}': {error}")
    
    class DocumentProcessingError(Exception):
        """Raised when document processing fails"""
        def __init__(self, operation: str, error: str):
            self.operation = operation
            self.error = error
            super().__init__(f"Document processing error in '{operation}': {error}")
    
    class VectorStoreError(Exception):
        """Raised when vector store operations fail"""
        def __init__(self, operation: str, error: str):
            self.operation = operation
            self.error = error
            super().__init__(f"Vector store error in '{operation}': {error}")


def timeout_handler(timeout_seconds: float, operation_name: str):
    """
    Decorator to add timeout handling to async functions.
    
    Args:
        timeout_seconds: Maximum time to wait for operation
        operation_name: Name of the operation for error messages
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), 
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout in {operation_name} after {timeout_seconds} seconds")
                raise CustomExceptions.TimeoutError(operation_name, timeout_seconds)
            except Exception as e:
                logger.error(f"Error in {operation_name}: {str(e)}")
                raise
        return wrapper
    return decorator


def retry_handler(max_retries: int = 3, backoff_factor: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Decorator to add retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor for exponential backoff
        exceptions: Tuple of exceptions to retry on
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {str(e)}")
                        raise
                    
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {wait_time}s: {str(e)}")
                    await asyncio.sleep(wait_time)
            
            # This should never be reached, but just in case
            raise last_exception
        return wrapper
    return decorator


@asynccontextmanager
async def http_session_with_timeout():
    """
    Context manager for HTTP sessions with proper timeout configuration.
    Provides fallback mechanisms for connection failures.
    """
    timeout = aiohttp.ClientTimeout(
        total=TimeoutConfig.HTTP_TOTAL_TIMEOUT,
        connect=TimeoutConfig.HTTP_CONNECT_TIMEOUT,
        sock_read=TimeoutConfig.HTTP_READ_TIMEOUT
    )
    
    connector = aiohttp.TCPConnector(
        limit=100,  # Connection pool limit
        limit_per_host=30,  # Per-host connection limit
        ttl_dns_cache=300,  # DNS cache TTL
        use_dns_cache=True,
        keepalive_timeout=30,
        enable_cleanup_closed=True
    )
    
    try:
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'User-Agent': 'Bajaj-QuerySystem/1.0'}
        ) as session:
            yield session
    except Exception as e:
        logger.error(f"HTTP session error: {str(e)}")
        raise CustomExceptions.ExternalServiceError("HTTP", str(e))


class FallbackMechanisms:
    """Fallback mechanisms for critical failures"""
    
    @staticmethod
    async def fallback_document_processing(url: str) -> str:
        """
        Fallback mechanism for document processing failures.
        Returns a basic error message when document processing fails.
        """
        logger.warning(f"Using fallback for document processing: {url}")
        return "Document processing failed. Please try again with a different document or check the URL."
    
    @staticmethod
    async def fallback_answer_generation(question: str) -> str:
        """
        Fallback mechanism for answer generation failures.
        Returns a helpful error message when LLM generation fails.
        """
        logger.warning(f"Using fallback for answer generation: {question[:50]}...")
        return "I'm sorry, I couldn't generate an answer for this question due to a technical issue. Please try rephrasing your question or try again later."
    
    @staticmethod
    async def fallback_vector_search(question: str) -> str:
        """
        Fallback mechanism for vector search failures.
        Returns a basic response when vector search fails.
        """
        logger.warning(f"Using fallback for vector search: {question[:50]}...")
        return "I couldn't search the document for relevant information. Please ensure the document was processed correctly and try again."
    
    @staticmethod
    def get_fallback_response(operation: str, error: str) -> dict:
        """
        Generate a structured fallback response for API endpoints.
        
        Args:
            operation: Name of the failed operation
            error: Error message
            
        Returns:
            Structured error response
        """
        return {
            "status": "error",
            "operation": operation,
            "message": f"Operation failed: {operation}",
            "error": error,
            "fallback_used": True,
            "suggestion": "Please try again later or contact support if the issue persists."
        }


class ErrorHandler:
    """Centralized error handling for the application"""
    
    @staticmethod
    def handle_startup_error(error: Exception, resource: str) -> None:
        """
        Handle errors during application startup.
        These are critical errors that should prevent the app from starting.
        """
        logger.critical(f"Startup error in {resource}: {str(error)}")
        raise CustomExceptions.ResourceInitializationError(resource, str(error))
    
    @staticmethod
    def handle_request_error(error: Exception, operation: str) -> HTTPException:
        """
        Handle errors during request processing.
        Convert internal errors to appropriate HTTP responses.
        """
        logger.error(f"Request error in {operation}: {str(error)}")
        
        if isinstance(error, CustomExceptions.TimeoutError):
            return HTTPException(
                status_code=504,
                detail=f"Request timeout: {error.operation} took longer than {error.timeout} seconds"
            )
        elif isinstance(error, CustomExceptions.ExternalServiceError):
            return HTTPException(
                status_code=502,
                detail=f"External service error: {error.service} - {error.error}"
            )
        elif isinstance(error, CustomExceptions.DocumentProcessingError):
            return HTTPException(
                status_code=422,
                detail=f"Document processing failed: {error.operation} - {error.error}"
            )
        elif isinstance(error, CustomExceptions.VectorStoreError):
            return HTTPException(
                status_code=503,
                detail=f"Vector store error: {error.operation} - {error.error}"
            )
        else:
            # Generic error handling
            return HTTPException(
                status_code=500,
                detail=f"Internal server error in {operation}: {str(error)}"
            )
    
    @staticmethod
    async def safe_execute_with_fallback(
        primary_func: Callable,
        fallback_func: Callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with fallback mechanism.
        If primary function fails, execute fallback function.
        """
        try:
            return await primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary function failed for {operation_name}, using fallback: {str(e)}")
            try:
                return await fallback_func(*args, **kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed for {operation_name}: {str(fallback_error)}")
                raise CustomExceptions.ExternalServiceError(operation_name, str(e))


# Health check utilities
class HealthChecker:
    """Health check utilities for monitoring system status"""
    
    @staticmethod
    async def check_external_service_health(service_name: str, check_func: Callable) -> dict:
        """
        Check the health of an external service.
        
        Args:
            service_name: Name of the service to check
            check_func: Async function to perform the health check
            
        Returns:
            Health status dictionary
        """
        try:
            start_time = asyncio.get_event_loop().time()
            await asyncio.wait_for(check_func(), timeout=10.0)
            end_time = asyncio.get_event_loop().time()
            
            return {
                "service": service_name,
                "status": "healthy",
                "response_time": round(end_time - start_time, 3),
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            }
        except asyncio.TimeoutError:
            return {
                "service": service_name,
                "status": "timeout",
                "error": "Health check timed out",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "service": service_name,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            }