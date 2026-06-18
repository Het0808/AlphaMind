"""Authentication layer for MCP servers.

Resolves each server's required credentials from its spec env or the process
environment, injects them into the connection env, and fails fast with a clear
`MCPAuthError` when a required secret is missing — before any process is spawned.
Secrets are never logged (use `MCPServerSpec.redacted()`).
"""

from __future__ import annotations

import logging
import os
from typing import Mapping, Optional

from .exceptions import MCPAuthError
from .schemas import MCPServerSpec

logger = logging.getLogger(__name__)


def resolve_auth(spec: MCPServerSpec, *, environ: Optional[Mapping[str, str]] = None) -> MCPServerSpec:
    """Validate and inject required credentials for a server spec.

    Returns the same spec with its `env` populated from the environment for any
    `required_auth` variable not already set. Raises MCPAuthError if any required
    credential cannot be found.
    """
    environ = os.environ if environ is None else environ

    missing = []
    for var in spec.required_auth:
        value = spec.env.get(var) or environ.get(var)
        if not value:
            missing.append(var)
        else:
            spec.env[var] = value

    if missing:
        raise MCPAuthError(
            f"missing required credential(s): {', '.join(missing)}", server=spec.name
        )

    if spec.required_auth:
        logger.debug("Auth resolved for %s: %s", spec.name, list(spec.env.keys()))
    return spec


def is_authorized(spec: MCPServerSpec, *, environ: Optional[Mapping[str, str]] = None) -> bool:
    """Non-raising check used to filter servers before connecting."""
    try:
        resolve_auth(spec, environ=environ)
        return True
    except MCPAuthError:
        return False
