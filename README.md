# kt-py-logger

Shareable, configurable logging for Keytrends Python services. The package
(`import kt_logger`) wraps [loguru](https://github.com/Delgan/loguru) with:

- a stdlib `logging` → loguru bridge so third-party library logs share one pipeline;
- **field-agnostic per-request context** propagated via contextvars (asyncio-safe);
- noise demotion / dropping driven by config, with package-owned defaults;
- an optional aligned "kind" marker column for plain-text log viewers.

It is framework-agnostic: it fits FastAPI services, batch/clusterizer jobs, and
agent runtimes equally. The core hard-codes **no** field names — each service
declares the context fields it has.

## Install

```bash
# pip
pip install "kt-py-logger @ git+ssh://git@github.com/dataxquare/kt-py-logger.git@v0.1.0"
```

```toml
# pyproject.toml (PEP 621)
dependencies = [
    "kt-py-logger @ git+ssh://git@github.com/dataxquare/kt-py-logger.git@v0.1.0",
]
```

> `github.com` with the org deploy key. CI/Docker builds need that key (or a PAT)
> to install from the private repo.

## Usage

```python
from kt_logger import make_logger, bind_context

logger = make_logger("logging_config.json", level="INFO")

# Bind whatever per-request fields this service has:
bind_context(request_id="abc123")          # FastAPI middleware
# bind_context(job_id="...", cluster_id="...")   # a clusterizer
```

Computed fields (evaluated at log time, e.g. a current span or an agent stack):

```python
from kt_logger import register_field
register_field("agent_name", my_active_agent_fn)
```

### `logging_config.json`

Service config is merged **on top of** the package defaults (lists unioned, dict
overrides applied), so upgrading the package improves the baseline without
editing each service's config. Recognised `logger` keys:

| key | meaning |
| --- | --- |
| `path`, `level`, `rotation`, `retention` | sink basics (omit `path` for stdout-only) |
| `format` | loguru format string (falls back to a generic default) |
| `context_defaults` | `{field: default}` for fields the format references |
| `name_strip_prefix` | strip this prefix from logger names |
| `trace_logger_name` | logger whose source location is blanked |
| `demote_to_debug` | extra logger prefixes: INFO → DEBUG |
| `noise_message_patterns` | extra message substrings to drop |
| `noise_logger_substrings` | extra logger-name substrings to drop |
| `level_overrides` | `{logger_name: LEVEL}` |
| `drop_below_warning` | extra loggers floored at WARNING |
| `propagate_loggers` | extra loggers whose own handlers are cleared |

## Versioning

Tagged releases (`vMAJOR.MINOR.PATCH`). Consumers pin a tag in their dependency
URL and bump deliberately.

Versioning is **automatic** (`.github/workflows/version-bump.yml`): every push to
`main` derives the next version from the commit messages since the last tag using
[Conventional Commits](https://www.conventionalcommits.org/) —

| commit | bump |
| --- | --- |
| `feat: …` | minor |
| `fix: …` / anything else | patch |
| `feat!: …` / `BREAKING CHANGE` | major |

The workflow bumps `pyproject.toml`, commits `[skip ci]`, and pushes a `vX.Y.Z`
tag. Write commit messages accordingly.
