// Small DOM helpers. Untrusted strings only ever reach the page through text nodes
// and setAttribute, never through innerHTML.

import { markSegments } from "./format.js";

export function h(tag, props, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value == null || value === false) continue;
    if (key.startsWith("on") && typeof value === "function") {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === "class") {
      el.className = value;
    } else if (value === true) {
      el.setAttribute(key, "");
    } else {
      el.setAttribute(key, String(value));
    }
  }
  append(el, children);
  return el;
}

export function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

// Text with the segments that match a search term wrapped in <mark>.
export function marked(text, terms) {
  return markSegments(text, terms).map((seg) => (seg.hit ? h("mark", { class: "hit" }, seg.text) : seg.text));
}

export function clear(el) {
  el.replaceChildren();
  return el;
}

export function $(selector, root = document) {
  return root.querySelector(selector);
}
