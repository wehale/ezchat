"""ezchat-registry — entry point.

Usage
-----
    ezchat-registry                        # default: port 8080
    ezchat-registry --port 8080
    ezchat-registry --config /path/to/registry.toml

registry.toml example
---------------------
    [registry]
    host          = "0.0.0.0"
    port          = 8080
    heartbeat_ttl = 180
    log_level     = "info"
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path


async def _main(cfg) -> None:
    from aiohttp import web
    from ezchat_registry.api import make_app
    from ezchat_registry.directory import Directory

    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    )
    log = logging.getLogger("ezchat-registry")

    directory = Directory(ttl=cfg.heartbeat_ttl)
    app       = make_app(directory)
    runner    = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, cfg.host, cfg.port)
    await site.start()

    log.info("registry listening on %s:%d  (ttl=%ds)", cfg.host, cfg.port, cfg.heartbeat_ttl)

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ezchat-registry",
        description="ezchat server registry — directory of available servers",
    )
    parser.add_argument("--config",   metavar="FILE", help="Path to registry.toml")
    parser.add_argument("--host",     default=None)
    parser.add_argument("--port",     type=int, default=None)
    parser.add_argument("--ttl",      type=int, default=None, dest="heartbeat_ttl")
    parser.add_argument("--log-level", default=None, dest="log_level")
    args = parser.parse_args()

    from ezchat_registry.config import load_registry_config
    cfg_path = Path(args.config) if args.config else None
    cfg      = load_registry_config(cfg_path)

    if args.host:          cfg.host          = args.host
    if args.port:          cfg.port          = args.port
    if args.heartbeat_ttl: cfg.heartbeat_ttl = args.heartbeat_ttl
    if args.log_level:     cfg.log_level     = args.log_level

    asyncio.run(_main(cfg))


if __name__ == "__main__":
    main()
