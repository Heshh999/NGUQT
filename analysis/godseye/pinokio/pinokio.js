// MROF God's Eye View — Pinokio launcher (OPTIONAL).
//
// Starts and stops ONLY the dashboard server. It never starts, stops,
// installs over, or restarts NinjaTrader, the recorder, the ingestion
// jobs or the research pipeline, and it copies no capture data: the
// dashboard reads its permitted summary exports from the folder named
// in godseye.config.json.
//
// Written against the pinokio.js / <script>.js convention documented for
// Pinokio 3.x (menu() returning entries whose `href` is a script; scripts
// as arrays of {method, params} steps; `daemon: true` for a long-running
// process; `on: [{event, done}]` to detect readiness). It could NOT be
// exercised in the build environment (no Pinokio there). Check the
// installed Pinokio version's script docs before relying on it, and use
// launch_godseye.bat if in doubt -- the .bat works independently.
const path = require("path");

module.exports = {
  version: "3.0",
  title: "MROF God's Eye View",
  description: "Read-only research monitor for the MROF NQ/MNQ order-flow study. Dashboard only; the recorder is never touched.",
  menu: async (kernel, info) => {
    const running = info.running("start.js");
    const installed = info.exists("app/godseye.config.json");
    if (running) {
      const local = info.local("start.js");
      const url = local && local.url ? local.url : "http://127.0.0.1:8765/";
      return [
        { default: true, icon: "fa-solid fa-eye", text: "Open dashboard", href: url, target: "_blank" },
        { icon: "fa-solid fa-terminal", text: "Server log", href: "start.js" },
        { icon: "fa-solid fa-stop", text: "Stop dashboard (only the dashboard)", href: "stop.js" },
      ];
    }
    if (installed) {
      return [
        { default: true, icon: "fa-solid fa-play", text: "Start dashboard", href: "start.js" },
        { icon: "fa-solid fa-rotate", text: "Refresh snapshot only", href: "export.js" },
        { icon: "fa-solid fa-gear", text: "Edit config (godseye.config.json)", href: "app/godseye.config.json" },
      ];
    }
    return [
      { default: true, icon: "fa-solid fa-download", text: "Install (link to your MROF folder)", href: "install.js" },
    ];
  },
};
