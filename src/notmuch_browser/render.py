"""Turn `notmuch show` JSON into the view model of the UI, and sanitise HTML mail.

HTML mail is hostile input. `sanitize_html` removes scripts, styles, forms, event
handlers and every remote resource. Only `cid:` images of the same message survive,
rewritten to the part download URL. The result is served as its own document inside a
sandboxed iframe, which is a second, independent layer.
"""

from __future__ import annotations

import re
from typing import Any, Iterator
from urllib.parse import quote

import nh3

ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "caption", "center", "cite", "code", "col",
    "colgroup", "dd", "div", "dl", "dt", "em", "font", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "img", "li", "ol", "p", "pre", "q", "s", "small", "span", "strike", "strong",
    "sub", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
}  # fmt: skip
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan", "align"},
    "th": {"colspan", "rowspan", "align"},
    "table": {"border", "cellpadding", "cellspacing", "width"},
    "font": {"color", "size"},
    "*": {"dir", "lang"},
}
LINK_SCHEMES = ("http://", "https://", "mailto:")
URL_SCHEMES = {"http", "https", "mailto", "cid"}
_CID_RE = re.compile(r"^cid:<?([^>]*)>?$", re.IGNORECASE)

DOCUMENT_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
html{{background:#fff;color:#1b1b1f}}
body{{margin:12px 14px;font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
overflow-wrap:anywhere}}
img{{max-width:100%;height:auto}}
table{{max-width:100%}}
blockquote{{margin:.5em 0;padding-left:.8em;border-left:3px solid #c8c8d0;color:#55555f}}
a{{color:#1a52b8}}
</style></head><body>{body}</body></html>
"""


def sanitize_html(html: str, message_id: str, cid_map: dict[str, int]) -> str:
    """Return a safe HTML fragment. `cid_map` maps Content-IDs to part numbers."""

    def attribute_filter(tag: str, attr: str, value: str) -> str | None:
        if tag == "img" and attr == "src":
            match = _CID_RE.match(value.strip())
            part = cid_map.get(match.group(1)) if match else None
            if part is None:
                return None
            return f"/api/message/{quote(message_id, safe='')}/part/{part}"
        if tag == "a" and attr == "href":
            href = value.strip()
            if href.lower().startswith(LINK_SCHEMES) or href.startswith("#"):
                return href
            return None
        return value

    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=URL_SCHEMES,
        attribute_filter=attribute_filter,
        link_rel="noopener noreferrer",
        set_tag_attribute_values={"a": {"target": "_blank"}},
        strip_comments=True,
    )


def wrap_document(fragment: str) -> str:
    return DOCUMENT_TEMPLATE.format(body=fragment)


# ---------------------------------------------------------------- show parsing


def iter_parts(parts: list[dict]) -> Iterator[dict]:
    for part in parts:
        yield part
        if isinstance(part.get("content"), list):
            yield from iter_parts(part["content"])


def cid_map(message: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for part in iter_parts(message.get("body", [])):
        cid = part.get("content-id")
        if cid:
            out[cid.strip("<>")] = part["id"]
    return out


def _is_attachment(part: dict) -> bool:
    if isinstance(part.get("content"), list):
        return False
    ctype = part.get("content-type", "")
    if part.get("filename") or part.get("content-disposition") == "attachment":
        return True
    return not ctype.startswith("text/") and not ctype.startswith("multipart/")


def collect_bodies(message: dict) -> tuple[str, str]:
    """Return (text, html) joined over the inline text parts of a message."""
    texts: list[str] = []
    htmls: list[str] = []
    for part in iter_parts(message.get("body", [])):
        content = part.get("content")
        if not isinstance(content, str) or _is_attachment(part):
            continue
        ctype = part.get("content-type", "")
        if ctype == "text/plain":
            texts.append(content)
        elif ctype == "text/html":
            htmls.append(content)
    return "\n".join(texts), "\n".join(htmls)


def referenced_cids(html: str) -> set[str]:
    return {m.group(1) for m in re.finditer(r"cid:<?([^\"'>\s]+)", html, re.IGNORECASE)}


def collect_attachments(message: dict, html: str) -> list[dict]:
    inline = referenced_cids(html)
    out = []
    for part in iter_parts(message.get("body", [])):
        if not _is_attachment(part):
            continue
        cid = (part.get("content-id") or "").strip("<>")
        if cid and cid in inline:
            continue
        out.append(
            {
                "part": part["id"],
                "filename": part.get("filename") or f"part-{part['id']}",
                "content_type": part.get("content-type", "application/octet-stream"),
                "size": part.get("content-length"),
            }
        )
    return out


def message_view(message: dict, depth: int = 0) -> dict[str, Any]:
    """The JSON the UI receives for one message. File system paths are left out."""
    text, html = collect_bodies(message)
    headers = message.get("headers", {})
    return {
        "id": message["id"],
        "depth": depth,
        "match": bool(message.get("match")),
        "tags": message.get("tags", []),
        "timestamp": message.get("timestamp"),
        "date_relative": message.get("date_relative"),
        "headers": {
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "cc": headers.get("Cc", ""),
            "date": headers.get("Date", ""),
        },
        "text": text,
        "has_html": bool(html.strip()),
        "text_is_empty": not text.strip(),
        "attachments": collect_attachments(message, html),
    }


def thread_view(thread_id: str, nested: list) -> dict[str, Any]:
    """Flatten the nested `show` structure depth first, keeping the depth of each reply."""
    messages: list[dict] = []

    def walk(node: Any, depth: int) -> None:
        # A level is a list of [message, [replies]] pairs.
        for item in node:
            if isinstance(item, list) and item and isinstance(item[0], dict):
                messages.append(message_view(item[0], depth))
                if len(item) > 1:
                    walk(item[1], depth + 1)
            elif isinstance(item, list):
                walk(item, depth)

    walk(nested, 0)
    subject = messages[0]["headers"]["subject"] if messages else ""
    return {"thread": thread_id, "subject": subject, "messages": messages}


def html_document_for(message: dict) -> str | None:
    """The sanitised standalone HTML document of a message, or None without HTML."""
    _, html = collect_bodies(message)
    if not html.strip():
        return None
    return wrap_document(sanitize_html(html, message["id"], cid_map(message)))
