#!/usr/bin/env python3
"""
Simple Test Server

This is a minimal FastAPI server to test if the basic setup works
before running the full optimized application.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Test Server", version="1.0.0")

class SubmissionRequest(BaseModel):
    documents: HttpUrl
    questions: List[str]

class SubmissionResponse(BaseModel):
    answers: List[str]

@app.get("/")
async def read_root():
    return {"status": "ok", "message": "Test server is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/api/v1/hackrx/run", response_model=SubmissionResponse)
async def test_endpoint(request: SubmissionRequest):
    """Test endpoint that returns mock responses"""
    logger.info(f"Received request with {len(request.questions)} questions")
    logger.info(f"Document URL: {request.documents}")
    
    # Validate request
    if not request.questions:
        raise HTTPException(status_code=400, detail="At least one question is required")
    
    if len(request.questions) > 10:
        raise HTTPException(status_code=400, detail="Too many questions (maximum 10 allowed)")
    
    # Return mock answers
    mock_answers = []
    for i, question in enumerate(request.questions):
        mock_answers.append(f"Mock answer {i+1} for question: '{question}'. This is a test response from the simplified server.")
    
    logger.info(f"Returning {len(mock_answers)} mock answers")
    
    return SubmissionResponse(answers=mock_answers)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Test Server...")
    print("Server will be available at: http://localhost:8001")
    print("Health check: http://localhost:8001/health")
    print("API endpoint: http://localhost:8001/api/v1/hackrx/run")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")