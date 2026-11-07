import { h, clear, append, marked } from "./dom.js";
import { initials, hueOf, personKey, tagTone } from "./hue.js";
import { icon } from "./icons.js";
import { htmlUrl, partUrl } from "./api.js";
import { displayName, fileSize, firstLine, fullDate, linkSegments, textBlocks, TAG_RE, tagQuery } from "./format.js";

function textNodes(text, terms) {
  return linkSegments(text).map((seg) =>
    seg.href
      ? h("a", { href: seg.href, target: "_blank", rel: "noopener noreferrer" }, seg.text)
      : marked(seg.text, terms),
  );
}

function textBody(text, terms) {
  const wrap = h("div", { class: "text" });
  for (const block of textBlocks(text)) {
    if (!block.text) continue;
    if (block.quoted) {
      const lines = block.text.split("\n").length;
      const details = h(
        "details",
        { class: "quote", open: lines <= 3 },
        h("summary", {}, `Quoted text (${lines} lines)`),
        h("div", { class: "quote-text" }, textNodes(block.text, terms)),
      );
      wrap.append(details);
    } else {
      wrap.append(h("div", { class: "text-block" }, textNodes(block.text, terms)));
    }
  }
  return wrap;
}

function htmlFrame(msg) {
  const frame = h("iframe", {
    class: "mail-frame",
    sandbox: "allow-popups allow-popups-to-escape-sandbox",
    src: htmlUrl(msg.id),
    title: `HTML content of the message from ${displayName(msg.headers.from)}`,
    referrerpolicy: "no-referrer",
    loading: "lazy",
  });
  const toggle = h(
    "button",
    {
      class: "button",
      type: "button",
      "aria-pressed": "false",
      onclick: () => {
        const tall = frame.classList.toggle("is-tall");
        toggle.setAttribute("aria-pressed", String(tall));
        toggle.replaceChildren(icon(tall ? "collapse" : "expand", 16), tall ? "Shorter" : "Taller");
      },
    },
    icon("expand", 16),
    "Taller",
  );
  return h(
    "div",
    { class: "html-view" },
    h("p", { class: "html-note" }, "HTML message. Remote images and scripts are blocked."),
    frame,
    toggle,
  );
}

function messageBody(msg, terms) {
  const wrap = h("div", { class: "message-body" });
  const set = (...kids) => append(clear(wrap), kids);
  const showText = () => set(msg.has_html ? toggleTo("html") : null, textBody(msg.text, terms));
  const showHtml = () => set(msg.text_is_empty ? null : toggleTo("text"), htmlFrame(msg));
  function toggleTo(which) {
    return h(
      "button",
      { class: "button body-toggle", type: "button", onclick: which === "html" ? showHtml : showText },
      which === "html" ? "Show HTML version" : "Show plain text",
    );
  }
  if (msg.text_is_empty && msg.has_html) showHtml();
  else if (msg.text_is_empty) wrap.append(h("p", { class: "state-note" }, "This message has no text content."));
  else showText();
  return wrap;
}

function attachments(msg) {
  if (!msg.attachments.length) return null;
  return h(
    "ul",
    { class: "attachments", "aria-label": "Attachments" },
    msg.attachments.map((a) =>
      h(
        "li",
        {},
        h(
          "a",
          { class: "attachment", href: partUrl(msg.id, a.part), download: a.filename },
          icon("download", 16),
          h("span", { class: "attachment-name" }, a.filename),
          a.size != null ? h("span", { class: "attachment-size" }, fileSize(a.size)) : null,
        ),
      ),
    ),
  );
}

function messageEl(msg, expanded, terms) {
  const el = h("article", { class: "message", "aria-label": `Message from ${displayName(msg.headers.from)}` });
  let open = expanded;
  function render() {
    clear(el);
    el.classList.toggle("is-collapsed", !open);
    const name = displayName(msg.headers.from) || "(unknown sender)";
    const toggle = h(
      "button",
      { class: "message-toggle", type: "button", "aria-expanded": String(open), onclick: () => { open = !open; render(); } },
      h("span", { class: "message-chevron" }, icon("chevronDown", 16)),
      h("span", { class: "avatar", "data-hue": hueOf(personKey(msg.headers.from) || name), "aria-hidden": "true" }, initials(name)),
      h("span", { class: "message-from" }, marked(name, terms)),
      open
        ? h("span", { class: "message-addr" }, msg.headers.from.includes("<") ? msg.headers.from.replace(/^.*?(<[^>]+>).*$/, "$1") : "")
        : h("span", { class: "message-snippet" }, firstLine(msg.text) || (msg.has_html ? "HTML message" : "")),
      h("time", { class: "message-date" }, fullDate(msg.timestamp)),
    );
    el.append(toggle);
    if (!open) return;
    const to = [msg.headers.to && `to ${msg.headers.to}`, msg.headers.cc && `cc ${msg.headers.cc}`].filter(Boolean);
    append(el, [
      to.length ? h("p", { class: "message-to" }, to.join(" · ")) : null,
      messageBody(msg, terms),
      attachments(msg),
    ]);
  }
  render();
  return el;
}

function threadTags(thread) {
  const all = new Set();
  for (const m of thread.messages) for (const t of m.tags) all.add(t);
  return [...all].sort((a, b) => a.localeCompare(b));
}

export function createReader({ onFlag, onAddTag, onRemoveTag, onBack, onSearch }) {
  const el = h("section", { class: "reader", "aria-label": "Thread" });
  const tagInput = h("input", {
    class: "tag-input",
    type: "text",
    list: "tag-options",
    placeholder: "Add tag",
    "aria-label": "Add a tag to this thread",
    autocomplete: "off",
    spellcheck: "false",
  });
  const options = h("datalist", { id: "tag-options" });
  const tagError = h("p", { class: "tag-error", role: "alert", hidden: true });
  const strip = h("div", { class: "tag-strip" });
  let current = null;
  let terms = [];

  tagInput.addEventListener("keydown", (event) => {
    if (event.key === "Escape") tagInput.blur();
    if (event.key !== "Enter") return;
    event.preventDefault();
    const value = tagInput.value.trim();
    if (!value) return;
    if (!TAG_RE.test(value)) {
      tagError.hidden = false;
      tagError.textContent = "Tag names start with a letter, digit or underscore and use only letters, digits and _ . @ : / = -";
      return;
    }
    tagError.hidden = true;
    tagInput.value = "";
    onAddTag(value);
  });

  function renderTags() {
    if (!current) return;
    const tags = threadTags(current);
    clear(strip);
    append(strip, [
      h("span", { class: "tag-label" }, icon("tag", 16), "Tags"),
      tags.map((t) =>
        h(
          "span",
          { class: "chip", ...tagTone(t) },
          h("a", { class: "chip-name", href: `#q=${encodeURIComponent(tagQuery(t))}`, onclick: (e) => { e.preventDefault(); onSearch(tagQuery(t)); } }, t),
          h("button", { class: "chip-remove", type: "button", "aria-label": `Remove tag ${t}`, onclick: () => onRemoveTag(t) }, icon("close", 14)),
        ),
      ),
      tagInput,
    ]);
    const flagged = tags.includes("flagged");
    flagButton.setAttribute("aria-pressed", String(flagged));
    flagButton.replaceChildren(icon(flagged ? "flagFilled" : "flag", 18), flagged ? "Flagged" : "Flag");
  }

  const flagButton = h("button", { class: "button button-flag", type: "button", "aria-pressed": "false", onclick: onFlag }, icon("flag", 18), "Flag");

  function empty() {
    current = null;
    clear(el);
    el.append(
      h(
        "div",
        { class: "reader-empty" },
        h("p", { class: "state-title" }, "No thread selected"),
        h("p", {}, "Pick a thread from the list to read it."),
        h("dl", { class: "keys" }, [
          ["/", "search"],
          ["j / k", "next, previous thread"],
          ["f", "flag or unflag"],
          ["t", "add a tag"],
        ].flatMap(([k, v]) => [h("dt", {}, h("kbd", {}, k)), h("dd", {}, v)])),
      ),
    );
  }

  empty();
  return {
    el,
    empty,
    loading() {
      current = null;
      clear(el);
      el.setAttribute("aria-busy", "true");
      el.append(h("p", { class: "state-note" }, "Opening thread…"));
    },
    error(err, retry) {
      current = null;
      el.removeAttribute("aria-busy");
      clear(el);
      el.append(
        h(
          "div",
          { class: "state-box", role: "alert" },
          h("p", { class: "state-title" }, err.kind === "not_found" ? "That thread no longer exists" : "The thread did not open"),
          h("p", {}, err.message),
          err.kind === "not_found" ? null : h("button", { class: "button", type: "button", onclick: retry }, "Try again"),
        ),
      );
    },
    show(thread) {
      current = thread;
      el.removeAttribute("aria-busy");
      clear(el);
      const unreadIdx = thread.messages.map((m, i) => (m.tags.includes("unread") ? i : -1)).filter((i) => i >= 0);
      const expanded = new Set(unreadIdx.length ? unreadIdx : [thread.messages.length - 1]);
      el.append(
        h(
          "div",
          { class: "reader-head" },
          h("button", { class: "icon-button back-button", type: "button", "aria-label": "Back to the thread list", onclick: onBack }, icon("chevronLeft", 20)),
          h("h1", { class: "reader-subject" }, marked(thread.subject || "(no subject)", terms)),
          flagButton,
        ),
        h("div", { class: "reader-tags" }, strip, tagError),
        h("div", { class: "messages" }, thread.messages.map((m, i) => messageEl(m, expanded.has(i), terms))),
      );
      renderTags();
      el.scrollTop = 0;
    },
    setTerms(list) {
      terms = list || [];
    },
    retag() {
      renderTags();
    },
    tagsOf() {
      return current ? threadTags(current) : [];
    },
    setKnownTags(list) {
      clear(options);
      options.append(...list.map((t) => h("option", { value: t })));
      if (!options.isConnected) document.body.append(options);
    },
    focusTagInput() {
      tagInput.focus();
    },
  };
}
