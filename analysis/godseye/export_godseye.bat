@echo off
rem MROF God's Eye View - refresh the snapshot only (for Task Scheduler,
rem e.g. every 5 minutes). Bounded, read-only on the capture folder.
setlocal
cd /d "%~dp0"
python godseye_export.py --config godseye.config.json
endlocal
