from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_pinecone import PineconeVectorStore

from app.tools import create_pinecone_retriever  # Make sure this returns a @tool-decorated function

def get_answers_with_agent(vector_store: PineconeVectorStore, questions: List[str]) -> List[str]:
    """
    Uses a Gemini agent to answer a list of questions by retrieving information
    from the Pinecone vector store using a dedicated tool.
    """
    answers = []

    print("[1] Initializing Gemini LLM...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        convert_system_message_to_human=True  # ✅ Required
    )

    print("[2] Setting up prompt...")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert document query assistant. Use the tools to answer questions, each in 1 paragraph."),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),  # ✅ Correct order
    ])

    print("[3] Creating retriever tool...")
    retriever_tool = create_pinecone_retriever(vector_store=vector_store)  # ✅ Make sure it's a real Tool object

    print("[4] Creating agent...")
    agent = create_tool_calling_agent(llm, [retriever_tool], prompt)

    print("[5] Creating agent executor...")
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=[retriever_tool],
        verbose=True
    )

    print("[6] Running agent on each question...")
    for query in questions:
        print(f"→ Processing query: {query}")
        result = agent_executor.invoke({"input": query})
        answers.append(result["output"].strip())

    print("[7] Done. Returning answers.")
    return answers
