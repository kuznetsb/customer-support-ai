import logging
from contextlib import redirect_stdout
from io import StringIO
from uuid import UUID

import pytest

from app.logging_config import TRACE_ID, configure_logging, trace_context
from app.settings import Settings


@pytest.fixture(autouse=True)
def clean_logging_handlers():
    yield
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if getattr(handler, "customer_support_stdout_handler", False):
            root_logger.removeHandler(handler)
            handler.close()


def test_logs_are_written_to_stdout_with_trace_id() -> None:
    output = StringIO()
    with redirect_stdout(output):
        configure_logging()
        logger = logging.getLogger("test.logging_config")
        with trace_context("test-trace"):
            logger.info("operation completed")

    assert (
        "INFO test.logging_config trace_id=test-trace operation completed"
        in output.getvalue()
    )


def test_trace_context_generates_a_uuid_when_not_provided() -> None:
    with trace_context() as trace_id:
        UUID(trace_id)
        assert TRACE_ID.get() == trace_id


def test_trace_context_is_restored_after_an_exception() -> None:
    with pytest.raises(RuntimeError), trace_context("failed-operation"):
        assert TRACE_ID.get() == "failed-operation"
        raise RuntimeError("test failure")

    assert TRACE_ID.get() == "-"


def test_repeated_configuration_does_not_duplicate_handlers() -> None:
    configure_logging()
    configure_logging()

    handlers = [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "customer_support_stdout_handler", False)
    ]
    assert len(handlers) == 1


def test_trace_context_is_restored() -> None:
    with trace_context("outer"):
        with trace_context("inner"):
            assert TRACE_ID.get() == "inner"
        assert TRACE_ID.get() == "outer"

    assert TRACE_ID.get() == "-"


def test_log_level_is_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")

    assert Settings().log_level == "DEBUG"


def test_invalid_log_level_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "verbose")

    with pytest.raises(ValueError):
        Settings()
