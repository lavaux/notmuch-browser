---
version: 1
slug: "web-src"
primary_target: "web/src"
related_targets: []
---

# Surface brief: mail browser (web/src)

## Scope and mode
Operate. One surface: the three-pane mail browser (tag rail, thread list with search, thread reader) in light and dark themes, from 1440 px desktop down to a 390 px one-pane stack.

## Audience, job, task, constraints
A researcher with a very large notmuch archive (about 91k threads) who mostly finds and reads old mail, sometimes tags. Colleagues may install the package. Search with notmuch syntax is the main way in. Reads change nothing, tag edits have undo. Constraints: vanilla JS and CSS, no external fonts or hosts, loopback only, WCAG AA in both themes, keyboard operable.

## Chosen direction
The user took the category standard, played straight: a Gmail-like three-pane webmail in neutral greys with one blue accent. Bar: Gmail (list, search, reader) and GitHub notifications (plain, text-forward list, clear read state). No costume, no smuggled quirk. The memorable thing is execution: an exact grid, a real type scale, tabular numerals, honest states.

## Built decisions
Dates: the list uses notmuch's relative form (ISO date for older mail, which suits an archive), the reader shows the full local date and time. Collapsed messages show a rotating chevron so they read as expandable. Opening a thread does not mark it read. Read and unread and archive go through the free-form tag editor.

## Unresolved
Key bindings beyond `/ j k f t`. Whether message cards collapse older messages by default (decided in build: yes, all but the last matching and last unread).

## Direction contract
THESIS: A working mail browser that looks like the best of its category and refuses everything else: no cards-as-structure, no gradients, no decorative colour. Search is the hero control, state is carried by weight, marker and shape, and colour is one action accent, five category hues for tags and senders, a search highlight and the meaning colours. The owner asked for more colour and highlights after the first build, so the earlier "no decorative colour" line still holds but colour now identifies things as well as reporting state.
OWN-WORLD: Neutral grey ramp tinted a few degrees toward the accent blue, one blue accent (light #1b57c7, dark #8fb8ff), five category hues (teal, green, sky, violet, pink; OKLCH hue angles 190, 145, 225, 300, 345) hashed from tag names and sender addresses, a faint blue wash on unread rows, a yellow search highlight, red for errors, amber for the busy-database warning and for the flag mark (a flag is state the user set, so it gets a meaning colour, never decoration). System UI sans, tabular numerals for counts and dates, 1px hairlines, 6px radius on controls, no shadows except the toast, the search syntax popover and the mobile rail drawer. Authored inline SVG icons at one 1.5px stroke.
STORY: The visitor types a query or picks a tag, scans 50 threads at a glance, opens one, reads it comfortably, flags or tags it, and can undo. Errors name the problem and the recovery.
FIRST VIEWPORT: 1440 x 900. A 56px top bar holds the product name at left, a wide search field (max 760px) left-aligned with the thread list column and carrying the notmuch syntax help, and the theme toggle at right. An empty field with a placeholder means All mail. Below: a 232px tag rail (saved searches Inbox, Unread, Flagged, then all tags with unread counts loading in), a 420px thread list of two-line rows (sender, thread size and date on the first line, subject with attachment and flag marks on the second, unread rows bold with a filled dot; one line cannot hold sender and subject in 420px), and the reader filling the rest with headers, text body, attachment chips and the tag strip with an add-tag field. Primary action: the search field.
FORM: category standard (canon), position: standing exit, seed:e26d6265b966079c.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
