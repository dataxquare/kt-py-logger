"""Logger bootstrap: merge package defaults with service config, configure sinks.

Service config (``logging_config.json``) is merged ON TOP of the package
defaults from :mod:`kt_logger.defaults` — lists are unioned, dict overrides are
applied — so upgrading the package improves the baseline without per-service edits.

Recognised ``logger`` config keys (all optional except ``path``):
    path, level, rotation, retention      sink basics
    format                                loguru format (falls back to DEFAULT_FORMAT)
    context_defaults                      {field: default} for fields the format references
    name_strip_prefix                     strip this prefix from logger names
    trace_logger_name                     logger whose source location is blanked
    demote_to_debug                       extra logger prefixes: INFO -> DEBUG
    noise_message_patterns                extra message substrings to drop
    noise_logger_substrings               extra logger-name substrings to drop
    level_overrides                       {logger_name: LEVEL} (override/extend defaults)
    drop_below_warning                    extra loggers to floor at WARNING
    propagate_loggers                     extra loggers whose handlers are cleared
"""

import json
import logging
import sys
import warnings
from pathlib import Path

from loguru import logger

from kt_logger import defaults
from kt_logger.filters import make_enrich_filter
from kt_logger.intercept import DropBelowWarning, InterceptHandler


def _merge_seq(default: tuple, extra) -> tuple:
    """Union a default tuple with an optional config sequence (dedup, order-stable)."""
    out = list(default)
    for item in extra or []:
        if item not in out:
            out.append(item)
    return tuple(out)


def make_logger(config_path: Path | str, level: str | None = None):
    """Load ``config_path``, merge with package defaults, configure logging.

    ``level`` (e.g. from an env var) overrides the config file's level.
    Returns the configured loguru ``logger``.
    """
    with open(config_path) as f:
        cfg = (json.load(f).get("logger") or {})

    effective_level = (level if level is not None else cfg.get("level") or "INFO").upper()
    fmt = cfg.get("format") or defaults.DEFAULT_FORMAT

    demote = _merge_seq(defaults.DEFAULT_DEMOTE, cfg.get("demote_to_debug"))
    noise_msgs = _merge_seq(defaults.DEFAULT_NOISE_MSG_PATTERNS, cfg.get("noise_message_patterns"))
    noise_loggers = _merge_seq(defaults.DEFAULT_NOISE_LOGGER_SUBSTRINGS, cfg.get("noise_logger_substrings"))
    drop_below_warning = _merge_seq(defaults.DEFAULT_DROP_BELOW_WARNING, cfg.get("drop_below_warning"))
    propagate_loggers = _merge_seq(defaults.DEFAULT_PROPAGATE_LOGGERS, cfg.get("propagate_loggers"))
    level_overrides = {**defaults.DEFAULT_LEVEL_OVERRIDES, **(cfg.get("level_overrides") or {})}

    enrich = make_enrich_filter(
        noise_msg_patterns=noise_msgs,
        noise_logger_substrings=noise_loggers,
        name_strip_prefix=cfg.get("name_strip_prefix"),
        trace_logger_name=cfg.get("trace_logger_name"),
    )

    # Seed default values for every extra the format references, so a line that
    # isn't enriched still renders. ``location``/``kind``/``kind_fmt`` are core;
    # service field defaults (e.g. session_id/agent_name) come from config.
    logger.configure(extra={
        "location": "", "kind": "", "kind_fmt": "",
        **(cfg.get("context_defaults") or {}),
    })
    logger.remove()

    logger.add(
        sys.stdout,
        enqueue=True,
        backtrace=True,
        diagnose=False,  # no variable dumps on stdout — keeps tracebacks clean
        level=effective_level,
        format=fmt,
        filter=enrich,
    )
    if cfg.get("path"):
        logger.add(
            str(cfg["path"]),
            rotation=cfg.get("rotation"),
            retention=cfg.get("retention"),
            enqueue=True,
            backtrace=True,
            diagnose=True,  # full variable dumps in file for deep debugging
            level=effective_level,
            format=fmt,
            filter=enrich,
        )

    # Single InterceptHandler on root; all loggers propagate to it by default.
    root = logging.getLogger()
    root.handlers = [InterceptHandler(demote_to_debug=demote, noise_patterns=noise_msgs)]
    root.setLevel(0)

    # Clear own handlers so these propagate to root (not double-emit).
    for name in propagate_loggers:
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True

    # Route warnings.warn() through logging so they appear formatted.
    logging.captureWarnings(True)
    for pattern in defaults.DEFAULT_SUPPRESSED_WARNINGS:
        warnings.filterwarnings("ignore", message=pattern, category=UserWarning)

    # Per-logger level floors.
    for name, lvl in level_overrides.items():
        logging.getLogger(name).setLevel(lvl)

    # Loggers that re-set their own level after our config: attach a WARNING-floor
    # filter on the logger itself so it runs in Logger.handle before ANY handler.
    for name in drop_below_warning:
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
        lg.setLevel(logging.WARNING)
        lg.addFilter(DropBelowWarning())

    return logger.bind(request_id=None, method=None)


class CustomizeLogger:
    """Backward-compatible facade around :func:`make_logger`."""

    @classmethod
    def make_logger(cls, config_path: Path | str, level: str | None = None):
        return make_logger(config_path, level=level)
