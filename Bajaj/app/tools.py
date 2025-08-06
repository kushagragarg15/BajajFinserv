from langchain_core.tools import tool
from langchain_pinecone import PineconeVectorStore
from typing import List


def create_pinecone_retriever(vector_store: PineconeVectorStore):
    """
    Returns a LangChain Tool for querying a Pinecone vector store.
    """

    @tool
    def pinecone_retriever(query: str) -> List[str]:
        """Searches for relevant document chunks in the Pinecone vector store based on a query."""
        if not vector_store:
            return ["Vector store not available or improperly initialized."]
        docs = vector_store.similarity_search(query, k=3)
        return [doc.page_content for doc in docs]

    return pinecone_retriever
