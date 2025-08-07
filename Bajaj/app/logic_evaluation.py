from typing import List
from langchain_pinecone import PineconeVectorStore

from app.direct_answer_generator import DirectAnswerGenerator

def get_answers_with_agent(vector_store: PineconeVectorStore, questions: List[str]) -> List[str]:
    """
    Uses direct retrieval approach to answer a list of questions by retrieving information
    from the Pinecone vector store and generating answers with direct LLM calls.
    This replaces the previous agent-based approach for faster processing.
    """
    print("[1] Initializing DirectAnswerGenerator...")
    answer_generator = DirectAnswerGenerator()

    print("[2] Processing questions with direct retrieval approach...")
    answers = answer_generator.answer_questions_sync(vector_store, questions)

    print("[3] Done. Returning answers.")
    return answers

async def get_answers_async(vector_store: PineconeVectorStore, questions: List[str]) -> List[str]:
    """
    Async version of get_answers_with_agent for better performance.
    Uses direct retrieval approach with parallel question processing.
    """
    print("[1] Initializing DirectAnswerGenerator...")
    answer_generator = DirectAnswerGenerator()

    print("[2] Processing questions in parallel with direct retrieval approach...")
    answers = await answer_generator.answer_questions_parallel(vector_store, questions)

    print("[3] Done. Returning answers.")
    return answers
