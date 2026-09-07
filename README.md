# Dropship.IO Customer Support AI

Dropship.IO Customer Support AI is a pet project that demonstrates how modern
AI capabilities can be integrated into a real-world customer-support workflow.
It is aimed at providing augmented customer support for Dropship.IO through a
chatbot that can search an internal knowledge base before answering a question.

The project is also a practical demonstration of AI integration patterns for a
business and product I have worked with. It combines a local language model,
document ingestion, vector search, retrieval-augmented generation (RAG), and a
Streamlit interface into one runnable application.

## Main Purpose

The chatbot is intended to help a support agent or customer by:

- answering questions about the Dropship.IO platform and its workflows;
- grounding support answers in indexed product documentation;
- showing the retrieved context used to produce each answer;
- running locally with open-source services instead of requiring a hosted LLM;
- providing traceability through application logs and optional LangSmith traces.

This is a demonstration project, not a production support system. The sample
knowledge base and model behavior are intentionally limited, and production
deployment would require stronger access control, evaluation, monitoring,
privacy safeguards, and operational hardening.

## How It Works

The current workflow is:

1. The application loads Markdown files from `data/`.
2. Markdown headings are preserved as section metadata and context.
3. Documents are split into chunks and stored in PostgreSQL with PGVector.
4. Ollama creates embeddings for the chunks.
5. A user question is passed to the LangChain agent.
6. The retrieval tool performs a similarity search over the vector store.
7. The model uses the retrieved context to formulate an answer.
8. The UI displays the answer and the retrieved source chunks.

The vector store and embedding objects are cached as configuration-keyed
singletons. This allows ingestion and retrieval to reuse the same resources
without creating a new PGVector connection for every request.

## Project Structure

```text
app/
	backend/
		ingestion.py       Markdown loading, chunking, and vector indexing
		retrieval.py       Retrieval tool and LLM agent orchestration
	dependencies/
		vector_store.py    Cached embeddings and PGVector factories
	main.py              Streamlit application and chat interface
	settings.py          Environment-backed application settings
	logging_config.py    Structured application logging and trace IDs
	tests/               Unit tests for ingestion, retrieval, and logging
data/
	guide_dropship_knowledge_ingestion.md
scripts/
	init-ollama.sh       Starts Ollama and downloads configured models
docker-compose.yml     PostgreSQL, Ollama, and Streamlit services
Dockerfile             Application container definition
```

## Prerequisites

For the Docker-based setup, install:

- Docker Desktop with Docker Compose;
- Git.

For running the Python test suite locally, also install:

- Python 3.14 or a compatible interpreter;
- [uv](https://docs.astral.sh/uv/).

## Run Locally With Docker Compose

1. Create the local environment file:

	 ```bash
	 cp .env.sample .env
	 ```

2. Start PostgreSQL, Ollama, and Streamlit:

	 ```bash
	 docker compose up -d
	 ```

	 The first startup may take several minutes because Ollama downloads the
	 configured embedding and chat models.

3. Open the application:

	 ```text
	 http://localhost:8501
	 ```

The application ingests the Markdown knowledge base when the Streamlit app is
first opened. PostgreSQL and Ollama data are stored in Docker volumes, so they
survive normal container restarts.

Useful commands:

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f ollama
docker compose restart app
docker compose down
```

To remove the persisted PostgreSQL and Ollama data and start from scratch:

```bash
docker compose down -v
docker compose up -d
```

Use this only when you intentionally want to delete the local vector store and
downloaded model data.

## Environment Configuration

`.env.sample` contains the main settings:

```env
LOG_LEVEL=INFO
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=llama3.2
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

The Compose file supplies the service-specific values for the database and
Ollama URLs inside the app container. The most relevant settings are:

| Variable | Purpose |
| --- | --- |
| `DB_URL` | PostgreSQL connection string |
| `OLLAMA_BASE_URL` | Ollama service URL |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model used for indexing and search |
| `OLLAMA_LLM_MODEL` | Chat model used by the agent |
| `PGVECTOR_COLLECTION` | PGVector collection name, when overridden |
| `LOG_LEVEL` | Minimum application log level |

Do not commit `.env` or place real credentials in `.env.sample`.

## Optional LangSmith Tracing

LangSmith tracing is disabled by default for local development. To enable it,
set a valid LangSmith API key in `.env`:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your-valid-langsmith-api-key>
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

Use the endpoint for the LangSmith region associated with your account when
necessary. An invalid, expired, empty, or unauthorized key produces warnings
such as `403 Forbidden` when the application tries to upload runs. These
warnings do not mean that Ollama or PGVector has failed, but they do mean that
the traces were not recorded.

After changing `.env`, recreate the app container so Docker reloads the
environment:

```bash
docker compose up -d --force-recreate app
```

`docker compose restart app` restarts the existing container but does not
reliably apply changed values from `env_file`.

Never commit or share LangSmith API keys. Revoke and rotate a key immediately
if it is exposed.

## Development

Install the locked dependencies, including development tools:

```bash
uv sync --locked --dev
```

Run all tests:

```bash
uv run pytest app/tests
```

Run linting and formatting checks:

```bash
uv run ruff check app
uv run ruff format --check app
```

Run the Streamlit application outside Docker when the required PostgreSQL and
Ollama services are available and the appropriate environment variables are
configured:

```bash
uv run streamlit run app/main.py
```

## CI/CD Automation

GitHub Actions runs on pull requests and pushes to `main`. Pull requests run
the full validation suite. After a merge, the `main` workflow only rebuilds and
smoke-tests the image before packaging the release artifact. The pipeline:

- installs the locked `uv` environment and runs Ruff, pytest, and Python
  compilation checks;
- validates the Docker Compose configuration without starting PostgreSQL or
  downloading Ollama models;
- builds the application image and verifies its Streamlit dependency command;
- packages the verified image on `main` as a downloadable release artifact.

The release artifact contains `customer-support-ai-image.tar.gz` and
`release-metadata.txt`. It is a deployment handoff rather than a cloud
deployment; the application still requires PostgreSQL, PGVector, Ollama, and
the configured models at runtime.

## Logging and Diagnostics

The application uses Python's standard `logging` package and writes logs to
stdout so Docker and Cloud Run can collect them directly. Each operation log
includes an application-generated `trace_id`. This identifier is independent
of LangSmith and remains useful when tracing is disabled or unavailable.

Logs should contain lifecycle events, counts, status codes, and stack traces.
They should not contain credentials, database connection strings, prompts,
model output, or document contents.

For a quick service check:

```bash
docker compose ps
docker compose logs --tail=100 app
```

## Current Limitations

- The chatbot relies on the quality and coverage of the Markdown knowledge
	base.
- Similarity search returns the top matching chunks, which can come from the
	same source document.
- The local model may occasionally decide to retrieve context for casual
	messages such as greetings.
- There is no authentication, conversation persistence, feedback collection,
	or production-grade evaluation pipeline yet.
- LangSmith tracing is optional and requires valid external credentials.

## Roadmap

The current agent orchestration uses LangChain's agent abstraction and leaves
some decisions to the language model. The planned next architectural step is
to migrate the orchestration to **LangGraph**. This should provide more
deterministic control over model behavior, including explicit routing for
casual conversation versus support questions, predictable retrieval steps,
retry and failure handling, and clearer state transitions.

The LangGraph migration is intended to improve control and observability while
preserving the current RAG and Streamlit experience.

### User Feedback

Another planned capability is lightweight feedback collection for each answer.
Users could mark a response as helpful or unhelpful and optionally provide a
short explanation. Feedback would be associated with the question, answer,
retrieved context, and application trace when available.

This would provide several benefits:

- identify inaccurate, incomplete, or poorly grounded answers;
- discover gaps and outdated information in the knowledge base;
- measure answer quality over time with real user signals;
- prioritize improvements to prompts, retrieval, chunking, and models;
- create evaluation datasets from real support interactions;
- help compare future LangGraph workflows against the current agent behavior.

Feedback should be collected with appropriate privacy controls and should avoid
capturing sensitive customer information unnecessarily.
