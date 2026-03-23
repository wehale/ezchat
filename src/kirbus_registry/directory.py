"""Server directory — in-memory store of registered kirbus servers.

Servers register via heartbeat.  Entries expire after ``ttl`` seconds
of silence.  No persistence — the directory rebuilds from heartbeats.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServerEntry:
    name:         str
    description:  str
    url:          str              # rendezvous API URL
    access:       str = "open"     # "open" | "password" | "unlisted"
    password:     str = ""         # hashed; only for access == "password"
    secret:       str = ""         # shared token for server → registry auth
    online_count: int = 0
    expires:      float = 0.0     # monotonic timestamp


class Directory:
    """Thread-safe (single-threaded async) server directory."""

    def __init__(self, ttl: int = 180) -> None:
        self._ttl = ttl
        self._servers: dict[str, ServerEntry] = {}

    def _purge(self) -> None:
        now = time.monotonic()
        expired = [n for n, s in self._servers.items() if s.expires <= now]
        for n in expired:
            del self._servers[n]

    def register(
        self,
        name: str,
        description: str,
        url: str,
        access: str,
        secret: str,
        password: str = "",
        online_count: int = 0,
    ) -> bool:
        """Register or update a server.

        First registration claims the name with the given secret.
        Subsequent updates must use the same secret (prevents hijacking).
        Returns False only on secret mismatch for an existing entry.
        """
        existing = self._servers.get(name)
        if existing and existing.secret != secret:
            return False

        self._servers[name] = ServerEntry(
            name=name,
            description=description,
            url=url,
            access=access,
            password=password,
            secret=secret,
            online_count=online_count,
            expires=time.monotonic() + self._ttl,
        )
        return True

    def deregister(self, name: str, secret: str) -> bool:
        """Remove a server.  Returns False if not found or secret mismatch."""
        entry = self._servers.get(name)
        if not entry or entry.secret != secret:
            return False
        del self._servers[name]
        return True

    def verify(self, name: str, password: str) -> str | None:
        """Check password for a protected server.  Returns URL or None."""
        self._purge()
        entry = self._servers.get(name)
        if not entry or entry.access != "password":
            return None
        if entry.password and entry.password == password:
            return entry.url
        return None

    def list_public(self) -> list[dict[str, Any]]:
        """Return all non-unlisted servers for the public directory."""
        self._purge()
        result = []
        for s in sorted(self._servers.values(), key=lambda s: s.name):
            if s.access == "unlisted":
                continue
            entry: dict[str, Any] = {
                "name": s.name,
                "description": s.description,
                "access": s.access,
                "online_count": s.online_count,
            }
            # Only expose URL for open servers
            if s.access == "open":
                entry["url"] = s.url
            else:
                entry["url"] = None
            result.append(entry)
        return result
