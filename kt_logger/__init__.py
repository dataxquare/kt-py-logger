"""kt_logger — shareable, configurable logging for our Python services.

Generic core (loguru + stdlib intercept, field-agnostic per-request context,
noise demotion, aligned kind column). Depends only on ``loguru`` — no service- or
framework-specific imports — so it is ready to be extracted into its own
``kt-logger`` package/repo when a second service needs it.

Typical use::

    from kt_logger import make_logger, bind_context
    logger = make_logger("logging_config.json", level="INFO")
    bind_context(request_id="abc123")          # FastAPI middleware, a job runner, …

Context is field-agnostic: a service binds whatever per-request values it has
(``request_id``, ``job_id``, …) with :func:`bind_context`, or registers a computed
field (e.g. an agent stack's current agent) with :func:`register_field`. The
format string and ``context_defaults`` in that service's config decide which
fields are shown.
"""

from kt_logger.context import (
    bind_context,
    clear_context,
    context,
    current_fields,
    get_context,
    register_field,
    unbind_context,
    unregister_field,
)
from kt_logger.intercept import DropBelowWarning, InterceptHandler
from kt_logger.setup import CustomizeLogger, make_logger

__all__ = [
    "make_logger",
    "CustomizeLogger",
    "InterceptHandler",
    "DropBelowWarning",
    "bind_context",
    "unbind_context",
    "clear_context",
    "get_context",
    "context",
    "register_field",
    "unregister_field",
    "current_fields",
]
