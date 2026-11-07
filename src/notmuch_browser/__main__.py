"""Command line entry point: `notmuch-browser`."""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
import webbrowser

from aiohttp import web

from . import __version__
from .app import create_app, default_static_dir
from .notmuch import Notmuch, NotmuchError

HOST = "127.0.0.1"  # the server never binds anything else


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="notmuch-browser",
        description="Browse and tag a notmuch database in a local web UI.",
    )
    parser.add_argument("--port", type=int, default=8765, help="port on 127.0.0.1 (default 8765)")
    parser.add_argument(
        "--notmuch-config",
        metavar="FILE",
        help="notmuch configuration file (default: the usual notmuch lookup)",
    )
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if shutil.which("notmuch") is None:
        print("error: the notmuch command was not found on PATH", file=sys.stderr)
        return 1
    nm = Notmuch(config=args.notmuch_config)
    try:
        version = asyncio.run(nm.check_version())
    except NotmuchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not (default_static_dir() / "index.html").is_file():
        print("warning: the UI bundle is missing, run `npm ci && npm run build`", file=sys.stderr)
    url = f"http://{HOST}:{args.port}/"
    app = create_app(nm)

    async def announce(_app: web.Application) -> None:
        print(f"notmuch {'.'.join(map(str, version))}, serving on {url} (Ctrl+C to stop)", flush=True)
        if not args.no_browser:
            webbrowser.open(url)

    app.on_startup.append(announce)
    try:
        web.run_app(app, host=HOST, port=args.port, print=None)
    except OSError as exc:
        print(f"error: cannot listen on {HOST}:{args.port}: {exc.strerror}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
