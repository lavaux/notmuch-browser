# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Fixed by the project plan, not delegated: Python (aiohttp) REST API over the `notmuch` CLI, vanilla JavaScript and CSS bundled by webpack 5, no UI framework, no external font host. The compiled bundle ships inside a Python wheel installed with `uv tool install notmuch-browser`.

## Users

Primary: the author, a researcher with a very large notmuch database (147k messages, about 91k threads, 22 tags) who mostly goes back into the archive to find and read old mail, and occasionally tags. Secondary: colleagues and other notmuch users who install the package from PyPI. They already know notmuch's words (thread, tag, query) and may know notmuch-emacs, alot or Gmail-style web mail. Desktop on a large monitor is the main device. A phone through an SSH tunnel is an occasional second one.

## Product Purpose

A small local web UI over an existing notmuch database. It lets a user search with notmuch's own query syntax, browse tags, scan thread lists, read messages safely, and edit tags. Success means a known message is found and read in seconds, nothing is ever lost or sent, and every tag change can be undone.

## Positioning

It is a thin window onto the user's own notmuch index, not a mail client. It never indexes, composes, sends or deletes, it exposes notmuch's query language as the primary way in, and it runs only on loopback. A webmail product could not truthfully claim that the user's mail never leaves their machine.

## Operating Context

Local server on 127.0.0.1, started from a terminal with `notmuch-browser`. The database is a Maildir indexed by notmuch 0.40 with `maildir.synchronize_flags=true`, so tagging unread, flagged, replied, draft or passed renames Maildir files. Another process (`notmuch new`, an IMAP sync tool) can hold the database write lock, so a tag edit can fail with a busy error and must say so. Counting every tag on the real database costs about 7.5 s, so counts load lazily.

## Capabilities and Constraints

- Search (notmuch syntax, 50 threads per page), tag list with lazily loaded unread counts, thread reading, flag and free-form tag add and remove with undo.
- Message bodies: text first. HTML-only mail is sanitised and shown in a sandboxed frame. Remote images never load. Attachments download as attachments.
- Light and dark themes: system preference by default, a header toggle overrides it.
- Non-goals: compose, reply, send, delete, indexing, authentication, TLS, offline mode.
- Terms to keep: thread, message, tag, query. Saved searches shown are `inbox`, `unread`, `flagged`.
- Undecided: which keys beyond `/`, `j`, `k`, `f`, `t` exist.

## Brand Commitments

The user chose the category standard, played straight and at full fidelity: a Gmail-like three-pane webmail layout in neutral greys with one blue accent, no costume and no smuggled quirk. At the owner's later request it carries more colour: five category hues for tags and senders, a tint on unread rows and a search highlight, all in service of scanning rather than decoration. The craft bar is Gmail (conversation list, search, reading pane) and GitHub notifications (plain, text-forward list with filters and clear read and unread state). Offered and not chosen: a library shelf-mark world, a preprint listing, and a tab-rail manual.

## Evidence on Hand

Real data only through the user's own database. The test fixture corpus under `tests/conftest.py` is synthetic and must not appear as product content. No logo, brand assets or testimonials exist. Nothing here may claim popularity, compatibility or performance that was not measured.

## Product Principles

1. Search first. The query box is the primary control, and the interface teaches notmuch's syntax instead of hiding it.
2. Nothing is lost. Reads change nothing, writes are tag edits only, and every write has a visible undo.
3. Scanability over decoration. A page of 50 threads must be readable at a glance and the reader must make long mail comfortable.
4. Say what is wrong. A busy database, a bad query or a missing bundle shows a plain message and a way to retry, never a silent failure.
5. Hostile mail stays contained. Nothing in a message may run, load remote content or reach the app.

## Accessibility & Inclusion

Keyboard operable throughout with visible focus. Text contrast of at least WCAG AA in both themes. State never relies on colour alone: unread, flagged and selected also differ in weight, marker or shape. Respect `prefers-reduced-motion` and `prefers-color-scheme`.
