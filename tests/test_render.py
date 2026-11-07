import pytest

from notmuch_browser.notmuch import iter_messages
from notmuch_browser.render import (
    cid_map,
    html_document_for,
    message_view,
    sanitize_html,
    thread_view,
)


def clean(html, cids=None, mid="m@test"):
    return sanitize_html(html, mid, cids or {})


@pytest.mark.parametrize(
    "dirty, must_not_contain",
    [
        ("<script>alert(1)</script><p>x</p>", "script"),
        ("<p onclick=\"x()\">x</p>", "onclick"),
        ('<img src="x" onerror="alert(1)">', "onerror"),
        ('<a href="javascript:alert(1)">x</a>', "javascript"),
        ('<a href="data:text/html,<b>x</b>">x</a>', "data:"),
        ('<img src="http://evil.example/p.gif">', "evil.example"),
        ('<img src="https://evil.example/p.gif">', "evil.example"),
        ('<img src="//evil.example/p.gif">', "evil.example"),
        ('<img src="data:image/png;base64,AAAA">', "data:"),
        ("<style>p{background:url(http://evil.example/x)}</style><p>x</p>", "evil.example"),
        ('<p style="background:url(http://evil.example/x)">x</p>', "style"),
        ('<form action="http://evil.example"><input name=q></form>', "form"),
        ('<iframe src="http://evil.example"></iframe>', "iframe"),
        ('<link rel="stylesheet" href="http://evil.example/a.css">', "evil.example"),
        ('<a href="//evil.example/x">x</a>', "evil.example"),
        ('<a href="/relative">x</a>', "/relative"),
        ("<!-- comment --><p>x</p>", "comment"),
    ],
)
def test_hostile_markup_is_removed(dirty, must_not_contain):
    assert must_not_contain not in clean(dirty).lower()


def test_good_content_survives():
    out = clean('<p>Hi <b>there</b> <a href="https://example.org/ok">link</a></p>')
    assert "<b>there</b>" in out
    assert 'href="https://example.org/ok"' in out


def test_links_are_forced_to_new_window_without_opener():
    out = clean('<a href="https://example.org/">x</a>')
    assert 'target="_blank"' in out
    assert "noopener" in out and "noreferrer" in out


def test_cid_image_is_rewritten_to_part_url():
    out = clean('<img src="cid:logo@test">', {"logo@test": 5}, mid="a b@test")
    assert 'src="/api/message/a%20b%40test/part/5"' in out


def test_unknown_cid_and_protocol_relative_images_are_dropped():
    out = clean('<img src="cid:unknown"><img src="//evil.example/p.gif">', {"logo@test": 5})
    assert "src" not in out


def test_cid_with_angle_brackets():
    out = clean('<img src="cid:logo@test">', {"logo@test": 7})
    assert "/part/7" in out


async def _message(nm, corpus, mid):
    data = await nm.show_thread(corpus.thread_of(mid))
    return next(m for m in iter_messages(data) if m["id"] == mid)


async def test_plain_message_view(nm, corpus):
    view = message_view(await _message(nm, corpus, "plain1@test"))
    assert "plain text" in view["text"]
    assert view["has_html"] is False
    assert view["attachments"] == []
    assert "filename" not in view  # no file system paths reach the client
    assert "/tmp" not in str(view)


async def test_alternative_prefers_text_and_offers_html(nm, corpus):
    view = message_view(await _message(nm, corpus, "alt@test"))
    assert view["text"].startswith("Plain version")
    assert view["has_html"] is True


async def test_html_only_message(nm, corpus):
    msg = await _message(nm, corpus, "hostile@test")
    view = message_view(msg)
    assert view["text_is_empty"] and view["has_html"]
    doc = html_document_for(msg)
    for bad in ("<script", "onerror", "onload", "javascript:", "evil.example", "<form", "<style>p"):
        assert bad not in doc
    assert "https://example.org/ok" in doc
    assert "<b>world</b>" in doc


async def test_attachment_listed(nm, corpus):
    view = message_view(await _message(nm, corpus, "attach@test"))
    [att] = view["attachments"]
    assert att["filename"] == "report.pdf"
    assert att["content_type"] == "application/pdf"
    assert att["part"] == 3


async def test_inline_image_is_not_an_attachment_and_is_rewritten(nm, corpus):
    msg = await _message(nm, corpus, "cid@test")
    assert message_view(msg)["attachments"] == []
    assert cid_map(msg) == {"logo@test": 5}
    doc = html_document_for(msg)
    assert "/api/message/cid%40test/part/5" in doc
    assert "evil.example" not in doc


async def test_non_utf8_charset_is_decoded(nm, corpus):
    view = message_view(await _message(nm, corpus, "latin1@test"))
    assert "Café crème" in view["text"]
    assert "�" not in view["text"]


async def test_thread_view_flattens_in_order_with_depth(nm, corpus):
    nested = await nm.show_thread(corpus.thread_of("long0@test"))
    view = thread_view("t", nested)
    assert view["subject"] == "Long thread"
    assert [m["id"] for m in view["messages"]] == [f"long{i}@test" for i in range(12)]
    assert [m["depth"] for m in view["messages"]] == list(range(12))
