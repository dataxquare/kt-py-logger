"""Bridge stdlib ``logging`` → loguru, with noise drop + INFO demotion."""

import logging

from loguru import logger


class DropBelowWarning(logging.Filter):
    """Logger-level filter that drops records below WARNING.

    Attached to noisy loggers whose level we can't reliably control because the
    library re-sets it after our configuration. Runs in ``Logger.handle`` before
    any handler, so the record never reaches a rogue handler.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.WARNING


class InterceptHandler(logging.Handler):
    """Redirect stdlib logging → loguru, preserving the original source location.

    Uses ``logger.patch()`` with the LogRecord's pre-resolved name/funcName/lineno
    instead of frame-walking, which produced 'logging:callHandlers' for all
    third-party library logs.

    Configured (not hard-coded) with:
      - ``demote_to_debug``: logger-name prefixes whose INFO is downgraded to DEBUG.
      - ``noise_patterns``: message substrings dropped before forwarding.
    """

    def __init__(
        self,
        *,
        demote_to_debug: tuple[str, ...] = (),
        noise_patterns: tuple[str, ...] = (),
    ) -> None:
        super().__init__()
        self._demote_to_debug = tuple(demote_to_debug)
        self._noise_patterns = tuple(noise_patterns)

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if any(p in msg for p in self._noise_patterns):
            return

        if record.levelno == logging.INFO and record.name.startswith(self._demote_to_debug):
            level: str | int = "DEBUG"
        else:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

        # Forward our trace marker (set via logging's extra=) so it lands in the
        # loguru record's extra and can occupy its own format column.
        kind = getattr(record, "kind", "")

        (
            logger
            .bind(kind=kind)
            .patch(lambda r: r.update(name=record.name, function=record.funcName, line=record.lineno))
            .opt(exception=record.exc_info)
            .log(level, msg)
        )
