"""Compatibility contract for the OpenCode API v2 integration."""
from __future__ import annotations


# These exact server releases were verified with the API v2 contracts used by
# the Analyst. Keep this allowlist strict; unknown releases must fail closed.
SUPPORTED_OPENCODE_VERSIONS = frozenset({"2.0.27", "2.1.2"})


def is_supported_opencode_version(version: object) -> bool:
    """Return whether a server release is in the verified API v2 allowlist."""
    return isinstance(version, str) and version in SUPPORTED_OPENCODE_VERSIONS
