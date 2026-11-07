"""Create a throwaway notmuch database from the test corpus.

    uv run python scripts/fixture_db.py /tmp/nb-fixture

Prints the path of the notmuch config. Use it with `notmuch-browser --notmuch-config`.
"""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.conftest import build_messages  # noqa: E402


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "nb-fixture").resolve()
    mail = root / "mail"
    for sub in ("cur", "new", "tmp"):
        (mail / sub).mkdir(parents=True, exist_ok=True)
    for n, (msg, flags) in enumerate(build_messages()):
        (mail / "cur" / f"{1700000000 + n}.{n}.test:2,{flags}").write_bytes(msg.as_bytes())
    config = root / "notmuch-config"
    config.write_text(
        f"[database]\npath={mail}\n\n[user]\nname=Test\nprimary_email=me@example.org\n\n"
        "[new]\ntags=unread;inbox\n\n[maildir]\nsynchronize_flags=true\n"
    )
    env = {**os.environ, "NOTMUCH_CONFIG": str(config)}
    subprocess.run(["notmuch", "new"], env=env, check=True, capture_output=True)
    subprocess.run(
        ["notmuch", "tag", "+flagged", "--", 'id:"mixed1@test"'], env=env, check=True
    )
    # A few user tags so screenshots show the category colours.
    for tags, mid in (
        (["project-x", "travel"], "plain1@test"),
        (["lists/hpc"], "attach@test"),
        (["receipts", "project-x", "travel"], "long0@test"),
        (["notes"], "mixed0@test"),
        (["lists/hpc", "archive"], "cid@test"),
    ):
        subprocess.run(
            ["notmuch", "tag", *[f"+{t}" for t in tags], "--", f'id:"{mid}"'], env=env, check=True
        )
    print(config)


if __name__ == "__main__":
    main()
