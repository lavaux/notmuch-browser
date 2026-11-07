"""The aiohttp application: a small REST API over notmuch plus the bundled UI."""

from __future__ import annotations

import asyncio
import time
from importlib import resources
from pathlib import Path
from urllib.parse import quote

from aiohttp import web

from . import render
from .notmuch import (
    BadQuery,
    DatabaseBusy,
    NotFound,
    Notmuch,
    NotmuchError,
    message_query,
    thread_query,
)

PAGE_SIZE = 50
COUNTS_TTL = 30.0
MAX_BATCH = 1000
MAX_TAGS_PER_REQUEST = 20
NM = web.AppKey("nm", Notmuch)
STATIC = web.AppKey("static", Path)
COUNTS = web.AppKey("counts", dict)

APP_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; frame-src 'self'; base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'self'"
)
ATTACHMENT_CSP = "default-src 'none'; sandbox"
# Types a browser could execute if it ever rendered them. They are downloaded as opaque bytes.
RISKY_TYPES = ("text/html", "application/xhtml+xml", "image/svg+xml", "text/xml", "application/xml")


def default_static_dir() -> Path:
    return Path(str(resources.files("notmuch_browser") / "static"))


# ------------------------------------------------------------------ middleware


def listening_port(request: web.Request) -> int | None:
    transport = request.transport
    sockname = transport.get_extra_info("sockname") if transport else None
    return sockname[1] if sockname else None


def forbidden(reason: str) -> web.Response:
    return web.json_response({"error": reason, "kind": "forbidden"}, status=403)


def is_inline_image(request: web.Request) -> bool:
    """The one cross-site request the app serves itself.

    HTML mail is shown in a sandboxed frame without allow-same-origin, so the browser
    treats that frame as a foreign origin and labels its inline `cid:` image requests
    cross-site. They are plain image loads of a message part, which a foreign page could
    only use to learn that a part exists and how large the image is, and only if it
    already knew the message id. Everything else cross-site stays refused.
    """
    return (
        request.method == "GET"
        and request.headers.get("Sec-Fetch-Dest") == "image"
        and request.path.startswith("/api/message/")
        and "/part/" in request.path
    )


@web.middleware
async def security(request: web.Request, handler):
    port = listening_port(request)
    host = request.headers.get("Host", "")
    if port is None or host not in (f"127.0.0.1:{port}", f"localhost:{port}"):
        return forbidden("unexpected Host header")
    if request.headers.get("Sec-Fetch-Site") == "cross-site" and not is_inline_image(request):
        return forbidden("cross-site request")
    if request.method not in ("GET", "HEAD"):
        if request.headers.get("Origin") != f"http://{host}":
            return forbidden("unexpected Origin header")
        if request.content_type != "application/json":
            return web.json_response(
                {"error": "content type must be application/json", "kind": "bad_request"},
                status=415,
            )
    try:
        response = await handler(request)
    except web.HTTPException:
        raise
    except BadQuery as exc:
        return web.json_response({"error": str(exc), "kind": "bad_request"}, status=400)
    except NotFound as exc:
        return web.json_response({"error": str(exc), "kind": "not_found"}, status=404)
    except DatabaseBusy as exc:
        return web.json_response(
            {"error": str(exc), "kind": "busy"}, status=503, headers={"Retry-After": "5"}
        )
    except NotmuchError as exc:
        return web.json_response({"error": str(exc), "kind": "error"}, status=500)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Content-Security-Policy", APP_CSP)
    if request.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


# --------------------------------------------------------------------- helpers


def int_param(request: web.Request, name: str, default: int, low: int, high: int) -> int:
    raw = request.query.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise BadQuery(f"{name} must be an integer") from None
    if not low <= value <= high:
        raise BadQuery(f"{name} must be between {low} and {high}")
    return value


async def read_json(request: web.Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        raise BadQuery("request body is not valid JSON") from None
    if not isinstance(body, dict):
        raise BadQuery("request body must be a JSON object")
    return body


def tag_list(body: dict, key: str) -> list[str]:
    value = body.get(key, [])
    if not isinstance(value, list) or len(value) > MAX_TAGS_PER_REQUEST:
        raise BadQuery(f"{key} must be a short list of tag names")
    if not all(isinstance(t, str) for t in value):
        raise BadQuery(f"{key} must contain strings")
    return value


def invalidate_counts(app: web.Application) -> None:
    app[COUNTS].clear()


# ------------------------------------------------------------------- handlers


async def api_search(request: web.Request) -> web.Response:
    nm = request.app[NM]
    query = request.query.get("q", "").strip() or "*"
    offset = int_param(request, "offset", 0, 0, 10_000_000)
    limit = int_param(request, "limit", PAGE_SIZE, 1, PAGE_SIZE)
    rows = await nm.search(query, offset, limit + 1)
    keep = ("thread", "timestamp", "date_relative", "matched", "total", "authors", "subject", "tags")
    threads = [{k: row.get(k) for k in keep} for row in rows[:limit]]
    return web.json_response(
        {"threads": threads, "offset": offset, "limit": limit, "has_more": len(rows) > limit}
    )


async def api_count(request: web.Request) -> web.Response:
    query = request.query.get("q", "").strip() or "*"
    unit = request.query.get("unit", "messages")
    count = await request.app[NM].count(query, unit)
    return web.json_response({"count": count, "unit": unit})


async def api_tags(request: web.Request) -> web.Response:
    return web.json_response({"tags": await request.app[NM].tags()})


async def api_tag_counts(request: web.Request) -> web.Response:
    cache = request.app[COUNTS]
    async with cache.setdefault("lock", asyncio.Lock()):
        fresh = cache.get("at") is not None and time.monotonic() - cache["at"] < COUNTS_TTL
        if not fresh:
            nm = request.app[NM]
            counts = await nm.unread_counts(await nm.tags())
            cache["counts"], cache["at"] = counts, time.monotonic()
    return web.json_response({"counts": cache["counts"], "unit": "unread threads"})


async def api_thread(request: web.Request) -> web.Response:
    thread_id = request.match_info["id"]
    nested = await request.app[NM].show_thread(thread_id)
    return web.json_response(render.thread_view(thread_id, nested))


def changed_payload(changed: dict) -> web.Response:
    return web.json_response({"changed": changed})


async def api_thread_tags(request: web.Request) -> web.Response:
    body = await read_json(request)
    changed = await request.app[NM].apply_tag_changes(
        thread_query(request.match_info["id"]), tag_list(body, "add"), tag_list(body, "remove")
    )
    invalidate_counts(request.app)
    return changed_payload(changed)


async def api_message_tags(request: web.Request) -> web.Response:
    body = await read_json(request)
    changed = await request.app[NM].apply_tag_changes(
        message_query(request.match_info["id"]), tag_list(body, "add"), tag_list(body, "remove")
    )
    invalidate_counts(request.app)
    return changed_payload(changed)


async def api_messages_tags(request: web.Request) -> web.Response:
    body = await read_json(request)
    changes = body.get("changes")
    if not isinstance(changes, list) or not changes or len(changes) > MAX_BATCH:
        raise BadQuery(f"changes must be a list of 1 to {MAX_BATCH} entries")
    entries = []
    for change in changes:
        if not isinstance(change, dict) or not isinstance(change.get("id"), str):
            raise BadQuery("each change needs a message id")
        entries.append(
            {"id": change["id"], "add": tag_list(change, "add"), "remove": tag_list(change, "remove")}
        )
    await request.app[NM].tag_batch(entries)
    invalidate_counts(request.app)
    return web.json_response({"applied": len(entries)})


def find_part(message: dict, part: int) -> dict:
    for candidate in render.iter_parts(message.get("body", [])):
        if candidate.get("id") == part:
            return candidate
    raise NotFound("no such part")


def attachment_filename(part: dict, number: int) -> str:
    name = part.get("filename") or f"part-{number}"
    return name.replace("\\", "_").replace("/", "_").replace("\r", " ").replace("\n", " ")


async def api_part(request: web.Request) -> web.Response:
    nm = request.app[NM]
    message_id = request.match_info["id"]
    try:
        number = int(request.match_info["part"])
    except ValueError:
        raise BadQuery("invalid part number") from None
    message = await nm.show_message(message_id)
    part = find_part(message, number)
    data = await nm.get_part(message_id, number)
    ctype = part.get("content-type", "application/octet-stream").split(";")[0].strip().lower()
    if ctype.startswith(RISKY_TYPES) or "/" not in ctype:
        ctype = "application/octet-stream"
    name = attachment_filename(part, number)
    return web.Response(
        body=data,
        content_type=ctype,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(name, safe='')}",
            "Content-Security-Policy": ATTACHMENT_CSP,
        },
    )


async def api_html(request: web.Request) -> web.Response:
    message = await request.app[NM].show_message(request.match_info["id"])
    document = render.html_document_for(message)
    if document is None:
        raise NotFound("message has no HTML part")
    origin = f"http://{request.headers['Host']}"
    csp = (
        f"default-src 'none'; img-src {origin}; style-src 'unsafe-inline'; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
    )
    return web.Response(
        text=document, content_type="text/html", headers={"Content-Security-Policy": csp}
    )


async def index(request: web.Request) -> web.StreamResponse:
    page = request.app[STATIC] / "index.html"
    if not page.is_file():
        return web.Response(
            status=503,
            text="The UI bundle is missing. Run `npm ci && npm run build` and restart.",
        )
    return web.FileResponse(page, headers={"Cache-Control": "no-cache"})


# ------------------------------------------------------------------------ app


def create_app(nm: Notmuch, static_dir: Path | None = None) -> web.Application:
    app = web.Application(middlewares=[security])
    app[NM] = nm
    app[STATIC] = static_dir or default_static_dir()
    app[COUNTS] = {}
    app.router.add_get("/api/search", api_search)
    app.router.add_get("/api/count", api_count)
    app.router.add_get("/api/tags", api_tags)
    app.router.add_get("/api/tags/counts", api_tag_counts)
    app.router.add_get("/api/thread/{id}", api_thread)
    app.router.add_post("/api/thread/{id}/tags", api_thread_tags)
    app.router.add_post("/api/message/{id}/tags", api_message_tags)
    app.router.add_post("/api/messages/tags", api_messages_tags)
    app.router.add_get(r"/api/message/{id}/part/{part}", api_part)
    app.router.add_get("/api/message/{id}/html", api_html)
    app.router.add_get("/", index)
    assets = app[STATIC] / "assets"
    if assets.is_dir():
        app.router.add_static("/assets", assets, follow_symlinks=False)
    return app

