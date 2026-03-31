"""Server configuration."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RegistrySection:
    """Config for registering this server with an kirbus-registry."""
    url:         str = ""          # registry URL, e.g. "https://ezchat.kirbus.ai"
    name:        str = ""          # server listing name
    description: str = ""          # short description for the directory
    secret:      str = ""          # shared token for registry auth
    access:      str = "open"      # "open" | "password" | "unlisted"
    password:    str = ""          # server-level password (for access == "password")
    public_url:  str = ""          # this server's public URL, e.g. "http://100.0.197.245:8000"


@dataclass
class AuthSection:
    """Config for server-level access control."""
    mode:     str = "open"         # "open" | "password" | "allowlist"
    password: str = ""             # required if mode == "password"


@dataclass
class ServerConfig:
    host:           str = "0.0.0.0"
    api_port:       int = 8000
    relay_port:     int = 9001
    ttl:            int = 60
    log_level:      str = "info"
    welcome:        str = ""       # shown to all clients on connect
    secret_message: str = ""       # shown only after successful auth
    agents:         list[str] = field(default_factory=list)  # e.g. ["home", "games"]
    registry:       RegistrySection = field(default_factory=RegistrySection)
    auth:           AuthSection     = field(default_factory=AuthSection)


def load_server_config(path: Path | None = None) -> ServerConfig:
    if path is None or not path.exists():
        return ServerConfig()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ServerConfig()
    s = data.get("server", {})
    r = data.get("registry", {})
    a = data.get("auth", {})
    return ServerConfig(
        host           = s.get("host",           "0.0.0.0"),
        api_port       = s.get("api_port",       8000),
        relay_port     = s.get("relay_port",     9001),
        ttl            = s.get("ttl",            60),
        log_level      = s.get("log_level",      "info"),
        welcome        = s.get("welcome",        ""),
        agents         = s.get("agents",         []),
        secret_message = s.get("secret_message", ""),
        registry   = RegistrySection(
            url         = r.get("url",         ""),
            name        = r.get("name",        ""),
            description = r.get("description", ""),
            secret      = r.get("secret",      ""),
            access      = r.get("access",      "open"),
            password    = r.get("password",    ""),
            public_url  = r.get("public_url",  ""),
        ),
        auth       = AuthSection(
            mode     = a.get("mode",     "open"),
            password = a.get("password", ""),
        ),
    )
