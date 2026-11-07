import { h } from "./dom.js";
import { icon } from "./icons.js";
import { themeButton } from "./theme.js";

const LONG_PLACEHOLDER = "Search mail, for example from:alice tag:inbox";
const SHORT_PLACEHOLDER = "Search mail";
const narrow = window.matchMedia("(max-width: 719px)");

const SYNTAX = [
  ["from:alice", "sender contains alice"],
  ["to:bob", "recipient contains bob"],
  ["subject:allocation", "word in the subject"],
  ["tag:inbox and tag:unread", "combine with and, or, not"],
  ["date:2024-01-01..2024-06-30", "date range"],
  ["attachment:pdf", "attachment file name"],
  ['"exact phrase"', "words in this order"],
  ["thread:0000000000001a2b", "one thread by id"],
];

export function createTopbar({ onSearch, onMenu }) {
  const input = h("input", {
    class: "search-input",
    id: "search",
    type: "search",
    name: "q",
    autocomplete: "off",
    spellcheck: "false",
    placeholder: LONG_PLACEHOLDER,
    "aria-label": "Search mail with a notmuch query",
  });
  const fitPlaceholder = () => {
    input.placeholder = narrow.matches ? SHORT_PLACEHOLDER : LONG_PLACEHOLDER;
  };
  narrow.addEventListener("change", fitPlaceholder);
  fitPlaceholder();
  const help = h("div", { class: "syntax", id: "syntax-help", hidden: true }, [
    h("p", { class: "syntax-title" }, "notmuch search syntax"),
    h(
      "ul",
      { class: "syntax-list" },
      SYNTAX.map(([q, text]) =>
        h(
          "li",
          {},
          h(
            "button",
            {
              type: "button",
              class: "syntax-example",
              onclick: () => {
                input.value = q;
                input.focus();
                toggleHelp(false);
              },
            },
            q,
          ),
          h("span", {}, text),
        ),
      ),
    ),
    h("p", { class: "syntax-foot" }, "Full reference: man notmuch-search-terms"),
  ]);
  const helpButton = h(
    "button",
    {
      class: "icon-button",
      type: "button",
      "aria-label": "Search syntax help",
      "aria-expanded": "false",
      "aria-controls": "syntax-help",
      onclick: () => toggleHelp(),
    },
    icon("help"),
  );

  function toggleHelp(force) {
    const open = force ?? help.hidden;
    help.hidden = !open;
    helpButton.setAttribute("aria-expanded", String(open));
  }

  const form = h(
    "form",
    {
      class: "search",
      role: "search",
      onsubmit: (event) => {
        event.preventDefault();
        toggleHelp(false);
        onSearch(input.value.trim() || "*");
      },
    },
    icon("search", 18),
    input,
    helpButton,
    help,
  );
  document.addEventListener("click", (event) => {
    if (!help.hidden && !form.contains(event.target)) toggleHelp(false);
  });
  form.addEventListener("keydown", (event) => {
    if (event.key === "Escape") toggleHelp(false);
  });

  const el = h(
    "header",
    { class: "topbar" },
    h("button", { class: "icon-button menu-button", type: "button", "aria-label": "Show tags", onclick: onMenu }, icon("menu")),
    h("span", { class: "brand" }, h("span", { class: "brand-mark", "aria-hidden": "true" }, icon("mail", 16)), "notmuch-browser"),
    form,
    themeButton(),
  );
  return {
    el,
    setQuery(q) {
      input.value = q === "*" ? "" : q;
    },
    focusSearch() {
      input.focus();
      input.select();
    },
  };
}
