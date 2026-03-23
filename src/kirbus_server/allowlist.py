"""Pubkey allowlist for server access control.

Stores allowed Ed25519 public keys in allowlist.toml alongside the server.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_DEFAULT_PATH = Path.home() / ".kirbus-server" / "allowlist.toml"


@dataclass
class AllowedPeer:
    handle:    str
    pubkey:    str   # base64 Ed25519 public key
    added:     str   # ISO timestamp
    added_via: str   # "password" | "manual"


class Allowlist:
    """Manages the pubkey allowlist for server access control."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_PATH
        self._allowed: dict[str, AllowedPeer] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = tomllib.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return
        for handle, attrs in data.get("allowed", {}).items():
            self._allowed[attrs.get("ed25519_pub", "")] = AllowedPeer(
                handle=handle,
                pubkey=attrs.get("ed25519_pub", ""),
                added=attrs.get("added", ""),
                added_via=attrs.get("added_via", ""),
            )

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# kirbus server allowlist\n\n"]
        for peer in sorted(self._allowed.values(), key=lambda p: p.handle):
            lines.append(f"[allowed.{peer.handle}]\n")
            lines.append(f'ed25519_pub = "{peer.pubkey}"\n')
            lines.append(f'added = "{peer.added}"\n')
            lines.append(f'added_via = "{peer.added_via}"\n')
            lines.append("\n")
        self._path.write_text("".join(lines), encoding="utf-8")

    def is_allowed(self, pubkey: str) -> bool:
        """Check if a pubkey is in the allowlist."""
        return pubkey in self._allowed

    def add(self, handle: str, pubkey: str, via: str = "password") -> None:
        """Add a pubkey to the allowlist."""
        self._allowed[pubkey] = AllowedPeer(
            handle=handle,
            pubkey=pubkey,
            added=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            added_via=via,
        )
        self._save()

    def remove(self, handle: str) -> bool:
        """Remove a peer by handle. Returns True if found."""
        to_remove = [k for k, v in self._allowed.items() if v.handle == handle]
        if not to_remove:
            return False
        for k in to_remove:
            del self._allowed[k]
        self._save()
        return True

    def list_all(self) -> list[AllowedPeer]:
        """Return all allowed peers."""
        return sorted(self._allowed.values(), key=lambda p: p.handle)
