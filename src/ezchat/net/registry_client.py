"""Client-side registry interaction — fetch server list, verify passwords."""
from __future__ import annotations

import aiohttp
import logging

_log = logging.getLogger(__name__)

DEFAULT_REGISTRY = "https://ezchat.kirbus.ai"


async def fetch_servers(registry_url: str) -> list[dict]:
    """Fetch the server directory from a registry.

    Returns a list of server dicts: {name, description, access, online_count, url}.
    """
    url = registry_url.rstrip("/") + "/servers"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    _log.warning("registry returned %d", resp.status)
                    return []
                data = await resp.json()
                return data.get("servers", [])
    except Exception as exc:
        _log.warning("failed to reach registry %s: %s", registry_url, exc)
        return []


async def verify_server_password(registry_url: str, server_name: str, password: str) -> str | None:
    """Verify a password for a protected server.

    Returns the server URL on success, None on failure.
    """
    url = f"{registry_url.rstrip('/')}/servers/{server_name}/verify"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"password": password},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("url")
                return None
    except Exception as exc:
        _log.warning("verify failed for %s: %s", server_name, exc)
        return None
