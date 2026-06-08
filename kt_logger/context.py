"""Per-request log context — field-agnostic, asyncio-safe.

The core knows nothing about *which* fields a service uses. A service binds
whatever per-request values it has (FastAPI: ``request_id``; a clusterizer:
``job_id``; an agent runtime: ``session_id`` + a computed ``agent_name``) and the
enrich filter stamps them onto every log record.

Two flavours of field:
  - **static**  — a fixed value for the duration of a request/task, set with
    :func:`bind_context` / scoped with :func:`context`.
  - **computed** — a value derived at log time, registered with
    :func:`register_field` (e.g. the top of an agent stack, a current span name).

All state lives in contextvars, so concurrent async tasks never see each other's
context.
"""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

# Static per-request fields (a single dict so binding is atomic per task).
_context_var: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})

# Computed fields: name -> zero-arg provider evaluated at log time. Process-global
# (registration is a setup-time concern); the data a provider reads can itself be
# a contextvar, keeping per-task isolation.
_providers: dict[str, Callable[[], Any]] = {}


def bind_context(**fields: Any) -> None:
    """Merge ``fields`` into the current static context (replacing same-named keys)."""
    _context_var.set({**_context_var.get(), **fields})


def unbind_context(*names: str) -> None:
    """Remove ``names`` from the current static context (silently ignores absent)."""
    current = _context_var.get()
    if any(n in current for n in names):
        _context_var.set({k: v for k, v in current.items() if k not in names})


def clear_context() -> None:
    """Drop all static context fields for the current task."""
    _context_var.set({})


def get_context() -> dict[str, Any]:
    """Snapshot of the current static context (excludes computed fields)."""
    return dict(_context_var.get())


@contextmanager
def context(**fields: Any) -> Generator[None, None, None]:
    """Scoped static binding: bind ``fields`` for the block, restore on exit."""
    token = _context_var.set({**_context_var.get(), **fields})
    try:
        yield
    finally:
        _context_var.reset(token)


def register_field(name: str, provider: Callable[[], Any]) -> None:
    """Register a computed field evaluated at log time (overrides static same-named)."""
    _providers[name] = provider


def unregister_field(name: str) -> None:
    """Remove a previously registered computed field."""
    _providers.pop(name, None)


def current_fields() -> dict[str, Any]:
    """Effective context for a log record: static fields plus computed providers."""
    fields = dict(_context_var.get())
    for name, provider in _providers.items():
        fields[name] = provider()
    return fields
