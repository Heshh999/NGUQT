@echo off
rem MROF God's Eye View - ordinary Windows launcher (no Pinokio needed).
rem Runs ONE bounded export, then serves the dashboard on 127.0.0.1.
rem It never starts, stops or touches NinjaTrader or the recorder.
setlocal
cd /d "%~dp0"
if not exist godseye.config.json (
  echo No godseye.config.json next to this file.
  echo   For the synthetic demonstration:   python godseye_demo.py demo   then copy demo\godseye.config.json here
  echo   For real reports: copy godseye.config.example.json to godseye.config.json and edit the paths
  pause
  exit /b 2
)
echo [1/2] exporting a bounded snapshot (read-only; seconds) ...
python godseye_export.py --config godseye.config.json
if errorlevel 1 (
  echo Export reported a problem. The previous snapshot, if any, is served as STALE.
)
echo [2/2] serving on http://127.0.0.1:8765/  (Ctrl+C stops the dashboard only)
start "" http://127.0.0.1:8765/
python godseye_server.py --config godseye.config.json
endlocal
