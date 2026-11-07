---
name: Notmuch Browser
description: A local three-pane mail browser in blue-tinted greys with one blue accent, five category hues for tags and senders, light and dark.
colors:
  primary: "#1b57c7"
  primary-ink: "#ffffff"
  primary-soft: "#e1eafa"
  canvas: "#f3f5f8"
  surface: "#ffffff"
  hover: "#e9edf3"
  hairline: "#dde2ea"
  hairline-strong: "#bcc4d0"
  text: "#1a1d24"
  text-secondary: "#444b59"
  text-tertiary: "#5d6574"
  flag-amber: "#94500a"
  flag-soft: "#fdf0dc"
  unread-wash: "#f0f5ff"
  highlight: "#ffe58a"
  danger: "#b3261e"
  danger-soft: "#fdecea"
  warn: "#6b4300"
  warn-soft: "#fff1cf"
  toast: "#262a33"
typography:
  title:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-0.01em"
  body:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.906rem"
    fontWeight: 400
    lineHeight: 1.62
  ui:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.78rem"
    fontWeight: 400
    lineHeight: 1.5
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
    fontSize: "0.78rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  xs: "4px"
  control: "6px"
  pane: "8px"
  chip: "13px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  button:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "32px"
  button-hover:
    backgroundColor: "{colors.hover}"
  button-pressed:
    backgroundColor: "{colors.primary-soft}"
    textColor: "{colors.primary}"
  icon-button:
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.control}"
    size: "36px"
  search-field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.pane}"
    height: "40px"
  rail-item:
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.control}"
    height: "32px"
    padding: "0 12px"
  rail-item-active:
    backgroundColor: "{colors.primary-soft}"
    textColor: "{colors.primary}"
  thread-row:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-secondary}"
    padding: "8px 16px 8px 12px"
  thread-row-hover:
    backgroundColor: "{colors.hover}"
  thread-row-selected:
    backgroundColor: "{colors.primary-soft}"
  tag-chip:
    textColor: "{colors.text}"
    typography: "{typography.label}"
    rounded: "{rounded.chip}"
    height: "26px"
  toast:
    backgroundColor: "{colors.toast}"
    textColor: "{colors.surface}"
    rounded: "{rounded.pane}"
    padding: "6px 6px 6px 16px"
---

# Design System: Notmuch Browser

## Overview

**Creative North Star: "The Standard Webmail, Played Straight"**

This is the category standard executed exactly: a Gmail-like three-pane browser (tag rail, thread list with search, thread reader) in neutral greys tinted a few degrees toward one blue accent. It is an Operate surface for a researcher who searches a very large archive with notmuch syntax and mostly reads old mail. There is no costume and no smuggled quirk. What the build offers is execution: an exact grid, a real type scale, tabular numerals everywhere, and honest states.

State is carried by weight, marker and shape, and colour reinforces it. Colour is one blue accent for action and selection, five category hues that identify tags and senders, a search highlight, and the meaning colours (red for errors, amber for the busy-database warning and for the flag mark). Structure comes from 1px hairlines and tonal steps between canvas and surface, never from gradients or cards-as-structure. Light and dark are both first class and share every role name.

**Key Characteristics:**
- Search is the hero control: a 40px field, up to 760px wide, left-aligned with the list column.
- Two-line thread rows: sender, thread size and relative date on line one; subject and marks on line two.
- Unread is weight 600, a filled 8px accent dot and a faint blue wash on the row. Read rows are regular weight on plain white with no dot.
- User tags show as hued pills on the second line of a row, two at most and then a "+n". Matching words from the query are highlighted in the list and the reader.
- System UI sans, tabular numerals on the body, a 6-step size scale from 0.78rem to 1.25rem.
- Flat at rest. Shadow appears only on floating layers.
- Inline authored SVG icons, one 1.5px stroke.

## Colors

Blue-tinted neutral greys with one accent. Every role has a light and a dark value; the light values are normative in the frontmatter and the dark values are in the sidecar.

### Primary
- **Mail Blue** (#1b57c7 light, #8fb8ff dark): links, the unread dot, the active rail item, the pressed state of toggle buttons, focus rings, the selected-row ring, the caret and form accent. Text on a filled accent uses the accent ink (#ffffff light, #0d1626 dark).
- **Blue Wash** (#e1eafa light, #22334f dark): the selected row, the active rail item, pressed buttons and text selection.

### Neutral
- **Canvas Grey** (#f3f5f8 light, #12151a dark): the page, top bar and tag rail. The rail has no panel of its own; it sits on the canvas.
- **Pane White** (#ffffff light, #181c22 dark): the list pane, the reader pane, the search field, popovers.
- **Hover Grey** (#e9edf3 light, #212630 dark): hover for buttons, rail items and rows.
- **Hairline** (#dde2ea light, #2a303a dark): row dividers, pane borders, top bar bottom edge.
- **Strong Hairline** (#bcc4d0 light, #444c5a dark): control borders, chips, quote rules, scrollbar thumb.
- **Ink** (#1a1d24 light, #e8ebf1 dark): primary text.
- **Ink Secondary** (#444b59 light, #bcc3d0 dark): rail items, read rows, quoted text, notes.
- **Ink Tertiary** (#5d6574 light, #959eae dark): dates, counts, addresses, placeholders. This is the lowest text tier; nothing lighter is used for text.

### Category hues
Five hues, each defined per theme as lightness and chroma pairs in tokens.css and combined with a hue angle (190 teal, 145 green, 225 sky, 300 violet, 345 pink) through `oklch()`. A tag or a sender takes its hue from a stable hash of its name or address (hue.js), so it keeps the same colour everywhere. The hues stay out of the red to yellow arc, which belongs to the meaning colours, and off the blue accent at about 262.
- **Tint roles** (light, dark): background L 0.95 C 0.035, L 0.31 C 0.05. Text L 0.38 C 0.10, L 0.86 C 0.08. Border L 0.82 C 0.06, L 0.46 C 0.07. Icon dot L 0.56 C 0.13, L 0.76 C 0.12. Avatar fill L 0.90 C 0.07, L 0.38 C 0.08.
- **Fixed tones** for tags with a meaning: inbox and unread take the accent tint, flagged takes the flag tint, other system tags (attachment, sent, replied, draft and similar) are neutral and are not shown as pills in the thread list.
- **Where they appear:** tag icons and unread count pills in the rail, tag pills in thread rows, tag chips and sender avatars in the reader. Colour is never the only code: every pill, chip and avatar carries its text.

### Row and highlight colours
- **Unread Wash** (#f0f5ff light, #1b2638 dark): the background of unread rows. Hover and selected rows replace it.
- **Search Highlight** (#ffe58a light with ink #1a1d24, #5a4a0a dark with ink #f6f1d9): words from the query found in sender, subject and message text. A pale yellow, kept apart from Flag Amber by being a background behind ink, never an icon or text colour.
- **Flag Wash** (#fdf0dc light, #35280f dark): the flagged chip and the pressed Flag button, with Flag Amber text.

### Meaning colours
- **Flag Amber** (#94500a light, #f2b866 dark): the flag mark only. A flag is state the user set, so it earns a meaning colour.
- **Alert Red** (#b3261e light, #ff9a92 dark) with a soft fill (#fdecea, #3b1e1c): error toasts, error state titles, tag errors, chip-remove hover.
- **Busy Amber** (#6b4300 light, #f6d58f dark) with a soft fill (#fff1cf, #3b2e12): the busy-database toast.
- **Toast Ink Surface** (#262a33 light, #e8ebf1 dark): the toast inverts against the page in both themes, with its own action link colour (#a9c7ff light, #1b57c7 dark).

### Named Rules
**The One Accent Rule.** Blue is the only colour for action, selection and focus. The category hues identify things (a tag, a sender) and never mark an action. A new surface may not add a sixth hue or use a category hue for state.
**The Meaning Colour Rule.** Amber and red appear only where they report state: a flag the user set, a busy database, an error. Never as ornament or category colour, which is why no category hue sits in the red to yellow arc.
**The Theme Resolution Rule.** boot.js writes the resolved theme to the root data-theme attribute before first paint. Components read only the custom properties and never branch on the theme. The prefers-color-scheme block in tokens.css is a no-script fallback.

## Typography

**Display Font:** none. **Body and UI Font:** system UI sans (system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial). **Mono:** the system monospace stack, used for the notmuch query echo and syntax examples and keycaps.

**Character:** Native and quiet. The product has no wordmark voice; hierarchy comes from size steps and weight 600, with tabular numerals on the whole body so counts and dates align.

### Hierarchy
- **Title** (600, 1.25rem, 1.3, -0.01em): the thread subject in the reader. Drops to 1rem below 720px.
- **Headline** (600, 1rem, -0.01em): the product name and state titles.
- **Body** (400, 0.906rem, 1.62, max 76ch): message text in the reader.
- **UI** (400, 0.875rem, 1.5): the base size for rows, buttons, rail items and list text.
- **Label** (400 or 600, 0.78rem): dates, counts, addresses, rail headings (600), chips, notes, tag errors.
- **Mono** (400, 0.78rem): query echo, syntax examples; keycaps are 500.

### Named Rules
**The Tabular Rule.** Tabular numerals are set on the body and inherited everywhere. Do not switch them off for dates or counts.
**The Weight Is State Rule.** Weight 600 means unread, selected or active, or a heading. Do not use it for emphasis elsewhere, and do not use uppercase or letter-spaced labels.

## Layout

A full-height grid: a 56px top bar over a shell of three columns, 232px tag rail, 420px thread list, and a reader that fills the rest. The panes are inset: the list and reader are bordered, white, rounded at the top corners only and run to the bottom edge; the reader has 8px side margins and 20px 32px 48px padding. Reader content is capped at 880px, message text at 76ch.

Spacing is a 4/8/12/16/24 rhythm. Rows and controls are 32px high (buttons, rail items, attachments), icon buttons 36px, the search field 40px. Thread rows pad 8px 16px 8px 12px with an 8px marker column and a 10px gap.

Responsive steps:
- Below 1100px the list narrows to 380px and the rail becomes a 264px fixed drawer under the top bar, opened by a menu button with a 40% scrim and a 160ms slide.
- Below 720px one pane shows at a time, switched by a data-view attribute on the shell; the panes lose side borders and radius, a back button appears in the reader, and the brand is hidden.

Content decisions that shape layout: list dates use notmuch's relative form (an ISO date for older mail), while the reader shows the full local date and time. Older messages in a thread collapse (all but the last matching and the last unread) and show a chevron that rotates to mark them expandable.

## Elevation & Depth

Flat by tonal layering. Depth is the step from canvas grey to white panes plus 1px hairlines. A single shadow token exists (`0 6px 24px` at 16% plus `0 1px 3px` at 12%, heavier in dark) and is used only on floating layers: the toast, the search syntax popover and the mobile rail drawer. The selected row and focused tag field use an accent ring (1px inset or spread), which is a state indicator, not elevation.

### Named Rules
**The Flat-By-Default Rule.** Panes, rows, chips and buttons carry no shadow. A shadow means the layer floats over content and will go away.

## Shapes

Quiet rectangles. Controls, rail items and attachments use a 6px radius; the search field, popover, toast and the two main panes use 8px (panes round only the top corners); keycaps and syntax examples use 4px. Chips, the tag input and the thread-count badge are pills (13px for 26px chips, 9px for the count). Unread markers are 8px circles. Borders are 1px hairlines; the tag input is dashed until focused. The HTML mail frame is a 6px rounded box with a strong hairline.

## Components

### Buttons
- **Shape:** 6px radius, 32px high, 12px side padding, 8px gap to an icon.
- **Default:** pane surface, strong hairline border, ink text. **Hover:** hover grey fill.
- **Pressed toggle:** blue wash fill, accent border and text, weight 600.
- **Quiet:** transparent border and fill, secondary ink. **Disabled:** 55% opacity.
- **Icon button:** 36px square, transparent, secondary ink, hover grey fill.
- **Focus:** a 2px accent outline with 1px offset for every focusable element, pulled inside (offset -2px) on rows and inside the search field.

### Search field
40px high, 8px radius, pane surface, strong hairline. On focus-within it takes a 2px accent outline and an accent border. An empty field with its placeholder means All mail. It carries the notmuch syntax help popover, whose example chips fill the field.

### Tag rail
Saved searches (Inbox, Unread, Flagged, All mail) then all tags, 32px items in a three-column grid (18px icon, label, count). Icons carry the item's colour: accent for Inbox and Unread, amber for Flagged, the tag's hue for tags. Active item: blue wash, accent text, weight 600. Unread counts are pills: filled accent with accent ink on Inbox and Unread, the tag's tint on tags.

### Thread list
- Two-line rows separated by hairlines. Line one: sender (ink, ellipsised), count badge, relative date. Line two: subject, then tag pills, then attachment and flag marks.
- Unread: sender, subject and date go weight 600, subject goes ink, date goes secondary, an 8px accent dot fills the marker column, and the row takes the Unread Wash.
- Selected: blue wash plus a 1px inset accent ring. Hover: hover grey.
- The flag mark is Flag Amber; other marks are tertiary ink.

### Tag chips and tag input
26px pills filled with the tag's tint and a matching border, the name in the tint's text colour (underlined on hover) and a 24px circular remove button in the same text colour that turns alert red on hover. Tags with no hue (neutral system tags) keep the strong hairline. The add field is a dashed pill, solid with an accent ring on focus.

### Reader and messages
Messages are separated by a top hairline, with a toggle row of chevron, a 26px round initials avatar in the sender's hue, sender (600), address, and full date. Body text is 0.906rem at 1.62 line height, max 76ch, pre-wrapped. Quoted text sits in a collapsible block with a 1px strong-hairline left rule. Attachments are 32px outlined chips whose border turns accent on hover.

### HTML mail frame
A sandboxed iframe (popups only, no scripts) on a fixed white ground in both themes. Because it cannot run scripts it cannot size itself to its content, so its height is deliberately fixed and viewport-relative: 60vh, with a Taller control that switches it to 88vh. Do not attempt to auto-size it.

### Toast
Bottom-left, 8px radius, the one inverted surface, with the shared floating shadow and a 180ms rise. Variants: busy (warn fill and border) and error (danger fill and border). The action is a bold link-coloured text button, usually Undo.

## Do's and Don'ts

### Do:
- **Do** take every colour from the custom properties in tokens.css and give each new role a light and a dark value.
- **Do** carry state with weight 600, the 8px dot and the pill or ring shapes, then let colour reinforce it.
- **Do** take a tag's or sender's hue from the hash in hue.js and keep every hued element labelled with its text.
- **Do** keep controls at 32px (36px icon buttons, 40px search) and 6px radius, panes at 8px.
- **Do** set dates and counts in tabular numerals at the label size in tertiary ink.
- **Do** use the 2px accent focus outline everywhere and keep every control keyboard operable.
- **Do** author icons inline as SVG with a single 1.5px stroke.
- **Do** write all prose, UI copy and docs without em dashes. Use a colon or a second sentence.

### Don't:
- **Don't** add a hue beyond the five, use a category hue for an action or a state, or add gradients or purely decorative colour.
- **Don't** put a shadow on anything that does not float over content.
- **Don't** use cards as structure; panes and hairlines carry it.
- **Don't** use amber or red for anything but the flag, the busy state and errors.
- **Don't** put text lighter than the tertiary ink on any surface.
- **Don't** load external fonts or hosts, or use emoji or glyph icons.
- **Don't** auto-size the HTML mail frame.
