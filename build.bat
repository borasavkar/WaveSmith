@echo off
REM Builds the portable WaveSmith package (dist\WaveSmith\ and a .zip).
REM Requires: Python with the packages from requirements.txt, ffmpeg.exe and ffprobe.exe in this folder or on PATH.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" build.py
) else (
    python build.py
)
pause
