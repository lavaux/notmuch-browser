# notmuch-browser

Local web UI over the notmuch CLI. Python (aiohttp) REST API in `src/notmuch_browser/`, vanilla JS and CSS in `web/src/` bundled by webpack into `src/notmuch_browser/static/` (gitignored, shipped in the wheel).

## Commands

- `uv sync && npm ci` set up.
- `npm run build` compile the UI. `npm run dev` rebuilds on change (the Python server serves `static/`, reload the page).
- `uv run pytest` run the tests. They use a throwaway notmuch database from `tests/conftest.py` and must never touch `/home/lavaux/Mail` or any real database.
- `uv run python scripts/fixture_db.py /tmp/nb-fixture` makes a fixture database. `node scripts/shots.mjs /tmp/nb-fixture/notmuch-config` runs the browser checks and writes screenshots to `shots/`.
- `scripts/release.sh` builds the wheel and sdist and checks them. It never uploads. Publishing is a separate step that needs the owner's go.

## Build order

`npm ci`, `npm run build`, then `uv build`. A wheel built before webpack has run has no UI. `hatch_build.py` refuses that build.

## Rules

- Always run notmuch with an argument list, never through a shell, and put user queries after `--`. Tag names and ids are validated in `notmuch.py` before they reach argv or a batch line.
- The only write path is `notmuch tag`. Do not add indexing, sending or deleting.
- The server binds 127.0.0.1 only. Keep the Host, Origin and content type checks in `app.py`. `tests/test_app.py` has the cases that must stay red when a check is removed.
- HTML mail is hostile input. Sanitise with nh3 (`render.py`), serve it as its own document with an explicit CSP, show it in `<iframe sandbox="allow-popups allow-popups-to-escape-sandbox">` with no scripts and no same-origin.
- In `web/src` never put untrusted strings through `innerHTML`. Use `h()` from `dom.js` (text nodes and `setAttribute`). `Element.append` turns arrays and `null` into text, so use the `append` helper from `dom.js` for those.
- Under `prefers-reduced-motion` the reset leaves a 0.01ms transition, so a style read right after a change can be stale for a frame. Tests wait for the value.
- `notmuch tag` blocks while another process holds the write lock. The adapter turns a short write timeout into `DatabaseBusy` (HTTP 503).
- Counting every tag takes about 7 s on a 91k-thread database, so tag counts load lazily and are cached for 30 s.
- Playwright is pinned to 1.62.0 to match the cached Chromium. Bumping it needs `npx playwright install chromium`.
- No em dashes in prose, docs or commit messages.

## Design

`PRODUCT.md` holds product truth and `DESIGN.md` the built visual system. The direction is the category standard (Gmail-like three panes, neutral greys, one blue accent), chosen by the owner. Use the impeccable skill in `.claude/skills/impeccable` for UI changes and read `reference/craft-floor.md` before editing UI.
