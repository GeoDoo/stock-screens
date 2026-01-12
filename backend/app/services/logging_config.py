import logging
import sys
import structlog
from typing import Any, Dict

def configure_logging():
    """
    Configure institutional-grade structured logging.
    - JSON output for production/CI
    - Console-pretty output for local development
    - Injected request context (Trace IDs)
    """
    
    # Processors are the heart of structlog
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Use JSON for machine-readability in prod, but pretty logs for devs
    if sys.stderr.isatty():
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer()
        ]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bridge standard logging to structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=logging.INFO,
    )
    
    return structlog.get_logger()

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)

# Initialize on module load
logger = configure_logging()
