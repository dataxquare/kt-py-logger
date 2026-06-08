"""Loguru enrich/filter factory.

The filter stamps the current context fields (whatever the service has bound or
registered — see :mod:`kt_logger.context`) onto each record and drops noisy
messages. Service-specific knobs — the logger-name prefix to strip and which
logger is the "trace" logger (whose source location is blanked) — are passed in
as config so the package stays generic.
"""

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from kt_logger.context import current_fields

if TYPE_CHECKING:
    # loguru exposes the ``Record`` TypedDict only to type checkers. Annotating the
    # filter with it (not a bare ``dict``) is what makes ``logger.add(..., filter=)``
    # type-check — a TypedDict param is not satisfied by a plain ``dict`` param.
    from loguru import Record


def make_enrich_filter(
    *,
    noise_msg_patterns: Iterable[str] = (),
    noise_logger_substrings: Iterable[str] = (),
    name_strip_prefix: str | None = None,
    trace_logger_name: str | None = None,
) -> "Callable[[Record], bool]":
    """Build a loguru filter closure bound to the effective (merged) config.

    Returns a function ``filter(record) -> bool`` that loguru calls per record:
    it enriches ``record["extra"]`` with context + ``location``/``kind_fmt``
    columns and returns ``False`` to drop noise.
    """
    noise_patterns = tuple(noise_msg_patterns)
    noise_loggers = tuple(s.lower() for s in noise_logger_substrings)

    def _enrich_and_filter(record: "Record") -> bool:
        # Stamp whatever fields the service has bound/registered (service-defined,
        # not assumed here). location/kind_fmt below are the universal columns.
        record["extra"].update(current_fields())

        if name_strip_prefix and record["name"].startswith(name_strip_prefix):
            record["name"] = record["name"][len(name_strip_prefix):]

        # Source location (name:function:line) is noise on our own trace markers —
        # the kind column already says what it is. Blank it for the trace logger;
        # keep it (with the " - " separator) elsewhere, where it locates the code.
        if trace_logger_name and record["name"] == trace_logger_name:
            record["extra"]["location"] = ""
        else:
            record["extra"]["location"] = f'{record["name"]}:{record["function"]}:{record["line"]} - '

        # Render the marker as its own column, only when present. Pad the kind to a
        # fixed width (6 = longest, "AGENT>") so trace lines align vertically — works
        # in plain-text viewers like Portainer where colour isn't available.
        kind = record["extra"].get("kind", "")
        record["extra"]["kind_fmt"] = f"[{kind:<6}] " if kind else ""

        message = record["message"]
        if any(p in message for p in noise_patterns):
            return False

        name = record.get("name", "") or ""
        if any(ul in name.lower() for ul in noise_loggers):
            return False

        return True

    return _enrich_and_filter
