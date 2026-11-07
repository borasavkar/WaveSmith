"""
WaveSmith audio engine — a thin, dependency-free wrapper around FFmpeg/FFprobe.

Everything here is UI-agnostic: conversion, trimming, fades, native stream
extraction, metadata (tag) reading/writing and folder scanning.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile


# ─────────────────────────────────────────────
#  BINARY RESOLUTION
# ─────────────────────────────────────────────
def _resolve_binary(name):
    """
    Locate ffmpeg/ffprobe reliably.

    Priority:
      1. Bundled binary next to the executable / project root
         (PyInstaller sets sys._MEIPASS; fall back to project dir).
      2. System PATH.
    """
    exe = f"{name}.exe" if os.name == "nt" else name
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), exe))
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, exe))
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(project_root, exe))

    for path in candidates:
        if os.path.isfile(path):
            return path
    found = shutil.which(name)
    return found if found else name


FFMPEG_BIN = _resolve_binary("ffmpeg")
FFPROBE_BIN = _resolve_binary("ffprobe")

# Hide the console window that would otherwise flash for every FFmpeg call
# when the app is built as a windowed (no-console) executable.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


class FFmpegNotFound(RuntimeError):
    pass


class Cancelled(RuntimeError):
    pass


def _run(cmd, timeout=None):
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout,
                              creationflags=_NO_WINDOW)
    except FileNotFoundError:
        raise FFmpegNotFound(cmd[0])


# ─────────────────────────────────────────────
#  FILE TYPES
# ─────────────────────────────────────────────
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".oga", ".flac", ".aac", ".m4a", ".m4b",
              ".opus", ".wma", ".aiff", ".aif", ".ac3", ".eac3", ".dts", ".mp2",
              ".mka", ".alac", ".ape", ".wv", ".amr"}
VIDEO_EXTS = {".mp4", ".mkv", ".ts", ".m2ts", ".webm", ".avi", ".mov", ".flv",
              ".wmv", ".mpg", ".mpeg", ".m4v", ".3gp", ".vob"}
MEDIA_EXTS = AUDIO_EXTS | VIDEO_EXTS

# Containers whose tags FFmpeg can rewrite without re-encoding
TAG_EXTS = {".mp3", ".flac", ".m4a", ".m4b", ".mp4", ".ogg", ".oga", ".opus",
            ".wma", ".wav", ".aiff", ".aif", ".mka", ".mkv"}
# Containers that can carry embedded cover art via FFmpeg
COVER_EXTS = {".mp3", ".flac", ".m4a", ".m4b", ".mp4"}

METADATA_FIELDS = ["title", "artist", "album", "album_artist", "date", "genre",
                   "track", "disc", "composer", "comment"]


def is_media(path, kind="any"):
    ext = os.path.splitext(path)[1].lower()
    if kind == "audio":
        return ext in AUDIO_EXTS
    if kind == "video":
        return ext in VIDEO_EXTS
    return ext in MEDIA_EXTS


def collect_media_files(paths, kind="any", recursive=True):
    """Expand a mix of files and folders into a sorted, de-duplicated list of media files."""
    out, seen = [], set()

    def add(p):
        key = os.path.normcase(os.path.abspath(p))
        if key not in seen and is_media(p, kind):
            seen.add(key)
            out.append(os.path.abspath(p))

    for p in paths:
        if os.path.isdir(p):
            if recursive:
                for root, _dirs, files in os.walk(p):
                    for f in sorted(files, key=str.lower):
                        add(os.path.join(root, f))
            else:
                for f in sorted(os.listdir(p), key=str.lower):
                    full = os.path.join(p, f)
                    if os.path.isfile(full):
                        add(full)
        elif os.path.isfile(p):
            add(p)
    return out


# ─────────────────────────────────────────────
#  CODEC CATALOGUE
#  (descriptions live in core/i18n.py as "codec_desc.<name>")
# ─────────────────────────────────────────────
CODEC_PROFILES = {
    "MP3": {
        "ext": ".mp3", "codec": "libmp3lame", "mode": "vbr", "quality": 2, "bitrate": "192k",
        "sample_rates": ["44100", "48000", "32000", "22050"],
        "channels": ["stereo", "mono", "joint stereo"],
        "recommended": {"quality": 2, "sample_rate": "44100", "channels": "stereo"},
    },
    "AAC": {
        "ext": ".m4a", "codec": "aac", "mode": "cbr", "quality": 3, "bitrate": "192k",
        "sample_rates": ["44100", "48000", "32000", "22050"],
        "channels": ["stereo", "mono"],
        "recommended": {"bitrate": "192k", "sample_rate": "44100", "channels": "stereo"},
    },
    "OGG Vorbis": {
        "ext": ".ogg", "codec": "libvorbis", "mode": "vbr", "quality": 5, "bitrate": "192k",
        "sample_rates": ["44100", "48000", "32000", "22050"],
        "channels": ["stereo", "mono"],
        "recommended": {"quality": 5, "sample_rate": "44100", "channels": "stereo"},
    },
    "OPUS": {
        "ext": ".opus", "codec": "libopus", "mode": "cbr", "quality": 5, "bitrate": "128k",
        "sample_rates": ["48000", "24000", "16000", "12000", "8000"],
        "channels": ["stereo", "mono"],
        "recommended": {"bitrate": "128k", "sample_rate": "48000", "channels": "stereo"},
    },
    "FLAC": {
        "ext": ".flac", "codec": "flac", "mode": "lossless", "quality": 5, "bitrate": None,
        "sample_rates": ["44100", "48000", "96000", "192000"],
        "channels": ["stereo", "mono", "5.1 surround"],
        "recommended": {"compression": 5, "sample_rate": "44100", "channels": "stereo"},
    },
    "WAV (PCM)": {
        "ext": ".wav", "codec": "pcm_s16le", "mode": "lossless", "quality": None, "bitrate": None,
        "sample_rates": ["44100", "48000", "96000", "192000"],
        "channels": ["stereo", "mono", "5.1 surround"],
        "recommended": {"sample_rate": "44100", "channels": "stereo"},
    },
    "AIFF": {
        "ext": ".aiff", "codec": "pcm_s16be", "mode": "lossless", "quality": None, "bitrate": None,
        "sample_rates": ["44100", "48000", "96000"],
        "channels": ["stereo", "mono"],
        "recommended": {"sample_rate": "44100", "channels": "stereo"},
    },
    "WMA": {
        "ext": ".wma", "codec": "wmav2", "mode": "cbr", "quality": 5, "bitrate": "192k",
        "sample_rates": ["44100", "48000", "32000"],
        "channels": ["stereo", "mono"],
        "recommended": {"bitrate": "192k", "sample_rate": "44100", "channels": "stereo"},
    },
    "AC3 (Dolby)": {
        "ext": ".ac3", "codec": "ac3", "mode": "cbr", "quality": None, "bitrate": "448k",
        "sample_rates": ["48000", "44100", "32000"],
        "channels": ["stereo", "mono", "5.1 surround"],
        "recommended": {"bitrate": "448k", "sample_rate": "48000", "channels": "5.1 surround"},
    },
    "DTS": {
        "ext": ".dts", "codec": "dca", "mode": "cbr", "quality": None, "bitrate": "1536k",
        "sample_rates": ["48000", "44100"],
        "channels": ["stereo", "5.1 surround"],
        "recommended": {"bitrate": "1536k", "sample_rate": "48000", "channels": "5.1 surround"},
    },
    "MP2": {
        "ext": ".mp2", "codec": "mp2", "mode": "cbr", "quality": None, "bitrate": "192k",
        "sample_rates": ["44100", "48000", "32000"],
        "channels": ["stereo", "mono"],
        "recommended": {"bitrate": "192k", "sample_rate": "48000", "channels": "stereo"},
    },
}

# Source codec → container extension for lossless stream copy ("native" extraction)
NATIVE_EXT = {
    "aac": ".m4a", "alac": ".m4a", "mp3": ".mp3", "vorbis": ".ogg", "opus": ".opus",
    "flac": ".flac", "pcm_s16le": ".wav", "pcm_s24le": ".wav", "pcm_s32le": ".wav",
    "pcm_f32le": ".wav", "pcm_s16be": ".aiff", "wmav2": ".wma", "wmapro": ".wma",
    "ac3": ".ac3", "eac3": ".eac3", "dts": ".dts", "mp2": ".mp2",
}
FALLBACK_NATIVE_EXT = ".mka"   # Matroska audio can hold any codec


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def parse_time(t):
    """Parse 'HH:MM:SS(.ms)', 'MM:SS' or plain seconds to float seconds. None on failure."""
    if t is None or str(t).strip() == "":
        return None
    try:
        s = str(t).strip().replace(",", ".")
        if ":" in s:
            parts = [float(p) for p in s.split(":")]
            while len(parts) < 3:
                parts.insert(0, 0.0)
            h, m, sec = parts[-3], parts[-2], parts[-1]
            return h * 3600 + m * 60 + sec
        return float(s)
    except (ValueError, TypeError):
        return None


def unique_path(path):
    """Return `path`, or `name (2).ext`, `name (3).ext`… if it already exists."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{base} ({n}){ext}"):
        n += 1
    return f"{base} ({n}){ext}"


def get_media_info(input_file):
    """Return duration (seconds), stream flags, first audio codec and raw ffprobe JSON."""
    cmd = [FFPROBE_BIN, "-v", "quiet", "-print_format", "json",
           "-show_streams", "-show_format", input_file]
    try:
        result = _run(cmd, timeout=20)
        data = json.loads(result.stdout.decode("utf-8", errors="replace") or "{}")
    except Exception:
        return {"duration": 0, "has_video": False, "has_audio": False,
                "audio_codec": "", "cover_index": None, "raw": {}}

    streams = data.get("streams", [])
    try:
        duration = float(data.get("format", {}).get("duration", 0) or 0)
    except ValueError:
        duration = 0
    cover_index = None
    has_video = False
    for s in streams:
        if s.get("codec_type") == "video":
            if s.get("disposition", {}).get("attached_pic") == 1:
                if cover_index is None:
                    cover_index = s.get("index")
            else:
                has_video = True
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    return {
        "duration": duration,
        "has_video": has_video,
        "has_audio": bool(audio),
        "audio_codec": audio[0].get("codec_name", "") if audio else "",
        "cover_index": cover_index,
        "raw": data,
    }


def _effective_duration(total, start_time, end_time):
    start_s = parse_time(start_time) or 0.0
    end_s = parse_time(end_time)
    if end_s and end_s > 0:
        return max(0.0, end_s - start_s)
    return max(0.0, (total or 0) - start_s)


def _execute(command, duration, on_progress=None, should_cancel=None):
    """Run FFmpeg with machine-readable progress on stdout. Raises on failure/cancel."""
    command = command[:1] + ["-hide_banner", "-loglevel", "error",
                             "-progress", "pipe:1", "-nostats"] + command[1:]
    err_file = tempfile.TemporaryFile()
    try:
        try:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=err_file,
                                    stdin=subprocess.DEVNULL, creationflags=_NO_WINDOW)
        except FileNotFoundError:
            raise FFmpegNotFound(command[0])

        cancelled = False
        for raw in proc.stdout:
            if should_cancel and should_cancel():
                cancelled = True
                proc.kill()
                break
            line = raw.decode("utf-8", errors="ignore").strip()
            if on_progress and duration and line.startswith("out_time_us="):
                try:
                    us = int(line.split("=", 1)[1])
                    on_progress(max(0.0, min(us / 1e6 / duration, 1.0)))
                except ValueError:
                    pass
        proc.wait()
        if cancelled:
            raise Cancelled()
        if proc.returncode != 0:
            err_file.seek(0)
            msg = err_file.read().decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"FFmpeg error (exit {proc.returncode}):\n{msg}\n\n"
                               f"Command:\n{' '.join(command)}")
        if on_progress:
            on_progress(1.0)
    finally:
        err_file.close()


def _metadata_args(metadata):
    args = []
    for k, v in (metadata or {}).items():
        args.extend(["-metadata", f"{k}={v if v is not None else ''}"])
    return args


# ─────────────────────────────────────────────
#  CONVERSION / TRIM / EXTRACT
# ─────────────────────────────────────────────
def process_audio(
    input_file,
    target_format=None,
    start_time=None,
    end_time=None,
    fade_in=False,
    fade_out=False,
    fade_duration=3.0,
    bitrate=None,
    quality=None,
    sample_rate=None,
    channels=None,
    compression_level=None,
    output_dir=None,
    output_suffix="_converted",
    copy_audio=False,
    metadata=None,
    keep_cover=True,
    on_progress=None,
    should_cancel=None,
):
    """
    Universal audio processing.

    copy_audio=True  → copy the first audio stream bit-for-bit (no re-encode);
                       the container is chosen from the source codec.
    metadata         → dict of tag overrides written to the output.
    Returns the output file path.
    """
    info = get_media_info(input_file)
    if not info["has_audio"] and info["raw"]:
        raise RuntimeError(f"No audio stream found in:\n{input_file}")

    if copy_audio:
        ext = NATIVE_EXT.get(info["audio_codec"], FALLBACK_NATIVE_EXT)
        profile = None
    else:
        profile = CODEC_PROFILES.get(target_format)
        if not profile:
            raise ValueError(f"Unsupported format: {target_format}")
        ext = profile["ext"]

    if not output_dir:
        output_dir = os.path.dirname(input_file) or "."
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = unique_path(os.path.join(output_dir, f"{base_name}{output_suffix}{ext}"))

    command = [FFMPEG_BIN, "-y"]

    # Trim: input-side seek (fast and accurate with modern FFmpeg)
    if start_time and parse_time(start_time):
        command.extend(["-ss", str(start_time)])
    if end_time and parse_time(end_time):
        command.extend(["-to", str(end_time)])
    command.extend(["-i", input_file])

    # Stream selection: first audio + (optionally) embedded cover art
    command.extend(["-map", "0:a:0", "-map_metadata", "0"])
    with_cover = keep_cover and info["cover_index"] is not None and ext in COVER_EXTS
    if with_cover:
        command.extend(["-map", f"0:{info['cover_index']}", "-c:v", "copy",
                        "-disposition:v:0", "attached_pic"])

    if copy_audio:
        command.extend(["-c:a", "copy"])
    else:
        codec = profile["codec"]
        command.extend(["-c:a", codec])
        if codec == "dca":                         # DTS encoder is experimental
            command.extend(["-strict", "-2"])

        mode = profile["mode"]
        if mode == "lossless":
            if target_format == "FLAC" and compression_level is not None:
                command.extend(["-compression_level", str(compression_level)])
        elif mode == "vbr":
            q = quality if quality is not None else profile["quality"]
            command.extend(["-q:a", str(q)])
        elif mode == "cbr":
            command.extend(["-b:a", bitrate or profile["bitrate"]])

        if sample_rate:
            command.extend(["-ar", str(sample_rate)])

        if channels:
            ch_num = {"stereo": "2", "mono": "1", "joint stereo": "2", "5.1 surround": "6"}.get(channels, "2")
            command.extend(["-ac", ch_num])
            # Explicit layout helps receivers detect AC3/DTS 5.1 over S/PDIF.
            # The dca (DTS) encoder only accepts the *side* variant.
            if channels == "5.1 surround":
                command.extend(["-channel_layout", "5.1(side)" if codec == "dca" else "5.1"])
            elif channels in ("stereo", "joint stereo"):
                command.extend(["-channel_layout", "stereo"])
            elif channels == "mono":
                command.extend(["-channel_layout", "mono"])
            if channels == "joint stereo" and codec == "libmp3lame":
                command.extend(["-joint_stereo", "1"])

        # Fades (only possible when re-encoding)
        effective = _effective_duration(info["duration"], start_time, end_time)
        filters = []
        if fade_in and effective > 0:
            filters.append(f"afade=t=in:st=0:d={min(fade_duration, effective):.3f}")
        if fade_out and effective > 0:
            fd = min(fade_duration, effective)
            filters.append(f"afade=t=out:st={max(0.0, effective - fd):.3f}:d={fd:.3f}:curve=exp")
        if filters:
            command.extend(["-af", ",".join(filters)])

    if ext == ".mp3":
        command.extend(["-id3v2_version", "3"])   # best compatibility with Windows/players
    command.extend(_metadata_args(metadata))
    command.append(output_file)

    duration = _effective_duration(info["duration"], start_time, end_time)
    try:
        _execute(command, duration, on_progress, should_cancel)
    except BaseException:
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except OSError:
                pass
        raise
    return output_file


# ─────────────────────────────────────────────
#  METADATA
# ─────────────────────────────────────────────
_TAG_ALIASES = {
    "albumartist": "album_artist", "album artist": "album_artist",
    "tracknumber": "track", "discnumber": "disc", "year": "date",
    "description": "comment",
}


def read_metadata(input_file):
    """Return {field: value} for METADATA_FIELDS (lower-case keys), plus 'has_cover'."""
    info = get_media_info(input_file)
    raw = info.get("raw", {})
    tags = {}
    # Stream tags first (OGG/OPUS store tags per stream), then container tags win.
    for s in raw.get("streams", []):
        if s.get("codec_type") == "audio":
            for k, v in (s.get("tags") or {}).items():
                tags.setdefault(k.lower(), v)
            break
    for k, v in (raw.get("format", {}).get("tags") or {}).items():
        tags[k.lower()] = v
    out = {}
    for k, v in tags.items():
        key = _TAG_ALIASES.get(k, k)
        if key in METADATA_FIELDS and key not in out:
            out[key] = v
    out["has_cover"] = info.get("cover_index") is not None
    return out


def supports_tags(path):
    return os.path.splitext(path)[1].lower() in TAG_EXTS


def supports_cover(path):
    return os.path.splitext(path)[1].lower() in COVER_EXTS


def write_metadata(input_file, metadata, cover_path=None, remove_cover=False):
    """
    Rewrite tags in place without re-encoding (stream copy into a temp file, then replace).

    metadata     : {field: value}; an empty string removes that field.
    cover_path   : image file to embed as cover art (MP3/FLAC/M4A/MP4 only).
    remove_cover : strip existing embedded cover art.
    """
    ext = os.path.splitext(input_file)[1].lower()
    if ext not in TAG_EXTS:
        raise RuntimeError(f"Tag writing is not supported for '{ext}' files.")
    if (cover_path or remove_cover) and ext not in COVER_EXTS:
        raise RuntimeError(f"Cover art is not supported for '{ext}' files.")

    info = get_media_info(input_file)
    folder = os.path.dirname(os.path.abspath(input_file))
    tmp = os.path.join(folder, f".wavesmith-tmp-{os.getpid()}{ext}")

    cmd = [FFMPEG_BIN, "-y", "-i", input_file]
    if cover_path:
        cmd.extend(["-i", cover_path])
    cmd.extend(["-map_metadata", "0"])

    if cover_path:
        cmd.extend(["-map", "0:a", "-map", "1:0", "-c", "copy",
                    "-disposition:v:0", "attached_pic"])
        if ext == ".mp3":
            cmd.extend(["-metadata:s:v", "title=Album cover", "-metadata:s:v", "comment=Cover (front)"])
    elif remove_cover:
        cmd.extend(["-map", "0:a", "-c", "copy"])
    else:
        cmd.extend(["-map", "0", "-c", "copy"])
        if info.get("cover_index") is not None:
            cmd.extend(["-disposition:v:0", "attached_pic"])

    if ext == ".mp3":
        cmd.extend(["-id3v2_version", "3"])
    # OGG/OPUS keep tags on the audio stream
    if ext in (".ogg", ".oga", ".opus"):
        for k, v in (metadata or {}).items():
            cmd.extend(["-metadata:s:a:0", f"{k}={v if v is not None else ''}"])
    cmd.extend(_metadata_args(metadata))
    cmd.append(tmp)

    try:
        _execute(cmd, info.get("duration", 0))
        os.replace(tmp, input_file)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def extract_cover(input_file, out_path):
    """Save embedded cover art to out_path (jpg/png). Returns True on success."""
    info = get_media_info(input_file)
    if info.get("cover_index") is None:
        return False
    cmd = [FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error", "-i", input_file,
           "-map", f"0:{info['cover_index']}", "-frames:v", "1", out_path]
    r = _run(cmd, timeout=30)
    return r.returncode == 0 and os.path.exists(out_path)
