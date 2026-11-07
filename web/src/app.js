import { h } from "./dom.js";
import { api, ApiError } from "./api.js";
import * as router from "./router.js";
import { toast } from "./toast.js";
import { createSidebar } from "./sidebar.js";
import { createTopbar } from "./topbar.js";
import { createThreadList } from "./threadlist.js";
import { createReader } from "./reader.js";
import { queryTerms } from "./format.js";

export function start(root) {
  let q = router.DEFAULT_QUERY;
  let selected = null;
  let thread = null;
  let offset = 0;
  let searchAbort = null;
  let threadAbort = null;
  let countsTimer = null;

  const sidebar = createSidebar({ onSearch: (query) => go({ q: query, t: null }) });
  const topbar = createTopbar({
    onSearch: (query) => go({ q: query, t: null }),
    onMenu: () => shell.classList.toggle("rail-open"),
  });
  const list = createThreadList({ onLoadMore: loadMore, onRetry: () => runSearch() });
  const reader = createReader({
    onFlag: toggleFlag,
    onAddTag: (tag) => editTags([tag], [], `Added tag ${tag}`),
    onRemoveTag: (tag) => editTags([], [tag], `Removed tag ${tag}`),
    onBack: () => go({ q, t: null }),
    onSearch: (query) => go({ q: query, t: null }),
  });
  const scrim = h("div", { class: "scrim", onclick: () => shell.classList.remove("rail-open") });
  const shell = h("div", { class: "shell", "data-view": "list" }, sidebar.el, list.el, reader.el, scrim);
  root.append(topbar.el, shell);

  // ----------------------------------------------------------------- navigation

  function go(next, options) {
    router.write(next, options);
    // A same-value write fires no hashchange, so apply directly in that case.
    apply(router.read());
  }

  function apply({ q: nextQ, t: nextT }) {
    shell.classList.remove("rail-open");
    if (nextQ !== q) {
      q = nextQ;
      reader.setTerms(queryTerms(q));
      topbar.setQuery(q);
      sidebar.setQuery(q);
      selected = null;
      reader.empty();
      thread = null;
      runSearch();
    }
    if (nextT !== selected) openThread(nextT);
    shell.dataset.view = nextT ? "reader" : "list";
  }

  // --------------------------------------------------------------------- search

  async function runSearch() {
    if (searchAbort) searchAbort.abort();
    searchAbort = new AbortController();
    const signal = searchAbort.signal;
    offset = 0;
    list.set({ query: q, threads: [], hasMore: false, status: "loading", error: null, selected });
    try {
      const data = await api.search(q, 0, signal);
      offset = data.threads.length;
      list.set({ threads: data.threads, hasMore: data.has_more, status: "idle", loadingMore: false });
      if (selected) list.select(selected);
    } catch (err) {
      if (err.name === "AbortError") return;
      list.set({ status: "error", error: err });
    }
  }

  async function loadMore() {
    list.set({ loadingMore: true });
    try {
      const data = await api.search(q, offset);
      offset += data.threads.length;
      list.set({ threads: [...list.threads, ...data.threads], hasMore: data.has_more, loadingMore: false });
      if (selected) list.select(selected);
    } catch (err) {
      list.set({ loadingMore: false });
      toast(err.message, { kind: "error", actions: [{ label: "Retry", run: loadMore }] });
    }
  }

  // --------------------------------------------------------------------- thread

  async function openThread(id) {
    if (threadAbort) threadAbort.abort();
    selected = id;
    list.select(id);
    shell.dataset.view = id ? "reader" : "list";
    if (!id) {
      thread = null;
      reader.empty();
      return;
    }
    threadAbort = new AbortController();
    reader.loading();
    try {
      thread = await api.thread(id, threadAbort.signal);
      reader.show(thread);
    } catch (err) {
      if (err.name === "AbortError") return;
      thread = null;
      reader.error(err, () => openThread(id));
    }
  }

  // ----------------------------------------------------------------- tag edits

  function threadTagSet() {
    return new Set(reader.tagsOf());
  }

  // Apply the message ids a write reported, in the given direction (+1 apply, -1 undo).
  function applyLocal(changed, direction) {
    if (!thread) return;
    const byId = new Map(thread.messages.map((m) => [m.id, m]));
    const edit = (kind, sign) => {
      for (const [tag, ids] of Object.entries(changed[kind] || {})) {
        for (const id of ids) {
          const msg = byId.get(id);
          if (!msg) continue;
          const adding = (kind === "add") === (sign > 0);
          const has = msg.tags.includes(tag);
          if (adding && !has) msg.tags.push(tag);
          if (!adding && has) msg.tags = msg.tags.filter((t) => t !== tag);
        }
      }
    };
    edit("add", direction);
    edit("remove", direction);
    reader.retag();
    list.patchTags(thread.thread, reader.tagsOf());
  }

  function inverse(changed) {
    const merged = new Map();
    const entry = (id) => {
      if (!merged.has(id)) merged.set(id, { id, add: [], remove: [] });
      return merged.get(id);
    };
    for (const [tag, ids] of Object.entries(changed.add || {})) for (const id of ids) entry(id).remove.push(tag);
    for (const [tag, ids] of Object.entries(changed.remove || {})) for (const id of ids) entry(id).add.push(tag);
    return [...merged.values()];
  }

  function fail(err, retry) {
    const busy = err instanceof ApiError && err.kind === "busy";
    toast(
      busy ? "The notmuch database is busy, another program is writing to it. Nothing was changed." : err.message,
      { kind: busy ? "busy" : "error", actions: retry ? [{ label: "Try again", run: retry }] : [], duration: 12000 },
    );
  }

  async function editTags(add, remove, label) {
    if (!thread) return;
    const id = thread.thread;
    try {
      const { changed } = await api.tagThread(id, add, remove);
      const touched = Object.values(changed.add).concat(Object.values(changed.remove)).some((ids) => ids.length);
      if (!touched) {
        toast("No change: every message already had that tag state.", { duration: 4000 });
        return;
      }
      if (!thread || thread.thread !== id) return;
      applyLocal(changed, +1);
      refreshSidebarSoon();
      toast(label, {
        actions: [{ label: "Undo", icon: "undo", run: () => undo(changed, id) }],
      });
    } catch (err) {
      fail(err, () => editTags(add, remove, label));
    }
  }

  async function undo(changed, id) {
    try {
      await api.tagMessages(inverse(changed));
      if (thread && thread.thread === id) applyLocal(changed, -1);
      refreshSidebarSoon();
      toast("Change undone.", { duration: 3000 });
    } catch (err) {
      fail(err, () => undo(changed, id));
    }
  }

  function toggleFlag() {
    if (!thread) return;
    const flagged = threadTagSet().has("flagged");
    editTags(flagged ? [] : ["flagged"], flagged ? ["flagged"] : [], flagged ? "Thread unflagged" : "Thread flagged");
  }

  // ------------------------------------------------------------------- sidebar

  async function loadTags() {
    try {
      const { tags } = await api.tags();
      sidebar.setTags(tags);
      reader.setKnownTags(tags);
    } catch (err) {
      sidebar.setTags([], err.message);
    }
  }

  async function loadCounts() {
    try {
      const { counts } = await api.tagCounts();
      sidebar.setCounts(counts);
    } catch (_err) {
      sidebar.setCounts({});
    }
  }

  function refreshSidebarSoon() {
    clearTimeout(countsTimer);
    countsTimer = setTimeout(() => {
      loadTags();
      loadCounts();
    }, 1500);
  }

  // ------------------------------------------------------------------ keyboard

  document.addEventListener("keydown", (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const target = event.target;
    const typing = target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));
    if (typing) return;
    switch (event.key) {
      case "/":
        event.preventDefault();
        topbar.focusSearch();
        break;
      case "j":
      case "k": {
        const threads = list.threads;
        if (!threads.length) return;
        const index = threads.findIndex((t) => t.thread === selected);
        const next = event.key === "j" ? Math.min(index + 1, threads.length - 1) : Math.max(index - 1, 0);
        const target2 = threads[index < 0 ? 0 : next];
        if (target2) go({ q, t: target2.thread }, { replace: true });
        break;
      }
      case "f":
        toggleFlag();
        break;
      case "t":
        if (thread) {
          event.preventDefault();
          reader.focusTagInput();
        }
        break;
      default:
    }
  });

  router.onChange(apply);
  const initial = router.read();
  router.write(initial, { replace: true });
  q = null; // force the first apply to run a search
  apply(initial);
  loadTags();
  loadCounts();
}
