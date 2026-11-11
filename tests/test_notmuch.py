import os
import subprocess
import time

import pytest

from notmuch_browser.notmuch import (
    BadQuery,
    DatabaseBusy,
    NotFound,
    decode_output,
    iter_messages,
    message_query,
    quote_term,
    thread_query,
    validate_tag,
)


async def test_version_ok(nm):
    assert await nm.check_version() >= (0, 36)


async def test_count_units(nm, corpus):
    messages = await nm.count("*")
    threads = await nm.count("*", "threads")
    assert messages == 23
    assert threads < messages
    assert messages == int(corpus.cli("count", "--", "*"))


async def test_count_rejects_bad_unit(nm):
    with pytest.raises(BadQuery):
        await nm.count("*", "bytes")


async def test_search_pages_and_order(nm):
    first = await nm.search("*", 0, 4)
    second = await nm.search("*", 4, 4)
    assert len(first) == 4 and len(second) == 4
    assert {t["thread"] for t in first}.isdisjoint({t["thread"] for t in second})
    stamps = [t["timestamp"] for t in first]
    assert stamps == sorted(stamps, reverse=True)


async def test_search_query_that_looks_like_an_option(nm):
    # After `--` a leading dash is query text. If it acted as a flag, `--format=text`
    # would make the output non-JSON and `--limit=1` would cap the result.
    assert await nm.search("--format=text", 0, 5) == []
    assert await nm.search("--limit=1", 0, 5) == []


async def test_bad_query_is_reported(nm):
    # `tag:(` is accepted by notmuch (empty result), `foo AND (` is a real parse error.
    with pytest.raises(BadQuery):
        await nm.search("foo AND (", 0, 5)
    with pytest.raises(BadQuery):
        await nm.search("date:garbage..", 0, 5)


async def test_tags_and_unread_counts(nm):
    tags = await nm.tags()
    assert {"inbox", "unread", "flagged"} <= set(tags)
    counts = await nm.unread_counts(["inbox", "flagged"])
    assert counts["inbox"] > 0
    assert counts["flagged"] == 0


async def test_show_thread_and_parts(nm, corpus):
    tid = corpus.thread_of("attach@test")
    data = await nm.show_thread(tid)
    [msg] = list(iter_messages(data))
    assert msg["id"] == "attach@test"
    names = []

    def walk(parts):
        for p in parts:
            names.append(p.get("filename"))
            if isinstance(p.get("content"), list):
                walk(p["content"])

    walk(msg["body"])
    assert "report.pdf" in names
    raw = await nm.get_part("attach@test", 3)
    assert raw.startswith(b"%PDF")


async def test_show_missing_thread(nm):
    with pytest.raises(NotFound):
        await nm.show_thread("deadbeef")


async def test_show_long_thread_is_nested(nm, corpus):
    data = await nm.show_thread(corpus.thread_of("long0@test"))
    assert len(list(iter_messages(data))) == 12


def test_validators():
    for good in ("inbox", "x.y", "a-b", "p:q", "A_1"):
        assert validate_tag(good) == good
    for bad in ("-x", "+x", "", "a b", "a\nb", 'a"b', "x" * 65, None):
        with pytest.raises(BadQuery):
            validate_tag(bad)
    with pytest.raises(BadQuery):
        thread_query("abc; rm -rf")
    with pytest.raises(BadQuery):
        quote_term("a\nb")
    assert message_query('we"ird id') == 'id:"we""ird id"'


async def test_apply_tag_changes_reports_only_changed_ids(nm, corpus):
    tid = corpus.thread_of("mixed0@test")
    changed = await nm.apply_tag_changes(f"thread:{tid}", ["flagged"], [])
    # mixed1 was already flagged, so only the other two changed.
    assert sorted(changed["add"]["flagged"]) == ["mixed0@test", "mixed2@test"]
    for i in range(3):
        assert "flagged" in corpus.tags_of(f"mixed{i}@test")


async def test_undo_restores_exact_state(nm, corpus):
    tid = corpus.thread_of("mixed0@test")
    changed = await nm.apply_tag_changes(f"thread:{tid}", ["flagged"], [])
    undo = [
        {"id": i, "add": [], "remove": [tag]} for tag, ids in changed["add"].items() for i in ids
    ]
    await nm.tag_batch(undo)
    assert "flagged" not in corpus.tags_of("mixed0@test")
    assert "flagged" in corpus.tags_of("mixed1@test")
    assert "flagged" not in corpus.tags_of("mixed2@test")


async def test_tag_rejects_conflicting_and_empty(nm):
    with pytest.raises(BadQuery):
        await nm.apply_tag_changes("*", ["x"], ["x"])
    with pytest.raises(BadQuery):
        await nm.apply_tag_changes("*", [], [])
    with pytest.raises(BadQuery):
        await nm.apply_tag_changes("*", ["-evil"], [])


async def test_flag_sync_renames_maildir_file(nm, corpus):
    before = {p.name for p in (corpus.mail / "cur").iterdir()}
    await nm.apply_tag_changes('id:"plain1@test"', ["flagged"], [])
    after = {p.name for p in (corpus.mail / "cur").iterdir()}
    gone, new = before - after, after - before
    assert len(gone) == 1 and len(new) == 1
    assert new.pop().endswith(":2,F")


async def test_database_busy_when_locked(nm, corpus):
    """Hold the Xapian write lock with a batch tagger whose stdin stays open."""
    holder = subprocess.Popen(
        ["notmuch", "tag", "--batch"],
        stdin=subprocess.PIPE,
        env=corpus.env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(1.0)
        assert holder.poll() is None
        with pytest.raises(DatabaseBusy):
            await nm.apply_tag_changes('id:"plain1@test"', ["flagged"], [])
    finally:
        holder.stdin.close()
        holder.wait(timeout=10)
    # Once the lock is released the same call works again.
    await nm.apply_tag_changes('id:"plain1@test"', ["flagged"], [])
    assert "flagged" in corpus.tags_of("plain1@test")
    assert os.path.exists(corpus.config)


# ------------------------------------------------------ non-UTF-8 output


@pytest.mark.parametrize(
    "raw, text",
    [
        ("Café “ok”".encode(), "Café “ok”"),
        (b"caf\xe9", "café"),
        (b"\xe2\x80", "\u00e2\u20ac"),
        (b"\x81\x93ok\x94", "\x81“ok”"),
        (b"\xe2\x80\x9c ok \xe9", "“ ok é"),
    ],
)
def test_decode_output_falls_back_per_byte(raw, text):
    assert decode_output(raw) == text


async def test_show_thread_with_raw_8bit_body(nm, raw8bit):
    data = await nm.show_thread(raw8bit)
    (msg,) = iter_messages(data)
    parts = msg["body"][0]["content"]
    plain = next(p for p in parts if p["content-type"] == "text/plain")
    assert "Café “cité”" in plain["content"]
