import logging
import sys
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

DEFAULT_LOG_LEVEL = "INFO"
TRACE_ID = ContextVar("trace_id", default="-")
_HANDLER_MARKER = "customer_support_stdout_handler"


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = TRACE_ID.get()
        return True


def configure_logging(log_level: str = DEFAULT_LOG_LEVEL) -> None:
    """Configure one stdout handler for application logs."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers:
        if getattr(handler, _HANDLER_MARKER, False):
            return

    handler = logging.StreamHandler(sys.stdout)
    setattr(handler, _HANDLER_MARKER, True)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s trace_id=%(trace_id)s %(message)s"
        )
    )
    handler.addFilter(TraceIdFilter())
    root_logger.addHandler(handler)


@contextmanager
def trace_context(trace_id: str | None = None) -> Generator[str]:
    """Make one operation's trace ID available to all logs in its context."""
    operation_trace_id = trace_id or str(uuid4())
    token = TRACE_ID.set(operation_trace_id)
    try:
        yield operation_trace_id
    finally:
        TRACE_ID.reset(token)
