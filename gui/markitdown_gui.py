#!/usr/bin/env python3
"""MarkItDown — cross-platform desktop GUI (Linux / macOS / Windows)."""

import sys
import zipfile
from pathlib import Path

from PySide6.QtCore import Qt, QObject, QThread, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QStackedWidget,
    QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from markitdown import MarkItDown

C = {
    "bg":     "#0f1117",
    "bg2":    "#1a2035",
    "bg3":    "#1e2433",
    "border": "#2d3748",
    "accent": "#6366f1",
    "text":   "#cbd5e1",
    "dim":    "#64748b",
    "green":  "#22c55e",
    "red":    "#ef4444",
    "white":  "#f8fafc",
}


# ── Worker ──────────────────────────────────────────────────────────────────

class ConvertWorker(QObject):
    done   = Signal(str, str, str)  # fid, name, markdown
    failed = Signal(str, str, str)  # fid, name, error

    def __init__(self, fid: str, path: str):
        super().__init__()
        self._fid  = fid
        self._path = path

    def run(self):
        try:
            result = MarkItDown().convert(self._path)
            self.done.emit(self._fid, Path(self._path).name, result.text_content)
        except Exception as exc:
            self.failed.emit(self._fid, Path(self._path).name, str(exc))


# ── Drop zone ────────────────────────────────────────────────────────────────

class DropZone(QLabel):
    dropped = Signal(list)

    _BASE = f"""
        QLabel {{
            border: 2px dashed {C['border']};
            border-radius: 10px;
            color: {C['dim']};
            font-size: 14px;
            padding: 28px;
        }}
    """
    _OVER = f"""
        QLabel {{
            border: 2px dashed {C['accent']};
            border-radius: 10px;
            color: {C['text']};
            font-size: 14px;
            padding: 28px;
            background: rgba(99,102,241,0.08);
        }}
    """

    def __init__(self):
        super().__init__("📂  Drop files here")
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(self._BASE)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.setStyleSheet(self._OVER)

    def dragLeaveEvent(self, e):
        self.setStyleSheet(self._BASE)

    def dropEvent(self, e):
        self.setStyleSheet(self._BASE)
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.dropped.emit(paths)


# ── Button factory ───────────────────────────────────────────────────────────

def mk_btn(text: str, kind: str = "ghost", small: bool = False) -> QPushButton:
    p = "5px 10px" if small else "7px 16px"
    f = "12px"     if small else "13px"
    styles = {
        "primary": f"""
            QPushButton {{
                background:{C['accent']}; color:#fff; border:none;
                border-radius:6px; padding:{p}; font-size:{f}; font-weight:500;
            }}
            QPushButton:hover   {{ background:#4f52d4; }}
            QPushButton:disabled {{ background:#2d2f6b; color:#555; }}
        """,
        "green": f"""
            QPushButton {{
                background:#166534; color:#4ade80; border:1px solid #14532d;
                border-radius:6px; padding:{p}; font-size:{f};
            }}
            QPushButton:hover   {{ background:#15803d; }}
            QPushButton:disabled {{ opacity:0.4; }}
        """,
        "ghost": f"""
            QPushButton {{
                background:{C['bg3']}; color:{C['dim']}; border:1px solid {C['border']};
                border-radius:6px; padding:{p}; font-size:{f};
            }}
            QPushButton:hover   {{ background:#252d3d; color:{C['white']}; }}
            QPushButton:disabled {{ opacity:0.4; }}
        """,
    }
    b = QPushButton(text)
    b.setStyleSheet(styles.get(kind, styles["ghost"]))
    b.setCursor(Qt.PointingHandCursor)
    return b


# ── Main window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MarkItDown")
        self.resize(1100, 680)
        self.setMinimumSize(780, 480)

        self._store:   dict       = {}    # fid → {name, path, status, markdown, thread, worker}
        self._active:  str | None = None
        self._counter: int        = 0
        self._view:    str        = "raw" # "raw" | "preview"

        self._set_palette()
        self._build_ui()

    # ── Palette ──────────────────────────────────────────────────────────────

    def _set_palette(self):
        pal = QPalette()
        pal.setColor(QPalette.Window,     QColor(C["bg"]))
        pal.setColor(QPalette.Base,       QColor(C["bg"]))
        pal.setColor(QPalette.Text,       QColor(C["text"]))
        pal.setColor(QPalette.WindowText, QColor(C["text"]))
        pal.setColor(QPalette.Button,     QColor(C["bg3"]))
        pal.setColor(QPalette.ButtonText, QColor(C["text"]))
        QApplication.setPalette(pal)

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self._make_left())
        h.addWidget(self._make_right(), 1)

    def _make_left(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(290)
        w.setStyleSheet(f"background:{C['bg']}; border-right:1px solid {C['border']};")
        v = QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(10)

        self._drop = DropZone()
        self._drop.dropped.connect(self._add_paths)
        v.addWidget(self._drop)

        browse = mk_btn("Browse Files")
        browse.clicked.connect(self._browse)
        v.addWidget(browse)

        # File list header row
        hdr = QWidget()
        hh  = QHBoxLayout(hdr)
        hh.setContentsMargins(0, 0, 0, 0)
        cap = QLabel("CONVERTED FILES")
        cap.setStyleSheet(f"color:{C['dim']}; font-size:10px; font-weight:700; letter-spacing:1px;")
        hh.addWidget(cap)
        hh.addStretch()
        self._dl_all = mk_btn("↓ All .zip", "green", small=True)
        self._dl_all.setEnabled(False)
        self._dl_all.clicked.connect(self._save_all)
        hh.addWidget(self._dl_all)
        v.addWidget(hdr)

        self._lst = QListWidget()
        self._lst.setStyleSheet(f"""
            QListWidget {{
                background:transparent; border:none; outline:none;
            }}
            QListWidget::item {{
                color:{C['text']}; padding:8px 10px;
                border-radius:6px; margin-bottom:2px;
            }}
            QListWidget::item:selected {{
                background:{C['bg2']}; border:1px solid {C['accent']}; color:{C['white']};
            }}
            QListWidget::item:hover:!selected {{ background:{C['bg2']}; }}
        """)
        self._lst.currentItemChanged.connect(self._on_list_select)
        v.addWidget(self._lst)

        return w

    def _make_right(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{C['bg']};")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ── Toolbar ──
        tb = QWidget()
        tb.setStyleSheet(f"background:{C['bg']}; border-bottom:1px solid {C['border']};")
        th = QHBoxLayout(tb)
        th.setContentsMargins(16, 10, 16, 10)
        th.setSpacing(8)

        self._fname = QLabel("No file selected")
        self._fname.setStyleSheet(f"color:{C['dim']}; font-size:13px;")
        th.addWidget(self._fname, 1)

        self._view_btn = mk_btn("👁  View MD", small=True)
        self._view_btn.setEnabled(False)
        self._view_btn.clicked.connect(self._toggle_view)
        th.addWidget(self._view_btn)

        self._copy_btn = mk_btn("Copy", small=True)
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._copy)
        th.addWidget(self._copy_btn)

        self._save_btn = mk_btn("↓ .md", "primary", small=True)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_one)
        th.addWidget(self._save_btn)

        v.addWidget(tb)

        # ── Content area: empty (0) | output (1) ──
        self._content = QStackedWidget()

        empty = QLabel("Drop files or click Browse to get started")
        empty.setAlignment(Qt.AlignCenter)
        empty.setStyleSheet(f"color:{C['border']}; font-size:15px;")
        self._content.addWidget(empty)     # index 0

        # Output: raw (0) | preview (1)
        self._out = QStackedWidget()

        self._raw = QTextEdit()
        self._raw.setReadOnly(True)
        self._raw.setStyleSheet(f"""
            QTextEdit {{
                background:{C['bg']}; color:{C['text']}; border:none;
                font-family:'JetBrains Mono','Fira Code','Cascadia Code',monospace;
                font-size:13px; padding:20px;
            }}
        """)
        self._out.addWidget(self._raw)     # index 0

        self._preview = QTextBrowser()
        self._preview.setOpenExternalLinks(True)
        self._preview.setStyleSheet(f"""
            QTextBrowser {{
                background:{C['bg']}; color:{C['text']}; border:none;
                font-size:14px; padding:20px 28px;
            }}
        """)
        self._out.addWidget(self._preview) # index 1

        self._content.addWidget(self._out) # index 1
        v.addWidget(self._content)

        return w

    # ── File ops ─────────────────────────────────────────────────────────────

    def _browse(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "",
            "All Files (*);;"
            "Documents (*.pdf *.docx *.pptx *.xlsx *.xls *.epub);;"
            "Images (*.png *.jpg *.jpeg *.webp *.gif);;"
            "Web & Data (*.html *.htm *.csv *.json *.xml)",
        )
        if paths:
            self._add_paths(paths)

    def _add_paths(self, paths: list[str]):
        for path in paths:
            self._counter += 1
            fid  = f"f{self._counter}"
            name = Path(path).name
            self._store[fid] = {
                "name": name, "path": path,
                "status": "loading", "markdown": "",
            }
            item = QListWidgetItem(f"⏳  {name}")
            item.setData(Qt.UserRole, fid)
            item.setForeground(QColor(C["dim"]))
            self._lst.addItem(item)
            self._spawn_thread(fid, path)

    def _spawn_thread(self, fid: str, path: str):
        thread = QThread(self)
        worker = ConvertWorker(fid, path)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(self._on_done)
        worker.failed.connect(self._on_fail)
        worker.done.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        self._store[fid]["thread"] = thread
        self._store[fid]["worker"] = worker
        thread.start()

    def _item_for(self, fid: str) -> QListWidgetItem | None:
        for i in range(self._lst.count()):
            item = self._lst.item(i)
            if item.data(Qt.UserRole) == fid:
                return item
        return None

    # ── Conversion callbacks ─────────────────────────────────────────────────

    def _on_done(self, fid: str, name: str, markdown: str):
        self._store[fid].update(status="ok", markdown=markdown)
        item = self._item_for(fid)
        if item:
            item.setText(f"✅  {name}")
            item.setForeground(QColor(C["green"]))
        self._dl_all.setEnabled(True)
        if self._active is None:
            self._lst.setCurrentItem(item)
            self._activate(fid)

    def _on_fail(self, fid: str, name: str, error: str):
        self._store[fid]["status"] = "error"
        item = self._item_for(fid)
        if item:
            item.setText(f"❌  {name}")
            item.setForeground(QColor(C["red"]))
            item.setToolTip(error)

    def _on_list_select(self, current: QListWidgetItem, _prev):
        if not current:
            return
        fid = current.data(Qt.UserRole)
        if self._store[fid]["status"] == "ok":
            self._activate(fid)

    def _activate(self, fid: str):
        self._active = fid
        entry = self._store[fid]
        self._fname.setText(entry["name"])
        self._raw.setPlainText(entry["markdown"])
        self._preview.setMarkdown(entry["markdown"])
        for w in (self._copy_btn, self._save_btn, self._view_btn):
            w.setEnabled(True)
        self._content.setCurrentIndex(1)
        self._apply_view()

    # ── View toggle ──────────────────────────────────────────────────────────

    def _toggle_view(self):
        self._view = "preview" if self._view == "raw" else "raw"
        self._apply_view()

    def _apply_view(self):
        if self._view == "raw":
            self._out.setCurrentIndex(0)
            self._view_btn.setText("👁  View MD")
        else:
            self._out.setCurrentIndex(1)
            self._view_btn.setText("✏️  Raw")

    # ── Export ───────────────────────────────────────────────────────────────

    def _copy(self):
        QApplication.clipboard().setText(self._raw.toPlainText())

    def _save_one(self):
        if not self._active:
            return
        name = self._store[self._active]["name"]
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save Markdown", Path(name).stem + ".md", "Markdown (*.md)"
        )
        if dest:
            Path(dest).write_text(self._store[self._active]["markdown"], encoding="utf-8")

    def _save_all(self):
        ok = [(e["name"], e["markdown"]) for e in self._store.values() if e["status"] == "ok"]
        if not ok:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save All as ZIP", "markitdown-export.zip", "ZIP Archive (*.zip)"
        )
        if not dest:
            return
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, md in ok:
                zf.writestr(Path(name).stem + ".md", md)


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MarkItDown")
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
