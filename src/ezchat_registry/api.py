"""Registry HTTP API.

Endpoints
---------
GET /servers
    Returns the public server directory.

POST /servers
    Register or heartbeat a server (called by ezchat-server instances).
    Body: { "name", "description", "url", "access", "secret",
            "password"?, "online_count"? }

DELETE /servers/{name}
    Deregister a server.
    Body: { "secret" }

POST /servers/{name}/verify
    Verify credentials for a password-protected server.
    Body: { "password" }
    Returns: { "url": "..." } on success, 403 on failure.
"""
from __future__ import annotations

import logging

from aiohttp import web

from ezchat_registry.directory import Directory

_log = logging.getLogger(__name__)


async def handle_list_servers(request: web.Request) -> web.Response:
    directory: Directory = request.app["directory"]
    return web.json_response({"servers": directory.list_public()})


async def handle_register_server(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        name        = body["name"]
        description = body["description"]
        url         = body["url"]
        access      = body["access"]
        secret      = body["secret"]
    except (KeyError, ValueError):
        return web.json_response({"error": "bad request"}, status=400)

    if access not in ("open", "password", "unlisted"):
        return web.json_response({"error": "invalid access type"}, status=400)

    password     = body.get("password", "")
    online_count = body.get("online_count", 0)

    ok = request.app["directory"].register(
        name=name,
        description=description,
        url=url,
        access=access,
        secret=secret,
        password=password,
        online_count=online_count,
    )
    if not ok:
        return web.json_response({"error": "secret mismatch"}, status=403)

    _log.info("registered server %r (%s, %s)", name, access, url)
    return web.json_response({"ok": True})


async def handle_deregister_server(request: web.Request) -> web.Response:
    name = request.match_info["name"]
    try:
        body = await request.json()
        secret = body["secret"]
    except (KeyError, ValueError):
        return web.json_response({"error": "bad request"}, status=400)

    ok = request.app["directory"].deregister(name, secret)
    if not ok:
        return web.json_response({"error": "not found or secret mismatch"}, status=403)

    _log.info("deregistered server %r", name)
    return web.json_response({"ok": True})


async def handle_verify(request: web.Request) -> web.Response:
    name = request.match_info["name"]
    try:
        body = await request.json()
        password = body["password"]
    except (KeyError, ValueError):
        return web.json_response({"error": "bad request"}, status=400)

    url = request.app["directory"].verify(name, password)
    if url is None:
        return web.json_response({"error": "denied"}, status=403)

    _log.info("verified access to %r", name)
    return web.json_response({"url": url})


def make_app(directory: Directory) -> web.Application:
    app = web.Application()
    app["directory"] = directory
    app.router.add_get("/servers",               handle_list_servers)
    app.router.add_post("/servers",              handle_register_server)
    app.router.add_delete("/servers/{name}",     handle_deregister_server)
    app.router.add_post("/servers/{name}/verify", handle_verify)
    return app
