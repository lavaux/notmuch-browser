// Pure formatting helpers: names, dates, sizes, and safe text structure for message bodies.

export function authorsOf(raw) {
  // notmuch separates matching authors from the others with "|".
  const names = (raw || "").replace(/\s*\|\s*/g, ", ").split(/,\s*/).filter(Boolean);
  if (names.length === 0) return "(unknown sender)";
  if (names.length <= 2) return names.join(", ");
  return `${names[0]}, ${names[1]} +${names.length - 2}`;
}

export function displayName(address) {
  const match = /^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/.exec(address || "");
  if (match && match[1].trim()) return match[1].trim();
  return (address || "").replace(/[<>]/g, "").trim();
}

export function fullDate(timestamp) {
  if (!timestamp) return "";
  return new Date(timestamp * 1000).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fileSize(bytes) {
  if (bytes == null) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(bytes < 10240 ? 1 : 0)} kB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

const URL_RE = /\bhttps?:\/\/[^\s<>"')\]]+[^\s<>"')\].,;:!?]/g;

// Split text into plain and link segments. Links are limited to http and https.
export function linkSegments(text) {
  const out = [];
  let last = 0;
  for (const match of text.matchAll(URL_RE)) {
    if (match.index > last) out.push({ text: text.slice(last, match.index) });
    out.push({ text: match[0], href: match[0] });
    last = match.index + match[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}

// Group message lines into plain and quoted blocks (lines starting with ">").
export function textBlocks(text) {
  const blocks = [];
  for (const line of text.replace(/\r\n?/g, "\n").split("\n")) {
    const quoted = /^\s*>/.test(line);
    const last = blocks[blocks.length - 1];
    if (last && last.quoted === quoted) last.lines.push(line);
    else blocks.push({ quoted, lines: [line] });
  }
  return blocks.map((b) => ({ quoted: b.quoted, text: b.lines.join("\n").replace(/^\n+|\n+$/g, "") }));
}

export function firstLine(text) {
  for (const line of (text || "").split("\n")) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith(">")) return trimmed.slice(0, 140);
  }
  return "";
}

// Words from a notmuch query worth highlighting in results: bare words, quoted phrases and
// the values of from:, to: and subject:. Other prefixes and operators carry no visible text.
const TEXT_PREFIXES = new Set(["from", "to", "subject"]);
const OPERATORS = new Set(["and", "or", "not", "xor"]);

export function queryTerms(query) {
  const terms = [];
  const token = /"((?:[^"]|"")*)"|(\S+)/g;
  for (const match of (query || "").matchAll(token)) {
    let word = match[1] != null ? match[1].replace(/""/g, '"') : match[2];
    const prefixed = /^([a-z]+):(.*)$/i.exec(word);
    if (prefixed) {
      if (!TEXT_PREFIXES.has(prefixed[1].toLowerCase())) continue;
      word = prefixed[2].replace(/^"|"$/g, "");
    }
    word = word.replace(/[()]/g, "").replace(/\*+$/, "").trim();
    if (word.length < 2 || word === "*" || OPERATORS.has(word.toLowerCase())) continue;
    terms.push(word);
  }
  return [...new Set(terms.map((t) => t.toLowerCase()))].slice(0, 8);
}

// Split text into segments, flagging the ones that match a term (case-insensitive).
export function markSegments(text, terms) {
  if (!terms || !terms.length || !text) return [{ text }];
  const escaped = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).sort((a, b) => b.length - a.length);
  const re = new RegExp(escaped.join("|"), "gi");
  const out = [];
  let last = 0;
  for (const match of text.matchAll(re)) {
    if (match.index > last) out.push({ text: text.slice(last, match.index) });
    out.push({ text: match[0], hit: true });
    last = match.index + match[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}

export const TAG_RE = /^[A-Za-z0-9_][A-Za-z0-9_.@:/=-]{0,63}$/;

// Quote a tag for use inside a notmuch query.
export function tagQuery(tag) {
  return `tag:"${tag.replace(/"/g, '""')}"`;
}
