# app/direct_answer_generator.py
import asyncio
import logging
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from app.global_resources import global_resources
from .error_handling import (
    TimeoutConfig, CustomExceptions, ErrorHandler, FallbackMechanisms,
    timeout_handler, retry_handler
)
from .performance_monitor import timed_operation

# Configure logging
logger = logging.getLogger(__name__)


class DirectAnswerGenerator:
    """
    Direct answer generator that replaces agent-based approach with simple
    retrieval + LLM pattern for faster processing. Supports parallel question
    processing using asyncio.
    """
    
    def __init__(self):
        """Initialize the direct answer generator"""
        self.llm = None
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an expert document query assistant. Based on the provided context from relevant documents, answer the question in 1 paragraph. If the context doesn't contain enough information to answer the question, say so clearly."),
            ("human", "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:")
        ])
    
    def _ensure_llm_initialized(self) -> ChatGoogleGenerativeAI:
        """Ensure LLM is initialized from global resources"""
        if self.llm is None:
            if not global_resources.is_initialized():
                raise RuntimeError("Global resources not initialized. Call global_resources.initialize() first.")
            self.llm = global_resources.get_llm()
        return self.llm
    
    @timeout_handler(TimeoutConfig.LLM_GENERATION_TIMEOUT * 3, "parallel_question_processing")
    @timed_operation("parallel_question_processing")
    async def answer_questions_parallel(self, vector_store: PineconeVectorStore, questions: List[str]) -> List[str]:
        """
        Process multiple questions concurrently with comprehensive error handling.
        Maintains correct order corresponding to input questions.
        
        Args:
            vector_store: PineconeVectorStore for document retrieval
            questions: List of questions to answer
            
        Returns:
            List of answers in the same order as input questions
        """
        if not questions:
            logger.warning("[DirectAnswerGenerator] No questions provided")
            return []
        
        logger.info(f"[DirectAnswerGenerator] Processing {len(questions)} questions in parallel...")
        
        try:
            # Validate inputs
            if not vector_store:
                raise CustomExceptions.VectorStoreError(
                    "question_processing",
                    "Vector store not provided"
                )
            
            # Create tasks for parallel processing with individual error handling
            tasks = [
                self._answer_single_question_with_fallback(vector_store, question, idx)
                for idx, question in enumerate(questions)
            ]
            
            # Execute all tasks concurrently with timeout
            results = await asyncio.gather(*tasks, return_exceptions=False)
            
            logger.info(f"[DirectAnswerGenerator] Completed processing {len(questions)} questions.")
            return results
            
        except Exception as e:
            logger.error(f"[DirectAnswerGenerator] Parallel processing failed: {str(e)}")
            # Return fallback answers for all questions
            return [
                await FallbackMechanisms.fallback_answer_generation(q) 
                for q in questions
            ]
    
    async def _answer_single_question_with_fallback(self, vector_store: PineconeVectorStore, question: str, idx: int) -> str:
        """
        Answer a single question with fallback mechanism.
        
        Args:
            vector_store: PineconeVectorStore for document retrieval
            question: Question to answer
            idx: Question index for logging
            
        Returns:
            Generated answer string
        """
        return await ErrorHandler.safe_execute_with_fallback(
            self._answer_single_question,
            lambda vs, q, i: FallbackMechanisms.fallback_answer_generation(q),
            f"question_{idx}",
            vector_store, question, idx
        )

    @timeout_handler(TimeoutConfig.LLM_GENERATION_TIMEOUT, "single_question_processing")
    @retry_handler(max_retries=2, backoff_factor=1.0, exceptions=(CustomExceptions.ExternalServiceError,))
    @timed_operation("single_question_processing")
    async def _answer_single_question(self, vector_store: PineconeVectorStore, question: str, idx: int) -> str:
        """
        Answer a single question using direct retrieval + LLM approach with error handling.
        
        Args:
            vector_store: PineconeVectorStore for document retrieval
            question: Question to answer
            idx: Question index for logging
            
        Returns:
            Generated answer string
        """
        try:
            logger.info(f"[DirectAnswerGenerator] Processing question {idx}: {question[:50]}...")
            
            # Validate question
            if not question or not question.strip():
                raise CustomExceptions.DocumentProcessingError(
                    "question_validation",
                    "Empty or invalid question provided"
                )
            
            # Retrieve relevant documents with timeout
            relevant_docs = await asyncio.wait_for(
                self._retrieve_relevant_docs(vector_store, question),
                timeout=TimeoutConfig.VECTOR_STORE_SEARCH_TIMEOUT
            )
            
            # Generate answer using direct LLM call with timeout
            answer = await asyncio.wait_for(
                self.generate_answer(relevant_docs, question),
                timeout=TimeoutConfig.LLM_GENERATION_TIMEOUT
            )
            
            logger.info(f"[DirectAnswerGenerator] Completed question {idx}")
            return answer
            
        except asyncio.TimeoutError:
            logger.error(f"[DirectAnswerGenerator] Timeout processing question {idx}")
            raise CustomExceptions.TimeoutError(f"question_{idx}", TimeoutConfig.LLM_GENERATION_TIMEOUT)
        except Exception as e:
            logger.error(f"[DirectAnswerGenerator] Error processing question {idx}: {str(e)}")
            raise
    
    @timeout_handler(TimeoutConfig.VECTOR_STORE_SEARCH_TIMEOUT, "document_retrieval")
    @timed_operation("document_retrieval")
    async def _retrieve_relevant_docs(self, vector_store: PineconeVectorStore, question: str, k: int = 3) -> str:
        """
        Retrieve relevant documents from vector store with comprehensive error handling.
        
        Args:
            vector_store: PineconeVectorStore for document retrieval
            question: Question to search for
            k: Number of documents to retrieve
            
        Returns:
            Combined context string from relevant documents
        """
        try:
            logger.debug(f"[DirectAnswerGenerator] Retrieving documents for: {question[:50]}...")
            
            # Validate inputs
            if not vector_store:
                raise CustomExceptions.VectorStoreError(
                    "document_retrieval",
                    "Vector store not available"
                )
            
            if not question.strip():
                raise CustomExceptions.DocumentProcessingError(
                    "document_retrieval",
                    "Empty question provided for retrieval"
                )
            
            # Perform similarity search with error handling
            loop = asyncio.get_event_loop()
            docs = await loop.run_in_executor(
                None,
                lambda: vector_store.similarity_search(question, k=k)
            )
            
            # Validate retrieved documents
            if not docs:
                logger.warning("[DirectAnswerGenerator] No documents retrieved from vector store")
                return await FallbackMechanisms.fallback_vector_search(question)
            
            # Combine document contents into context with size limits
            context_parts = []
            total_length = 0
            max_context_length = 4000  # Limit context size for LLM
            
            for i, doc in enumerate(docs, 1):
                doc_content = doc.page_content.strip()
                if not doc_content:
                    continue
                
                # Truncate if necessary to stay within limits
                if total_length + len(doc_content) > max_context_length:
                    remaining_space = max_context_length - total_length
                    if remaining_space > 100:  # Only add if meaningful space remains
                        doc_content = doc_content[:remaining_space] + "..."
                    else:
                        break
                
                context_parts.append(f"Document {i}:\n{doc_content}")
                total_length += len(doc_content)
            
            if not context_parts:
                logger.warning("[DirectAnswerGenerator] No meaningful content in retrieved documents")
                return await FallbackMechanisms.fallback_vector_search(question)
            
            context = "\n\n".join(context_parts)
            logger.debug(f"[DirectAnswerGenerator] Retrieved context: {len(context)} characters")
            return context
            
        except Exception as e:
            logger.error(f"[DirectAnswerGenerator] Error retrieving documents: {str(e)}")
            raise CustomExceptions.VectorStoreError("document_retrieval", str(e))
    
    @timeout_handler(TimeoutConfig.LLM_GENERATION_TIMEOUT, "answer_generation")
    @retry_handler(max_retries=2, backoff_factor=1.0, exceptions=(CustomExceptions.ExternalServiceError,))
    @timed_operation("llm_answer_generation")
    async def generate_answer(self, context: str, question: str) -> str:
        """
        Generate answer using direct LLM call with comprehensive error handling.
        
        Args:
            context: Retrieved document context
            question: Question to answer
            
        Returns:
            Generated answer string
        """
        try:
            logger.debug(f"[DirectAnswerGenerator] Generating answer for: {question[:50]}...")
            
            # Validate inputs
            if not context or not context.strip():
                logger.warning("[DirectAnswerGenerator] Empty context provided")
                return await FallbackMechanisms.fallback_answer_generation(question)
            
            if not question or not question.strip():
                raise CustomExceptions.DocumentProcessingError(
                    "answer_generation",
                    "Empty question provided"
                )
            
            # Ensure LLM is initialized
            llm = self._ensure_llm_initialized()
            
            # Format the prompt with input validation
            try:
                formatted_prompt = self.prompt_template.format_messages(
                    context=context[:4000],  # Limit context size
                    question=question[:500]   # Limit question size
                )
            except Exception as e:
                raise CustomExceptions.DocumentProcessingError(
                    "prompt_formatting",
                    f"Failed to format prompt: {str(e)}"
                )
            
            # Generate answer using direct LLM call with timeout
            response = await asyncio.wait_for(
                llm.ainvoke(formatted_prompt),
                timeout=TimeoutConfig.LLM_GENERATION_TIMEOUT
            )
            
            # Validate and extract the answer
            if not response or not hasattr(response, 'content'):
                raise CustomExceptions.ExternalServiceError(
                    "llm",
                    "Invalid response from LLM service"
                )
            
            answer = response.content.strip()
            
            # Validate answer quality
            if not answer:
                logger.warning("[DirectAnswerGenerator] Empty answer generated")
                return await FallbackMechanisms.fallback_answer_generation(question)
            
            if len(answer) < 10:
                logger.warning(f"[DirectAnswerGenerator] Suspiciously short answer: {answer}")
            
            logger.debug(f"[DirectAnswerGenerator] Generated answer: {len(answer)} characters")
            return answer
            
        except asyncio.TimeoutError:
            logger.error("[DirectAnswerGenerator] LLM generation timeout")
            raise CustomExceptions.TimeoutError("answer_generation", TimeoutConfig.LLM_GENERATION_TIMEOUT)
        except CustomExceptions.ExternalServiceError:
            raise  # Re-raise custom exceptions
        except Exception as e:
            logger.error(f"[DirectAnswerGenerator] Error generating answer: {str(e)}")
            raise CustomExceptions.ExternalServiceError("llm", str(e))
    
    def answer_questions_sync(self, vector_store: PineconeVectorStore, questions: List[str]) -> List[str]:
        """
        Synchronous wrapper for answer_questions_parallel for backward compatibility.
        
        Args:
            vector_store: PineconeVectorStore for document retrieval
            questions: List of questions to answer
            
        Returns:
            List of answers in the same order as input questions
        """
        return asyncio.run(self.answer_questions_parallel(vector_store, questions))