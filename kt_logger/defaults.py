"""Package-owned defaults for the shared logger.

These are the *baseline* behaviors every consuming service inherits. Service
config (``logging_config.json``) is merged ON TOP of these (additions/overrides,
never replacement) — see :mod:`kt_logger.setup`. The point: upgrading the
``kt_logger`` package upgrades the baseline for every service without anyone
editing per-service config.

Keep entries here broadly applicable (common infra/web noise). Anything specific
to one service belongs in that service's JSON, not here.
"""

# Generic fallback format — time · level · location · kind_fmt · message. It uses
# only the universal columns the core always provides; service-specific columns
# (e.g. session/invocation/agent) belong in that service's ``format`` config,
# alongside ``context_defaults`` for the fields it references. ``location`` and
# ``kind_fmt`` are filled by the enrich filter (blank where not applicable).
# Colour tags only render on a TTY; plain-text viewers (e.g. Portainer) see the
# bare text, which is why the kind column is padded for vertical alignment.
DEFAULT_FORMAT = (
    "[<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>] "
    "[<level>{level:<7}</level>] "
    "<blue>{extra[location]}</blue><yellow>{extra[kind_fmt]}</yellow>"
    "<level>{message}</level>"
)

# Loggers whose INFO chatter is demoted to DEBUG (recoverable at DEBUG, not
# dropped). Matched with ``name.startswith(...)``. Common framework noise lives
# here; service-specific demotions go in the service JSON's ``demote_to_debug``.
DEFAULT_DEMOTE: tuple[str, ...] = ("google_adk", "google_genai")

# Messages containing any of these substrings are dropped outright (file-watcher
# churn, DB heartbeat/topology spam). Checked both when intercepting stdlib logs
# and in the loguru enrich filter.
DEFAULT_NOISE_MSG_PATTERNS: tuple[str, ...] = (
    "INOTIFY", "WATCHDOG", "file_watcher", "FileWatcher", "inotify", "IN_",
    "change detected",
    "Server heartbeat started", "topologyId", "driverConnectionId",
    "serverConnectionId", "serverHost", 'awaited": true',
)

# Loggers whose records are dropped entirely (matched as a case-insensitive
# substring of the logger name).
DEFAULT_NOISE_LOGGER_SUBSTRINGS: tuple[str, ...] = (
    "watchdog", "watchfiles", "inotify", "fsevents", "pymongo", "motor",
)

# Per-logger level floors applied via ``logging.getLogger(name).setLevel(...)``.
DEFAULT_LEVEL_OVERRIDES: dict[str, str] = {
    # File-watcher noise.
    "watchdog": "WARNING", "watchdog.observers": "WARNING", "watchfiles": "WARNING",
    "inotify": "WARNING", "fsevents": "WARNING", "filelock": "WARNING",
    # MongoDB at INFO (not DEBUG).
    "pymongo": "INFO", "pymongo.connection": "INFO", "pymongo.topology": "INFO",
    "pymongo.server": "INFO", "pymongo.heartbeat": "INFO", "motor": "INFO", "motor.core": "INFO",
    # Pika floods INFO with raw socket repr strings — only surface errors.
    "pika": "ERROR", "pika.adapters": "ERROR", "pika.adapters.utils": "ERROR",
    "pika.adapters.utils.io_services_utils": "ERROR",
    "pika.adapters.select_connection": "ERROR", "pika.adapters.blocking_connection": "ERROR",
    "pika.connection": "ERROR", "pika.channel": "ERROR",
}

# Loggers that re-set their own level after our config (e.g. MCP). A
# WARNING-floor filter is attached to the logger itself so it runs in
# ``Logger.handle`` before ANY handler fires, regardless of later level changes.
DEFAULT_DROP_BELOW_WARNING: tuple[str, ...] = (
    "mcp", "mcp.server", "mcp.server.lowlevel", "mcp.server.lowlevel.server",
)

# Loggers whose own handlers are cleared so they propagate to the root (avoids
# double emit). Typical web-server stack.
DEFAULT_PROPAGATE_LOGGERS: tuple[str, ...] = (
    "uvicorn", "uvicorn.error", "uvicorn.access", "fastapi",
)

# warnings.warn() messages suppressed (repetitive, non-actionable). Matched as a
# regex by ``warnings.filterwarnings(message=...)``.
DEFAULT_SUPPRESSED_WARNINGS: tuple[str, ...] = (
    r"\[EXPERIMENTAL\]", r"\[WIP\]",
)
