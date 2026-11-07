// Colour roles for tags and people. Colour is never the only code: every chip and avatar
// also carries its text. Hues come from a stable hash, so a tag or sender keeps its colour.

export const HUE_COUNT = 5;

// Tags notmuch and mail tools set themselves. They are not shown as chips in the thread list.
export const SYSTEM_TAGS = new Set([
  "inbox",
  "unread",
  "flagged",
  "attachment",
  "sent",
  "replied",
  "draft",
  "passed",
  "signed",
  "encrypted",
  "deleted",
  "spam",
]);

function hash(text) {
  let value = 2166136261;
  for (let i = 0; i < text.length; i++) {
    value ^= text.charCodeAt(i);
    value = Math.imul(value, 16777619);
  }
  return value >>> 0;
}

export function hueOf(key) {
  return hash(String(key).toLowerCase()) % HUE_COUNT;
}

// Attributes that pick a tag's colour: fixed tones for the meaning tags, a hue for the rest.
export function tagTone(tag) {
  if (tag === "inbox" || tag === "unread") return { "data-tone": "accent" };
  if (tag === "flagged") return { "data-tone": "flag" };
  if (SYSTEM_TAGS.has(tag)) return { "data-tone": "quiet" };
  return { "data-hue": hueOf(tag) };
}

// The address inside a From header, used as the stable key for a person.
export function personKey(from) {
  const match = /<([^>]+)>/.exec(from || "");
  return (match ? match[1] : from || "").trim().toLowerCase();
}

export function initials(name) {
  const words = (name || "").replace(/[^\p{L}\p{N}\s.-]/gu, " ").split(/[\s.-]+/).filter(Boolean);
  if (!words.length) return "?";
  const first = [...words[0]][0];
  const last = words.length > 1 ? [...words[words.length - 1]][0] : "";
  return (first + last).toUpperCase();
}
