// Drives the real UI against a fixture database. Asserts behaviour, then captures screenshots.
//   node scripts/shots.mjs /tmp/nb-fixture/notmuch-config [outdir]
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const config = process.argv[2];
const out = process.argv[3] || "shots";
if (!config) {
  console.error("usage: node scripts/shots.mjs <notmuch-config> [outdir]");
  process.exit(2);
}
mkdirSync(out, { recursive: true });
const PORT = 8799;
const BASE = `http://127.0.0.1:${PORT}`;
let failures = 0;
// Reduced motion leaves a 0.01ms transition on everything, so wait a moment before capturing.
const shot = async (page, path) => {
  await page.waitForTimeout(300);
  await page.screenshot({ path });
};
const check = (name, ok, extra = "") => {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? "  " + extra : ""}`);
  if (!ok) failures += 1;
};

const server = spawn(".venv/bin/notmuch-browser", ["--notmuch-config", config, "--no-browser", "--port", String(PORT)], {
  stdio: ["ignore", "pipe", "inherit"],
});
await new Promise((resolve, reject) => {
  server.stdout.on("data", (d) => String(d).includes("serving on") && resolve());
  server.on("exit", (c) => reject(new Error(`server exited ${c}`)));
  setTimeout(() => {
    server.kill();
    reject(new Error("server did not start"));
  }, 15000);
});

const browser = await chromium.launch();
const consoleErrors = [];

async function open({ width, height, scheme = "light", hash = "" }) {
  const context = await browser.newContext({ viewport: { width, height }, colorScheme: scheme, reducedMotion: "reduce" });
  const page = await context.newPage();
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(`${m.text()} @ ${page.url()}`));
  page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));
  await page.goto(`${BASE}/${hash}`);
  await page.waitForSelector(".thread, .state-box", { timeout: 10000 });
  return { context, page };
}

const threadIdOf = async (mid) => {
  const q = encodeURIComponent(`id:"${mid}"`);
  const res = await fetch(`${BASE}/api/search?q=${q}`);
  return (await res.json()).threads[0].thread;
};
const tagsOfThread = async (tid) => {
  const data = await (await fetch(`${BASE}/api/thread/${tid}`)).json();
  return Object.fromEntries(data.messages.map((m) => [m.id, [...m.tags].sort()]));
};

try {
  // ------------------------------------------------------------ behaviour
  {
    const { context, page } = await open({ width: 1440, height: 900, hash: "#q=*" });
    check("list renders threads", (await page.locator(".thread").count()) === 9);
    check("All mail shows an empty search field and a plain title", (await page.locator("#search").inputValue()) === "" && (await page.locator(".list-title").innerText()) === "All mail");
    check("unread rows are marked", (await page.locator(".thread.is-unread").count()) > 0);
    // Top bar layout: no stray menu button on desktop, search centred in the 56px bar.
    check("the menu button is hidden on desktop", !(await page.locator(".menu-button").isVisible()));
    const bar = await page.locator(".topbar").boundingBox();
    const box = await page.locator(".search").boundingBox();
    const offset = Math.abs(box.y + box.height / 2 - (bar.y + bar.height / 2));
    check("search field is vertically centred in the top bar", offset <= 1.5, `offset=${offset.toFixed(1)}px bar=${bar.height}px`);

    // Inline image and link inside the sandboxed HTML frame.
    const cidTid = await threadIdOf("cid@test");
    await page.goto(`${BASE}/#q=*&t=${cidTid}`);
    await page.waitForSelector(".mail-frame, .text");
    const frameEl = page.locator("iframe.mail-frame");
    if ((await frameEl.count()) === 0) await page.getByRole("button", { name: "Show HTML version" }).click();
    const frame = page.frameLocator("iframe.mail-frame");
    await frame.locator("img").first().waitFor();
    const natural = await frame.locator("img").first().evaluate((img) => new Promise((r) => (img.complete ? r(img.naturalWidth) : img.addEventListener("load", () => r(img.naturalWidth)))));
    check("cid image loads inside the sandboxed frame", natural > 0, `naturalWidth=${natural}`);
    check("no remote image survives", (await frame.locator('img[src*="evil"]').count()) === 0);
    await shot(page, `${out}/desktop-light-htmlmail.png`);

    const hostileTid = await threadIdOf("hostile@test");
    await page.goto(`${BASE}/#q=*&t=${hostileTid}`);
    await page.waitForSelector("iframe.mail-frame");
    const popupPromise = context.waitForEvent("page", { timeout: 5000 }).catch(() => null);
    await page.frameLocator("iframe.mail-frame").getByRole("link", { name: "good link" }).click();
    const popup = await popupPromise;
    check("a link in HTML mail opens a new page", popup !== null);
    if (popup) await popup.close();
    check("script and javascript: links are gone from the frame", (await page.frameLocator("iframe.mail-frame").locator("script, a[href^=javascript]").count()) === 0);

    // Flag then undo on the partly flagged thread, checked per message.
    const mixedTid = await threadIdOf("mixed0@test");
    const before = await tagsOfThread(mixedTid);
    await page.goto(`${BASE}/#q=*&t=${mixedTid}`);
    await page.waitForSelector(".reader-subject");
    await page.getByRole("button", { name: /^Flag$|^Flagged$/ }).waitFor();
    // thread already holds a flagged message, so the button reads Flagged: unflag then undo.
    await page.keyboard.press("f");
    await page.getByText("Thread unflagged").waitFor();
    const during = await tagsOfThread(mixedTid);
    check("unflag removed flagged from every message", Object.values(during).every((t) => !t.includes("flagged")));
    await page.getByRole("button", { name: "Undo" }).click();
    await page.getByText("Change undone.").waitFor();
    const after = await tagsOfThread(mixedTid);
    check("undo restores the exact per-message tags", JSON.stringify(after) === JSON.stringify(before), JSON.stringify({ before, after }));

    // Collapsed messages carry a chevron and expand on click.
    const collapsed = page.locator(".message.is-collapsed").first();
    check("collapsed messages show a chevron", (await collapsed.locator(".message-chevron svg").count()) === 1);
    await collapsed.locator(".message-toggle").click();
    check("a collapsed message expands on click", (await page.locator(".message.is-collapsed").count()) === 1);

    // Tag editor.
    await page.keyboard.press("t");
    await page.locator(".tag-input").fill("project-x");
    await page.keyboard.press("Enter");
    await page.getByText("Added tag project-x").waitFor();
    check("a typed tag is added", (await page.locator(".chip-name", { hasText: "project-x" }).count()) === 1);
    await page.getByRole("button", { name: "Undo" }).click();
    await page.getByText("Change undone.").waitFor();
    check("undo removes the added tag", (await page.locator(".chip-name", { hasText: "project-x" }).count()) === 0);
    await page.locator(".tag-input").fill("-bad tag");
    await page.keyboard.press("Enter");
    check("an invalid tag name is refused inline", await page.locator(".tag-error").isVisible());

    // Keyboard navigation and search.
    await page.keyboard.press("Escape");
    await page.locator("body").click({ position: { x: 700, y: 10 } });
    await page.keyboard.press("/");
    check("/ focuses the search field", await page.locator("#search").evaluate((el) => el === document.activeElement));
    await page.locator("#search").fill("subject:attachment");
    await page.keyboard.press("Enter");
    await page.waitForFunction(() => document.querySelectorAll(".thread").length === 1);
    check("search narrows the list", (await page.locator(".thread").count()) === 1);
    // Colour roles: tag pills carry a hue, matching words are highlighted, senders get avatars.
    await page.goto(`${BASE}/#q=${encodeURIComponent("thread tag:inbox")}`);
    await page.waitForSelector(".thread");
    check("search terms are highlighted in the list", (await page.locator(".thread-subject mark.hit").count()) > 0 && (await page.locator(".thread-subject mark.hit").first().innerText()).toLowerCase() === "thread");
    check("a tag in a query is not highlighted as text", (await page.locator("mark.hit", { hasText: /^inbox$/i }).count()) === 0);
    check("user tags show as hued pills in the list", (await page.locator(".tag-pill[data-hue]").count()) > 0);
    check("system tags are not shown as pills in the list", (await page.locator(".tag-pill", { hasText: /^(inbox|unread)$/ }).count()) === 0);
    await page.locator(".thread").first().click();
    await page.waitForSelector(".avatar");
    check("messages show a sender avatar", (await page.locator(".avatar[data-hue]").count()) > 0);
    check("hit words are highlighted in the message body", (await page.locator(".text mark.hit, .reader-subject mark.hit").count()) > 0);
    await page.locator("#search").fill("foo AND (");
    await page.keyboard.press("Enter");
    await page.waitForSelector(".state-box[role=alert]");
    check("a bad query shows an inline error with retry", await page.getByRole("button", { name: "Try again" }).isVisible());
    // The browser logs the deliberate 400 as a console error. Expected, so drop it.
    for (let i = consoleErrors.length - 1; i >= 0; i--) if (consoleErrors[i].includes("status of 400")) consoleErrors.splice(i, 1);
    await context.close();
  }

  // Light override on a dark system preference holds.
  {
    const { context, page } = await open({ width: 1440, height: 900, scheme: "dark", hash: "#q=*" });
    check("dark system starts dark", (await page.evaluate(() => document.documentElement.dataset.theme)) === "dark");
    await page.getByRole("button", { name: "Switch to light theme" }).click();
    // The reduced-motion reset leaves a 0.01ms transition, so give the style one frame to settle.
    await page.waitForFunction(() => getComputedStyle(document.body).backgroundColor === "rgb(243, 245, 248)", null, { timeout: 2000 }).catch(() => {});
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    const themeNow = await page.evaluate(() => document.documentElement.dataset.theme);
    check("manual light choice holds on a dark system", themeNow === "light" && bg === "rgb(243, 245, 248)", `theme=${themeNow} bg=${bg}`);
    await page.reload();
    await page.waitForSelector(".thread");
    check("the choice survives a reload", (await page.evaluate(() => document.documentElement.dataset.theme)) === "light");
    await context.close();
  }

  // ---------------------------------------------------------- screenshots
  const mixedTid = await threadIdOf("mixed0@test");
  const attachTid = await threadIdOf("attach@test");
  for (const scheme of ["light", "dark"]) {
    let { context, page } = await open({ width: 1440, height: 900, scheme, hash: `#q=*&t=${attachTid}` });
    await page.waitForSelector(".attachment");
    await shot(page, `${out}/desktop-${scheme}.png`);
    await page.locator("#search + button, button[aria-label='Search syntax help']").first().click();
    await shot(page, `${out}/desktop-${scheme}-syntax.png`);
    await page.keyboard.press("Escape");
    await page.goto(`${BASE}/#q=*&t=${mixedTid}`);
    await page.waitForSelector(".chip");
    await shot(page, `${out}/desktop-${scheme}-thread.png`);
    await page.goto(`${BASE}/#q=${encodeURIComponent("thread")}&t=${mixedTid}`);
    await page.waitForSelector(".chip");
    await shot(page, `${out}/desktop-${scheme}-search.png`);
    await context.close();

    ({ context, page } = await open({ width: 390, height: 844, scheme, hash: "#q=*" }));
    check(`phone search placeholder fits (${scheme})`, (await page.locator("#search").getAttribute("placeholder")) === "Search mail");
    await shot(page, `${out}/mobile-${scheme}-list.png`);
    await page.goto(`${BASE}/#q=*&t=${attachTid}`);
    await page.waitForSelector(".attachment");
    await shot(page, `${out}/mobile-${scheme}-reader.png`);
    await context.close();
  }
  {
    const { context, page } = await open({ width: 900, height: 800, hash: `#q=*&t=${attachTid}` });
    await shot(page, `${out}/tablet-light.png`);
    const railBox = async () => page.locator(".rail").boundingBox();
    check("the tag drawer starts off screen", (await railBox()) === null || (await railBox()).x < 0 || !(await page.locator(".rail").isVisible()));
    await page.getByRole("button", { name: "Show tags" }).click();
    await page.waitForFunction(() => { const r = document.querySelector(".rail").getBoundingClientRect(); return r.left >= 0 && getComputedStyle(document.querySelector(".rail")).visibility === "visible"; }, null, { timeout: 2000 }).catch(() => {});
    const opened = await railBox();
    check("the tag drawer opens on screen", opened !== null && opened.x >= 0 && (await page.locator(".rail").isVisible()), JSON.stringify(opened));
    await shot(page, `${out}/tablet-light-drawer.png`);
    await page.locator(".scrim").click({ position: { x: 600, y: 400 } });
    await page.waitForFunction(() => !document.querySelector(".shell").classList.contains("rail-open"), null, { timeout: 2000 }).catch(() => {});
    check("tapping the scrim closes the drawer", !(await page.evaluate(() => document.querySelector(".shell").classList.contains("rail-open"))));
    await context.close();
  }
  {
    const { context, page } = await open({ width: 1440, height: 900, hash: `#q=${encodeURIComponent("from:nobody")}` });
    await page.waitForSelector(".state-box");
    await shot(page, `${out}/desktop-light-empty.png`);
    await context.close();
  }
  check("no console errors or CSP violations", consoleErrors.length === 0, consoleErrors.slice(0, 3).join(" | "));
} finally {
  await browser.close();
  server.kill();
}
console.log(failures ? `\n${failures} check(s) failed` : "\nall checks passed");
process.exit(failures ? 1 : 0);
