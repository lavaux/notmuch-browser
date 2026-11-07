import subprocess
import time

import pytest

from notmuch_browser.app import create_app


@pytest.fixture
def static_dir(tmp_path):
    root = tmp_path / "static"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<!doctype html><title>stub</title>")
    (root / "assets" / "app.js").write_text("console.log('stub')")
    return root


@pytest.fixture
async def client(aiohttp_client, nm, static_dir):
    return await aiohttp_client(create_app(nm, static_dir))


def origin(client):
    return f"http://127.0.0.1:{client.port}"


async def post(client, path, body, **headers):
    return await client.post(path, json=body, headers={"Origin": origin(client), **headers})


# ------------------------------------------------------------------- security


async def test_foreign_host_is_rejected(client):
    for host in ("evil.example", f"127.0.0.1:{client.port + 1}", "127.0.0.1", "localhost"):
        resp = await client.get("/api/tags", headers={"Host": host})
        assert resp.status == 403, host


async def test_loopback_hosts_are_accepted(client):
    resp = await client.get("/api/tags", headers={"Host": f"localhost:{client.port}"})
    assert resp.status == 200


async def test_cross_site_fetch_is_rejected(client):
    resp = await client.get("/api/tags", headers={"Sec-Fetch-Site": "cross-site"})
    assert resp.status == 403


async def test_cross_site_is_refused_except_inline_image_parts(client):
    cross = {"Sec-Fetch-Site": "cross-site"}
    image = {**cross, "Sec-Fetch-Dest": "image"}
    part = "/api/message/cid%40test/part/5"
    assert (await client.get(part, headers=image)).status == 200
    assert (await client.get(part, headers=cross)).status == 403
    assert (await client.get("/api/tags", headers=image)).status == 403
    assert (await client.get("/api/thread/deadbeef", headers=image)).status == 403
    assert (await client.get("/api/message/cid%40test/html", headers=image)).status == 403


async def test_post_needs_matching_origin(client):
    body = {"add": ["x"], "remove": []}
    assert (await client.post("/api/message/plain1@test/tags", json=body)).status == 403
    resp = await client.post(
        "/api/message/plain1@test/tags", json=body, headers={"Origin": "http://evil.example"}
    )
    assert resp.status == 403


async def test_post_needs_json_content_type(client):
    resp = await client.post(
        "/api/message/plain1@test/tags",
        data='{"add":["x"]}',
        headers={"Origin": origin(client), "Content-Type": "text/plain"},
    )
    assert resp.status == 415


async def test_security_headers(client):
    resp = await client.get("/api/tags")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]
    assert resp.headers["Cache-Control"] == "no-store"
    assert "Access-Control-Allow-Origin" not in resp.headers


# ---------------------------------------------------------------------- reads


async def test_search_paginates(client):
    first = await (await client.get("/api/search", params={"q": "*", "limit": 4})).json()
    assert len(first["threads"]) == 4 and first["has_more"] is True
    rest = await (
        await client.get("/api/search", params={"q": "*", "limit": 50, "offset": 4})
    ).json()
    assert rest["has_more"] is False
    assert {t["thread"] for t in first["threads"]}.isdisjoint({t["thread"] for t in rest["threads"]})
    assert "filename" not in first["threads"][0]


async def test_search_limit_is_capped(client):
    resp = await client.get("/api/search", params={"limit": 5000})
    assert resp.status == 400
    assert (await client.get("/api/search", params={"offset": "x"})).status == 400


async def test_bad_query_gives_400(client):
    resp = await client.get("/api/search", params={"q": "foo AND ("})
    assert resp.status == 400
    assert (await resp.json())["kind"] == "bad_request"


async def test_count_messages_by_default_and_threads_on_request(client, corpus):
    messages = (await (await client.get("/api/count", params={"q": "*"})).json())["count"]
    threads = (
        await (await client.get("/api/count", params={"q": "*", "unit": "threads"})).json()
    )["count"]
    assert messages == int(corpus.cli("count", "--", "*")) == 23
    assert threads == int(corpus.cli("count", "--output=threads", "--", "*"))
    assert threads < messages
    assert (await client.get("/api/count", params={"unit": "bytes"})).status == 400


async def test_tags_and_counts(client):
    tags = (await (await client.get("/api/tags")).json())["tags"]
    assert "inbox" in tags
    counts = (await (await client.get("/api/tags/counts")).json())["counts"]
    assert set(counts) == set(tags)
    assert counts["flagged"] == 0


async def test_thread_endpoint(client, corpus):
    resp = await client.get(f"/api/thread/{corpus.thread_of('long0@test')}")
    data = await resp.json()
    assert data["subject"] == "Long thread"
    assert len(data["messages"]) == 12
    assert "/tmp" not in str(data)


async def test_thread_id_is_validated(client):
    assert (await client.get("/api/thread/not-hex!")).status == 400
    assert (await client.get("/api/thread/deadbeef")).status == 404


async def test_message_id_with_slash_and_plus(client):
    resp = await client.get("/api/message/odd%2Fid%2Bx%40test/part/1")
    assert resp.status == 200
    assert b"slash and a plus" in await resp.read()


# ---------------------------------------------------------------- attachments


async def test_attachment_download_is_forced_and_sandboxed(client):
    resp = await client.get("/api/message/attach@test/part/3")
    assert resp.status == 200
    assert resp.headers["Content-Disposition"].startswith("attachment;")
    assert "report.pdf" in resp.headers["Content-Disposition"]
    assert resp.headers["Content-Security-Policy"] == "default-src 'none'; sandbox"
    assert (await resp.read()).startswith(b"%PDF")


async def test_part_ids_are_validated(client):
    for bad in ("..%2F..%2Fetc%2Fpasswd", "x", "0", "-1", "99"):
        resp = await client.get(f"/api/message/attach@test/part/{bad}")
        assert resp.status in (400, 404), bad
    assert (await client.get("/api/message/missing@test/part/1")).status == 404


# ----------------------------------------------------------------- HTML mail


async def test_html_document_is_sanitised_with_explicit_csp(client):
    resp = await client.get("/api/message/hostile@test/html")
    assert resp.status == 200
    csp = resp.headers["Content-Security-Policy"]
    assert f"img-src {origin(client)}" in csp
    assert "'self'" not in csp.split("frame-ancestors")[0]
    text = await resp.text()
    for bad in ("<script", "onerror", "onload", "javascript:", "evil.example"):
        assert bad not in text


async def test_cid_image_is_served_and_html_points_at_it(client):
    text = await (await client.get("/api/message/cid@test/html")).text()
    assert "/api/message/cid%40test/part/5" in text
    img = await client.get("/api/message/cid%40test/part/5")
    assert img.status == 200
    assert img.content_type == "image/png"


async def test_message_without_html_gives_404(client):
    assert (await client.get("/api/message/plain1@test/html")).status == 404


# ----------------------------------------------------------------- tag writes


async def test_flag_round_trip(client, corpus):
    resp = await post(client, "/api/message/plain1@test/tags", {"add": ["flagged"], "remove": []})
    assert resp.status == 200
    assert (await resp.json())["changed"]["add"] == {"flagged": ["plain1@test"]}
    assert "flagged" in corpus.tags_of("plain1@test")
    resp = await post(client, "/api/message/plain1@test/tags", {"add": [], "remove": ["flagged"]})
    assert (await resp.json())["changed"]["remove"] == {"flagged": ["plain1@test"]}
    assert "flagged" not in corpus.tags_of("plain1@test")


async def test_undo_on_partly_flagged_thread_restores_exact_state(client, corpus):
    before = {i: corpus.tags_of(f"mixed{i}@test") for i in range(3)}
    assert "flagged" in before[1] and "flagged" not in before[0]
    tid = corpus.thread_of("mixed0@test")
    resp = await post(client, f"/api/thread/{tid}/tags", {"add": ["flagged"], "remove": []})
    changed = (await resp.json())["changed"]
    assert sorted(changed["add"]["flagged"]) == ["mixed0@test", "mixed2@test"]
    changes = [
        {"id": i, "add": [], "remove": ["flagged"]} for i in changed["add"]["flagged"]
    ]
    resp = await post(client, "/api/messages/tags", {"changes": changes})
    assert (await resp.json())["applied"] == 2
    after = {i: corpus.tags_of(f"mixed{i}@test") for i in range(3)}
    assert after == before


async def test_tag_counts_cache_is_invalidated_by_writes(client):
    counts = (await (await client.get("/api/tags/counts")).json())["counts"]
    assert counts["flagged"] == 0
    await post(client, "/api/message/plain1@test/tags", {"add": ["flagged", "unread"], "remove": []})
    counts = (await (await client.get("/api/tags/counts")).json())["counts"]
    assert counts["flagged"] == 1


async def test_tag_write_validation(client):
    for body in (
        {"add": ["-evil"]},
        {"add": ["a b"]},
        {"add": "flagged"},
        {"add": [1]},
        {"add": ["x"], "remove": ["x"]},
        {},
        {"add": [f"t{i}" for i in range(50)]},
    ):
        resp = await post(client, "/api/message/plain1@test/tags", body)
        assert resp.status == 400, body
    resp = await post(client, "/api/messages/tags", {"changes": []})
    assert resp.status == 400
    resp = await post(client, "/api/messages/tags", {"changes": [{"id": 5}]})
    assert resp.status == 400


async def test_busy_database_gives_503(client, corpus):
    holder = subprocess.Popen(
        ["notmuch", "tag", "--batch"],
        stdin=subprocess.PIPE,
        env=corpus.env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(1.0)
        resp = await post(client, "/api/message/plain1@test/tags", {"add": ["flagged"]})
        assert resp.status == 503
        assert resp.headers["Retry-After"] == "5"
        assert (await resp.json())["kind"] == "busy"
        # Reads are not blocked by a writer.
        assert (await client.get("/api/count")).status == 200
    finally:
        holder.stdin.close()
        holder.wait(timeout=10)


# --------------------------------------------------------------------- static


async def test_static_files_are_served(client):
    resp = await client.get("/")
    assert resp.status == 200
    assert "stub" in await resp.text()
    assert resp.headers["Cache-Control"] == "no-cache"
    assert (await client.get("/assets/app.js")).status == 200


async def test_static_path_traversal_is_refused(client):
    resp = await client.get("/assets/..%2F..%2Findex.html")
    assert resp.status in (403, 404)
    resp = await client.get("/assets/%2e%2e/index.html")
    assert resp.status in (403, 404)


async def test_missing_bundle_gives_a_clear_503(aiohttp_client, nm, tmp_path):
    client = await aiohttp_client(create_app(nm, tmp_path / "nothing"))
    resp = await client.get("/")
    assert resp.status == 503
    assert "npm" in await resp.text()
