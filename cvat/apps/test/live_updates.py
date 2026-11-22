# SPDX-License-Identifier: MIT

"""
Live updates for the annotation counts page.

Saving annotations publishes "changed" on a Redis channel for the task. Every server
process holds the sockets of its own clients and forwards the message to the ones
watching that task. The browser then fetches the counts again over plain HTTP, so
the job filter and the access rules stay in one place: the HTTP endpoint.
"""

import asyncio
import json
import re
from urllib.parse import urlsplit

import redis
import redis.asyncio as aioredis
from django.conf import settings

SOCKET_PATH = re.compile(r"^/api/annotation-counts/(?P<task_id>\d+)/live$")

# close codes the page treats as final, no point reconnecting
CLOSE_FORBIDDEN = 4403
CLOSE_NOT_FOUND = 4404


def _redis_kwargs() -> dict:
    return {
        "host": settings.REDIS_INMEM_SETTINGS["HOST"],
        "port": int(settings.REDIS_INMEM_SETTINGS["PORT"]),
        "password": settings.REDIS_INMEM_SETTINGS["PASSWORD"] or None,
    }


def _channel(task_id: int) -> str:
    return f"annotation-counts:task:{task_id}"


def publish_task_changed(task_id: int) -> None:
    with redis.Redis(**_redis_kwargs()) as client:
        client.publish(_channel(task_id), "changed")


async def _http_status(django_app, ws_scope: dict, path: str) -> int | None:
    """
    Runs GET <path> through the normal Django stack with the socket's cookies and
    returns the status code, so the socket gets exactly the same login and access
    check as the HTTP endpoint.
    """
    scope = {
        **ws_scope,
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "scheme": "https" if ws_scope.get("scheme") == "wss" else "http",
    }
    scope.pop("subprotocols", None)
    status = None
    sent_body = False

    async def receive():
        nonlocal sent_body
        if not sent_body:
            sent_body = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await asyncio.Event().wait()  # never disconnects, Django cancels this when done

    async def send(message):
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]

    await django_app(scope, receive, send)
    return status


def _same_origin(scope: dict) -> bool:
    # cookies are sent with the handshake, so refuse sockets opened by other sites
    headers = dict(scope["headers"])
    origin = headers.get(b"origin", b"").decode()
    host = headers.get(b"host", b"").decode()
    return bool(origin) and urlsplit(origin).hostname == urlsplit(f"//{host}").hostname


async def serve_socket(scope, receive, send, django_app) -> None:
    await receive()  # websocket.connect

    match = SOCKET_PATH.match(scope["path"])
    if not match:
        await send({"type": "websocket.close", "code": CLOSE_NOT_FOUND})
        return
    task_id = int(match["task_id"])

    status = await _http_status(django_app, scope, f"/api/annotation-counts/{task_id}")
    await send({"type": "websocket.accept"})
    if not _same_origin(scope) or status != 200:
        await send({
            "type": "websocket.close",
            "code": CLOSE_NOT_FOUND if status == 404 else CLOSE_FORBIDDEN,
        })
        return

    client = aioredis.Redis(**_redis_kwargs())
    pubsub = client.pubsub()
    await pubsub.subscribe(_channel(task_id))

    async def forward_changes():
        async for message in pubsub.listen():
            if message["type"] == "message":
                await send({"type": "websocket.send", "text": json.dumps({"event": "changed"})})

    async def wait_for_disconnect():
        while (await receive())["type"] != "websocket.disconnect":
            pass

    forwarder = asyncio.create_task(forward_changes())
    listener = asyncio.create_task(wait_for_disconnect())
    try:
        await asyncio.wait({forwarder, listener}, return_when=asyncio.FIRST_COMPLETED)
        if forwarder.done():
            # lost Redis: close so the page reconnects instead of waiting on a dead socket
            await send({"type": "websocket.close", "code": 1011})
    finally:
        forwarder.cancel()
        listener.cancel()
        await pubsub.aclose()
        await client.aclose()
