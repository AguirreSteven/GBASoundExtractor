"""Spotify-esque dark theme with cobalt blue accents."""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt


def apply_dark_theme(app: QApplication):
    """Apply a dark Fusion palette and comprehensive QSS stylesheet."""
    palette = QPalette()

    # Base colors
    palette.setColor(QPalette.Window, QColor("#0d0d0d"))
    palette.setColor(QPalette.WindowText, QColor("#e0e0e0"))
    palette.setColor(QPalette.Base, QColor("#0a0a0a"))
    palette.setColor(QPalette.AlternateBase, QColor("#141428"))
    palette.setColor(QPalette.ToolTipBase, QColor("#232340"))
    palette.setColor(QPalette.ToolTipText, QColor("#e0e0e0"))
    palette.setColor(QPalette.Text, QColor("#e0e0e0"))
    palette.setColor(QPalette.Button, QColor("#1a1a2e"))
    palette.setColor(QPalette.ButtonText, QColor("#e0e0e0"))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Link, QColor("#1e90ff"))
    palette.setColor(QPalette.Highlight, QColor("#1e90ff"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.PlaceholderText, QColor("#555555"))

    # Disabled state
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#555555"))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#555555"))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#555555"))

    app.setPalette(palette)
    app.setStyleSheet(_STYLESHEET)


_STYLESHEET = """
/* ---- Global ---- */
QMainWindow {
    background-color: #0d0d0d;
}

QWidget {
    color: #e0e0e0;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ---- Menu Bar ---- */
QMenuBar {
    background-color: #121212;
    color: #e0e0e0;
    border-bottom: 1px solid #2a2a3a;
    padding: 2px 0;
}
QMenuBar::item {
    padding: 4px 10px;
    background: transparent;
}
QMenuBar::item:selected {
    background-color: #2a2a4a;
    border-radius: 4px;
}
QMenu {
    background-color: #1a1a2e;
    color: #e0e0e0;
    border: 1px solid #2a2a3a;
    padding: 4px 0;
}
QMenu::item {
    padding: 6px 24px;
}
QMenu::item:selected {
    background-color: #1e90ff;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background: #2a2a3a;
    margin: 4px 8px;
}

/* ---- Buttons ---- */
QPushButton {
    background-color: #232340;
    color: #e0e0e0;
    border: 1px solid #2a2a3a;
    border-radius: 16px;
    padding: 6px 18px;
    font-size: 12px;
    font-weight: 500;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #2a2a4a;
    border-color: #1e90ff;
}
QPushButton:pressed {
    background-color: #1570cc;
    border-color: #1570cc;
    color: #ffffff;
}
QPushButton:disabled {
    background-color: #1a1a1a;
    color: #555555;
    border-color: #1a1a1a;
}

/* Accent play button */
QPushButton#playBtn {
    background-color: #1e90ff;
    color: #ffffff;
    border: none;
    font-weight: bold;
    font-size: 13px;
}
QPushButton#playBtn:hover {
    background-color: #3da5ff;
}
QPushButton#playBtn:pressed {
    background-color: #1570cc;
}
QPushButton#playBtn:disabled {
    background-color: #1a1a1a;
    color: #555555;
}

/* ---- Labels ---- */
QLabel {
    color: #e0e0e0;
    background: transparent;
}

/* ---- QTextEdit (details pane) ---- */
QTextEdit {
    background-color: #121212;
    color: #e0e0e0;
    border: 1px solid #2a2a3a;
    border-radius: 8px;
    padding: 8px;
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 12px;
    selection-background-color: #1e90ff;
}

/* ---- QTableView (song list) ---- */
QTableView {
    background-color: #0a0a0a;
    alternate-background-color: #141428;
    color: #e0e0e0;
    gridline-color: #1a1a2a;
    border: 1px solid #2a2a3a;
    border-radius: 8px;
    selection-background-color: #142a4a;
    selection-color: #ffffff;
    outline: none;
}
QTableView::item {
    padding: 4px 8px;
    border: none;
}
QTableView::item:selected {
    background-color: #142a4a;
    color: #ffffff;
}
QTableView::item:hover {
    background-color: #1a1a3a;
}
QHeaderView::section {
    background-color: #121212;
    color: #8a8a9a;
    border: none;
    border-bottom: 1px solid #2a2a3a;
    padding: 6px 8px;
    font-weight: 600;
    font-size: 11px;
}
QHeaderView::section:hover {
    color: #e0e0e0;
}

/* ---- Horizontal Slider (progress bar) ---- */
QSlider::groove:horizontal {
    height: 4px;
    background: #2a2a3a;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #1e90ff;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider::handle:horizontal:hover {
    background: #3da5ff;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #1e90ff;
    border-radius: 2px;
}
QSlider::add-page:horizontal {
    background: #2a2a3a;
    border-radius: 2px;
}
QSlider::handle:horizontal:disabled {
    background: #3a3a4a;
}
QSlider::sub-page:horizontal:disabled {
    background: #2a2a3a;
}

/* ---- ComboBox ---- */
QComboBox {
    background-color: #232340;
    color: #e0e0e0;
    border: 1px solid #2a2a3a;
    border-radius: 8px;
    padding: 4px 12px;
    min-width: 60px;
}
QComboBox:hover {
    border-color: #1e90ff;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
}
QComboBox QAbstractItemView {
    background-color: #1a1a2e;
    color: #e0e0e0;
    border: 1px solid #2a2a3a;
    selection-background-color: #1e90ff;
    selection-color: #ffffff;
    outline: none;
}

/* ---- Scrollbars ---- */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3a3a4a;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #5a5a6a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
}
QScrollBar::handle:horizontal {
    background: #3a3a4a;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #5a5a6a;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
    width: 0;
}

/* ---- Splitter ---- */
QSplitter::handle {
    background: #2a2a3a;
    width: 2px;
}
QSplitter::handle:hover {
    background: #1e90ff;
}

/* ---- Status Bar ---- */
QStatusBar {
    background-color: #0d0d0d;
    color: #8a8a9a;
    border-top: 1px solid #2a2a3a;
    font-size: 11px;
    padding: 2px 8px;
}

/* ---- Player Bar ---- */
QWidget#playerBar {
    background-color: #1a1a2e;
    border-top: 1px solid #2a2a3a;
}

/* ---- Progress Dialog ---- */
QProgressDialog {
    background-color: #1a1a2e;
}
QProgressBar {
    background-color: #2a2a3a;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #e0e0e0;
    max-height: 6px;
}
QProgressBar::chunk {
    background-color: #1e90ff;
    border-radius: 4px;
}

/* ---- Tooltips ---- */
QToolTip {
    background-color: #232340;
    color: #e0e0e0;
    border: 1px solid #2a2a3a;
    border-radius: 4px;
    padding: 4px 8px;
}

/* ---- Message Box ---- */
QMessageBox {
    background-color: #1a1a2e;
}

/* ---- File Dialog ---- */
QFileDialog {
    background-color: #121212;
}
"""
