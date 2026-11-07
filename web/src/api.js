// Thin fetch wrapper around the notmuch-browser REST API.

export class ApiError extends Error {
  constructor(status, kind, message) {
    super(message);
    this.status = status;
    this.kind = kind; // busy, bad_request, not_found, error, network
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(0, "network", "Cannot reach the notmuch-browser server. Is it still running?");
  }
  let body = null;
  try {
    body = await response.json();
  } catch (_err) {
    body = null;
  }
  if (!response.ok) {
    const message = (body && body.error) || `The server answered ${response.status}.`;
    throw new ApiError(response.status, (body && body.kind) || "error", message);
  }
  return body;
}

export function get(path, params = {}, signal) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value != null) query.set(key, value);
  }
  const suffix = query.toString() ? `?${query}` : "";
  return request(path + suffix, { signal, headers: { Accept: "application/json" } });
}

export function post(path, body) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  search: (q, offset, signal) => get("/api/search", { q, offset }, signal),
  count: (q, unit) => get("/api/count", { q, unit }),
  tags: () => get("/api/tags"),
  tagCounts: () => get("/api/tags/counts"),
  thread: (id, signal) => get(`/api/thread/${encodeURIComponent(id)}`, {}, signal),
  tagThread: (id, add, remove) => post(`/api/thread/${encodeURIComponent(id)}/tags`, { add, remove }),
  tagMessages: (changes) => post("/api/messages/tags", { changes }),
};

export const partUrl = (messageId, part) =>
  `/api/message/${encodeURIComponent(messageId)}/part/${part}`;
export const htmlUrl = (messageId) => `/api/message/${encodeURIComponent(messageId)}/html`;
