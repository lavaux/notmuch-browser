// The URL hash is the view state: #q=<query>&t=<thread id>. Back and forward work and a
// thread can be linked.

export const DEFAULT_QUERY = "tag:inbox";

export function read() {
  const params = new URLSearchParams(location.hash.replace(/^#/, ""));
  return { q: params.get("q") || DEFAULT_QUERY, t: params.get("t") || null };
}

export function write({ q, t }, { replace = false } = {}) {
  const params = new URLSearchParams();
  params.set("q", q);
  if (t) params.set("t", t);
  const hash = `#${params}`;
  if (hash === location.hash) return;
  if (replace) history.replaceState(null, "", hash);
  else location.hash = hash;
}

export function onChange(handler) {
  window.addEventListener("hashchange", () => handler(read()));
}
