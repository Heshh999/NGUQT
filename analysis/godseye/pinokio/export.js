// Refresh the snapshot only (bounded, read-only on the capture folder).
module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        path: "app",
        message: "python godseye_export.py --config godseye.config.json",
      },
    },
  ],
};
