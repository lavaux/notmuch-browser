// One icon family: 24px grid, 1.5px stroke, round caps. Drawn here, no icon font.

const SVG_NS = "http://www.w3.org/2000/svg";

const ICONS = {
  search: [["circle", { cx: 11, cy: 11, r: 6.5 }], ["path", { d: "M20 20l-4.2-4.2" }]],
  flag: [["path", { d: "M6 21V4" }], ["path", { d: "M6 5h11l-2.2 4L17 13H6" }]],
  flagFilled: [
    ["path", { d: "M6 21V4" }],
    ["path", { d: "M6 5h11l-2.2 4L17 13H6z", fill: "currentColor" }],
  ],
  paperclip: [
    ["path", { d: "M20 11.5l-8 8a5 5 0 01-7-7l8.5-8.5a3.5 3.5 0 015 5L10 17.5a2 2 0 01-3-3l7.5-7.5" }],
  ],
  sun: [
    ["circle", { cx: 12, cy: 12, r: 4 }],
    ["path", { d: "M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" }],
  ],
  moon: [["path", { d: "M20 14.5A8 8 0 019.5 4 8 8 0 1020 14.5z" }]],
  tag: [["path", { d: "M3.5 12.5V4.5h8l9 9-8 8-9-9z" }], ["circle", { cx: 8, cy: 9, r: 1 }]],
  chevronLeft: [["path", { d: "M15 5l-7 7 7 7" }]],
  chevronDown: [["path", { d: "M5 9l7 7 7-7" }]],
  undo: [["path", { d: "M9 14L4 9l5-5" }], ["path", { d: "M4 9h10a6 6 0 010 12h-3" }]],
  close: [["path", { d: "M6 6l12 12M18 6L6 18" }]],
  plus: [["path", { d: "M12 5v14M5 12h14" }]],
  inbox: [["path", { d: "M3 13l3-8h12l3 8v6H3v-6z" }], ["path", { d: "M3 13h5l1 3h6l1-3h5" }]],
  mail: [["path", { d: "M3 6h18v12H3z" }], ["path", { d: "M3 7l9 7 9-7" }]],
  stack: [["path", { d: "M3 7h18M3 12h18M3 17h18" }]],
  alert: [["circle", { cx: 12, cy: 12, r: 9 }], ["path", { d: "M12 7.5v5.5M12 16.5h.01" }]],
  download: [["path", { d: "M12 4v11M7 11l5 5 5-5M5 20h14" }]],
  menu: [["path", { d: "M4 6h16M4 12h16M4 18h16" }]],
  help: [
    ["circle", { cx: 12, cy: 12, r: 9 }],
    ["path", { d: "M9.5 9.2a2.5 2.5 0 114 2c-1 .8-1.5 1.3-1.5 2.5M12 17h.01" }],
  ],
  expand: [["path", { d: "M5 9l7 7 7-7" }]],
  collapse: [["path", { d: "M5 15l7-7 7 7" }]],
};

export function icon(name, size = 18) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.5");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.classList.add("icon");
  for (const [tag, attrs] of ICONS[name] || []) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    svg.append(node);
  }
  return svg;
}
