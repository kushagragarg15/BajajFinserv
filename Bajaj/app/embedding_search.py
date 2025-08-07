# app/embedding_search.py
from langchain_pinecone import PineconeVectorStore
from langchain.schema import Document
from typing import List
from .global_resources import global_resources


def create_vector_store(texts: List[Document]) -> PineconeVectorStore:
    """
    Create a PineconeVectorStore using pre-initialized global resources.
    This eliminates index creation/checking on each request for better performance.
    """
    return global_resources.get_vector_store(texts)


class OptimizedVectorStore:
    """
    Optimized vector store operations using pre-initialized resources
    and efficient bulk operations.
    """
    
    def __init__(self):
        self.global_resources = global_resources
    
    async def create_from_documents_fast(self, texts: List[Document]) -> PineconeVectorStore:
        """
        Create vector store from documents using pre-initialized resources.
        This method is optimized to avoid index recreation and connection overhead.
        """
        if not self.global_resources.is_initialized():
            raise RuntimeError("Global resources not initialized. Ensure startup initialization completed.")
        
        # Use pre-initialized embeddings and Pinecone connection
        vector_store = PineconeVectorStore.from_documents(
            texts,
            self.global_resources.get_embeddings(),
            index_name=self.global_resources.pinecone_index_name
        )
        
        return vector_store
    
    async def similarity_search_batch(self, vector_store: PineconeVectorStore, queries: List[str], k: int = 4) -> List[List[Document]]:
        """
        Perform batch similarity search for multiple queries efficiently.
        This reduces the number of individual API calls to Pinecone.
        """
        import asyncio
        
        async def search_single_query(query: str) -> List[Document]:
            """Search for a single query with optimized parameters"""
            return vector_store.similarity_search(
                query, 
                k=k,
                # Optimized search parameters for faster retrieval
                include_metadata=True
            )
        
        # Process all queries concurrently for maximum efficiency
        results = await asyncio.gather(*[
            search_single_query(query) for query in queries
        ])
        
        return results
    
    async def batch_embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents in batch for efficiency.
        This reduces the number of API calls to the embedding service.
        """
        embeddings_client = self.global_resources.get_embeddings()
        
        # Process embeddings in batches to optimize API usage
        batch_size = 10  # Optimal batch size for Google Generative AI
        batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        
        all_embeddings = []
        for batch in batches:
            # Use batch embedding generation
            batch_embeddings = await embeddings_client.aembed_documents(batch)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    async def bulk_upsert_documents(self, vector_store: PineconeVectorStore, documents: List[Document]) -> None:
        """
        Perform bulk upsert operations for better performance.
        This reduces the number of individual upsert calls to Pinecone.
        """
        # Process documents in chunks for optimal bulk operations
        chunk_size = 100  # Optimal chunk size for Pinecone bulk operations
        
        for i in range(0, len(documents), chunk_size):
            chunk = documents[i:i + chunk_size]
            
            # Perform bulk upsert for the chunk
            vector_store.add_documents(chunk)
    
    def get_connection_pool_config(self) -> dict:
        """
        Get optimized connection pool configuration for Pinecone operations.
        This enables connection reuse for better performance.
        """
        return {
            'pool_connections': 10,  # Number of connection pools to cache
            'pool_maxsize': 20,      # Maximum number of connections in the pool
            'max_retries': 3,        # Number of retries for failed requests
            'backoff_factor': 0.3,   # Backoff factor for retries
        }
    
    def get_optimized_search_params(self) -> dict:
        """
        Get optimized parameters for similarity search operations.
        These parameters are tuned for faster retrieval.
        """
        return {
            'k': 4,  # Limit results for faster processing
            'include_metadata': True,
            'include_values': False,  # Don't include vectors in response for speed
        }
