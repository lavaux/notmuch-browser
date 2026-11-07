import { h, clear } from "./dom.js";
import { icon } from "./icons.js";
import { tagQuery } from "./format.js";
import { tagTone } from "./hue.js";

const SAVED = [
  { label: "Inbox", tag: "inbox", query: "tag:inbox", icon: "inbox", tone: { "data-tone": "accent" } },
  { label: "Unread", tag: "unread", query: "tag:unread", icon: "mail", tone: { "data-tone": "accent" } },
  { label: "Flagged", tag: "flagged", query: "tag:flagged", icon: "flag", tone: { "data-tone": "flag" } },
  { label: "All mail", tag: null, query: "*", icon: "stack", tone: { "data-tone": "quiet" } },
];

export function createSidebar({ onSearch }) {
  const el = h("nav", { class: "rail", "aria-label": "Saved searches and tags" });
  let tags = [];
  let counts = null;
  let query = "";
  let tagsError = null;

  function item({ label, query: q, icon: name, count, tone }) {
    const active = q === query;
    return h(
      "a",
      {
        class: `rail-item${active ? " is-active" : ""}`,
        href: `#q=${encodeURIComponent(q)}`,
        "aria-current": active ? "page" : null,
        ...tone,
        onclick: (event) => {
          event.preventDefault();
          onSearch(q);
        },
      },
      icon(name, 18),
      h("span", { class: "rail-label" }, label),
      count ? h("span", { class: "rail-count", title: `${count} unread threads` }, count.toLocaleString()) : null,
    );
  }

  function render() {
    clear(el);
    const unread = (tag) => (counts && tag ? counts[tag] : null);
    el.append(
      h("ul", { class: "rail-list" }, SAVED.map((s) => h("li", {}, item({ ...s, count: unread(s.tag) })))),
      h("h2", { class: "rail-heading" }, "Tags"),
    );
    const saved = new Set(SAVED.map((s) => s.tag));
    const rest = tags.filter((t) => !saved.has(t)).sort((a, b) => a.localeCompare(b));
    if (tagsError) {
      el.append(h("p", { class: "rail-note" }, tagsError));
    } else if (!tags.length) {
      el.append(h("p", { class: "rail-note" }, "Loading tags…"));
    } else {
      el.append(
        h(
          "ul",
          { class: "rail-list" },
          rest.map((t) => h("li", {}, item({ label: t, query: tagQuery(t), icon: "tag", count: unread(t), tone: tagTone(t) }))),
        ),
      );
    }
    if (counts == null && tags.length) {
      el.append(h("p", { class: "rail-note rail-note-quiet" }, "Counting unread threads…"));
    }
  }

  render();
  return {
    el,
    setQuery(q) {
      query = q;
      render();
    },
    setTags(list, error) {
      tags = list || [];
      tagsError = error || null;
      render();
    },
    setCounts(value) {
      counts = value;
      render();
    },
  };
}
