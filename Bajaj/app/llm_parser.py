# app/llm_parser.py
import asyncio
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from typing import List

from .error_handling import (
    TimeoutConfig, CustomExceptions, timeout_handler, retry_handler
)
from .performance_monitor import timed_operation

# Configure logging
logger = logging.getLogger(__name__)

@timeout_handler(TimeoutConfig.DOCUMENT_PROCESSING_TIMEOUT, "document_chunking")
@retry_handler(max_retries=2, backoff_factor=1.0, exceptions=(Exception,))
@timed_operation("document_chunking")
async def chunk_document_async(raw_text: List[Document]) -> List[Document]:
    """
    Splits the document into smaller chunks for processing asynchronously with error handling.
    Optimized chunk size and overlap for better performance.
    """
    try:
        logger.info(f"[DocumentChunker] Starting chunking for {len(raw_text)} documents")
        
        # Validate input
        if not raw_text:
            raise CustomExceptions.DocumentProcessingError(
                "chunking",
                "No documents provided for chunking"
            )
        
        # Check total content size
        total_content = sum(len(doc.page_content) for doc in raw_text)
        if total_content == 0:
            raise CustomExceptions.DocumentProcessingError(
                "chunking",
                "Documents contain no content"
            )
        
        if total_content > 1000000:  # 1MB limit
            logger.warning(f"[DocumentChunker] Large document: {total_content} characters")
        
        # Optimized parameters for better performance
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,  # Increased chunk size for better context
            chunk_overlap=150,  # Reduced overlap for faster processing
            length_function=len,
            separators=["\n\n", "\n", " ", ""]  # Better separation strategy
        )
        
        # Run text splitting in executor since it's CPU-bound with timeout
        loop = asyncio.get_event_loop()
        texts = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                text_splitter.split_documents,
                raw_text
            ),
            timeout=TimeoutConfig.DOCUMENT_PROCESSING_TIMEOUT
        )
        
        # Validate output
        if not texts:
            raise CustomExceptions.DocumentProcessingError(
                "chunking",
                "No chunks generated from documents"
            )
        
        # Check for reasonable chunk sizes
        avg_chunk_size = sum(len(chunk.page_content) for chunk in texts) / len(texts)
        if avg_chunk_size < 50:
            logger.warning(f"[DocumentChunker] Small average chunk size: {avg_chunk_size}")
        
        logger.info(f"[DocumentChunker] Successfully created {len(texts)} chunks, avg size: {avg_chunk_size:.0f}")
        return texts
        
    except asyncio.TimeoutError:
        logger.error("[DocumentChunker] Chunking timeout")
        raise CustomExceptions.TimeoutError("document_chunking", TimeoutConfig.DOCUMENT_PROCESSING_TIMEOUT)
    except CustomExceptions.DocumentProcessingError:
        raise  # Re-raise custom exceptions
    except Exception as e:
        logger.error(f"[DocumentChunker] Chunking error: {str(e)}")
        raise CustomExceptions.DocumentProcessingError("chunking", str(e))

# Keep the original synchronous function for backward compatibility
def chunk_document(raw_text: List[Document]) -> List[Document]:
    """
    Splits the document into smaller chunks for processing.
    (Synchronous version - deprecated, use async version instead)
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    texts = text_splitter.split_documents(raw_text)
    return texts