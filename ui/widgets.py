"""Reusable widgets: file queue, single-file picker, output folder, codec panel, trim bar, metadata form."""
import os
import random
import re
import sys
import subprocess

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QPolygon, QPixmap, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QComboBox,
    QFileDialog, QLineEdit, QCheckBox, QGroupBox, QFrame, QSizePolicy, QSpinBox,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView, QHeaderView, QStackedWidget,
    QDialog, QPlainTextEdit, QApplication,
)

from core import ffmpeg_engine as eng
from core.i18n import tr
from core.settings import settings


# ═══════════════════════════════════════════════════════════════════════════════
#  SMALL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def sec_to_ts(seconds):
    seconds = max(0.0, float(seconds or 0))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def ts_to_sec(ts):
    v = eng.parse_time(ts)
    if v is None:
        raise ValueError(ts)
    return v


def open_folder_select(path):
    """Open the file manager and highlight the given file."""
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path)])
    except Exception:
        pass


def lbl(text, size=13):
    l = QLabel(text)
    l.setStyleSheet(f"color:#8aaccc; font-weight:600; font-size:{size}px;")
    l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return l


def vsep():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet("color:rgba(85,170,255,0.15);")
    f.setFixedWidth(1)
    return f


def _ext_list(exts):
    return " ".join(f"*{e}" for e in sorted(exts))


def media_filter(kind="any"):
    a, v = _ext_list(eng.AUDIO_EXTS), _ext_list(eng.VIDEO_EXTS)
    if kind == "video":
        return f"{tr('filter.video')} ({v})"
    if kind == "audio":
        return f"{tr('filter.audio')} ({a})"
    if kind == "tags":
        return f"{tr('filter.audio')} ({_ext_list(eng.TAG_EXTS)})"
    return f"{tr('filter.all_media')} ({a} {v});;{tr('filter.video')} ({v});;{tr('filter.audio')} ({a})"


def last_dir():
    return settings().value("last_dir", "", type=str)


def remember_dir(path):
    if path:
        settings().setValue("last_dir", path if os.path.isdir(path) else os.path.dirname(path))


def show_error_dialog(parent, title, message):
    """Wide, resizable error dialog with scrollable, selectable text."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    screen = QApplication.primaryScreen()
    if screen:
        g = screen.availableGeometry()
        dlg.resize(max(800, int(g.width() * 0.6)), max(420, int(g.height() * 0.5)))
    dlg.setSizeGripEnabled(True)
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(16, 14, 16, 14)
    header = QLabel(tr("err.header"))
    header.setStyleSheet("color:#aac4dc; font-size:12px;")
    header.setWordWrap(True)
    lay.addWidget(header)
    box = QPlainTextEdit()
    box.setReadOnly(True)
    box.setPlainText(str(message))
    box.setStyleSheet(
        "QPlainTextEdit { background:#0f1620; color:#e6edf3; border:1px solid rgba(120,160,200,0.25);"
        "border-radius:6px; font-family:Consolas,'Courier New',monospace; font-size:12px; padding:8px; }")
    box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    lay.addWidget(box, 1)
    btns = QHBoxLayout()
    btns.addStretch(1)
    b_copy, b_close = QPushButton(tr("err.copy")), QPushButton(tr("err.close"))
    b_copy.clicked.connect(lambda: QApplication.clipboard().setText(str(message)))
    b_close.clicked.connect(dlg.accept)
    btns.addWidget(b_copy)
    btns.addWidget(b_close)
    lay.addLayout(btns)
    dlg.exec()


# ═══════════════════════════════════════════════════════════════════════════════
#  BACKGROUND PROBE
# ═══════════════════════════════════════════════════════════════════════════════
class ProbeWorker(QThread):
    probed = pyqtSignal(str, dict)

    def __init__(self, paths, mode):
        super().__init__()
        self.paths, self.mode = list(paths), mode
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        for p in self.paths:
            if self._stop:
                return
            try:
                info = eng.read_metadata(p) if self.mode == "tags" else eng.get_media_info(p)
            except Exception:
                info = {}
            info.pop("raw", None)
            self.probed.emit(p, info)


# ═══════════════════════════════════════════════════════════════════════════════
#  FILE QUEUE (batch list with drag & drop)
# ═══════════════════════════════════════════════════════════════════════════════
class FileQueue(QGroupBox):
    """
    A list of files. kind: "any" | "video" | "tags".
    Each row is a dict: {path, item, info, tags, override, pending, status}.
    """
    changed = pyqtSignal()
    selection_changed = pyqtSignal()

    def __init__(self, title, kind="any", tag_button=False, parent=None):
        super().__init__(title, parent)
        self.kind = kind
        self.rows = []
        self._index = {}
        self._probes = []
        self._locked = False

        root = QVBoxLayout()
        root.setContentsMargins(12, 16, 12, 10)
        root.setSpacing(8)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.btn_files = QPushButton(tr("queue.add_files"))
        self.btn_folder = QPushButton(tr("queue.add_folder"))
        self.btn_remove = QPushButton(tr("queue.remove"))
        self.btn_clear = QPushButton(tr("queue.clear"))
        for b in (self.btn_files, self.btn_folder):
            bar.addWidget(b)
        self.chk_sub = QCheckBox(tr("queue.subfolders"))
        self.chk_sub.setChecked(settings().value("recursive", True, type=bool))
        self.chk_sub.toggled.connect(lambda v: settings().setValue("recursive", v))
        bar.addWidget(self.chk_sub)
        bar.addStretch()
        self.btn_tags = None
        if tag_button:
            self.btn_tags = QPushButton(tr("queue.edit_tags"))
            bar.addWidget(self.btn_tags)
        bar.addWidget(self.btn_remove)
        bar.addWidget(self.btn_clear)
        root.addLayout(bar)

        self.stack = QStackedWidget()
        hint = QLabel("⬇\n" + tr("queue.hint") + ("\n\n" + tr("meta.only_tag_formats") if kind == "tags" else ""))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        hint.setMinimumHeight(140)
        hint.setStyleSheet("color:#4a7a9e; font-size:13px; border:2px dashed rgba(85,170,255,0.28);"
                           "border-radius:10px; background:rgba(85,170,255,0.035); padding:16px;")
        self.stack.addWidget(hint)

        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setUniformRowHeights(True)
        self.tree.setMinimumHeight(170)
        if kind == "tags":
            cols = [tr("queue.col_file"), tr("meta.col_title"), tr("meta.col_artist"), tr("queue.col_status")]
        else:
            cols = [tr("queue.col_file"), tr("queue.col_info"), tr("queue.col_status")]
        self.tree.setHeaderLabels(cols)
        hdr = self.tree.header()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(cols)):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            hdr.resizeSection(i, 150 if kind != "tags" else (85 if i == 3 else 115))
        self.tree.itemSelectionChanged.connect(self.selection_changed.emit)
        self.stack.addWidget(self.tree)
        root.addWidget(self.stack, 1)

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color:#3a6a8a; font-size:11px;")
        root.addWidget(self.lbl_count)
        self.setLayout(root)

        self.btn_files.clicked.connect(self._browse_files)
        self.btn_folder.clicked.connect(self._browse_folder)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self.tree, activated=self.remove_selected)
        self._refresh()

    # ── public ──────────────────────────────────────────────────────────────
    def engine_kind(self):
        return "video" if self.kind == "video" else "any"

    def add_paths(self, paths):
        """Add files/folders. Returns number of new rows."""
        if self._locked:
            return 0
        files = eng.collect_media_files(paths, self.engine_kind(), self.chk_sub.isChecked())
        if self.kind == "tags":
            files = [f for f in files if eng.supports_tags(f)]
        new = []
        for f in files:
            key = os.path.normcase(f)
            if key in self._index:
                continue
            item = QTreeWidgetItem([os.path.basename(f)])
            item.setToolTip(0, f)
            if self.kind == "tags":
                item.setText(3, tr("info.probing"))
            else:
                item.setText(1, tr("info.probing"))
                item.setText(2, tr("status.pending"))
            row = {"path": f, "item": item, "info": {}, "tags": {}, "override": {},
                   "pending": {}, "status": "pending"}
            self._index[key] = row
            self.rows.append(row)
            self.tree.addTopLevelItem(item)
            new.append(f)
        if paths:
            remember_dir(paths[0])
        if new:
            w = ProbeWorker(new, "tags" if self.kind == "tags" else "media")
            w.probed.connect(self._on_probed)
            w.finished.connect(lambda w=w: self._probes.remove(w) if w in self._probes else None)
            self._probes.append(w)
            w.start()
        self._refresh()
        return len(new)

    def paths(self):
        return [r["path"] for r in self.rows]

    def selected_rows(self):
        sel = set(id(i) for i in self.tree.selectedItems())
        return [r for r in self.rows if id(r["item"]) in sel]

    def remove_selected(self):
        if self._locked:
            return
        for r in self.selected_rows():
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(r["item"]))
            self.rows.remove(r)
            self._index.pop(os.path.normcase(r["path"]), None)
        self._refresh()

    def clear(self):
        if self._locked:
            return
        self.tree.clear()
        self.rows.clear()
        self._index.clear()
        self._refresh()

    def set_locked(self, locked):
        self._locked = locked
        for b in (self.btn_files, self.btn_folder, self.btn_remove, self.btn_clear, self.btn_tags):
            if b:
                b.setEnabled(not locked)

    def is_locked(self):
        return self._locked

    def set_status(self, row, status, text=None):
        row["status"] = status
        col = 3 if self.kind == "tags" else 2
        colors = {"done": "#70e0a0", "failed": "#ff8a70", "working": "#ffd840",
                  "cancelled": "#8aaccc", "pending": "#8aaccc"}
        row["item"].setText(col, text if text is not None else tr(f"status.{status}"))
        row["item"].setForeground(col, QColor(colors.get(status, "#8aaccc")))

    def refresh_row(self, row):
        it = row["item"]
        if self.kind == "tags":
            eff = {**row["tags"], **row["pending"]}
            for c, k in ((1, "title"), (2, "artist")):
                it.setText(c, eff.get(k, ""))
                f = it.font(c)
                f.setItalic(k in row["pending"])
                it.setFont(c, f)
        else:
            info = row["info"]
            if info:
                if not info.get("has_audio"):
                    txt = tr("info.no_audio")
                else:
                    txt = tr("info.video") if info.get("has_video") else tr("info.audio")
                it.setText(1, f"{txt} · {sec_to_ts(info.get('duration', 0))[:8]}")
            if row["override"] and row["status"] == "pending":
                it.setText(2, f"{tr('status.pending')} · {tr('queue.tags_edited')}")

    def stop_probes(self):
        for w in self._probes:
            w.stop()
            w.wait(2000)

    # ── internals ───────────────────────────────────────────────────────────
    def _on_probed(self, path, info):
        row = self._index.get(os.path.normcase(path))
        if not row:
            return
        if self.kind == "tags":
            row["tags"] = {k: v for k, v in info.items() if k != "has_cover"}
            row["info"] = {"has_cover": info.get("has_cover", False)}
            self.set_status(row, "pending", "")
        else:
            row["info"] = info
        self.refresh_row(row)
        if row["item"].isSelected():
            self.selection_changed.emit()

    def _refresh(self):
        self.stack.setCurrentIndex(1 if self.rows else 0)
        self.lbl_count.setText(tr("queue.count", n=len(self.rows)) if self.rows else "")
        self.changed.emit()

    def _browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, tr("dlg.choose_files"), last_dir(),
                                                media_filter(self.kind))
        if paths:
            self.add_paths(paths)

    def _browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, tr("dlg.choose_folder"), last_dir())
        if d:
            self.add_paths([d])


# ═══════════════════════════════════════════════════════════════════════════════
#  SINGLE FILE PICKER (trim tab)
# ═══════════════════════════════════════════════════════════════════════════════
class FilePicker(QGroupBox):
    loaded = pyqtSignal()

    def __init__(self, label, parent=None):
        super().__init__(label, parent)
        self.file_path = None
        self.media_info = {}
        lay = QHBoxLayout()
        lay.setContentsMargins(14, 14, 14, 10)
        lay.setSpacing(12)
        self.btn = QPushButton(tr("picker.choose"))
        self.btn.setMinimumWidth(120)
        self.btn.setFixedHeight(36)
        self.btn.clicked.connect(self._browse)
        self.lbl = QLabel(tr("picker.none"))
        self.lbl.setStyleSheet("color:#55aaff; font-weight:600;")
        self.lbl.setWordWrap(True)
        self.lbl_meta = QLabel("")
        self.lbl_meta.setStyleSheet("color:#3a6a8a; font-size:11px;")
        self.lbl_meta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_meta.setMinimumWidth(160)
        lay.addWidget(self.btn)
        lay.addWidget(self.lbl, 1)
        lay.addWidget(self.lbl_meta)
        self.setLayout(lay)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("dlg.choose_files"), last_dir(), media_filter("any"))
        if path:
            self.set_file(path)

    def accept_drop(self, paths):
        files = eng.collect_media_files(paths, "any", recursive=False)
        if files:
            self.set_file(files[0])
            return 1
        return 0

    def set_file(self, path):
        remember_dir(path)
        self.file_path = path
        self.media_info = eng.get_media_info(path)
        tag = tr("info.video") if self.media_info.get("has_video") else tr("info.audio")
        self.lbl.setText(os.path.basename(path))
        self.lbl.setToolTip(path)
        self.lbl_meta.setText(f"{tag}  ·  {sec_to_ts(self.media_info.get('duration', 0))}")
        self.loaded.emit()


# ═══════════════════════════════════════════════════════════════════════════════
#  OUTPUT DIR PICKER
# ═══════════════════════════════════════════════════════════════════════════════
class OutputDirPicker(QGroupBox):
    def __init__(self, key, parent=None):
        super().__init__(tr("out.title"), parent)
        self._key = f"output_dir/{key}"
        self._dir = settings().value(self._key, "", type=str) or None
        if self._dir and not os.path.isdir(self._dir):
            self._dir = None
        lay = QHBoxLayout()
        lay.setContentsMargins(14, 14, 14, 10)
        lay.setSpacing(12)
        self.btn = QPushButton(tr("out.choose"))
        self.btn.setMinimumWidth(110)
        self.btn.setFixedHeight(36)
        self.btn.clicked.connect(self._pick)
        self.btn_reset = QPushButton(tr("out.reset"))
        self.btn_reset.setFixedHeight(36)
        self.btn_reset.clicked.connect(lambda: self._set(None))
        self.lbl = QLabel()
        lay.addWidget(self.btn)
        lay.addWidget(self.lbl, 1)
        lay.addWidget(self.btn_reset)
        self.setLayout(lay)
        self._set(self._dir)

    def _pick(self):
        d = QFileDialog.getExistingDirectory(self, tr("dlg.choose_folder"), self._dir or last_dir())
        if d:
            self._set(d)

    def _set(self, d):
        self._dir = d
        settings().setValue(self._key, d or "")
        self.lbl.setText(d or tr("out.same"))
        self.lbl.setStyleSheet(f"color:{'#55aaff' if d else '#3a6a8a'}; font-size:12px;")
        self.btn_reset.setVisible(bool(d))

    def get_dir(self):
        return self._dir


# ═══════════════════════════════════════════════════════════════════════════════
#  FORMAT + CODEC SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
class _Grid(QGridLayout):
    def __init__(self):
        super().__init__()
        self.setHorizontalSpacing(16)
        self.setVerticalSpacing(12)
        self.setColumnStretch(1, 2)
        self.setColumnStretch(3, 2)
        self._row = 0

    def add_row(self, l1, w1, l2=None, w2=None):
        self.addWidget(lbl(l1, 12), self._row, 0)
        self.addWidget(w1, self._row, 1)
        if l2 and w2 is not None:
            self.addWidget(lbl(l2, 12), self._row, 2)
            self.addWidget(w2, self._row, 3)
        self._row += 1


class FormatBox(QGroupBox):
    """Format combo + extension label."""
    format_changed = pyqtSignal(str)

    def __init__(self, title, key, parent=None):
        super().__init__(title, parent)
        self._key = f"format/{key}"
        fl = QHBoxLayout()
        fl.setContentsMargins(14, 14, 14, 10)
        fl.setSpacing(16)
        fl.addWidget(lbl(tr("fmt.format")))
        self.combo = QComboBox()
        self.combo.addItems(list(eng.CODEC_PROFILES.keys()))
        self.combo.setFixedHeight(36)
        self.combo.setMinimumWidth(210)
        saved = settings().value(self._key, "MP3", type=str)
        if saved in eng.CODEC_PROFILES:
            self.combo.setCurrentText(saved)
        self.ext = QLabel()
        self.ext.setStyleSheet("color:#55aaff; font-weight:bold; font-size:13px;")
        fl.addWidget(self.combo)
        fl.addWidget(self.ext)
        fl.addStretch()
        self.setLayout(fl)
        self.combo.currentTextChanged.connect(self._changed)

    def _changed(self, fmt):
        settings().setValue(self._key, fmt)
        self.ext.setText(eng.CODEC_PROFILES.get(fmt, {}).get("ext", ""))
        self.format_changed.emit(fmt)

    def emit_current(self):
        self._changed(self.combo.currentText())

    def current(self):
        return self.combo.currentText()


class CodecSettingsPanel(QGroupBox):
    BITRATES = ["32k", "48k", "64k", "80k", "96k", "112k", "128k", "160k", "192k", "224k", "256k",
                "320k", "384k", "448k", "512k", "640k", "768k", "960k", "1024k", "1152k", "1280k",
                "1411k", "1536k"]

    def __init__(self, parent=None):
        super().__init__(tr("codec.title"), parent)
        self._codec = None
        root = QVBoxLayout()
        root.setContentsMargins(16, 20, 16, 16)
        root.setSpacing(12)

        self.lbl_desc = QLabel("—")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color:#7ec8e3; font-style:italic; font-size:12px;"
                                    "background:rgba(85,170,255,0.07); border-radius:6px; padding:8px 12px;")
        root.addWidget(self.lbl_desc)

        badge_row = QHBoxLayout()
        self.lbl_mode = QLabel("VBR")
        self.lbl_mode.setFixedSize(84, 28)
        self.lbl_mode.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_mode.setStyleSheet("background:rgba(85,170,255,0.18); color:#7ec8e3; font-weight:bold;"
                                    "font-size:12px; border-radius:5px; border:1px solid rgba(85,170,255,0.35);")
        badge_row.addWidget(self.lbl_mode)
        badge_row.addStretch()
        self.btn_rec = QPushButton(tr("codec.reset"))
        self.btn_rec.setFixedHeight(32)
        self.btn_rec.clicked.connect(lambda: self.load_codec(self._codec))
        badge_row.addWidget(self.btn_rec)
        root.addLayout(badge_row)

        H = 36
        self.spin_quality = QSpinBox(); self.spin_quality.setFixedHeight(H); self.spin_quality.setMinimumWidth(150)
        self.combo_br = QComboBox(); self.combo_br.addItems(self.BITRATES); self.combo_br.setFixedHeight(H)
        self.spin_comp = QSpinBox(); self.spin_comp.setRange(0, 12); self.spin_comp.setValue(5)
        self.spin_comp.setSuffix(tr("codec.flac_suffix")); self.spin_comp.setFixedHeight(H)
        self.combo_sr = QComboBox(); self.combo_sr.setFixedHeight(H)
        self.combo_ch = QComboBox(); self.combo_ch.setFixedHeight(H)

        grid = _Grid()
        grid.add_row(tr("codec.quality"), self.spin_quality, tr("codec.bitrate"), self.combo_br)
        grid.add_row(tr("codec.flac"), self.spin_comp, tr("codec.sample_rate"), self.combo_sr)
        grid.add_row(tr("codec.channels"), self.combo_ch)
        root.addLayout(grid)
        self.setLayout(root)

    def load_codec(self, codec_name):
        profile = eng.CODEC_PROFILES.get(codec_name)
        if not profile:
            return
        self._codec = codec_name
        self.lbl_desc.setText(tr(f"codec_desc.{codec_name}"))
        mode = profile["mode"]
        self.lbl_mode.setText(mode.upper())

        if codec_name == "MP3":
            self.spin_quality.setRange(0, 9); self.spin_quality.setSuffix(tr("codec.quality_mp3"))
        else:
            self.spin_quality.setRange(0, 10); self.spin_quality.setSuffix(tr("codec.quality_ogg"))

        for w, en in ((self.spin_quality, mode == "vbr"), (self.combo_br, mode == "cbr"),
                      (self.spin_comp, codec_name == "FLAC")):
            w.setEnabled(en)

        self.combo_sr.clear()
        self.combo_sr.addItems(profile["sample_rates"])
        self.combo_ch.clear()
        for ch in profile["channels"]:
            self.combo_ch.addItem(tr(f"ch.{ch}"), ch)

        rec = profile["recommended"]
        self.spin_quality.setValue(rec.get("quality", profile["quality"] or 5))
        self.spin_comp.setValue(rec.get("compression", 5))
        if profile["bitrate"]:
            self.combo_br.setCurrentText(rec.get("bitrate", profile["bitrate"]))
        if "sample_rate" in rec:
            self.combo_sr.setCurrentText(rec["sample_rate"])
        if "channels" in rec:
            idx = self.combo_ch.findData(rec["channels"])
            if idx >= 0:
                self.combo_ch.setCurrentIndex(idx)

    def get_settings(self):
        return {
            "bitrate": self.combo_br.currentText() if self.combo_br.isEnabled() else None,
            "quality": self.spin_quality.value() if self.spin_quality.isEnabled() else None,
            "compression_level": self.spin_comp.value() if self.spin_comp.isEnabled() else None,
            "sample_rate": self.combo_sr.currentText(),
            "channels": self.combo_ch.currentData(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  WAVEFORM-STYLE TRIM BAR (with playhead)
# ═══════════════════════════════════════════════════════════════════════════════
class TrimBar(QWidget):
    range_changed = pyqtSignal(float, float)
    seek_requested = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._start, self._end, self._playhead = 0.0, 1.0, 0.0
        self._drag = None
        rng = random.Random(42)
        self._bars = [rng.uniform(0.08, 1.0) for _ in range(160)]

    def set_range(self, s, e):
        self._start = max(0.0, min(s, 1.0))
        self._end = max(0.0, min(e, 1.0))
        self.update()

    def set_playhead(self, pct):
        self._playhead = max(0.0, min(pct, 1.0))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(8, 10, 22))
        n = len(self._bars)
        bw = max(1, w / n)
        for i, amp in enumerate(self._bars):
            bh = amp * (h - 20)
            pct = i / n
            if self._start <= pct <= self._end:
                c = QColor(85, 195, 255, 220 if pct <= self._playhead else 160)
            else:
                c = QColor(40, 48, 72, 140)
            p.fillRect(int(i * bw), int((h - bh) / 2), max(1, int(bw) - 1), int(bh), c)
        sx, ex = int(self._start * w), int(self._end * w)
        p.fillRect(sx, 0, ex - sx, h, QColor(85, 195, 255, 18))
        for hx, col in ((sx, QColor(80, 220, 120)), (ex, QColor(220, 100, 80))):
            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(hx - 5, 0, 10, h, 4, 4)
        px = int(self._playhead * w)
        p.setPen(QPen(QColor(255, 220, 60, 230), 2))
        p.drawLine(px, 0, px, h)
        p.setBrush(QBrush(QColor(255, 220, 60, 230)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygon([QPoint(px - 6, 0), QPoint(px + 6, 0), QPoint(px, 10)]))

    def _pct(self, x):
        return max(0.0, min(x / max(self.width(), 1), 1.0))

    def mousePressEvent(self, e):
        pct = self._pct(e.position().x())
        ds, de = abs(pct - self._start), abs(pct - self._end)
        if ds < 0.02 and ds <= de:
            self._drag = "start"
        elif de < 0.02:
            self._drag = "end"
        else:
            self._drag = "seek"
            self._playhead = pct
            self.update()
            self.seek_requested.emit(pct)

    def mouseMoveEvent(self, e):
        if not self._drag:
            return
        pct = self._pct(e.position().x())
        if self._drag == "start":
            self._start = min(pct, self._end - 0.005)
            self.range_changed.emit(self._start, self._end)
        elif self._drag == "end":
            self._end = max(pct, self._start + 0.005)
            self.range_changed.emit(self._start, self._end)
        else:
            self._playhead = pct
            self.seek_requested.emit(pct)
        self.update()

    def mouseReleaseEvent(self, _):
        self._drag = None


# ═══════════════════════════════════════════════════════════════════════════════
#  METADATA FORM
# ═══════════════════════════════════════════════════════════════════════════════
class MetadataForm(QWidget):
    """Edits the common tags of one or more files. Tracks which fields were edited."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.edits = {}
        self._edited = set()
        self._loading = False
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        layout = [("title", 0, 0, 3), ("artist", 1, 0, 3), ("album", 2, 0, 3), ("album_artist", 3, 0, 3),
                  ("date", 4, 0, 1), ("genre", 4, 2, 1), ("track", 5, 0, 1), ("disc", 5, 2, 1),
                  ("composer", 6, 0, 3), ("comment", 7, 0, 3)]
        for field, r, c, span in layout:
            e = QLineEdit()
            e.setFixedHeight(32)
            e.setClearButtonEnabled(True)
            e.textChanged.connect(lambda _t, f=field: None if self._loading else self._mark(f))
            self.edits[field] = e
            grid.addWidget(lbl(tr(f"meta.{field}"), 12), r, c)
            grid.addWidget(e, r, c + 1, 1, span)

    def _mark(self, field):
        self._edited.add(field)
        f = self.edits[field].font()
        f.setBold(True)
        self.edits[field].setFont(f)

    def load(self, tag_dicts):
        """tag_dicts: list of {field: value}. Common values are shown; differing ones get a placeholder."""
        self._edited.clear()
        self._loading = True
        for field, e in self.edits.items():
            vals = {d.get(field, "") for d in tag_dicts} if tag_dicts else {""}
            f = e.font(); f.setBold(False); e.setFont(f)
            if len(vals) == 1:
                e.setText(vals.pop())
                e.setPlaceholderText("")
            else:
                e.setText("")
                e.setPlaceholderText(tr("meta.multiple"))
        self._loading = False
        self.setEnabled(bool(tag_dicts))

    def set_field(self, field, value):
        """Programmatic edit that counts as a user change."""
        self.edits[field].setText(value)
        self._mark(field)

    def changes(self):
        return {f: self.edits[f].text().strip() for f in self._edited}


class MetadataDialog(QDialog):
    """Pick tag overrides for files that are about to be converted."""

    def __init__(self, tag_dicts, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("meta.dialog_title"))
        self.resize(640, 460)
        lay = QVBoxLayout(self)
        hint = QLabel(tr("meta.dialog_hint") + "\n" + tr("meta.editing", n=len(tag_dicts)))
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#7ec8e3; font-size:12px;")
        lay.addWidget(hint)
        self.form = MetadataForm()
        self.form.load(tag_dicts)
        lay.addWidget(self.form, 1)
        row = QHBoxLayout()
        row.addStretch()
        b_cancel, b_ok = QPushButton(tr("meta.cancel")), QPushButton(tr("meta.apply"))
        b_cancel.clicked.connect(self.reject)
        b_ok.clicked.connect(self.accept)
        b_ok.setDefault(True)
        row.addWidget(b_cancel)
        row.addWidget(b_ok)
        lay.addLayout(row)


# ═══════════════════════════════════════════════════════════════════════════════
#  FILE-NAME PARSING (for "Fill from file name")
# ═══════════════════════════════════════════════════════════════════════════════
_TRACK_RE = re.compile(r"^\s*(\d{1,3})\s*[-._)\]]?\s+(.*)$")


def tags_from_filename(path):
    name = os.path.splitext(os.path.basename(path))[0].replace("_", " ").strip()
    out = {}
    m = _TRACK_RE.match(name)
    if m:
        out["track"] = str(int(m.group(1)))
        name = m.group(2).strip()
    parts = [p.strip() for p in re.split(r"\s+[-–—]\s+", name) if p.strip()]
    if len(parts) >= 2:
        out["artist"] = parts[0]
        out["title"] = " - ".join(parts[1:])
    elif parts:
        out["title"] = parts[0]
    return out


def pixmap_label(path, size=150):
    pm = QPixmap(path)
    if pm.isNull():
        return None
    return pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
