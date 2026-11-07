// Runs before first paint (loaded first, blocking) so a stored theme choice never flashes.
// It always writes the resolved theme to data-theme, so a manual light choice on a dark
// system holds.
(function () {
  var stored = null;
  try {
    stored = window.localStorage.getItem("nb-theme");
  } catch (_err) {
    stored = null;
  }
  var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  var resolved = stored === "light" || stored === "dark" ? stored : dark ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", resolved);
})();
