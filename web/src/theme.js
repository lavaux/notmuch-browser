import { h } from "./dom.js";
import { icon } from "./icons.js";

const KEY = "nb-theme";
const media = window.matchMedia("(prefers-color-scheme: dark)");

function stored() {
  try {
    const value = window.localStorage.getItem(KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch (_err) {
    return null;
  }
}

function resolved() {
  return stored() || (media.matches ? "dark" : "light");
}

function apply(theme) {
  document.documentElement.setAttribute("data-theme", theme);
}

export function themeButton() {
  const button = h("button", { class: "icon-button", type: "button" });
  const paint = () => {
    const dark = document.documentElement.getAttribute("data-theme") === "dark";
    button.replaceChildren(icon(dark ? "sun" : "moon"));
    const label = dark ? "Switch to light theme" : "Switch to dark theme";
    button.setAttribute("aria-label", label);
    button.title = label;
  };
  button.addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    apply(next);
    try {
      window.localStorage.setItem(KEY, next);
    } catch (_err) {
      // The choice still holds for this page view.
    }
    paint();
  });
  // Without a stored choice the theme follows the system as it changes.
  media.addEventListener("change", () => {
    if (!stored()) {
      apply(resolved());
      paint();
    }
  });
  apply(resolved());
  paint();
  return button;
}
