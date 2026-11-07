"""
Build WaveSmith as a portable Windows app.

    python build.py

Result:
    dist/WaveSmith/                              ready-to-run folder
    dist/WaveSmith-<version>-win64-portable.zip  the same folder, zipped

ffmpeg.exe and ffprobe.exe must be in the project root (or on PATH);
they are copied next to WaveSmith.exe.
"""
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from core import APP_NAME, __version__  # noqa: E402

DIST = os.path.join(ROOT, "dist")
OUT = os.path.join(DIST, APP_NAME)


def find_tool(name):
    local = os.path.join(ROOT, f"{name}.exe")
    if os.path.isfile(local):
        return local
    found = shutil.which(name)
    if not found:
        sys.exit(f"[x] {name}.exe not found. Put it in the project folder or install FFmpeg on PATH.")
    return found


def version_file():
    parts = (__version__.split(".") + ["0", "0", "0"])[:4]
    tup = ", ".join(str(int(p)) for p in parts)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    with open(os.path.join(ROOT, "build", "version_info.txt"), "w", encoding="utf-8") as f:
        f.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({tup}), prodvers=({tup}), mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Bora Şavkar'),
      StringStruct('FileDescription', '{APP_NAME} – audio converter, trimmer and tag editor'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('InternalName', '{APP_NAME}'),
      StringStruct('OriginalFilename', '{APP_NAME}.exe'),
      StringStruct('ProductName', '{APP_NAME}'),
      StringStruct('ProductVersion', '{__version__}'),
      StringStruct('LegalCopyright', 'MIT License')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])])
""")


def main():
    ffmpeg, ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
    version_file()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                           os.path.join(ROOT, "WaveSmith.spec")], cwd=ROOT)

    print("[i] Copying FFmpeg and docs…")
    shutil.copy2(ffmpeg, OUT)
    shutil.copy2(ffprobe, OUT)
    for doc in ("README.md", "LICENSE", "THIRD-PARTY-NOTICES.md"):
        src = os.path.join(ROOT, doc)
        if os.path.isfile(src):
            shutil.copy2(src, OUT)

    zip_path = os.path.join(DIST, f"{APP_NAME}-{__version__}-win64-portable.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    print(f"[i] Zipping → {zip_path}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for folder, _dirs, files in os.walk(OUT):
            for f in files:
                full = os.path.join(folder, f)
                z.write(full, os.path.join(APP_NAME, os.path.relpath(full, OUT)))
    print(f"[✓] Done: {OUT}\n    {zip_path} ({os.path.getsize(zip_path) / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
