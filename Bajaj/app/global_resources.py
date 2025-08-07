# app/global_resources.py
import os
import asyncio
import logging
from typing import Optional
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_pinecone import PineconeVectorStore
from langchain.schema import Document
from typing import List

from .error_handling import (
    TimeoutConfig, CustomExceptions, ErrorHandler, 
    timeout_handler, retry_handler, HealthChecker
)
from .performance_monitor import timed_operation

# Configure logging
logger = logging.getLogger(__name__)


class GlobalResources:
    """
    Singleton class to manage global resources that are expensive to initialize.
    This ensures Pinecone connection, embeddings, and LLM client are created once
    at startup and reused across requests.
    """
    
    _instance: Optional['GlobalResources'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'GlobalResources':
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(GlobalResources, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize instance variables (only called once due to singleton)"""
        if not self._initialized:
            self.pinecone_client: Optional[Pinecone] = None
            self.pinecone_index_name: str = "hackrx-query-index"
            self.embeddings: Optional[GoogleGenerativeAIEmbeddings] = None
            self.llm: Optional[ChatGoogleGenerativeAI] = None
            self._initialized = True
    
    @timed_operation("global_resources_initialization")
    async def initialize(self) -> None:
        """
        Initialize all expensive resources once at startup with comprehensive error handling.
        This method should be called during FastAPI startup event.
        """
        logger.info("[GlobalResources] Initializing global resources...")
        
        try:
            # Initialize resources with timeout and error handling
            await asyncio.gather(
                self._initialize_pinecone_with_retry(),
                self._initialize_embeddings_with_retry(),
                self._initialize_llm_with_retry(),
                return_exceptions=False  # Fail fast if any initialization fails
            )
            
            # Verify all resources are properly initialized
            if not self.is_initialized():
                raise CustomExceptions.ResourceInitializationError(
                    "global_resources", 
                    "One or more resources failed to initialize properly"
                )
            
            logger.info("[GlobalResources] All resources initialized successfully!")
            
        except Exception as e:
            logger.critical(f"[GlobalResources] Failed to initialize: {str(e)}")
            ErrorHandler.handle_startup_error(e, "global_resources")
    
    @timeout_handler(TimeoutConfig.PINECONE_CONNECT_TIMEOUT, "pinecone_initialization")
    @retry_handler(max_retries=3, backoff_factor=2.0, exceptions=(Exception,))
    async def _initialize_pinecone_with_retry(self) -> None:
        """Initialize Pinecone connection with timeout and retry logic"""
        await self._initialize_pinecone()
    
    @timed_operation("pinecone_initialization")
    async def _initialize_pinecone(self) -> None:
        """Initialize Pinecone connection and ensure index exists"""
        logger.info("[GlobalResources] Initializing Pinecone connection...")
        
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                raise CustomExceptions.ResourceInitializationError(
                    "pinecone", 
                    "PINECONE_API_KEY environment variable is required"
                )
            
            # Initialize Pinecone client with optimized connection settings
            self.pinecone_client = Pinecone(
                api_key=api_key,
                pool_threads=4,  # Number of threads for connection pool
            )
            
            # Test connection with timeout
            await asyncio.wait_for(
                self._ensure_index_exists(),
                timeout=TimeoutConfig.PINECONE_OPERATION_TIMEOUT
            )
            
            logger.info("[GlobalResources] Pinecone initialized successfully.")
            
        except asyncio.TimeoutError:
            raise CustomExceptions.TimeoutError("pinecone_initialization", TimeoutConfig.PINECONE_CONNECT_TIMEOUT)
        except Exception as e:
            logger.error(f"[GlobalResources] Pinecone initialization failed: {str(e)}")
            raise CustomExceptions.ResourceInitializationError("pinecone", str(e))
    
    async def _ensure_index_exists(self) -> None:
        """Ensure Pinecone index exists, create if it doesn't"""
        try:
            # Check if index exists
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self.pinecone_client.describe_index, 
                self.pinecone_index_name
            )
            logger.info(f"[GlobalResources] Index '{self.pinecone_index_name}' already exists.")
            
        except Exception:
            logger.info(f"[GlobalResources] Index '{self.pinecone_index_name}' does not exist. Creating it now...")
            
            # Create index in executor to avoid blocking
            await loop.run_in_executor(
                None,
                lambda: self.pinecone_client.create_index(
                    name=self.pinecone_index_name,
                    dimension=768,  # Google Generative AI embeddings dimension
                    metric='cosine',
                    spec=ServerlessSpec(cloud='aws', region='us-east-1')
                )
            )
            
            logger.info(f"[GlobalResources] Index '{self.pinecone_index_name}' created successfully.")
            
            # Wait for index to be ready with timeout
            await asyncio.sleep(10)  # Allow index initialization to complete
    
    @timeout_handler(TimeoutConfig.LLM_EMBEDDING_TIMEOUT, "embeddings_initialization")
    @retry_handler(max_retries=3, backoff_factor=1.5, exceptions=(Exception,))
    async def _initialize_embeddings_with_retry(self) -> None:
        """Initialize embeddings with timeout and retry logic"""
        await self._initialize_embeddings()
    
    async def _initialize_embeddings(self) -> None:
        """Initialize Google Generative AI embeddings with error handling"""
        logger.info("[GlobalResources] Initializing embeddings...")
        
        try:
            # Check for required API key
            if not os.getenv("GOOGLE_API_KEY"):
                raise CustomExceptions.ResourceInitializationError(
                    "embeddings",
                    "GOOGLE_API_KEY environment variable is required"
                )
            
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                # Add timeout configuration
                request_timeout=TimeoutConfig.LLM_EMBEDDING_TIMEOUT
            )
            
            # Test embeddings with a simple query
            await self._test_embeddings()
            
            logger.info("[GlobalResources] Embeddings initialized successfully.")
            
        except Exception as e:
            logger.error(f"[GlobalResources] Embeddings initialization failed: {str(e)}")
            raise CustomExceptions.ResourceInitializationError("embeddings", str(e))
    
    async def _test_embeddings(self) -> None:
        """Test embeddings functionality"""
        try:
            test_text = "test embedding"
            await asyncio.wait_for(
                self.embeddings.aembed_query(test_text),
                timeout=TimeoutConfig.LLM_EMBEDDING_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise CustomExceptions.TimeoutError("embeddings_test", TimeoutConfig.LLM_EMBEDDING_TIMEOUT)
        except Exception as e:
            raise CustomExceptions.ExternalServiceError("embeddings", str(e))
    
    @timeout_handler(TimeoutConfig.LLM_GENERATION_TIMEOUT, "llm_initialization")
    @retry_handler(max_retries=3, backoff_factor=1.5, exceptions=(Exception,))
    async def _initialize_llm_with_retry(self) -> None:
        """Initialize LLM with timeout and retry logic"""
        await self._initialize_llm()
    
    async def _initialize_llm(self) -> None:
        """Initialize ChatGoogleGenerativeAI LLM client with error handling"""
        logger.info("[GlobalResources] Initializing LLM client...")
        
        try:
            # Check for required API key
            if not os.getenv("GOOGLE_API_KEY"):
                raise CustomExceptions.ResourceInitializationError(
                    "llm",
                    "GOOGLE_API_KEY environment variable is required"
                )
            
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0,
                convert_system_message_to_human=True,
                # Add timeout configuration
                request_timeout=TimeoutConfig.LLM_GENERATION_TIMEOUT
            )
            
            # Test LLM with a simple query
            await self._test_llm()
            
            logger.info("[GlobalResources] LLM client initialized successfully.")
            
        except Exception as e:
            logger.error(f"[GlobalResources] LLM initialization failed: {str(e)}")
            raise CustomExceptions.ResourceInitializationError("llm", str(e))
    
    async def _test_llm(self) -> None:
        """Test LLM functionality"""
        try:
            from langchain_core.messages import HumanMessage
            test_message = [HumanMessage(content="Hello")]
            
            await asyncio.wait_for(
                self.llm.ainvoke(test_message),
                timeout=TimeoutConfig.LLM_GENERATION_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise CustomExceptions.TimeoutError("llm_test", TimeoutConfig.LLM_GENERATION_TIMEOUT)
        except Exception as e:
            raise CustomExceptions.ExternalServiceError("llm", str(e))
    
    def get_vector_store(self, texts: List[Document]) -> PineconeVectorStore:
        """
        Create a PineconeVectorStore using pre-initialized resources with error handling.
        This replaces the create_vector_store function to avoid index recreation.
        """
        try:
            if not self.embeddings:
                raise CustomExceptions.ResourceInitializationError(
                    "embeddings", 
                    "Embeddings not initialized. Call initialize() first."
                )
            
            if not self.pinecone_client:
                raise CustomExceptions.ResourceInitializationError(
                    "pinecone", 
                    "Pinecone client not initialized. Call initialize() first."
                )
            
            # Create vector store using pre-initialized resources with optimized settings
            vector_store = PineconeVectorStore.from_documents(
                texts, 
                self.embeddings, 
                index_name=self.pinecone_index_name,
                batch_size=100,  # Optimize batch size for bulk operations
            )
            
            return vector_store
            
        except Exception as e:
            logger.error(f"[GlobalResources] Vector store creation failed: {str(e)}")
            raise CustomExceptions.VectorStoreError("create_vector_store", str(e))
    
    def get_vector_store_from_existing_index(self) -> PineconeVectorStore:
        """
        Create a PineconeVectorStore from existing index with error handling.
        This is useful for search operations without document insertion.
        """
        try:
            if not self.embeddings:
                raise CustomExceptions.ResourceInitializationError(
                    "embeddings", 
                    "Embeddings not initialized. Call initialize() first."
                )
            
            if not self.pinecone_client:
                raise CustomExceptions.ResourceInitializationError(
                    "pinecone", 
                    "Pinecone client not initialized. Call initialize() first."
                )
            
            # Create vector store from existing index for search operations
            vector_store = PineconeVectorStore(
                embedding=self.embeddings,
                index_name=self.pinecone_index_name
            )
            
            return vector_store
            
        except Exception as e:
            logger.error(f"[GlobalResources] Vector store from existing index failed: {str(e)}")
            raise CustomExceptions.VectorStoreError("get_existing_vector_store", str(e))
    
    def get_llm(self) -> ChatGoogleGenerativeAI:
        """Get the pre-initialized LLM client with error handling"""
        if not self.llm:
            raise CustomExceptions.ResourceInitializationError(
                "llm", 
                "LLM not initialized. Call initialize() first."
            )
        return self.llm
    
    def get_embeddings(self) -> GoogleGenerativeAIEmbeddings:
        """Get the pre-initialized embeddings with error handling"""
        if not self.embeddings:
            raise CustomExceptions.ResourceInitializationError(
                "embeddings", 
                "Embeddings not initialized. Call initialize() first."
            )
        return self.embeddings
    
    async def health_check(self) -> dict:
        """
        Perform comprehensive health check of all resources.
        Returns detailed status of each component.
        """
        health_results = {}
        
        # Check Pinecone health
        health_results["pinecone"] = await HealthChecker.check_external_service_health(
            "pinecone",
            self._check_pinecone_health
        )
        
        # Check embeddings health
        health_results["embeddings"] = await HealthChecker.check_external_service_health(
            "embeddings",
            self._check_embeddings_health
        )
        
        # Check LLM health
        health_results["llm"] = await HealthChecker.check_external_service_health(
            "llm",
            self._check_llm_health
        )
        
        # Overall health status
        all_healthy = all(
            result["status"] == "healthy" 
            for result in health_results.values()
        )
        
        return {
            "overall_status": "healthy" if all_healthy else "unhealthy",
            "components": health_results,
            "initialized": self.is_initialized()
        }
    
    async def _check_pinecone_health(self) -> None:
        """Check Pinecone connection health"""
        if not self.pinecone_client:
            raise Exception("Pinecone client not initialized")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.pinecone_client.describe_index,
            self.pinecone_index_name
        )
    
    async def _check_embeddings_health(self) -> None:
        """Check embeddings service health"""
        if not self.embeddings:
            raise Exception("Embeddings not initialized")
        
        await self.embeddings.aembed_query("health check")
    
    async def _check_llm_health(self) -> None:
        """Check LLM service health"""
        if not self.llm:
            raise Exception("LLM not initialized")
        
        from langchain_core.messages import HumanMessage
        await self.llm.ainvoke([HumanMessage(content="health check")])
    
    def is_initialized(self) -> bool:
        """Check if all resources are properly initialized"""
        return (
            self.pinecone_client is not None and
            self.embeddings is not None and
            self.llm is not None
        )


# Global instance to be used throughout the application
global_resources = GlobalResources()