import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/layout.css";
import "./styles/components.css";
import { start } from "./app.js";

function boot() {
  const root = document.getElementById("app");
  if (root) start(root);
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();
