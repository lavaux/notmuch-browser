"""Check the built wheel and sdist: the UI must ship, local tooling must not."""

import sys
import tarfile
import zipfile
from pathlib import Path

dist = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
wheels = sorted(dist.glob("*.whl"))
sdists = sorted(dist.glob("*.tar.gz"))
problems = []

if len(wheels) != 1 or len(sdists) != 1:
    sys.exit(f"expected one wheel and one sdist in {dist}, found {len(wheels)} and {len(sdists)}")

with zipfile.ZipFile(wheels[0]) as wheel:
    names = wheel.namelist()
for needed in ("notmuch_browser/static/index.html", "notmuch_browser/__main__.py"):
    if needed not in names:
        problems.append(f"wheel is missing {needed}")
if not any(n.startswith("notmuch_browser/static/assets/") and n.endswith(".js") for n in names):
    problems.append("wheel has no bundled JavaScript")
if not any(n.startswith("notmuch_browser/static/assets/") and n.endswith(".css") for n in names):
    problems.append("wheel has no bundled CSS")
if any(".claude" in n or ".impeccable" in n or "node_modules" in n for n in names):
    problems.append("wheel contains local tooling")

with tarfile.open(sdists[0]) as sdist:
    snames = sdist.getnames()
forbidden = [n for n in snames if "/.claude/" in n or "/.impeccable/" in n or "settings.local.json" in n or "/node_modules/" in n]
if forbidden:
    problems.append(f"sdist contains local tooling, for example {forbidden[0]}")
if not any(n.endswith("/src/notmuch_browser/static/index.html") for n in snames):
    problems.append("sdist is missing the compiled UI")

if problems:
    print("\n".join(f"FAIL  {p}" for p in problems))
    sys.exit(1)
print(f"OK  {wheels[0].name}: {len(names)} files, UI bundle present")
print(f"OK  {sdists[0].name}: {len(snames)} files, no local tooling")
