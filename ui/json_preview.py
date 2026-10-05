"""Right-hand JSON preview: syntax-coloured, read-only, with Copy / Save / Export buttons."""
from __future__ import annotations

from PySide6.QtCore import QRegularExpression, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout)

from .widgets import label, repolish


class JsonHighlighter(QSyntaxHighlighter):
    """Colours keys, strings, numbers and literals of pretty-printed JSON, line by line."""

    def __init__(self, document, tokens: dict[str, str]):
        super().__init__(document)
        self.set_tokens(tokens, rehighlight=False)

    def set_tokens(self, tokens: dict[str, str], rehighlight: bool = True) -> None:
        def fmt(colour: str, bold: bool = False) -> QTextCharFormat:
            f = QTextCharFormat()
            f.setForeground(QColor(colour))
            if bold:
                f.setFontWeight(QFont.DemiBold)
            return f

        self._key = fmt(tokens["j_key"], True)
        self._string = fmt(tokens["j_string"])
        self._number = fmt(tokens["j_number"])
        self._literal = fmt(tokens["j_literal"], True)
        self._punct = fmt(tokens["j_punct"])
        if rehighlight:
            self.rehighlight()

    _STRING = QRegularExpression(r'"(?:[^"\\]|\\.)*"')
    _NUMBER = QRegularExpression(r'(?<![\w."])-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?(?![\w."])')
    _LITERAL = QRegularExpression(r'\b(?:true|false|null)\b')
    _PUNCT = QRegularExpression(r'[{}\[\],:]')

    def highlightBlock(self, text: str) -> None:
        it = self._PUNCT.globalMatch(text)
        while it.hasNext():
            m = it.next()
            self.setFormat(m.capturedStart(), m.capturedLength(), self._punct)
        it = self._NUMBER.globalMatch(text)
        while it.hasNext():
            m = it.next()
            self.setFormat(m.capturedStart(), m.capturedLength(), self._number)
        it = self._LITERAL.globalMatch(text)
        while it.hasNext():
            m = it.next()
            self.setFormat(m.capturedStart(), m.capturedLength(), self._literal)
        it = self._STRING.globalMatch(text)
        while it.hasNext():
            m = it.next()
            end = m.capturedEnd()
            is_key = text[end:].lstrip().startswith(":")        # a string followed by ':' is a key
            self.setFormat(m.capturedStart(), m.capturedLength(), self._key if is_key else self._string)


class JsonPreviewPanel(QFrame):
    """Read-only preview. Buttons only emit signals; MainWindow owns generation and file IO."""

    copyRequested = Signal()
    saveJsonRequested = Signal()
    exportTextRequested = Signal()

    STATES = {
        "empty": "Not generated yet",
        "ok": "Up to date",
        "stale": "Form changed — regenerate",
        "blocked": "Fix the highlighted fields",
    }

    def __init__(self, tokens: dict[str, str], parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewPane")

        self.status = QLabel()
        self.status.setObjectName("StatusChip")

        self.copy_btn = QPushButton("Copy JSON")
        self.save_btn = QPushButton("Save JSON…")
        self.export_btn = QPushButton("Export Prompt TXT…")
        self.copy_btn.setToolTip("Copy the generated JSON to the clipboard (Ctrl+Shift+C).")
        self.save_btn.setToolTip("Save the generated JSON as a .json file.")
        self.export_btn.setToolTip("Save a plain-text version of the prompt, ready to paste into a chat or tool.")
        self.copy_btn.clicked.connect(self.copyRequested)
        self.save_btn.clicked.connect(self.saveJsonRequested)
        self.export_btn.clicked.connect(self.exportTextRequested)

        self.view = QPlainTextEdit()
        self.view.setObjectName("JsonView")
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.view.setPlaceholderText("Click “Generate JSON” to build the prompt.\n\nThe structured JSON appears here, "
                                     "ready to copy, save or export.")
        self.view.setTabStopDistance(24)
        self.highlighter = JsonHighlighter(self.view.document(), tokens)

        head = QHBoxLayout()
        head.addWidget(label("JSON Preview", "SubHeading"))
        head.addStretch(1)
        head.addWidget(self.status)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.copy_btn)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.export_btn)
        buttons.addStretch(1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 18)
        lay.setSpacing(12)
        lay.addLayout(head)
        lay.addLayout(buttons)
        lay.addWidget(self.view, 1)

        self._copy_timer = QTimer(self, singleShot=True, interval=1500)
        self._copy_timer.timeout.connect(lambda: self.copy_btn.setText("Copy JSON"))
        self.set_state("empty")

    def set_json(self, text: str) -> None:
        self.view.setPlainText(text)
        self.view.verticalScrollBar().setValue(0)
        self.set_state("ok")

    def clear(self) -> None:
        self.view.clear()
        self.set_state("empty")

    def has_json(self) -> bool:
        return bool(self.view.toPlainText().strip())

    def set_state(self, state: str) -> None:
        self.status.setText(self.STATES[state])
        self.status.setProperty("state", state)
        repolish(self.status)

    def flash_copied(self) -> None:
        self.copy_btn.setText("Copied ✓")
        self._copy_timer.start()

    def set_tokens(self, tokens: dict[str, str]) -> None:
        self.highlighter.set_tokens(tokens)
