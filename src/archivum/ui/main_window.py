from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QStackedWidget,
    QStatusBar, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from archivum.core.config import AppConfig
from archivum.core.database import Database
from archivum.core.scanner import MediaScanner
from archivum.ui.theme import APP_STYLE


class ScanWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, scanner: MediaScanner, source_id: int):
        super().__init__()
        self.scanner = scanner
        self.source_id = source_id

    def run(self):
        try:
            self.completed.emit(self.scanner.scan_source(self.source_id))
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, database: Database):
        super().__init__()
        self.config = config
        self.database = database
        self.scanner = MediaScanner(database)
        self.scan_worker = None
        self.setWindowTitle("ARCHIVUM — Biblioteca cinematográfica")
        self.resize(1280, 820)
        self.setMinimumSize(1000, 650)
        self.setStyleSheet(APP_STYLE)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        root_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.pages = {
            "Inicio": self._build_home(),
            "Biblioteca": self._build_library(),
            "Explorador": self._build_explorer(),
            "Colecciones": self._placeholder("Colecciones", "Las colecciones personalizadas se habilitarán en una fase posterior."),
            "Personas": self._placeholder("Personas", "El índice de actores y equipo técnico se habilitará con los metadatos."),
            "Estadísticas": self._placeholder("Estadísticas", "Las estadísticas se completarán cuando exista inventario multimedia."),
            "Operaciones": self._placeholder("Operaciones", "Aquí se revisarán las tareas automáticas y las modificaciones pendientes."),
            "Configuración": self._build_settings(),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        status = QStatusBar()
        status.showMessage(f"Datos: {self.database.data_dir}")
        self.setStatusBar(status)
        self.status_bar = status
        self.navigate("Inicio")

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(225)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 18)
        layout.setSpacing(8)

        brand = QLabel("ARCHIVUM")
        brand.setObjectName("Brand")
        layout.addWidget(brand)
        subtitle = QLabel("PERSONAL MEDIA ARCHIVE")
        subtitle.setObjectName("Muted")
        subtitle.setStyleSheet("font-size: 8pt; letter-spacing: 1px;")
        layout.addWidget(subtitle)
        layout.addSpacing(25)

        self.nav_buttons = {}
        for label in self.pages_labels():
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, name=label: self.navigate(name))
            self.nav_buttons[label] = button
            layout.addWidget(button)

        layout.addStretch()
        version = QLabel("ARCHIVUM 0.1.0 · FASE 1")
        version.setObjectName("Muted")
        version.setStyleSheet("font-size: 8pt;")
        layout.addWidget(version)
        return sidebar

    @staticmethod
    def pages_labels():
        return [
            "Inicio", "Biblioteca", "Explorador", "Colecciones", "Personas",
            "Estadísticas", "Operaciones", "Configuración"
        ]

    def navigate(self, name: str):
        page = self.pages[name]
        self.stack.setCurrentWidget(page)
        for label, button in self.nav_buttons.items():
            button.setChecked(label == name)
        self.status_bar.showMessage(f"{name}  |  Datos: {self.database.data_dir}")

    def _page_shell(self, title: str, description: str = ""):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 25pt; font-weight: 700;")
        layout.addWidget(heading)
        if description:
            desc = QLabel(description)
            desc.setObjectName("Muted")
            desc.setWordWrap(True)
            layout.addWidget(desc)
        return page, layout

    def _metric_card(self, label: str, value: str, note: str = "") -> QFrame:
        card = QFrame()
        card.setObjectName("Panel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        title = QLabel(label.upper())
        title.setObjectName("Muted")
        title.setStyleSheet("font-size: 8pt; font-weight: 600; letter-spacing: 1px;")
        metric = QLabel(value)
        metric.setObjectName("Metric")
        layout.addWidget(title)
        layout.addWidget(metric)
        if note:
            small = QLabel(note)
            small.setObjectName("Muted")
            layout.addWidget(small)
        return card

    def _build_home(self):
        page, layout = self._page_shell(
            "Panel de control",
            "Resumen de tu archivo cinematográfico. Las cifras se actualizarán a medida que incorporemos películas y archivos."
        )
        metrics = QHBoxLayout()
        self.movie_metric = self._metric_card("Películas", "0", "Fichas registradas")
        self.file_metric = self._metric_card("Archivos", "0", "Archivos multimedia")
        self.task_metric = self._metric_card("Tareas", "0", "Tareas registradas")
        metrics.addWidget(self.movie_metric)
        metrics.addWidget(self.file_metric)
        metrics.addWidget(self.task_metric)
        layout.addLayout(metrics)

        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 18, 20, 18)
        title = QLabel("Estado del sistema")
        title.setStyleSheet("font-size: 14pt; font-weight: 650;")
        panel_layout.addWidget(title)
        self.health_label = QLabel("Comprobando base de datos…")
        self.health_label.setObjectName("Muted")
        panel_layout.addWidget(self.health_label)
        self.location_label = QLabel()
        self.location_label.setWordWrap(True)
        panel_layout.addWidget(self.location_label)
        layout.addWidget(panel)

        quick = QHBoxLayout()
        library_btn = QPushButton("Abrir biblioteca")
        library_btn.clicked.connect(lambda: self.navigate("Biblioteca"))
        settings_btn = QPushButton("Configurar almacenamiento")
        settings_btn.clicked.connect(lambda: self.navigate("Configuración"))
        quick.addWidget(library_btn)
        quick.addWidget(settings_btn)
        quick.addStretch()
        layout.addLayout(quick)
        layout.addStretch()
        self.refresh_dashboard()
        return page

    def refresh_dashboard(self):
        counts = self.database.counts()
        self._set_metric(self.movie_metric, str(counts["movies"]))
        self._set_metric(self.file_metric, str(counts["media_files"]))
        self._set_metric(self.task_metric, str(counts["tasks"]))
        healthy = self.database.health_check()
        self.health_label.setText(
            "Base de datos operativa · comprobación de integridad correcta"
            if healthy else "No se pudo validar la integridad de la base de datos"
        )
        self.location_label.setText(f"Ubicación de datos: {self.database.data_dir}")

    @staticmethod
    def _set_metric(card: QFrame, value: str):
        labels = card.findChildren(QLabel)
        if len(labels) >= 2:
            labels[1].setText(value)

    def _build_library(self):
        page, layout = self._page_shell(
            "Biblioteca",
            "Catálogo cinematográfico. La importación e identificación automática se incorporarán en las fases 2 y 3."
        )
        toolbar = QHBoxLayout()
        self.movie_search = QLineEdit()
        self.movie_search.setPlaceholderText("Buscar por título…")
        self.movie_search.textChanged.connect(self.filter_library)
        toolbar.addWidget(self.movie_search, 1)
        add_button = QPushButton("Añadir ficha de prueba")
        add_button.setObjectName("Primary")
        add_button.clicked.connect(self.add_sample_movie)
        toolbar.addWidget(add_button)
        layout.addLayout(toolbar)

        self.movie_table = QTableWidget(0, 4)
        self.movie_table.setHorizontalHeaderLabels(["Título", "Título original", "Año", "Estado"])
        self.movie_table.setAlternatingRowColors(True)
        self.movie_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.movie_table.horizontalHeader().setStretchLastSection(True)
        self.movie_table.horizontalHeader().setSectionResizeMode(0, self.movie_table.horizontalHeader().ResizeMode.Stretch)
        self.movie_table.horizontalHeader().setSectionResizeMode(1, self.movie_table.horizontalHeader().ResizeMode.Stretch)
        layout.addWidget(self.movie_table, 1)
        self.refresh_movie_table()
        return page

    def refresh_movie_table(self):
        from sqlalchemy import select
        from archivum.models.schema import Movie

        with self.database.Session() as session:
            movies = session.scalars(select(Movie).order_by(Movie.title)).all()
            self.movie_table.setRowCount(len(movies))
            for row, movie in enumerate(movies):
                values = [movie.title, movie.original_title or "", str(movie.year or ""), movie.status]
                for column, value in enumerate(values):
                    self.movie_table.setItem(row, column, QTableWidgetItem(value))

    def filter_library(self, query: str):
        query = query.casefold().strip()
        for row in range(self.movie_table.rowCount()):
            title = self.movie_table.item(row, 0).text().casefold()
            original = self.movie_table.item(row, 1).text().casefold()
            self.movie_table.setRowHidden(row, query not in title and query not in original)

    def add_sample_movie(self):
        from archivum.models.schema import Movie
        from PySide6.QtWidgets import QInputDialog

        title, accepted = QInputDialog.getText(self, "Nueva ficha", "Título de la película:")
        if not accepted or not title.strip():
            return
        year, accepted_year = QInputDialog.getInt(
            self, "Año de estreno", "Año (0 si se desconoce):", 0, 0, 2200
        )
        if not accepted_year:
            return
        with self.database.Session() as session:
            session.add(Movie(title=title.strip(), year=year or None, status="unidentified"))
            session.commit()
        self.refresh_movie_table()
        self.refresh_dashboard()

    def _build_explorer(self):
        page, layout = self._page_shell(
            "Explorador de archivos",
            "Registra carpetas o unidades y construye un inventario de los archivos de vídeo encontrados."
        )
        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.addWidget(QLabel("Ubicaciones registradas"))
        self.source_table = QTableWidget(0, 4)
        self.source_table.setHorizontalHeaderLabels(["ID", "Nombre", "Ruta raíz", "Estado"])
        self.source_table.setColumnHidden(0, True)
        self.source_table.horizontalHeader().setStretchLastSection(True)
        self.source_table.horizontalHeader().setSectionResizeMode(2, self.source_table.horizontalHeader().ResizeMode.Stretch)
        panel_layout.addWidget(self.source_table)

        actions = QHBoxLayout()
        add_source = QPushButton("Añadir carpeta")
        add_source.setObjectName("Primary")
        add_source.clicked.connect(self.add_media_source)
        actions.addWidget(add_source)
        scan_source = QPushButton("Escanear ubicación seleccionada")
        scan_source.clicked.connect(self.scan_selected_source)
        actions.addWidget(scan_source)
        refresh_sources = QPushButton("Actualizar lista")
        refresh_sources.clicked.connect(self.refresh_sources)
        actions.addWidget(refresh_sources)
        actions.addStretch()
        panel_layout.addLayout(actions)
        self.scan_status = QLabel("El escaneo no modifica ni elimina archivos originales.")
        self.scan_status.setObjectName("Muted")
        self.scan_status.setWordWrap(True)
        panel_layout.addWidget(self.scan_status)
        layout.addWidget(panel)
        layout.addStretch()
        self.refresh_sources()
        return page


    def refresh_sources(self):
        sources = self.scanner.list_sources()
        self.source_table.setRowCount(len(sources))
        for row, source in enumerate(sources):
            values = [str(source["id"]), source["name"], source["root_path"], source["status"]]
            for column, value in enumerate(values):
                self.source_table.setItem(row, column, QTableWidgetItem(value))

    def add_media_source(self):
        selected = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta o unidad para inventariar"
        )
        if not selected:
            return
        try:
            self.scanner.add_source(Path(selected))
            self.refresh_sources()
            self.scan_status.setText("Ubicación registrada. Selecciónala y ejecuta el escaneo.")
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo registrar la ubicación", str(exc))

    def scan_selected_source(self):
        if self.scan_worker is not None and self.scan_worker.isRunning():
            QMessageBox.information(self, "Escaneo en curso", "Espera a que termine el escaneo actual.")
            return
        row = self.source_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selecciona una ubicación", "Selecciona una carpeta de la lista.")
            return
        source_id = int(self.source_table.item(row, 0).text())
        self.scan_status.setText("Escaneando… Puedes seguir utilizando la interfaz.")
        self.scan_worker = ScanWorker(self.scanner, source_id)
        self.scan_worker.completed.connect(self.on_scan_completed)
        self.scan_worker.failed.connect(self.on_scan_failed)
        self.scan_worker.start()

    def on_scan_completed(self, result):
        self.refresh_sources()
        self.refresh_movie_table()
        self.refresh_dashboard()
        self.scan_status.setText(
            f"Escaneo terminado: {result.files_found} archivos encontrados; "
            f"{result.files_added} nuevos; {result.files_updated} modificados; "
            f"{result.files_missing} no localizados; "
            f"{result.duplicate_groups} grupos candidatos a duplicado; "
            f"{result.probe_errors} errores de FFprobe."
        )
        if result.warnings:
            QMessageBox.warning(
                self, "Escaneo con advertencias",
                "\\n".join(result.warnings[:15])
            )

    def on_scan_failed(self, message: str):
        self.refresh_sources()
        self.scan_status.setText("El escaneo terminó con un error.")
        QMessageBox.critical(self, "Error de escaneo", message)

    def _build_settings(self):
        page, layout = self._page_shell(
            "Configuración",
            "Configura dónde ARCHIVUM guardará la base de datos, los carteles, la caché y las copias de seguridad."
        )
        panel = QFrame()
        panel.setObjectName("Panel")
        form = QVBoxLayout(panel)
        form.setContentsMargins(20, 20, 20, 20)
        label = QLabel("Carpeta de datos")
        label.setStyleSheet("font-weight: 650;")
        form.addWidget(label)
        row = QHBoxLayout()
        self.data_path_edit = QLineEdit(str(self.config.data_dir))
        row.addWidget(self.data_path_edit, 1)
        browse = QPushButton("Examinar…")
        browse.clicked.connect(self.browse_data_dir)
        row.addWidget(browse)
        form.addLayout(row)

        self.db_path_label = QLabel(f"Base de datos: {self.database.db_path}")
        self.db_path_label.setObjectName("Muted")
        self.db_path_label.setWordWrap(True)
        form.addWidget(self.db_path_label)

        warning = QLabel(
            "Cambiar la ubicación no mueve ni elimina los datos de la carpeta anterior. "
            "Si eliges una carpeta que ya contiene una base de datos ARCHIVUM, se utilizará esa base."
        )
        warning.setWordWrap(True)
        warning.setObjectName("Muted")
        form.addWidget(warning)

        buttons = QHBoxLayout()
        save = QPushButton("Guardar ubicación")
        save.setObjectName("Primary")
        save.clicked.connect(self.save_data_location)
        buttons.addWidget(save)
        open_folder = QPushButton("Abrir carpeta")
        open_folder.clicked.connect(self.open_data_folder)
        buttons.addWidget(open_folder)
        buttons.addStretch()
        form.addLayout(buttons)
        layout.addWidget(panel)
        layout.addStretch()
        return page

    def browse_data_dir(self):
        selected = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de datos", self.data_path_edit.text()
        )
        if selected:
            self.data_path_edit.setText(selected)

    def save_data_location(self):
        selected = Path(self.data_path_edit.text()).expanduser()
        if not selected.is_absolute():
            QMessageBox.warning(self, "Ruta no válida", "Selecciona una ruta absoluta.")
            return
        try:
            selected.mkdir(parents=True, exist_ok=True)
            self.database.change_location(selected)
            self.config.data_dir = selected
            self.config.save()
            self.db_path_label.setText(f"Base de datos: {self.database.db_path}")
            self.status_bar.showMessage(f"Datos: {selected}")
            self.refresh_dashboard()
            self.refresh_movie_table()
            QMessageBox.information(
                self, "Almacenamiento actualizado",
                "ARCHIVUM utilizará la ubicación seleccionada. La carpeta anterior no se ha modificado."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo cambiar la ubicación:\n{exc}")

    def open_data_folder(self):
        import os
        import subprocess
        import sys

        folder = self.database.data_dir
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(folder))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])

    def closeEvent(self, event):
        if self.scan_worker is not None and self.scan_worker.isRunning():
            self.scan_worker.wait()
        event.accept()

    def _placeholder(self, title: str, description: str):
        page, layout = self._page_shell(title, description)
        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        message = QLabel("Módulo planificado")
        message.setStyleSheet("font-size: 15pt; font-weight: 650;")
        panel_layout.addWidget(message)
        detail = QLabel("La navegación ya está preparada. La funcionalidad se desarrollará por fases.")
        detail.setObjectName("Muted")
        panel_layout.addWidget(detail)
        layout.addWidget(panel)
        layout.addStretch()
        return page
