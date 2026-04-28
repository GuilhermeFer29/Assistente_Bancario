"""Logging estruturado (structlog) para o bot_service."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

import structlog

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


def _injetar_correlation_id(logger, method_name, event_dict):  # type: ignore[no-untyped-def]
    cid = correlation_id_ctx.get("")
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def configurar_logging(nivel: str = "INFO") -> None:
    """Configura structlog em modo JSON para stdout."""
    nivel_int = getattr(logging, nivel.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=nivel_int)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _injetar_correlation_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(nivel_int),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger("bot_service")
