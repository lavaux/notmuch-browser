"""Async wrapper over the notmuch command line.

Every call spawns `notmuch` with an argument list, never through a shell. User
supplied queries always come after a `--` separator. Tag names and identifiers
are validated before they reach an argument list or a batch line.
"""

from __future__ import annotations

import asyncio
import codecs
import json
import os
import re
from dataclasses import dataclass, field

MIN_VERSION = (0, 36)  # developed and tested against 0.40
READ_TIMEOUT = 60.0
# A running `notmuch new` or another writer holds the Xapian lock and notmuch
# then waits for it instead of failing. A short write timeout turns that wait
# into a clear "database busy" error.
WRITE_TIMEOUT = 15.0

TAG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.@:/=-]{0,63}$")
THREAD_RE = re.compile(r"^[0-9a-f]{1,32}$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")

# Bytes Windows-1252 leaves undefined. They decode as Latin-1 instead.
_CP1252_HOLES = frozenset({0x81, 0x8D, 0x8F, 0x90, 0x9D})


def _legacy_fallback(exc: UnicodeError) -> tuple[str, int]:
    if not isinstance(exc, UnicodeDecodeError):
        raise exc
    bad = exc.object[exc.start : exc.end]
    text = "".join(
        chr(b) if b in _CP1252_HOLES else bytes([b]).decode("cp1252") for b in bad
    )
    return text, exc.end


codecs.register_error("notmuch-browser-legacy", _legacy_fallback)


def decode_output(data: bytes) -> str:
    """Decode notmuch output as UTF-8, reading stray bytes as Windows-1252.

    notmuch copies a text part through unconverted when it declares no charset
    (or one notmuch cannot convert), so its JSON can hold raw legacy bytes. Such
    bytes are all >= 0x80 and therefore sit inside JSON strings, never in the
    structure. Valid UTF-8 is unchanged.

    Known limit: a Message-ID holding non-UTF-8 bytes decodes to Windows-1252
    text and no longer matches when sent back as `id:"..."`, so the routes that
    look that message up again return 404.
    """
    return data.decode("utf-8", "notmuch-browser-legacy")


class NotmuchError(Exception):
    """A notmuch command failed."""


class DatabaseBusy(NotmuchError):
    """The notmuch database is locked by another process."""


class BadQuery(NotmuchError):
    """The query or an argument is not valid."""


class NotFound(NotmuchError):
    """The thread, message or part does not exist."""


def validate_tag(tag: str) -> str:
    if not isinstance(tag, str) or not TAG_RE.match(tag):
        raise BadQuery(f"invalid tag name: {tag!r}")
    return tag


def thread_query(thread_id: str) -> str:
    if not isinstance(thread_id, str) or not THREAD_RE.match(thread_id):
        raise BadQuery("invalid thread id")
    return f"thread:{thread_id}"


def quote_term(value: str) -> str:
    """Quote a value with the Xapian boolean term rules (double quotes doubled)."""
    if not isinstance(value, str) or not value or _CONTROL_RE.search(value):
        raise BadQuery("invalid identifier")
    return '"' + value.replace('"', '""') + '"'


def message_query(message_id: str) -> str:
    return "id:" + quote_term(message_id)


def tag_query(tag: str) -> str:
    return "tag:" + quote_term(tag)


@dataclass
class Notmuch:
    config: str | None = None
    binary: str = "notmuch"
    read_timeout: float = READ_TIMEOUT
    write_timeout: float = WRITE_TIMEOUT
    max_processes: int = 4
    _sem: asyncio.Semaphore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._sem = asyncio.Semaphore(self.max_processes)

    # ------------------------------------------------------------------ core

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.config:
            env["NOTMUCH_CONFIG"] = self.config
        return env

    async def _run(
        self, *args: str, stdin: bytes | None = None, timeout: float | None = None
    ) -> bytes:
        timeout = self.read_timeout if timeout is None else timeout
        async with self._sem:
            proc = await asyncio.create_subprocess_exec(
                self.binary,
                *args,
                stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._env(),
            )
            try:
                out, err = await asyncio.wait_for(proc.communicate(stdin), timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise DatabaseBusy(
                    "notmuch did not answer in time; the database may be locked by "
                    "another process such as `notmuch new`"
                ) from None
        if proc.returncode != 0:
            message = err.decode("utf-8", "replace").strip() or f"exit status {proc.returncode}"
            lowered = message.lower()
            if "lock" in lowered:
                raise DatabaseBusy(message)
            if "parsing query" in lowered:
                raise BadQuery(message)
            raise NotmuchError(message)
        return out

    async def _json(self, *args: str, timeout: float | None = None):
        out = await self._run(*args, timeout=timeout)
        try:
            return json.loads(decode_output(out)) if out.strip() else []
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise NotmuchError(f"unexpected notmuch output: {exc}") from exc

    # ---------------------------------------------------------------- version

    async def version(self) -> tuple[int, ...]:
        out = (await self._run("--version")).decode().strip()
        match = re.search(r"(\d+)\.(\d+)", out)
        if not match:
            raise NotmuchError(f"cannot read the notmuch version from {out!r}")
        return int(match.group(1)), int(match.group(2))

    async def check_version(self) -> tuple[int, ...]:
        found = await self.version()
        if found < MIN_VERSION:
            need = ".".join(map(str, MIN_VERSION))
            have = ".".join(map(str, found))
            raise NotmuchError(f"notmuch {have} is too old, {need} or newer is required")
        return found

    # ------------------------------------------------------------------ reads

    async def search(self, query: str, offset: int = 0, limit: int = 50) -> list[dict]:
        return await self._json(
            "search",
            "--format=json",
            "--output=summary",
            "--sort=newest-first",
            f"--offset={int(offset)}",
            f"--limit={int(limit)}",
            "--",
            query,
        )

    async def count(self, query: str, unit: str = "messages") -> int:
        if unit not in ("messages", "threads"):
            raise BadQuery("unit must be messages or threads")
        args = ["count"]
        if unit == "threads":
            args.append("--output=threads")
        out = await self._run(*args, "--", query)
        return int(out.strip() or 0)

    async def tags(self) -> list[str]:
        return await self._json("search", "--format=json", "--output=tags", "--", "*")

    async def unread_counts(self, tags: list[str]) -> dict[str, int]:
        async def one(tag: str) -> tuple[str, int]:
            n = await self.count(f"{tag_query(tag)} and tag:unread", "threads")
            return tag, n

        return dict(await asyncio.gather(*(one(t) for t in tags)))

    async def show_thread(self, thread_id: str) -> list:
        """Return the nested notmuch JSON of a whole thread, HTML parts included."""
        data = await self._json(
            "show",
            "--format=json",
            "--entire-thread=true",
            "--include-html",
            "--",
            thread_query(thread_id),
        )
        if not data:
            raise NotFound("no such thread")
        return data

    async def show_message(self, message_id: str) -> dict:
        data = await self._json(
            "show",
            "--format=json",
            "--entire-thread=false",
            "--include-html",
            "--",
            message_query(message_id),
        )
        for msg in iter_messages(data):
            return msg
        raise NotFound("no such message")

    async def get_part(self, message_id: str, part: int) -> bytes:
        if not isinstance(part, int) or part < 1:
            raise BadQuery("invalid part number")
        return await self._run(
            "show", "--format=raw", f"--part={part}", "--", message_query(message_id)
        )

    # ----------------------------------------------------------------- writes

    async def _message_ids(self, query: str) -> list[str]:
        return await self._json("search", "--format=json", "--output=messages", "--", query)

    async def apply_tag_changes(
        self, scope: str, add: list[str], remove: list[str]
    ) -> dict[str, dict[str, list[str]]]:
        """Add and remove tags on every message matching `scope`.

        Returns the ids of the messages that actually changed, per tag, so a
        caller can undo exactly this change and nothing more.
        """
        add = [validate_tag(t) for t in dict.fromkeys(add)]
        remove = [validate_tag(t) for t in dict.fromkeys(remove)]
        if set(add) & set(remove):
            raise BadQuery("a tag cannot be added and removed in the same request")
        if not add and not remove:
            raise BadQuery("nothing to do")
        changed: dict[str, dict[str, list[str]]] = {"add": {}, "remove": {}}
        for tag in add:
            changed["add"][tag] = await self._message_ids(f"({scope}) and not {tag_query(tag)}")
        for tag in remove:
            changed["remove"][tag] = await self._message_ids(f"({scope}) and {tag_query(tag)}")
        entries = []
        for tag, ids in changed["add"].items():
            entries += [{"id": i, "add": [tag], "remove": []} for i in ids]
        for tag, ids in changed["remove"].items():
            entries += [{"id": i, "add": [], "remove": [tag]} for i in ids]
        await self.tag_batch(entries)
        return changed

    async def tag_batch(self, entries: list[dict]) -> None:
        """Apply `{id, add, remove}` entries with a single `notmuch tag --batch`."""
        lines = []
        for entry in entries:
            ops = [f"+{validate_tag(t)}" for t in entry.get("add", [])]
            ops += [f"-{validate_tag(t)}" for t in entry.get("remove", [])]
            if not ops:
                continue
            lines.append(" ".join(ops) + " -- " + message_query(entry["id"]))
        if not lines:
            return
        await self._run(
            "tag", "--batch", stdin=("\n".join(lines) + "\n").encode(), timeout=self.write_timeout
        )


def iter_messages(node):
    """Yield every message dict in the nested `notmuch show` structure."""
    if isinstance(node, dict):
        if "id" in node and "headers" in node:
            yield node
    elif isinstance(node, list):
        for child in node:
            yield from iter_messages(child)
