import { h } from "./dom.js";
import { icon } from "./icons.js";

let region;
let timer;

function ensureRegion() {
  if (!region) {
    region = h("div", { class: "toast-region", role: "status", "aria-live": "polite" });
    document.body.append(region);
  }
  return region;
}

export function dismiss() {
  clearTimeout(timer);
  if (region) region.replaceChildren();
}

// kind: "info" or "error" or "busy". Actions are { label, run }.
export function toast(message, { kind = "info", actions = [], duration = 8000 } = {}) {
  dismiss();
  const buttons = actions.map((a) =>
    h(
      "button",
      {
        class: "toast-action",
        type: "button",
        onclick: () => {
          dismiss();
          a.run();
        },
      },
      a.icon ? icon(a.icon, 16) : null,
      a.label,
    ),
  );
  const close = h(
    "button",
    { class: "icon-button toast-close", type: "button", "aria-label": "Dismiss", onclick: dismiss },
    icon("close", 16),
  );
  ensureRegion().append(h("div", { class: `toast toast-${kind}` }, h("span", { class: "toast-text" }, message), buttons, close));
  if (duration) timer = setTimeout(dismiss, duration);
}
