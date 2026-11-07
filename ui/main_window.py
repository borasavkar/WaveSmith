import os
import sys
import tempfile

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QFileDialog, QLineEdit, QCheckBox, QMessageBox, QGroupBox, QFrame, QProgressBar,
    QTabWidget, QScrollArea, QSlider, QDoubleSpinBox, QApplication, QSplitter,
)

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    _MULTIMEDIA_OK = True
except Exception:
    _MULTIMEDIA_OK = False

from core import APP_NAME, __version__
from core import ffmpeg_engine as eng
from core.i18n import tr, set_language, current_language, LANGUAGES
from core.settings import settings
from ui.widgets import (
    FileQueue, FilePicker, OutputDirPicker, FormatBox, CodecSettingsPanel, TrimBar,
    MetadataForm, MetadataDialog, tags_from_filename, pixmap_label,
    sec_to_ts, ts_to_sec, open_folder_select, lbl, vsep, show_error_dialog, last_dir,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  GENERIC JOB WORKER
# ═══════════════════════════════════════════════════════════════════════════════
class JobWorker(QThread):
    """Runs jobs sequentially. Each job is (key, fn); fn(on_progress, should_cancel) -> result."""
    item_started = pyqtSignal(object)
    item_progress = pyqtSignal(object, float)
    item_done = pyqtSignal(object, object)
    item_failed = pyqtSignal(object, str)
    cancelled = pyqtSignal()

    def __init__(self, jobs):
        super().__init__()
        self.jobs = jobs
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        for key, fn in self.jobs:
            if self._cancel:
                break
            self.item_started.emit(key)
            try:
                res = fn(lambda f, k=key: self.item_progress.emit(k, f), lambda: self._cancel)
                self.item_done.emit(key, res)
            except eng.Cancelled:
                break
            except eng.FFmpegNotFound:
                self.item_failed.emit(key, tr("app.ffmpeg_missing"))
            except Exception as e:
                self.item_failed.emit(key, str(e))
        if self._cancel:
            self.cancelled.emit()


CONVERT_BTN_STYLE = """
    QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1a78c2,stop:1 #0f4d8a);
        border: 1px solid rgba(85,170,255,0.55); color:#fff; font-size:14px; font-weight:bold; border-radius:10px; }
    QPushButton:hover  { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #2a8ae0,stop:1 #1860a8); }
    QPushButton:pressed { background:#0d3e72; }
    QPushButton:disabled { background:rgba(30,40,55,0.6); color:#334455; border-color:rgba(85,170,255,0.1); }
"""
SECONDARY_RED = """
    QPushButton { background: rgba(220,100,60,0.18); border:1px solid rgba(220,100,60,0.45);
        color:#ffb090; font-size:13px; font-weight:bold; border-radius:9px; }
    QPushButton:hover { background:rgba(220,100,60,0.35); }
"""
GREEN_BTN = ("QPushButton { background:rgba(60,200,100,0.18); border:1px solid rgba(60,200,100,0.45);"
             "color:#80ffb0; border-radius:8px; font-weight:bold; font-size:13px; }"
             "QPushButton:hover { background:rgba(60,200,100,0.35); }")
AMBER_BTN = ("QPushButton { background:rgba(255,180,40,0.2); border:1px solid rgba(255,180,40,0.45);"
             "color:#ffd840; border-radius:8px; font-weight:bold; font-size:13px; }"
             "QPushButton:hover { background:rgba(255,180,40,0.35); }")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):

    SS = """
        QMainWindow { background:#0c0e1b; }
        QWidget { background:transparent; color:#cce0f5;
                  font-family:'Segoe UI','SF Pro Text',Helvetica,sans-serif; font-size:13px; }
        QTabWidget::pane { border:1px solid rgba(85,170,255,0.18); border-radius:12px;
                           background:rgba(255,255,255,0.025); margin-top:-1px; }
        QTabBar::tab { background:rgba(255,255,255,0.04); color:#5a7a9a; padding:11px 24px; margin-right:3px;
                       border-top-left-radius:9px; border-top-right-radius:9px; font-weight:600; font-size:13px;
                       border:1px solid transparent; border-bottom:none; }
        QTabBar::tab:selected { background:rgba(85,170,255,0.14); color:#c8e4ff; border-color:rgba(85,170,255,0.28); }
        QTabBar::tab:hover:!selected { background:rgba(85,170,255,0.07); color:#90b8d8; }
        QGroupBox { border:1px solid rgba(85,170,255,0.16); border-radius:10px; margin-top:14px;
                    padding:12px 14px 12px 14px; background:rgba(255,255,255,0.028); }
        QGroupBox::title { subcontrol-origin:margin; left:14px; color:#4a7a9e; font-weight:bold; font-size:12px; }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background:rgba(6,8,20,0.75); border:1px solid rgba(85,170,255,0.28); border-radius:7px;
            color:#d8eeff; padding:5px 10px; font-size:13px; selection-background-color:rgba(85,170,255,0.4); }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color:rgba(85,170,255,0.65); }
        QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { color:#2a3a4a; background:rgba(0,0,0,0.25); }
        QComboBox::drop-down { border:none; width:22px; }
        QComboBox QAbstractItemView { background:#101320; color:#d0e4f5; selection-background-color:rgba(85,170,255,0.3);
                                      border:1px solid rgba(85,170,255,0.22); }
        QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            width:22px; background:rgba(85,170,255,0.1); border:none; border-radius:3px; }
        QPushButton { background:rgba(85,170,255,0.1); border:1px solid rgba(85,170,255,0.3); color:#b8d8f5;
                      padding:7px 14px; border-radius:8px; font-weight:600; }
        QPushButton:hover { background:rgba(85,170,255,0.24); border-color:rgba(85,170,255,0.6); }
        QPushButton:pressed { background:rgba(85,170,255,0.42); }
        QPushButton:disabled { color:#2a3a4a; border-color:rgba(85,170,255,0.08); }
        QCheckBox { color:#8ab0cc; spacing:8px; }
        QCheckBox::indicator { width:18px; height:18px; border:1px solid rgba(85,170,255,0.38); border-radius:5px;
                               background:rgba(0,0,0,0.4); }
        QCheckBox::indicator:checked { background:#2f8fff; border-color:#8cc8ff; image:url(%CHECK%); }
        QProgressBar { border:1px solid rgba(85,170,255,0.2); border-radius:6px; background:rgba(0,0,0,0.3);
                       text-align:center; color:#cfe4f7; min-height:20px; }
        QProgressBar::chunk { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0e5ca8,stop:1 #3399ff);
                              border-radius:5px; }
        QSlider::groove:horizontal { height:4px; background:rgba(85,170,255,0.18); border-radius:2px; }
        QSlider::handle:horizontal { width:14px; height:14px; margin:-5px 0; background:#55aaff; border-radius:7px; }
        QSlider::sub-page:horizontal { background:rgba(85,170,255,0.5); border-radius:2px; }
        QTreeWidget { background:rgba(6,8,20,0.6); border:1px solid rgba(85,170,255,0.2); border-radius:8px;
                      color:#cfe4f7; outline:0; }
        QTreeWidget::item { padding:4px 2px; }
        QTreeWidget::item:selected { background:rgba(85,170,255,0.28); color:#ffffff; }
        QHeaderView::section { background:rgba(85,170,255,0.08); color:#7ea8cc; border:none;
                               border-right:1px solid rgba(85,170,255,0.12); padding:5px 8px; font-weight:600; }
        QFrame[frameShape="4"] { color:rgba(85,170,255,0.1); }
        QLabel { color:#88a8c8; }
        QScrollArea { border:none; background:transparent; }
        QScrollBar:vertical { background:#0a0c1a; width:8px; border-radius:4px; }
        QScrollBar::handle:vertical { background:rgba(85,170,255,0.28); border-radius:4px; min-height:30px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        QSplitter::handle { background:rgba(85,170,255,0.08); }
        QToolTip { background:#101320; color:#d0e4f5; border:1px solid rgba(85,170,255,0.35); }
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  {__version__}")
        self.setMinimumSize(960, 720)
        self.resize(1180, 880)
        check = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                             "assets", "check.svg").replace("\\", "/")
        self.setStyleSheet(self.SS.replace("%CHECK%", check))
        self.setAcceptDrops(True)
        self._workers = {}            # tag -> JobWorker
        self._trim_player = None
        self._trim_audio = None
        self._player_ok = False
        self._build_ui()

    # ── MASTER LAYOUT ──────────────────────────────────────────────────────
    def _build_ui(self, restore=None):
        root = QWidget()
        root.setStyleSheet("background:#0c0e1b;")
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(22, 16, 22, 16)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        ttl = QLabel(f"🎚  {APP_NAME}")
        ttl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        ttl.setStyleSheet("color:#55aaff; letter-spacing:1px;")
        hdr.addWidget(ttl)
        sub = QLabel(tr("app.tagline"))
        sub.setStyleSheet("color:#3f6a8e; font-size:12px; padding-left:10px;")
        hdr.addWidget(sub)
        hdr.addStretch()
        hdr.addWidget(lbl(tr("app.language"), 12))
        self.lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self.lang_combo.addItem(name, code)
        self.lang_combo.setCurrentIndex(self.lang_combo.findData(current_language()))
        self.lang_combo.setFixedHeight(32)
        self.lang_combo.currentIndexChanged.connect(self._language_changed)
        hdr.addWidget(self.lang_combo)
        lay.addLayout(hdr)

        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(div)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        lay.addWidget(self.tabs, 1)
        self.tabs.addTab(self._scroll(self._tab_convert()), tr("tab.convert"))
        self.tabs.addTab(self._scroll(self._tab_trim()), tr("tab.trim"))
        self.tabs.addTab(self._scroll(self._tab_extract()), tr("tab.extract"))
        self.tabs.addTab(self._tab_metadata(), tr("tab.metadata"))

        # Drop overlay
        self._overlay = QLabel("⬇\n" + tr("app.drop_overlay"), root)
        self._overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay.setStyleSheet("background:rgba(12,40,80,0.82); color:#cfe8ff; font-size:22px;"
                                    "font-weight:bold; border:3px dashed #55aaff; border-radius:16px;")
        self._overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._overlay.hide()

        # Text fields would otherwise swallow file drops as plain text
        for w in root.findChildren(QLineEdit):
            w.setAcceptDrops(False)

        if restore:
            self.c_queue.add_paths(restore.get("c", []))
            self.e_queue.add_paths(restore.get("e", []))
            self.m_queue.add_paths(restore.get("m", []))
            if restore.get("t"):
                self.t_picker.set_file(restore["t"])
            self.tabs.setCurrentIndex(restore.get("tab", 0))
        else:
            self.tabs.setCurrentIndex(settings().value("tab", 0, type=int))
        self.tabs.currentChanged.connect(lambda i: settings().setValue("tab", i))

    @staticmethod
    def _scroll(inner):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner.setStyleSheet("background:transparent;")
        scroll.setWidget(inner)
        return scroll

    # ── LANGUAGE ───────────────────────────────────────────────────────────
    def _language_changed(self, _idx):
        code = self.lang_combo.currentData()
        if code == current_language():
            return
        if self._busy():
            QMessageBox.information(self, tr("app.busy_title"), tr("app.lang_busy"))
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(self.lang_combo.findData(current_language()))
            self.lang_combo.blockSignals(False)
            return
        restore = {"c": self.c_queue.paths(), "e": self.e_queue.paths(), "m": self.m_queue.paths(),
                   "t": self.t_picker.file_path, "tab": self.tabs.currentIndex()}
        self._shutdown_children()
        set_language(code)
        settings().setValue("language", code)
        QTimer.singleShot(0, lambda: self._build_ui(restore))

    def _busy(self):
        return any(w.isRunning() for w in self._workers.values())

    def _shutdown_children(self):
        for q in (self.c_queue, self.e_queue, self.m_queue):
            q.stop_probes()
        if self._trim_player:
            self._trim_player.stop()
            self._trim_player.setSource(QUrl())
            self._trim_player.deleteLater()
            self._trim_audio.deleteLater()
        self._trim_player = self._trim_audio = None
        self._player_ok = False

    def closeEvent(self, e):
        for w in self._workers.values():
            w.cancel()
        for w in self._workers.values():
            w.wait(5000)
        self._shutdown_children()
        settings().sync()
        super().closeEvent(e)

    # ── DRAG & DROP ────────────────────────────────────────────────────────
    def _drop_target(self):
        i = self.tabs.currentIndex()
        target = [self.c_queue, self.t_picker, self.e_queue, self.m_queue][i]
        if isinstance(target, FileQueue) and target.is_locked():
            return None
        if i == 1 and self._workers.get("t") and self._workers["t"].isRunning():
            return None
        return target

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and self._drop_target() is not None:
            e.acceptProposedAction()
            self._overlay.setGeometry(self.centralWidget().rect().adjusted(10, 10, -10, -10))
            self._overlay.raise_()
            self._overlay.show()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._overlay.hide()

    def dropEvent(self, e):
        self._overlay.hide()
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        target = self._drop_target()
        if not paths or target is None:
            return
        e.acceptProposedAction()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            added = target.accept_drop(paths) if isinstance(target, FilePicker) else target.add_paths(paths)
        finally:
            QApplication.restoreOverrideCursor()
        if not added and not (isinstance(target, FileQueue) and target.rows):
            QMessageBox.information(self, APP_NAME, tr("queue.none_added"))

    # ════════════════════════════════════════════════════════════════════════
    #  SHARED BUILDING BLOCKS
    # ════════════════════════════════════════════════════════════════════════
    def _fx_box(self, prefix, with_cover):
        box = QGroupBox(tr("fx.title"))
        v = QVBoxLayout(); v.setContentsMargins(14, 14, 14, 10); v.setSpacing(10)
        row = QHBoxLayout(); row.setSpacing(24)
        fi, fo = QCheckBox(tr("fx.fade_in")), QCheckBox(tr("fx.fade_out"))
        dur = QDoubleSpinBox()
        dur.setRange(0.1, 60.0); dur.setSingleStep(0.5); dur.setDecimals(1)
        dur.setValue(settings().value("fade_len", 3.0, type=float))
        dur.setSuffix(tr("fx.seconds")); dur.setFixedHeight(32); dur.setMinimumWidth(100)
        dur.valueChanged.connect(lambda val: settings().setValue("fade_len", val))
        row.addWidget(fi); row.addWidget(fo); row.addSpacing(10)
        row.addWidget(lbl(tr("fx.fade_len"), 12)); row.addWidget(dur); row.addStretch()
        v.addLayout(row)
        cover = None
        if with_cover:
            cover = QCheckBox(tr("fx.keep_cover"))
            cover.setChecked(settings().value("keep_cover", True, type=bool))
            cover.toggled.connect(lambda val: settings().setValue("keep_cover", val))
            v.addWidget(cover)
        box.setLayout(v)
        setattr(self, f"{prefix}_fi", fi)
        setattr(self, f"{prefix}_fo", fo)
        setattr(self, f"{prefix}_fade_len", dur)
        setattr(self, f"{prefix}_cover", cover)
        return box

    def _action_row(self, parent_lay, tag, btn_text, slot):
        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        parent_lay.addWidget(div)
        row = QHBoxLayout(); row.setSpacing(12)
        prog = QProgressBar(); prog.setRange(0, 1000); prog.setVisible(False); prog.setFixedHeight(22)
        row.addWidget(prog, 1)
        retry = QPushButton(tr("action.retry")); retry.setMinimumHeight(48); retry.setStyleSheet(SECONDARY_RED)
        retry.setVisible(False)
        cancel = QPushButton(tr("action.cancel")); cancel.setMinimumHeight(48); cancel.setMinimumWidth(120)
        cancel.setStyleSheet(SECONDARY_RED); cancel.setVisible(False)
        cancel.clicked.connect(lambda: self._workers.get(tag) and self._workers[tag].cancel())
        btn = QPushButton(btn_text); btn.setMinimumHeight(48); btn.setMinimumWidth(200)
        btn.setStyleSheet(CONVERT_BTN_STYLE); btn.clicked.connect(slot)
        row.addWidget(retry); row.addWidget(cancel); row.addWidget(btn)
        parent_lay.addLayout(row)
        status = QLabel("")
        status.setStyleSheet("color:#3a7a9a; font-size:11px;")
        status.setWordWrap(True)
        status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        parent_lay.addWidget(status)
        setattr(self, f"_{tag}_ui", {"prog": prog, "retry": retry, "cancel": cancel, "btn": btn, "status": status})

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 1 — CONVERT (batch)
    # ════════════════════════════════════════════════════════════════════════
    def _tab_convert(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(12)
        self.c_queue = FileQueue(tr("queue.title"), kind="any", tag_button=True)
        self.c_queue.btn_tags.clicked.connect(self._c_edit_tags)
        lay.addWidget(self.c_queue)
        self.c_fmt = FormatBox(tr("fmt.target"), "convert")
        lay.addWidget(self.c_fmt)
        self.c_codec = CodecSettingsPanel()
        lay.addWidget(self.c_codec)
        self.c_fmt.format_changed.connect(self.c_codec.load_codec)
        self.c_fmt.emit_current()
        lay.addWidget(self._fx_box("c", with_cover=True))
        self.c_outdir = OutputDirPicker("convert")
        lay.addWidget(self.c_outdir)
        self._action_row(lay, "c", tr("convert.button"), lambda: self._run_batch("c"))
        return w

    def _c_edit_tags(self):
        rows = self.c_queue.selected_rows() or self.c_queue.rows
        if not rows:
            QMessageBox.warning(self, tr("msg.no_files_title"), tr("msg.no_files"))
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            dicts = []
            for r in rows:
                t = eng.read_metadata(r["path"]); t.pop("has_cover", None)
                t.update(r["override"])
                dicts.append(t)
        finally:
            QApplication.restoreOverrideCursor()
        dlg = MetadataDialog(dicts, self)
        if dlg.exec():
            ch = dlg.form.changes()
            for r in rows:
                r["override"].update(ch)
                self.c_queue.refresh_row(r)

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 2 — TRIM (single file, with playback)
    # ════════════════════════════════════════════════════════════════════════
    def _tab_trim(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(12)
        self.t_picker = FilePicker(tr("picker.title"))
        self.t_picker.loaded.connect(self._trim_loaded)
        lay.addWidget(self.t_picker)

        pb_box = QGroupBox(tr("trim.player"))
        pb = QVBoxLayout(); pb.setContentsMargins(14, 14, 14, 14); pb.setSpacing(10)
        self.t_bar = TrimBar()
        self.t_bar.range_changed.connect(self._trim_bar_moved)
        self.t_bar.seek_requested.connect(self._trim_seek)
        pb.addWidget(self.t_bar)

        time_row = QHBoxLayout()
        self.t_pos_lbl = QLabel("00:00:00.000")
        self.t_pos_lbl.setStyleSheet("color:#ffd840; font-size:12px; font-weight:bold; min-width:85px;")
        time_row.addWidget(self.t_pos_lbl); time_row.addStretch()
        self.t_dur_lbl = QLabel(tr("trim.duration_none"))
        self.t_dur_lbl.setStyleSheet("color:#3a7a9a; font-size:12px;")
        time_row.addWidget(self.t_dur_lbl)
        pb.addLayout(time_row)

        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        self.t_btn_play = QPushButton(tr("trim.play"))
        self.t_btn_play.setFixedHeight(38); self.t_btn_play.setMinimumWidth(120)
        self.t_btn_play.setStyleSheet(GREEN_BTN)
        self.t_btn_play.clicked.connect(self._trim_toggle_play)
        btn_row.addWidget(self.t_btn_play)
        btn_row.addWidget(vsep())
        self.t_btn_set_start = QPushButton(tr("trim.set_start"))
        self.t_btn_set_start.setFixedHeight(38)
        self.t_btn_set_start.setToolTip(tr("trim.set_start_tip"))
        self.t_btn_set_start.clicked.connect(self._trim_set_start_here)
        self.t_btn_set_end = QPushButton(tr("trim.set_end"))
        self.t_btn_set_end.setFixedHeight(38)
        self.t_btn_set_end.setToolTip(tr("trim.set_end_tip"))
        self.t_btn_set_end.clicked.connect(self._trim_set_end_here)
        btn_row.addWidget(self.t_btn_set_start); btn_row.addWidget(self.t_btn_set_end)
        btn_row.addStretch()
        btn_row.addWidget(lbl(tr("trim.volume"), 12))
        self.t_vol = QSlider(Qt.Orientation.Horizontal)
        self.t_vol.setRange(0, 100); self.t_vol.setValue(80); self.t_vol.setFixedWidth(120)
        self.t_vol.valueChanged.connect(self._trim_set_vol)
        btn_row.addWidget(self.t_vol)
        pb.addLayout(btn_row)

        manual = QHBoxLayout(); manual.setSpacing(14)
        manual.addWidget(lbl(tr("trim.start")))
        self.t_start = QLineEdit("00:00:00.000")
        self.t_start.setFixedHeight(34); self.t_start.setMaximumWidth(150)
        self.t_start.textEdited.connect(self._trim_time_typed)
        manual.addWidget(self.t_start)
        manual.addWidget(lbl(tr("trim.end")))
        self.t_end = QLineEdit("00:00:00.000")
        self.t_end.setFixedHeight(34); self.t_end.setMaximumWidth(150)
        self.t_end.textEdited.connect(self._trim_time_typed)
        manual.addWidget(self.t_end); manual.addStretch()
        pb.addLayout(manual)
        pb_box.setLayout(pb)
        lay.addWidget(pb_box)

        self.t_fmt = FormatBox(tr("fmt.output"), "trim")
        lay.addWidget(self.t_fmt)
        self.t_codec = CodecSettingsPanel()
        lay.addWidget(self.t_codec)
        self.t_fmt.format_changed.connect(self.t_codec.load_codec)
        self.t_fmt.emit_current()
        lay.addWidget(self._fx_box("t", with_cover=True))
        self.t_outdir = OutputDirPicker("trim")
        lay.addWidget(self.t_outdir)
        self._action_row(lay, "t", tr("trim.button"), self._run_trim)
        return w

    def _init_player(self):
        if self._player_ok:
            return True
        if not _MULTIMEDIA_OK:
            self._player_warn()
            return False
        try:
            self._trim_player = QMediaPlayer()
            self._trim_audio = QAudioOutput()
            self._trim_audio.setVolume(self.t_vol.value() / 100.0)
            self._trim_player.setAudioOutput(self._trim_audio)
            self._trim_player.positionChanged.connect(self._trim_pos_changed)
            self._trim_player.playbackStateChanged.connect(self._trim_state_changed)
            self._player_ok = True
            return True
        except Exception as ex:
            self._player_warn(str(ex))
            return False

    def _player_warn(self, detail=""):
        for b in (self.t_btn_play, self.t_btn_set_start, self.t_btn_set_end):
            b.setEnabled(False)
        self.t_btn_play.setText(tr("trim.no_player"))
        if detail:
            self.t_dur_lbl.setText(tr("trim.no_backend", d=detail[:60]))

    def _trim_loaded(self):
        dur = self.t_picker.media_info.get("duration", 0)
        self.t_start.setText("00:00:00.000")
        self.t_end.setText(sec_to_ts(dur))
        self.t_bar.set_range(0.0, 1.0)
        self.t_bar.set_playhead(0.0)
        self.t_dur_lbl.setText(tr("trim.duration", d=sec_to_ts(dur)) if dur else tr("trim.duration_none"))
        if self.t_picker.file_path and self._init_player():
            self._trim_player.stop()
            self._trim_player.setSource(QUrl.fromLocalFile(self.t_picker.file_path))

    def _trim_toggle_play(self):
        if not self.t_picker.file_path or not self._init_player():
            return
        if self._trim_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._trim_player.pause()
        else:
            self._trim_player.play()

    def _trim_state_changed(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.t_btn_play.setText(tr("trim.pause") if playing else tr("trim.play"))
        self.t_btn_play.setStyleSheet(AMBER_BTN if playing else GREEN_BTN)

    def _trim_pos_changed(self, ms):
        dur = self.t_picker.media_info.get("duration", 0)
        sec = ms / 1000.0
        self.t_pos_lbl.setText(sec_to_ts(sec))
        if dur:
            self.t_bar.set_playhead(sec / dur)

    def _trim_seek(self, pct):
        dur = self.t_picker.media_info.get("duration", 0)
        if self._player_ok and dur:
            self._trim_player.setPosition(int(pct * dur * 1000))

    def _trim_set_vol(self, v):
        if self._trim_audio:
            self._trim_audio.setVolume(v / 100.0)

    def _trim_set_start_here(self):
        if self._player_ok:
            self.t_start.setText(sec_to_ts(self._trim_player.position() / 1000.0))
            self._trim_time_typed()

    def _trim_set_end_here(self):
        if self._player_ok:
            self.t_end.setText(sec_to_ts(self._trim_player.position() / 1000.0))
            self._trim_time_typed()

    def _trim_bar_moved(self, s, e):
        dur = self.t_picker.media_info.get("duration", 0)
        if dur:
            self.t_start.setText(sec_to_ts(s * dur))
            self.t_end.setText(sec_to_ts(e * dur))

    def _trim_time_typed(self, *_):
        dur = self.t_picker.media_info.get("duration", 0)
        if not dur:
            return
        try:
            self.t_bar.set_range(ts_to_sec(self.t_start.text()) / dur, ts_to_sec(self.t_end.text()) / dur)
        except ValueError:
            pass

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 3 — EXTRACT (batch)
    # ════════════════════════════════════════════════════════════════════════
    def _tab_extract(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(12)
        banner = QLabel(tr("extract.banner"))
        banner.setWordWrap(True)
        banner.setStyleSheet("background:rgba(85,170,255,0.07); border:1px solid rgba(85,170,255,0.18);"
                             "border-radius:8px; color:#7ec8e3; font-size:12px; padding:10px 14px;")
        lay.addWidget(banner)
        self.e_queue = FileQueue(tr("queue.title_video"), kind="video")
        lay.addWidget(self.e_queue)

        mode_box = QGroupBox(tr("extract.mode"))
        ml = QVBoxLayout(); ml.setContentsMargins(14, 14, 14, 12); ml.setSpacing(10)
        self.e_native = QCheckBox(tr("extract.native"))
        self.e_native.setChecked(settings().value("extract_native", True, type=bool))
        self.e_native.setStyleSheet("color:#7ec8e3; font-size:13px; font-weight:600;")
        ml.addWidget(self.e_native)
        mode_box.setLayout(ml)
        lay.addWidget(mode_box)

        self.e_fmt = FormatBox(tr("extract.reencode"), "extract")
        lay.addWidget(self.e_fmt)
        self.e_codec = CodecSettingsPanel()
        lay.addWidget(self.e_codec)
        self.e_fmt.format_changed.connect(self.e_codec.load_codec)
        self.e_fmt.emit_current()
        self.e_outdir = OutputDirPicker("extract")
        lay.addWidget(self.e_outdir)
        lay.addStretch()
        self._action_row(lay, "e", tr("extract.button"), lambda: self._run_batch("e"))

        def mode_changed(native):
            settings().setValue("extract_native", native)
            self.e_fmt.setVisible(not native)
            self.e_codec.setVisible(not native)
        self.e_native.toggled.connect(mode_changed)
        mode_changed(self.e_native.isChecked())
        return w

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 4 — METADATA
    # ════════════════════════════════════════════════════════════════════════
    def _tab_metadata(self):
        w = QWidget()
        outer = QVBoxLayout(w); outer.setContentsMargins(16, 16, 16, 16); outer.setSpacing(12)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)

        self.m_queue = FileQueue(tr("meta.files"), kind="tags")
        self.m_queue.selection_changed.connect(self._m_selection)
        self.m_queue.changed.connect(self._m_selection)
        split.addWidget(self.m_queue)

        right = QGroupBox(tr("meta.editor"))
        rl = QVBoxLayout(); rl.setContentsMargins(14, 18, 14, 12); rl.setSpacing(10)
        self.m_hint = QLabel(tr("meta.select_hint"))
        self.m_hint.setWordWrap(True)
        self.m_hint.setStyleSheet("color:#7ec8e3; font-size:12px;")
        rl.addWidget(self.m_hint)
        self.m_form = MetadataForm()
        rl.addWidget(self.m_form)

        cover_row = QHBoxLayout(); cover_row.setSpacing(12)
        self.m_cover = QLabel(tr("meta.no_cover"))
        self.m_cover.setFixedSize(150, 150)
        self.m_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.m_cover.setStyleSheet("border:1px dashed rgba(85,170,255,0.3); border-radius:8px; color:#4a7a9e;")
        cover_row.addWidget(self.m_cover)
        cb = QVBoxLayout(); cb.setSpacing(8)
        cb.addWidget(QLabel(tr("meta.cover")))
        self.m_btn_cover = QPushButton(tr("meta.cover_choose"))
        self.m_btn_cover_rm = QPushButton(tr("meta.cover_remove"))
        self.m_btn_cover_ex = QPushButton(tr("meta.cover_export"))
        for b in (self.m_btn_cover, self.m_btn_cover_rm, self.m_btn_cover_ex):
            cb.addWidget(b)
        cb.addStretch()
        cover_row.addLayout(cb)
        cover_row.addStretch()
        rl.addLayout(cover_row)

        tools = QHBoxLayout(); tools.setSpacing(8)
        self.m_btn_fname = QPushButton(tr("meta.from_filename"))
        self.m_btn_fname.setToolTip(tr("meta.from_filename_tip"))
        self.m_btn_track = QPushButton(tr("meta.auto_track"))
        self.m_btn_track.setToolTip(tr("meta.auto_track_tip"))
        self.m_btn_revert = QPushButton(tr("meta.revert"))
        tools.addWidget(self.m_btn_fname); tools.addWidget(self.m_btn_track)
        tools.addStretch(); tools.addWidget(self.m_btn_revert)
        rl.addLayout(tools)
        rl.addStretch()
        right.setLayout(rl)

        rscroll = QScrollArea(); rscroll.setWidgetResizable(True); rscroll.setFrameShape(QFrame.Shape.NoFrame)
        rscroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rscroll.setWidget(right)
        split.addWidget(rscroll)
        split.setStretchFactor(0, 1); split.setStretchFactor(1, 1)
        split.setSizes([560, 560])
        outer.addWidget(split, 1)
        self._action_row(outer, "m", tr("meta.save"), self._m_save)

        self._m_cover_action = None      # None | ("set", path) | ("remove",)
        self._m_tmpdir = tempfile.mkdtemp(prefix="wavesmith-")
        self.m_btn_cover.clicked.connect(self._m_choose_cover)
        self.m_btn_cover_rm.clicked.connect(self._m_remove_cover)
        self.m_btn_cover_ex.clicked.connect(self._m_export_cover)
        self.m_btn_fname.clicked.connect(self._m_from_filename)
        self.m_btn_track.clicked.connect(self._m_number_tracks)
        self.m_btn_revert.clicked.connect(self._m_revert)
        self._m_selection()
        return w

    def _m_rows(self):
        return self.m_queue.selected_rows()

    def _m_selection(self):
        rows = self._m_rows()
        busy = self._workers.get("m") is not None and self._workers["m"].isRunning()
        self.m_form.load([{**r["tags"], **r["pending"]} for r in rows])
        self.m_form.setEnabled(bool(rows) and not busy)
        self._m_cover_action = None
        self.m_hint.setText(tr("meta.editing", n=len(rows)) if rows else tr("meta.select_hint"))
        cover_ok = bool(rows) and all(eng.supports_cover(r["path"]) for r in rows)
        for b in (self.m_btn_cover, self.m_btn_cover_rm):
            b.setEnabled(cover_ok and not busy)
            b.setToolTip("" if cover_ok else tr("meta.cover_unsupported"))
        single_cover = len(rows) == 1 and rows[0]["info"].get("has_cover")
        self.m_btn_cover_ex.setEnabled(bool(single_cover))
        for b in (self.m_btn_fname, self.m_btn_track, self.m_btn_revert):
            b.setEnabled(bool(rows) and not busy)
        self._m_show_cover(rows)

    def _m_show_cover(self, rows):
        self.m_cover.setPixmap(QPixmap_empty())
        if self._m_cover_action and self._m_cover_action[0] == "set":
            pm = pixmap_label(self._m_cover_action[1])
            if pm:
                self.m_cover.setPixmap(pm)
                return
            self.m_cover.setText(tr("meta.cover_new"))
            return
        if self._m_cover_action and self._m_cover_action[0] == "remove":
            self.m_cover.setText(tr("meta.cover_removed"))
            return
        if len(rows) == 1 and rows[0]["info"].get("has_cover"):
            out = os.path.join(self._m_tmpdir, f"cover-{abs(hash(rows[0]['path']))}.png")
            if os.path.exists(out) or eng.extract_cover(rows[0]["path"], out):
                pm = pixmap_label(out)
                if pm:
                    self.m_cover.setPixmap(pm)
                    return
        self.m_cover.setText(tr("meta.cover_multi") if len(rows) > 1 else tr("meta.no_cover"))

    def _m_choose_cover(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("meta.cover_choose"), last_dir(),
                                              f"{tr('filter.images')} (*.jpg *.jpeg *.png)")
        if path:
            self._m_cover_action = ("set", path)
            self._m_show_cover(self._m_rows())

    def _m_remove_cover(self):
        self._m_cover_action = ("remove",)
        self._m_show_cover(self._m_rows())

    def _m_export_cover(self):
        rows = self._m_rows()
        if len(rows) != 1:
            return
        base = os.path.splitext(rows[0]["path"])[0] + "_cover.png"
        path, _ = QFileDialog.getSaveFileName(self, tr("meta.cover_export"), base,
                                              f"{tr('filter.images')} (*.png *.jpg)")
        if path:
            if eng.extract_cover(rows[0]["path"], path):
                open_folder_select(path)

    def _m_from_filename(self):
        for r in self._m_rows():
            r["pending"].update(tags_from_filename(r["path"]))
            self.m_queue.refresh_row(r)
        self._m_selection()

    def _m_number_tracks(self):
        rows = self._m_rows()
        order = [r for r in self.m_queue.rows if r in rows]
        for i, r in enumerate(order, 1):
            r["pending"]["track"] = str(i)
            self.m_queue.refresh_row(r)
        self._m_selection()

    def _m_revert(self):
        for r in self._m_rows():
            r["pending"].clear()
            self.m_queue.refresh_row(r)
        self._m_selection()

    def _m_save(self):
        sel = self._m_rows()
        form_changes = self.m_form.changes()
        cover = self._m_cover_action
        targets = []
        for r in self.m_queue.rows:
            changes = dict(r["pending"])
            if r in sel:
                changes.update(form_changes)
            r_cover = cover if r in sel else None
            if changes or r_cover:
                targets.append((r, changes, r_cover))
        ui = self._m_ui
        if not targets:
            ui["status"].setText(tr("meta.nothing"))
            return

        def make_job(path, changes, r_cover):
            def job(_p, _c):
                eng.write_metadata(path, changes,
                                   cover_path=r_cover[1] if r_cover and r_cover[0] == "set" else None,
                                   remove_cover=bool(r_cover and r_cover[0] == "remove"))
                return eng.read_metadata(path)
            return job

        jobs = [(r, make_job(r["path"], ch, cv)) for r, ch, cv in targets]
        self._start_jobs("m", self.m_queue, jobs, open_result=False)

    # ════════════════════════════════════════════════════════════════════════
    #  RUN HANDLERS
    # ════════════════════════════════════════════════════════════════════════
    def _batch_kwargs(self, tag, row):
        if tag == "c":
            kw = dict(target_format=self.c_fmt.current(), fade_in=self.c_fi.isChecked(),
                      fade_out=self.c_fo.isChecked(), fade_duration=self.c_fade_len.value(),
                      keep_cover=self.c_cover.isChecked(), output_dir=self.c_outdir.get_dir(),
                      metadata=dict(row["override"]) or None, **self.c_codec.get_settings())
        else:
            if self.e_native.isChecked():
                kw = dict(copy_audio=True, output_dir=self.e_outdir.get_dir(), output_suffix="_audio")
            else:
                kw = dict(target_format=self.e_fmt.current(), output_dir=self.e_outdir.get_dir(),
                          output_suffix="_audio", **self.e_codec.get_settings())
        kw["input_file"] = row["path"]
        return kw

    def _run_batch(self, tag, only_failed=False):
        queue = self.c_queue if tag == "c" else self.e_queue
        rows = [r for r in queue.rows if (r["status"] == "failed" if only_failed else True)]
        if not rows:
            QMessageBox.warning(self, tr("msg.no_files_title"), tr("msg.no_files"))
            return

        def make_job(kw):
            return lambda prog, cancel: eng.process_audio(on_progress=prog, should_cancel=cancel, **kw)

        jobs = [(r, make_job(self._batch_kwargs(tag, r))) for r in rows]
        self._start_jobs(tag, queue, jobs)

    def _run_trim(self):
        if not self.t_picker.file_path:
            QMessageBox.warning(self, tr("msg.no_files_title"), tr("msg.no_file"))
            return
        if self._player_ok:
            self._trim_player.pause()
        dur = self.t_picker.media_info.get("duration", 0)
        start, end = self.t_start.text().strip(), self.t_end.text().strip()
        try:
            s_sec, e_sec = ts_to_sec(start), ts_to_sec(end)
        except ValueError:
            s_sec, e_sec = 0, 0
        if e_sec and e_sec <= s_sec:
            QMessageBox.warning(self, tr("msg.error"), tr("trim.bad_range"))
            return
        if dur and abs(e_sec - dur) < 0.05:
            end = None
        kw = dict(input_file=self.t_picker.file_path, target_format=self.t_fmt.current(),
                  start_time=start, end_time=end, fade_in=self.t_fi.isChecked(),
                  fade_out=self.t_fo.isChecked(), fade_duration=self.t_fade_len.value(),
                  keep_cover=self.t_cover.isChecked(), output_dir=self.t_outdir.get_dir(),
                  output_suffix="_trimmed", **self.t_codec.get_settings())
        job = lambda prog, cancel: eng.process_audio(on_progress=prog, should_cancel=cancel, **kw)
        self._start_jobs("t", None, [("trim", job)])

    # ════════════════════════════════════════════════════════════════════════
    #  JOB ORCHESTRATION (progress, status, retry, cancel)
    # ════════════════════════════════════════════════════════════════════════
    def _start_jobs(self, tag, queue, jobs, open_result=True):
        ui = getattr(self, f"_{tag}_ui")
        n = len(jobs)
        state = {"i": 0, "ok": 0, "fail": 0, "errors": [], "last": None}
        if queue:
            queue.set_locked(True)
            for key, _ in jobs:
                queue.set_status(key, "pending")
        ui["btn"].setEnabled(False)
        ui["retry"].setVisible(False)
        ui["cancel"].setVisible(True)
        ui["prog"].setValue(0)
        ui["prog"].setVisible(True)
        if tag == "m":
            self._m_selection()

        def name_of(key):
            return os.path.basename(key["path"]) if isinstance(key, dict) else os.path.basename(
                self.t_picker.file_path or "")

        def started(key):
            state["i"] += 1
            ui["status"].setText(tr("status.processing", i=state["i"], n=n, name=name_of(key)))
            if queue:
                queue.set_status(key, "working", tr("status.working", p=0))
                queue.tree.scrollToItem(key["item"])

        def progress(key, f):
            ui["prog"].setValue(int(((state["i"] - 1) + f) / n * 1000))
            if queue:
                queue.set_status(key, "working", tr("status.working", p=int(f * 100)))

        def done(key, res):
            state["ok"] += 1
            if queue:
                queue.set_status(key, "done")
                if tag == "m" and isinstance(res, dict):
                    key["info"]["has_cover"] = res.pop("has_cover", False)
                    key["tags"] = res
                    key["pending"].clear()
                    queue.refresh_row(key)
                    old = os.path.join(self._m_tmpdir, f"cover-{abs(hash(key['path']))}.png")
                    if os.path.exists(old):
                        os.remove(old)
            if isinstance(res, str):
                state["last"] = res

        def failed(key, msg):
            state["fail"] += 1
            state["errors"].append(f"■ {name_of(key)}\n{msg}")
            if queue:
                queue.set_status(key, "failed")

        def finished():
            cancelled = worker._cancel
            if queue:
                queue.set_locked(False)
                for key, _ in jobs:
                    if key["status"] in ("pending", "working"):
                        queue.set_status(key, "cancelled" if cancelled else "pending")
            ui["btn"].setEnabled(True)
            ui["cancel"].setVisible(False)
            ui["prog"].setVisible(False)
            if cancelled:
                ui["status"].setText(tr("status.summary_cancel", ok=state["ok"]))
            elif n == 1 and state["last"]:
                ui["status"].setText(tr("status.saved", path=state["last"]))
            elif tag == "m":
                ui["status"].setText(tr("meta.saved", n=state["ok"]) if not state["fail"]
                                     else tr("status.summary", ok=state["ok"], fail=state["fail"]))
            else:
                ui["status"].setText(tr("status.summary", ok=state["ok"], fail=state["fail"]))
            if state["fail"] and queue and tag != "m":
                try:
                    ui["retry"].clicked.disconnect()
                except TypeError:
                    pass
                ui["retry"].clicked.connect(lambda: self._run_batch(tag, only_failed=True))
                ui["retry"].setVisible(True)
            if tag == "m":
                self._m_selection()
            if state["errors"]:
                show_error_dialog(self, tr("msg.errors_title") if n > 1 else tr("msg.error"),
                                  "\n\n".join(state["errors"]))
            if open_result and state["last"] and not cancelled:
                open_folder_select(state["last"])

        worker = JobWorker(jobs)
        worker.item_started.connect(started)
        worker.item_progress.connect(progress)
        worker.item_done.connect(done)
        worker.item_failed.connect(failed)
        worker.finished.connect(finished)
        self._workers[tag] = worker
        worker.start()


def QPixmap_empty():
    from PyQt6.QtGui import QPixmap
    return QPixmap()
