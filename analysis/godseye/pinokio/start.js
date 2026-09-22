// Start ONLY the dashboard: one bounded export, then the local server.
// daemon: true keeps it running until stop.js; the `on` matcher reads the
// URL the server prints so the menu can open it.
module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        path: "app",
        message: "python godseye_export.py --config godseye.config.json",
      },
    },
    {
      method: "shell.run",
      params: {
        path: "app",
        message: "python godseye_server.py --config godseye.config.json",
        on: [{ event: "/(http:\\/\\/127\\.0\\.0\\.1:[0-9]+\\/)/", done: true }],
      },
    },
    {
      method: "local.set",
      params: { url: "{{input.event[0]}}" },
    },
  ],
};
