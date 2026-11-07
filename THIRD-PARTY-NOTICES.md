# Third-party notices

WaveSmith's own source code is MIT-licensed (see `LICENSE`). The portable Windows package also contains the following third-party software, each under its own license.

## FFmpeg (`ffmpeg.exe`, `ffprobe.exe`)

- Project: https://ffmpeg.org/
- Build used in the package: "full" build from https://www.gyan.dev/ffmpeg/builds/ (configured with `--enable-gpl --enable-version3`)
- License: **GNU General Public License v3.0** — https://www.gnu.org/licenses/gpl-3.0.html
- Source code: https://ffmpeg.org/download.html#get-sources and https://github.com/FFmpeg/FFmpeg ; build scripts: https://github.com/GyanD/codexffmpeg

FFmpeg is shipped as separate, unmodified executables that WaveSmith runs as external programs. You can replace them with any other FFmpeg build.

## Qt 6 / PyQt6

- Qt: https://www.qt.io/ — used under the GNU LGPL v3 (https://www.gnu.org/licenses/lgpl-3.0.html). Qt libraries are shipped as separate DLLs in `_internal\PyQt6\Qt6` and can be replaced.
- PyQt6: https://www.riverbankcomputing.com/software/pyqt/ — GPL v3 (https://www.gnu.org/licenses/gpl-3.0.html).

## Python

- CPython runtime: https://www.python.org/ — Python Software Foundation License (https://docs.python.org/3/license.html).
