"""Product Image Prompt Builder - application entry point."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from core import options as opt
from core.utils import app_data_dir, resource_path
from ui.main_window import MainWindow
from ui.theme import apply_theme

ORG = "ProductImagePromptBuilder"
LOG = logging.getLogger("app")


def setup_logging() -> Path:
    log_path = app_data_dir() / "app.log"
    handler = RotatingFileHandler(log_path, maxBytes=500_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    return log_path


def install_excepthook(log_path: Path) -> None:
    """A windowed .exe has no console: log unexpected errors and tell the user instead of dying silently."""
    def hook(exc_type, exc, tb):
        LOG.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        if QApplication.instance() is not None:
            QMessageBox.critical(None, opt.APP_NAME,
                                 f"Something unexpected went wrong:\n\n{exc}\n\nDetails were saved to:\n{log_path}")
    sys.excepthook = hook


def main() -> int:
    log_path = setup_logging()
    install_excepthook(log_path)

    try:                                    # own taskbar identity (icon grouping) on Windows
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ProductImagePromptBuilder.App")
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName(opt.APP_NAME)
    app.setOrganizationName(ORG)
    icon = resource_path("assets/icon.ico")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    settings = QSettings(QSettings.IniFormat, QSettings.UserScope, ORG, "settings")
    theme = str(settings.value("theme", "light"))
    apply_theme(app, theme)

    window = MainWindow(settings, theme)
    window.show()

    # Double-clicking a .project.json (or passing a path) opens it straight away.
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_file():
        window.open_project_path(sys.argv[1])
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
