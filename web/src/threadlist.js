import { h, clear, marked } from "./dom.js";
import { icon } from "./icons.js";
import { authorsOf, queryTerms } from "./format.js";
import { SYSTEM_TAGS, tagTone } from "./hue.js";

const MAX_CHIPS = 2;

function tagChips(tags) {
  const own = tags.filter((t) => !SYSTEM_TAGS.has(t)).sort((a, b) => a.localeCompare(b));
  if (!own.length) return null;
  const more = own.length - MAX_CHIPS;
  return h(
    "span",
    { class: "thread-tags", title: own.join(", ") },
    own.slice(0, MAX_CHIPS).map((t) => h("span", { class: "tag-pill", ...tagTone(t) }, t)),
    more > 0 ? h("span", { class: "tag-more" }, `+${more}`) : null,
  );
}

export function createThreadList({ onLoadMore, onRetry }) {
  const head = h("div", { class: "list-head" });
  const body = h("div", { class: "list-body", tabindex: "-1" });
  const el = h("section", { class: "list", "aria-label": "Threads" }, head, body);
  let rows = new Map();
  let state = { query: "", terms: [], threads: [], hasMore: false, status: "idle", error: null, selected: null, loadingMore: false };

  function href(threadId) {
    return `#q=${encodeURIComponent(state.query)}&t=${encodeURIComponent(threadId)}`;
  }

  function rowEl(t) {
    const tags = t.tags || [];
    const unread = tags.includes("unread");
    const flagged = tags.includes("flagged");
    const selected = state.selected === t.thread;
    return h(
      "a",
      {
        class: `thread${unread ? " is-unread" : ""}${selected ? " is-selected" : ""}`,
        href: href(t.thread),
        "aria-current": selected ? "true" : null,
        "data-thread": t.thread,
      },
      h("span", { class: "thread-marker", "aria-hidden": "true" }),
      h(
        "span",
        { class: "thread-line thread-line-top" },
        unread ? h("span", { class: "sr-only" }, "Unread. ") : null,
        h("span", { class: "thread-from" }, marked(authorsOf(t.authors), state.terms)),
        t.total > 1 ? h("span", { class: "thread-count", title: `${t.total} messages` }, t.total) : null,
        h("time", { class: "thread-date" }, t.date_relative || ""),
      ),
      h(
        "span",
        { class: "thread-line thread-line-bottom" },
        h("span", { class: "thread-subject" }, marked(t.subject || "(no subject)", state.terms)),
        tagChips(tags),
        h(
          "span",
          { class: "thread-marks" },
          tags.includes("attachment") ? h("span", { title: "Has an attachment" }, icon("paperclip", 15), h("span", { class: "sr-only" }, "Attachment")) : null,
          flagged ? h("span", { class: "mark-flag", title: "Flagged" }, icon("flagFilled", 15), h("span", { class: "sr-only" }, "Flagged")) : null,
        ),
      ),
    );
  }

  function headText() {
    if (state.status === "loading") return "Searching…";
    if (state.status === "error") return "Search failed";
    const n = state.threads.length;
    if (!n) return "No threads";
    return `${n}${state.hasMore ? "+" : ""} thread${n === 1 ? "" : "s"}`;
  }

  function render() {
    clear(head);
    head.append(h("span", { class: state.query === "*" ? "list-title" : "list-query", title: state.query }, state.query === "*" ? "All mail" : state.query), h("span", { class: "list-count" }, headText()));
    clear(body);
    rows = new Map();
    body.removeAttribute("aria-busy");
    if (state.status === "loading") {
      body.setAttribute("aria-busy", "true");
      body.append(h("p", { class: "state-note" }, "Searching the database…"));
      return;
    }
    if (state.status === "error") {
      body.append(
        h(
          "div",
          { class: "state-box", role: "alert" },
          h("p", { class: "state-title" }, "The search did not run"),
          h("p", {}, state.error ? state.error.message : "Something went wrong."),
          h("button", { class: "button", type: "button", onclick: onRetry }, "Try again"),
        ),
      );
      return;
    }
    if (!state.threads.length) {
      body.append(
        h(
          "div",
          { class: "state-box" },
          h("p", { class: "state-title" }, "No threads match this query"),
          h("p", {}, "Check the spelling, widen a date range, or open the syntax help next to the search field."),
        ),
      );
      return;
    }
    const list = h("div", { class: "thread-list" });
    for (const t of state.threads) {
      const row = rowEl(t);
      rows.set(t.thread, row);
      list.append(row);
    }
    body.append(list);
    if (state.hasMore) {
      body.append(
        h(
          "div",
          { class: "load-more" },
          h("button", { class: "button", type: "button", disabled: state.loadingMore, onclick: onLoadMore }, state.loadingMore ? "Loading…" : "Show 50 more threads"),
        ),
      );
    }
  }

  render();
  return {
    el,
    get threads() {
      return state.threads;
    },
    set(patch) {
      state = { ...state, ...patch };
      if ("query" in patch) state.terms = queryTerms(state.query);
      render();
    },
    select(id) {
      const previous = rows.get(state.selected);
      state.selected = id;
      if (previous) {
        previous.classList.remove("is-selected");
        previous.removeAttribute("aria-current");
      }
      const row = rows.get(id);
      if (row) {
        row.classList.add("is-selected");
        row.setAttribute("aria-current", "true");
        row.scrollIntoView({ block: "nearest" });
      }
    },
    patchTags(id, tags) {
      const t = state.threads.find((x) => x.thread === id);
      if (!t) return;
      t.tags = tags;
      const old = rows.get(id);
      if (old) {
        const fresh = rowEl(t);
        old.replaceWith(fresh);
        rows.set(id, fresh);
      }
    },
    focusSelected() {
      const row = rows.get(state.selected);
      if (row) row.focus();
    },
  };
}
