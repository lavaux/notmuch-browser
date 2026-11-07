"""Throwaway notmuch database for the tests. The real database is never touched."""

from __future__ import annotations

import base64
import os
import subprocess
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import format_datetime
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from notmuch_browser.notmuch import Notmuch

# A 1x1 transparent PNG.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

HOSTILE_HTML = """\
<html><head><style>body{background:url(http://evil.example/x.png)}</style></head>
<body onload="alert(1)">
<p>Hello <b>world</b></p>
<script>alert('xss')</script>
<img src="http://evil.example/pixel.gif">
<img src="//evil.example/proto.gif">
<img src="x" onerror="alert(2)">
<a href="javascript:alert(3)">js link</a>
<a href="https://example.org/ok">good link</a>
<form action="http://evil.example"><input name="q"></form>
</body></html>
"""


@dataclass
class Corpus:
    root: Path
    config: Path
    mail: Path

    def env(self) -> dict[str, str]:
        return {**os.environ, "NOTMUCH_CONFIG": str(self.config)}

    def cli(self, *args: str) -> str:
        return subprocess.run(
            ["notmuch", *args], env=self.env(), check=True, capture_output=True, text=True
        ).stdout

    def thread_of(self, message_id: str) -> str:
        out = self.cli("search", "--output=threads", "--", f'id:"{message_id}"')
        return out.strip().removeprefix("thread:")

    def tags_of(self, message_id: str) -> list[str]:
        out = self.cli("search", "--output=tags", "--", f'id:"{message_id}"')
        return out.split()


def _base(msg_id: str, subject: str, n: int, sender="alice@example.org", reply_to=None):
    msg = EmailMessage()
    msg["From"] = f"Sender <{sender}>"
    msg["To"] = "Guilhem <me@example.org>"
    msg["Subject"] = subject
    msg["Message-ID"] = f"<{msg_id}>"
    msg["Date"] = format_datetime(datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=n))
    if reply_to:
        msg["In-Reply-To"] = f"<{reply_to}>"
        msg["References"] = f"<{reply_to}>"
    return msg


def build_messages() -> list[tuple[EmailMessage, str]]:
    """Return (message, maildir flags) pairs. Flag S marks a message as already read."""
    out: list[tuple[EmailMessage, str]] = []

    m = _base("plain1@test", "Plain greeting", 1)
    m.set_content("Hello,\n\nthis is plain text. Visit https://example.org today.\n")
    out.append((m, ""))

    m = _base("plain1-reply@test", "Re: Plain greeting", 2, "bob@example.org", "plain1@test")
    m.set_content("Thanks, got it.\n")
    out.append((m, "S"))

    m = _base("alt@test", "Alternative body", 3)
    m.set_content("Plain version of the alternative message.\n")
    m.add_alternative("<p>HTML <i>version</i> of the alternative message.</p>", subtype="html")
    out.append((m, ""))

    m = _base("hostile@test", "Hostile HTML only", 4, "mallory@example.org")
    m.set_content(HOSTILE_HTML, subtype="html")
    out.append((m, ""))

    m = _base("attach@test", "Has an attachment", 5)
    m.set_content("Please find the report attached.\n")
    m.add_attachment(
        b"%PDF-1.4 fake report bytes\n", maintype="application", subtype="pdf", filename="report.pdf"
    )
    out.append((m, ""))

    m = _base("cid@test", "Inline image", 6)
    m.set_content("Plain fallback.\n")
    m.add_alternative(
        '<p>Logo: <img src="cid:logo@test"> and remote <img src="https://evil.example/t.gif"></p>',
        subtype="html",
    )
    html_part = m.get_payload()[1]
    html_part.add_related(PNG, maintype="image", subtype="png", cid="<logo@test>", filename="logo.png")
    out.append((m, ""))

    m = _base("latin1@test", "Café latin1", 7)
    m.set_content("Café crème et à la carte.\n", charset="iso-8859-1", cte="8bit")
    out.append((m, "S"))

    m = _base("odd/id+x@test", "Odd message id", 8)
    m.set_content("The Message-ID of this message contains a slash and a plus sign.\n")
    out.append((m, "S"))

    prev = None
    for i in range(12):
        mid = f"long{i}@test"
        m = _base(mid, "Long thread" if i == 0 else "Re: Long thread", 10 + i, reply_to=prev)
        m.set_content(f"Message number {i} of a long thread.\n")
        out.append((m, "S" if i % 2 else ""))
        prev = mid

    # A thread whose messages start with different tag sets, see the `mixed` tests.
    prev = None
    for i in range(3):
        mid = f"mixed{i}@test"
        m = _base(mid, "Mixed tags" if i == 0 else "Re: Mixed tags", 40 + i, reply_to=prev)
        m.set_content(f"Mixed thread message {i}.\n")
        out.append((m, "S"))
        prev = mid
    return out


@pytest.fixture
def corpus(tmp_path: Path) -> Corpus:
    mail = tmp_path / "mail"
    for sub in ("cur", "new", "tmp"):
        (mail / sub).mkdir(parents=True)
    for n, (msg, flags) in enumerate(build_messages()):
        (mail / "cur" / f"{1700000000 + n}.{n}.test:2,{flags}").write_bytes(msg.as_bytes())
    config = tmp_path / "notmuch-config"
    config.write_text(
        f"[database]\npath={mail}\n\n[user]\nname=Test\nprimary_email=me@example.org\n\n"
        "[new]\ntags=unread;inbox\n\n[maildir]\nsynchronize_flags=true\n"
    )
    c = Corpus(root=tmp_path, config=config, mail=mail)
    c.cli("new")
    # `mixed1` starts flagged, the others do not.
    c.cli("tag", "+flagged", "--", 'id:"mixed1@test"')
    return c


@pytest.fixture
def nm(corpus: Corpus) -> Notmuch:
    return Notmuch(config=str(corpus.config), write_timeout=3.0)
