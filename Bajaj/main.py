# main.py
import sys
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, HttpUrl
from typing import List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Import the modularized components
from app.input_documents import process_document_from_url
from app.llm_parser import chunk_document
from app.embedding_search import create_vector_store
from app.logic_evaluation import get_answers_with_agent

# --- Configuration & Initialization ---
load_dotenv()
app = FastAPI(
    title="Intelligent Query-Retrieval System",
    description="An API for processing documents and answering questions using LLMs and vector search.",
    version="1.0.0"
)

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
async def run_submission(
    request: SubmissionRequest,
    api_key: str = Depends(get_api_key)
):
    try:
        # Step 1: Input Documents
        raw_text = process_document_from_url(request.documents)

        # Step 2: LLM Parser (Chunking)
        texts = chunk_document(raw_text)

        # Step 3: Embedding Search
        # The vector store is now a Pinecone index object
        vector_store = create_vector_store(texts)

        # The agent uses the vector store to answer questions
        answers = get_answers_with_agent(vector_store, request.questions)
        
        return SubmissionResponse(answers=answers)

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@app.get("/", tags=["Health Check"])
async def read_root():
    return {"status": "ok", "message": "Intelligent Query-Retrieval System is running."}