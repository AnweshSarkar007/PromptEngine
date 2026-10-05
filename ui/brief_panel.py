"""ChatGPT Brief card: copy the instruction for ChatGPT, paste its reply back, load it into the form."""
from __future__ import annotations

import html

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QPushButton

from core.chatgpt_brief import BriefImport, build_instruction
from core.models import ProjectData

from .widgets import FieldBox, SectionCard, TextArea, label, repolish

STEPS = (
    "<ol style='margin:0 0 0 -22px'>"
    "<li>Click <b>Copy ChatGPT instruction</b>.</li>"
    "<li>In ChatGPT, attach your <b>old product photo</b> and paste the instruction.</li>"
    "<li>Copy ChatGPT's whole reply, paste it below and click <b>Load into form</b>.</li>"
    "</ol>"
)


class BriefCard(SectionCard):
    section_id = "brief"
    title = "ChatGPT Brief"
    subtitle = ("Let ChatGPT study your old product photo and fill in the scene, camera, lighting, "
                "composition and style for you. Your images, product details and restrictions are not touched.")

    loadRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        steps = label(STEPS, "Hint", wrap=True)
        steps.setTextFormat(Qt.RichText)
        self.add_widget(steps)

        self.copy_btn = QPushButton("Copy ChatGPT instruction")
        self.copy_btn.setToolTip("Copies the full instruction (with every option the app understands) to the clipboard.")
        self.copy_btn.clicked.connect(self._copy_instruction)
        self.add_button_row(self.copy_btn)

        # A plain FieldBox (not self.field): the paste box is a scratch area, not part of the
        # project, so typing in it must not mark the project as changed.
        self.paste = TextArea(8, "Paste ChatGPT's reply here…")
        self.add_row(FieldBox("ChatGPT's reply", self.paste,
                              "Paste the whole reply. Extra text around the JSON is fine."))

        self.load_btn = QPushButton("Load into form")
        self.load_btn.setObjectName("Primary")
        self.load_btn.setToolTip("Fill the form from the pasted reply. Only the fields ChatGPT filled are changed.")
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("Ghost")
        self.load_btn.clicked.connect(self._request_load)
        self.clear_btn.clicked.connect(self._clear)
        self.add_button_row(self.load_btn, self.clear_btn)

        self.result = label("", "BriefResult", wrap=True)
        self.result.setTextFormat(Qt.RichText)
        self.result.setVisible(False)
        self.add_widget(self.result)

        self._copy_timer = QTimer(self, singleShot=True, interval=1800)
        self._copy_timer.timeout.connect(lambda: self.copy_btn.setText("Copy ChatGPT instruction"))

    def _copy_instruction(self) -> None:
        QGuiApplication.clipboard().setText(build_instruction())
        self.copy_btn.setText("Copied ✓  Now paste it into ChatGPT")
        self._copy_timer.start()

    def _request_load(self) -> None:
        text = self.paste.toPlainText().strip()
        if not text:
            self._show("error", "Paste ChatGPT's reply into the box first.")
            return
        self.loadRequested.emit(text)

    def _clear(self) -> None:
        self.paste.clear()
        self.result.setVisible(False)

    def _show(self, state: str, rich_text: str) -> None:
        self.result.setText(rich_text)
        self.result.setProperty("state", state)
        repolish(self.result)
        self.result.setVisible(True)

    def show_result(self, result: BriefImport) -> None:
        if not result.ok:
            self._show("error", html.escape(result.message))
            return
        lines = [f"<b>✓ Filled {len(result.filled)} field{'s' if len(result.filled) != 1 else ''}:</b> "
                 + html.escape(", ".join(result.filled))]
        if result.custom:
            lines.append("<b>Kept as your own text</b> (not one of the listed options — check them): "
                         + html.escape(", ".join(result.custom)))
        if result.skipped:
            lines.append("<b>Ignored</b> (ChatGPT didn't pick a value): " + html.escape(", ".join(result.skipped)))
        lines.append("Review the cards below, then click <b>Generate JSON</b>.")
        self._show("ok", "<br><br>".join(lines))

    # The paste box is not saved with the project; loading / resetting just clears it.
    def load(self, data: ProjectData) -> None:
        self._clear()

    def collect(self, data: ProjectData) -> None:
        pass
