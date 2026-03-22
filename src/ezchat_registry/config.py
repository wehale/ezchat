"""Registry configuration."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RegistryConfig:
    host:             str = "0.0.0.0"
    port:             int = 8080
    heartbeat_ttl:    int = 180      # expire servers after 3 minutes of silence
    log_level:        str = "info"


def load_registry_config(path: Path | None = None) -> RegistryConfig:
    if path is None or not path.exists():
        return RegistryConfig()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return RegistryConfig()
    s = data.get("registry", {})
    return RegistryConfig(
        host          = s.get("host",          "0.0.0.0"),
        port          = s.get("port",          8080),
        heartbeat_ttl = s.get("heartbeat_ttl", 180),
        log_level     = s.get("log_level",     "info"),
    )
