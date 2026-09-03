## Development

Install the locked dependencies, including development tools, with:

```bash
uv sync --locked --dev
```

Run the test suite with:

```bash
uv run pytest app/tests
```

Run linting and formatting checks with:

```bash
uv run ruff check app
uv run ruff format --check app
```

## Running With Docker Compose

Copy `.env.sample` to `.env`, then start the application and its PostgreSQL
and Ollama services:

```bash
docker compose up -d
```

The Streamlit interface is available at `http://localhost:8501`.

## Logging

The application uses Python's standard `logging` package for operational logs.
Logs are written to stdout so Docker and Cloud Run can collect them directly.

Set the `LOG_LEVEL` environment variable to control verbosity. The default is
`INFO`; supported values include `DEBUG`, `INFO`, `WARNING`, `ERROR`, and
`CRITICAL`.

The configured level is a minimum threshold. For example, `LOG_LEVEL=ERROR`
emits error and critical records while suppressing informational records.

Each operation log includes a `trace_id`. The application generates an ID for
startup knowledge-base ingestion and will generate a new ID for each future
agent question. This identifier is independent of LangSmith, allowing
infrastructure and application failures to remain visible even when no LLM
trace exists. The future LangChain orchestrator will attach the active ID to
its LangSmith run metadata so both systems can be correlated.

Operational logs should contain lifecycle events, counts, status codes, and
stack traces. They must not contain credentials, database connection strings,
prompts, model output, or document contents.
