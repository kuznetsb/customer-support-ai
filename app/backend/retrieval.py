from typing import Any

from dependencies.vector_store import get_vector_store_for_settings
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import ToolMessage
from langchain.tools import tool
from langchain_core.documents import Document
from settings import Settings


@tool(response_format="content_and_artifact")
def _retrieve_context(query: str) -> tuple[str, list[Document]]:
    """Retrieve the most relevant support documents for a query.

    Args:
        query: Natural-language question to search for in the vector store.

    Returns:
        Serialized document context for the model and the retrieved documents
        as the tool artifact.
    """
    vector_store = get_vector_store_for_settings()
    retrieved_docs = vector_store.similarity_search(query, k=4)
    serialized = "\n\n".join(
        f"Source: {doc.metadata.get('source', 'unknown')}\n\nContent: {doc.page_content}"
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


def run_llm(query: str, settings: Settings) -> dict[str, Any]:
    """Run the support agent and return its answer with source documents.

    Args:
        query: Customer question to send to the support agent.
        settings: Application settings used to configure the chat model.

    Returns:
        A dictionary containing the generated ``answer`` and retrieved
        documents under ``context``.
    """
    model = init_chat_model(
        settings.ollama.llm_model,
        model_provider="ollama",
        base_url=settings.ollama.base_url,
    )
    system_prompt = (
        "You are a helpful customer support assistant. "
        "Always use the retrieve_context tool to search the support knowledge base "
        "before answering questions. Base your answer only on the retrieved context. "
        "If the context does not contain enough information, respond with "
        '"I don\'t know based on the available support information." '
        "Do not invent policies, orders, dates, or explanations."
    )
    agent = create_agent(
        model=model,
        tools=[_retrieve_context],
        system_prompt=system_prompt,
    )
    response = agent.invoke({"messages": [{"role": "user", "content": query}]})
    answer = response["messages"][-1].content
    context_docs = []
    for message in response["messages"]:
        artifact = getattr(message, "artifact", None)
        if isinstance(message, ToolMessage) and artifact:
            context_docs.extend(artifact)
    return {"answer": answer, "context": context_docs}
