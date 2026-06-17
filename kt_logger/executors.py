"""Context-preserving executors.

``ThreadPoolExecutor`` workers start with a *fresh* contextvars context, so any
per-request context bound for logging (session/invocation/agent, request_id, …)
is lost the moment work is offloaded to a thread — log lines from those threads
fall back to the configured defaults (e.g. ``(-/-) [-]``).

:class:`ContextThreadPoolExecutor` snapshots the caller's context at ``submit``
time and runs the task inside a copy of it, so logs from worker threads keep the
same context as the code that scheduled them. A fresh copy is taken per ``submit``
so concurrent workers never share (and re-enter) the same ``Context`` object.

``asyncio.create_task`` already copies context automatically; use this only for
thread offload (``ThreadPoolExecutor``/``run_in_executor``).
"""

import contextvars
from concurrent.futures import ThreadPoolExecutor

__all__ = ["ContextThreadPoolExecutor"]


class ContextThreadPoolExecutor(ThreadPoolExecutor):
    """A ``ThreadPoolExecutor`` that propagates contextvars into worker threads.

    Drop-in replacement — same constructor and API. Each submitted callable runs
    inside a copy of the context active at ``submit`` time.
    """

    def submit(self, fn, /, *args, **kwargs):
        ctx = contextvars.copy_context()
        return super().submit(ctx.run, fn, *args, **kwargs)
