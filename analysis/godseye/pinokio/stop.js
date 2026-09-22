// Stop ONLY the dashboard process started by start.js. The recorder,
// NinjaTrader and every research job are untouched.
module.exports = {
  run: [
    {
      method: "script.stop",
      params: { uri: "start.js" },
    },
  ],
};
