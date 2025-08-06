# app/embedding_search.py
import os
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore as PineconeLangChain
from langchain.schema import Document
from typing import List

def create_vector_store(texts: List[Document]) -> PineconeLangChain:
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = "hackrx-query-index"

    pc = Pinecone(api_key=api_key)

    try:
        pc.describe_index(index_name)
        print(f"Index '{index_name}' already exists.")
    except Exception:
        print(f"Index '{index_name}' does not exist. Creating it now...")
        pc.create_index(
            name=index_name,
            dimension=768,  # ✅ FIXED
            metric='cosine',
            spec=ServerlessSpec(cloud='aws', region='us-east-1')
        )

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    vector_store = PineconeLangChain.from_documents(texts, embeddings, index_name=index_name)
    return vector_store
