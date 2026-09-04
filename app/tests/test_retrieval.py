from types import SimpleNamespace

from backend import retrieval
from langchain.messages import ToolMessage
from langchain_core.documents import Document
from settings import Settings


def test_retrieve_context_searches_and_serializes_documents(monkeypatch) -> None:
    documents = [
        Document(
            page_content="Refunds are available within 30 days.",
            metadata={"source": "returns.md"},
        ),
        Document(page_content="Contact support for help."),
    ]

    class FakeVectorStore:
        def similarity_search(self, query, k):
            assert query == "How long do I have to request a refund?"
            assert k == 4
            return documents

    monkeypatch.setattr(
        retrieval,
        "get_vector_store_for_settings",
        lambda: FakeVectorStore(),
    )

    serialized, artifact = retrieval._retrieve_context.func(
        "How long do I have to request a refund?"
    )

    assert serialized == (
        "Source: returns.md\n\nContent: Refunds are available within 30 days.\n\n"
        "Source: unknown\n\nContent: Contact support for help."
    )
    assert artifact == documents


def test_run_llm_returns_answer_and_retrieved_context(monkeypatch) -> None:
    settings = Settings()
    context_documents = [Document(page_content="Relevant context")]
    model = object()
    agent = SimpleNamespace(
        invoke=lambda message: {
            "messages": [
                ToolMessage(
                    content="Relevant context",
                    tool_call_id="call-1",
                    artifact=context_documents,
                ),
                SimpleNamespace(content="The answer"),
            ]
        }
    )
    captured = {}

    def fake_init_chat_model(model_name, *, model_provider, base_url):
        captured["model"] = (model_name, model_provider, base_url)
        return model

    def fake_create_agent(*, model, tools, system_prompt):
        captured["agent"] = (model, tools, system_prompt)
        return agent

    monkeypatch.setattr(retrieval, "init_chat_model", fake_init_chat_model)
    monkeypatch.setattr(retrieval, "create_agent", fake_create_agent)

    result = retrieval.run_llm("Where is my order?", settings)

    assert result == {"answer": "The answer", "context": context_documents}
    assert captured["model"] == (
        settings.ollama.llm_model,
        "ollama",
        settings.ollama.base_url,
    )
    assert captured["agent"][0] is model
    assert captured["agent"][1] == [retrieval._retrieve_context]
    assert "provided context" in captured["agent"][2]
