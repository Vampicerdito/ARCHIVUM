from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication
from archivum.core.config import AppConfig
from archivum.core.database import Database
from archivum.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ARCHIVUM")
    app.setOrganizationName("ARCHIVUM")
    app.setApplicationVersion("0.3.0")

    config = AppConfig.load()
    database = Database(config.data_dir)
    database.initialize()

    window = MainWindow(config=config, database=database)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
