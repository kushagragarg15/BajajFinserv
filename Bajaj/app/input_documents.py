# app/input_documents.py
import requests
import os
from tempfile import NamedTemporaryFile
from fastapi import HTTPException
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document
from typing import List

def process_document_from_url(url: str) -> List[Document]:
    """
    Downloads a PDF from a URL, processes it, and returns the loaded document text.
    """
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