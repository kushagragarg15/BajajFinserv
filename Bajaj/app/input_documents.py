# app/input_documents.py
import aiohttp
import aiofiles
import os
import logging
from tempfile import NamedTemporaryFile
from fastapi import HTTPException
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document
from typing import List
import asyncio

from .error_handling import (
    TimeoutConfig, CustomExceptions, ErrorHandler, FallbackMechanisms,
    timeout_handler, retry_handler, http_session_with_timeout
)
from .performance_monitor import timed_operation

# Configure logging
logger = logging.getLogger(__name__)

@timeout_handler(TimeoutConfig.DOCUMENT_DOWNLOAD_TIMEOUT, "document_processing")
@retry_handler(max_retries=3, backoff_factor=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
@timed_operation("document_processing_total")
async def process_document_from_url_async(url: str) -> List[Document]:
    """
    Downloads a PDF from a URL asynchronously with comprehensive error handling,
    processes it, and returns the loaded document text.
    """
    return await ErrorHandler.safe_execute_with_fallback(
        _process_document_primary,
        _process_document_fallback,
        "document_processing",
        url
    )

async def _process_document_primary(url: str) -> List[Document]:
    """Primary document processing function with comprehensive error handling"""
    temp_file_path = None
    
    try:
        logger.info(f"[DocumentProcessor] Starting download from: {url}")
        
        # Validate URL format
        if not url or not isinstance(url, str):
            raise CustomExceptions.DocumentProcessingError(
                "url_validation", 
                "Invalid URL provided"
            )
        
        # Use HTTP session with proper timeout configuration
        async with http_session_with_timeout() as session:
            # Download with timeout and progress tracking
            temp_file_path = await _download_document_with_progress(session, url)
            
            # Process PDF with timeout
            raw_text = await _process_pdf_with_timeout(temp_file_path)
            
            # Validate processed content
            if not raw_text or len(raw_text) == 0:
                raise CustomExceptions.DocumentProcessingError(
                    "content_validation",
                    "No content extracted from document"
                )
            
            logger.info(f"[DocumentProcessor] Successfully processed document: {len(raw_text)} pages")
            return raw_text
            
    except aiohttp.ClientError as e:
        logger.error(f"[DocumentProcessor] HTTP error: {str(e)}")
        raise CustomExceptions.ExternalServiceError("document_download", str(e))
    except asyncio.TimeoutError:
        logger.error(f"[DocumentProcessor] Timeout downloading document from: {url}")
        raise CustomExceptions.TimeoutError("document_download", TimeoutConfig.DOCUMENT_DOWNLOAD_TIMEOUT)
    except CustomExceptions.DocumentProcessingError:
        raise  # Re-raise custom exceptions
    except Exception as e:
        logger.error(f"[DocumentProcessor] Unexpected error: {str(e)}")
        raise CustomExceptions.DocumentProcessingError("unexpected_error", str(e))
    finally:
        # Clean up temporary file with error handling
        await _cleanup_temp_file(temp_file_path)

@timed_operation("document_download")
async def _download_document_with_progress(session: aiohttp.ClientSession, url: str) -> str:
    """Download document with progress tracking and error handling"""
    try:
        async with session.get(url) as response:
            # Check response status
            if response.status != 200:
                raise CustomExceptions.ExternalServiceError(
                    "document_download",
                    f"HTTP {response.status}: {response.reason}"
                )
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                logger.warning(f"[DocumentProcessor] Unexpected content type: {content_type}")
            
            # Check content length
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > 50:  # 50MB limit
                    raise CustomExceptions.DocumentProcessingError(
                        "file_size",
                        f"Document too large: {size_mb:.1f}MB (max 50MB)"
                    )
                logger.info(f"[DocumentProcessor] Downloading {size_mb:.1f}MB document")
            
            # Create temporary file
            with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file_path = temp_file.name
            
            # Download with chunked reading and progress tracking
            downloaded_size = 0
            async with aiofiles.open(temp_file_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    await f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # Log progress for large files
                    if content_length and downloaded_size % (1024 * 1024) == 0:
                        progress = (downloaded_size / int(content_length)) * 100
                        logger.info(f"[DocumentProcessor] Download progress: {progress:.1f}%")
            
            logger.info(f"[DocumentProcessor] Download completed: {downloaded_size} bytes")
            return temp_file_path
            
    except aiohttp.ClientError as e:
        raise CustomExceptions.ExternalServiceError("document_download", str(e))

@timed_operation("pdf_processing")
async def _process_pdf_with_timeout(temp_file_path: str) -> List[Document]:
    """Process PDF with timeout and error handling"""
    try:
        logger.info("[DocumentProcessor] Processing PDF content...")
        
        # Run PDF processing in executor with timeout
        loop = asyncio.get_event_loop()
        raw_text = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: PyPDFLoader(file_path=temp_file_path).load()
            ),
            timeout=TimeoutConfig.DOCUMENT_PROCESSING_TIMEOUT
        )
        
        # Validate extracted content
        if not raw_text:
            raise CustomExceptions.DocumentProcessingError(
                "pdf_processing",
                "No content extracted from PDF"
            )
        
        # Check for reasonable content length
        total_content = sum(len(doc.page_content) for doc in raw_text)
        if total_content < 10:
            raise CustomExceptions.DocumentProcessingError(
                "content_validation",
                "Extracted content is too short (possible processing error)"
            )
        
        logger.info(f"[DocumentProcessor] PDF processed: {len(raw_text)} pages, {total_content} characters")
        return raw_text
        
    except asyncio.TimeoutError:
        raise CustomExceptions.TimeoutError("pdf_processing", TimeoutConfig.DOCUMENT_PROCESSING_TIMEOUT)
    except Exception as e:
        raise CustomExceptions.DocumentProcessingError("pdf_processing", str(e))

async def _cleanup_temp_file(temp_file_path: str) -> None:
    """Clean up temporary file with error handling"""
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.remove(temp_file_path)
            logger.debug(f"[DocumentProcessor] Cleaned up temp file: {temp_file_path}")
        except OSError as e:
            logger.warning(f"[DocumentProcessor] Failed to clean up temp file: {str(e)}")

async def _process_document_fallback(url: str) -> List[Document]:
    """Fallback mechanism for document processing failures"""
    logger.warning(f"[DocumentProcessor] Using fallback for URL: {url}")
    
    # Return a document with fallback content
    fallback_content = await FallbackMechanisms.fallback_document_processing(url)
    
    return [Document(
        page_content=fallback_content,
        metadata={"source": url, "fallback": True}
    )]

# Keep the original synchronous function for backward compatibility
def process_document_from_url(url: str) -> List[Document]:
    """
    Downloads a PDF from a URL, processes it, and returns the loaded document text.
    (Synchronous version - deprecated, use async version instead)
    """
    import requests
    try:
        response = requests.get(url)
        response.raise_for_status()

        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        loader = PyPDFLoader(file_path=temp_file_path)
        raw_text = loader.load()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to download document: {e}")
    finally:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    
    return raw_text