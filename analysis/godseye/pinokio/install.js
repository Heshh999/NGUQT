// Install = point Pinokio at an EXISTING MROF checkout. Nothing is
// downloaded, no research dataset is duplicated, no dependency is
// installed (the dashboard is Python standard library only), and the
// step is skipped when the link already exists so a relaunch never
// reinstalls.
//
// Set MROF_GODSEYE_DIR before running, or edit `src` below, to the
// analysis\godseye folder of the MROF folder you run the tools from
// (e.g. C:\MROF\NEW V9\analysis\godseye).
module.exports = {
  run: [
    {
      method: "fs.link",
      params: {
        drive: {
          app: process.env.MROF_GODSEYE_DIR || "C:\\MROF\\NEW V9\\analysis\\godseye",
        },
      },
    },
    {
      method: "notify",
      params: {
        html: "Linked. Copy godseye.config.example.json to godseye.config.json in that folder and set the paths, then Start.",
      },
    },
  ],
};
