"""Registry heartbeat — periodically register this server with the registry."""
from __future__ import annotations

import asyncio
import logging

import aiohttp

from ezchat_server.config import RegistrySection

_log = logging.getLogger(__name__)
_INTERVAL = 60  # seconds between heartbeats


async def heartbeat_loop(
    reg: RegistrySection,
    server_url: str,
    get_online_count: callable,
    stop: asyncio.Event,
) -> None:
    """Register with the registry and send periodic heartbeats.

    Parameters
    ----------
    reg : RegistrySection
        Registry config (url, name, secret, etc.)
    server_url : str
        This server's public rendezvous URL, e.g. "http://1.2.3.4:8000"
    get_online_count : callable
        Returns the current number of connected peers.
    stop : asyncio.Event
        Set to signal shutdown.
    """
    registry_url = reg.url.rstrip("/")

    async with aiohttp.ClientSession() as session:
        while not stop.is_set():
            payload = {
                "name":         reg.name,
                "description":  reg.description,
                "url":          server_url,
                "access":       reg.access,
                "secret":       reg.secret,
                "password":     reg.password,
                "online_count": get_online_count(),
            }
            try:
                async with session.post(
                    f"{registry_url}/servers", json=payload, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        _log.debug("heartbeat sent to %s", registry_url)
                    else:
                        text = await resp.text()
                        _log.warning("heartbeat rejected (%d): %s", resp.status, text)
            except Exception as exc:
                _log.warning("heartbeat failed: %s", exc)

            try:
                await asyncio.wait_for(stop.wait(), timeout=_INTERVAL)
                break  # stop was set
            except asyncio.TimeoutError:
                pass

        # Deregister on shutdown
        try:
            async with session.delete(
                f"{registry_url}/servers/{reg.name}",
                json={"secret": reg.secret},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    _log.info("deregistered from %s", registry_url)
        except Exception:
            pass
