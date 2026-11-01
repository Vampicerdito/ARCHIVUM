from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QStackedWidget,
    QStatusBar, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QAbstractItemView, QInputDialog,
)

from archivum.core.config import AppConfig
from archivum.core.database import Database
from archivum.core.scanner import MediaScanner
from archivum.core.library import LibraryIntake
from archivum.core.tmdb import TMDBClient, TMDBError, apply_movie_metadata
from archivum.core.tmdb_credentials import TMDBCredentials
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
        self.library_intake = LibraryIntake(database)
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
            "Fichas cinematográficas y archivos asociados. La incorporación de archivos requiere revisión."
        )
        toolbar = QHBoxLayout()
        self.movie_search = QLineEdit()
        self.movie_search.setPlaceholderText("Buscar por título…")
        self.movie_search.textChanged.connect(self.filter_library)
        toolbar.addWidget(self.movie_search, 1)
        add_button = QPushButton("Crear ficha manual")
        add_button.setObjectName("Primary")
        add_button.clicked.connect(self.add_sample_movie)
        toolbar.addWidget(add_button)
        layout.addLayout(toolbar)

        intake_panel = QFrame()
        intake_panel.setObjectName("Panel")
        intake_layout = QVBoxLayout(intake_panel)
        intake_layout.setContentsMargins(16, 14, 16, 14)
        intake_layout.addWidget(QLabel("Archivos inventariados sin ficha"))
        self.unassigned_table = QTableWidget(0, 5)
        self.unassigned_table.setHorizontalHeaderLabels(
            ["ID", "Archivo", "Carpeta", "Resolución", "Duración"]
        )
        self.unassigned_table.setColumnHidden(0, True)
        self.unassigned_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.unassigned_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.unassigned_table.horizontalHeader().setStretchLastSection(True)
        self.unassigned_table.horizontalHeader().setSectionResizeMode(
            1, self.unassigned_table.horizontalHeader().ResizeMode.Stretch
        )
        intake_layout.addWidget(self.unassigned_table)
        intake_actions = QHBoxLayout()
        refresh_unassigned = QPushButton("Actualizar archivos")
        refresh_unassigned.clicked.connect(self.refresh_unassigned_files)
        intake_actions.addWidget(refresh_unassigned)
        create_from_files = QPushButton("Crear película con archivos seleccionados")
        create_from_files.setObjectName("Primary")
        create_from_files.clicked.connect(self.create_movie_from_selected_files)
        intake_actions.addWidget(create_from_files)
        intake_actions.addStretch()
        intake_layout.addLayout(intake_actions)
        layout.addWidget(intake_panel)

        tmdb_panel = QFrame()
        tmdb_panel.setObjectName("Panel")
        tmdb_layout = QVBoxLayout(tmdb_panel)
        tmdb_layout.setContentsMargins(16, 14, 16, 14)
        tmdb_layout.addWidget(QLabel("Identificación mediante TMDB"))
        tmdb_search_row = QHBoxLayout()
        self.tmdb_query_edit = QLineEdit()
        self.tmdb_query_edit.setPlaceholderText("Título que quieres buscar en TMDB…")
        tmdb_search_row.addWidget(self.tmdb_query_edit, 1)
        self.tmdb_year_edit = QLineEdit()
        self.tmdb_year_edit.setPlaceholderText("Año")
        self.tmdb_year_edit.setMaximumWidth(90)
        tmdb_search_row.addWidget(self.tmdb_year_edit)
        search_tmdb = QPushButton("Buscar candidatos")
        search_tmdb.setObjectName("Primary")
        search_tmdb.clicked.connect(self.search_tmdb)
        tmdb_search_row.addWidget(search_tmdb)
        tmdb_layout.addLayout(tmdb_search_row)
        self.tmdb_candidates = QTableWidget(0, 5)
        self.tmdb_candidates.setHorizontalHeaderLabels(
            ["TMDB ID", "Título", "Título original", "Estreno", "Puntuación"]
        )
        self.tmdb_candidates.setColumnHidden(0, True)
        self.tmdb_candidates.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tmdb_candidates.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tmdb_candidates.horizontalHeader().setStretchLastSection(True)
        self.tmdb_candidates.horizontalHeader().setSectionResizeMode(
            1, self.tmdb_candidates.horizontalHeader().ResizeMode.Stretch
        )
        tmdb_layout.addWidget(self.tmdb_candidates)
        tmdb_actions = QHBoxLayout()
        identify_button = QPushButton("Confirmar identificación para película seleccionada")
        identify_button.setObjectName("Primary")
        identify_button.clicked.connect(self.import_selected_tmdb_candidate)
        tmdb_actions.addWidget(identify_button)
        tmdb_actions.addStretch()
        tmdb_layout.addLayout(tmdb_actions)
        self.tmdb_status = QLabel(
            "Selecciona primero una ficha de la biblioteca. La importación requiere confirmación."
        )
        self.tmdb_status.setObjectName("Muted")
        self.tmdb_status.setWordWrap(True)
        tmdb_layout.addWidget(self.tmdb_status)
        layout.addWidget(tmdb_panel)

        self.movie_table = QTableWidget(0, 5)
        self.movie_table.setHorizontalHeaderLabels(["ID", "Título", "Título original", "Año", "Estado"])
        self.movie_table.setColumnHidden(0, True)
        self.movie_table.setAlternatingRowColors(True)
        self.movie_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.movie_table.horizontalHeader().setStretchLastSection(True)
        self.movie_table.horizontalHeader().setSectionResizeMode(0, self.movie_table.horizontalHeader().ResizeMode.Stretch)
        self.movie_table.horizontalHeader().setSectionResizeMode(1, self.movie_table.horizontalHeader().ResizeMode.Stretch)
        layout.addWidget(self.movie_table, 1)
        self.refresh_movie_table()
        self.refresh_unassigned_files()
        return page

    def search_tmdb(self):
        query = self.tmdb_query_edit.text().strip()
        year_text = self.tmdb_year_edit.text().strip()
        year = None
        if year_text:
            if not year_text.isdigit() or not 1880 <= int(year_text) <= 2200:
                QMessageBox.warning(self, "Año no válido", "Introduce un año entre 1880 y 2200.")
                return
            year = int(year_text)
        try:
            token = TMDBCredentials.load()
            if not token:
                raise TMDBError("Configura primero el Read Access Token en Configuración.")
            candidates = TMDBClient(token).search_movies(query, year)
        except Exception as exc:
            QMessageBox.warning(self, "Error en la búsqueda TMDB", str(exc))
            return
        self.tmdb_candidates.setRowCount(len(candidates))
        for row, candidate in enumerate(candidates):
            values = [
                str(candidate.get("id", "")),
                candidate.get("title") or "",
                candidate.get("original_title") or "",
                candidate.get("release_date") or "—",
                f"{float(candidate.get('vote_average') or 0):.1f}",
            ]
            for column, value in enumerate(values):
                self.tmdb_candidates.setItem(row, column, QTableWidgetItem(value))
        self.tmdb_status.setText(
            f"TMDB devolvió {len(candidates)} candidato(s). Selecciona uno y una ficha local para comparar."
        )

    def import_selected_tmdb_candidate(self):
        candidate_row = self.tmdb_candidates.currentRow()
        movie_row = self.movie_table.currentRow()
        if candidate_row < 0:
            QMessageBox.information(self, "Selecciona un candidato", "Selecciona un resultado de TMDB.")
            return
        if movie_row < 0:
            QMessageBox.information(
                self, "Selecciona una película local",
                "Selecciona primero la ficha de la biblioteca que quieres identificar."
            )
            return
        tmdb_id = int(self.tmdb_candidates.item(candidate_row, 0).text())
        local_movie_id = int(self.movie_table.item(movie_row, 0).text())
        candidate_title = self.tmdb_candidates.item(candidate_row, 1).text()
        candidate_year = self.tmdb_candidates.item(candidate_row, 3).text()
        answer = QMessageBox.question(
            self, "Confirmar identificación",
            f"¿Vincular la ficha local seleccionada con este resultado de TMDB?\n\n"
            f"{candidate_title} ({candidate_year})\nTMDB ID: {tmdb_id}\n\n"
            "Se actualizarán los metadatos de la ficha. Los archivos de vídeo no se modificarán.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            token = TMDBCredentials.load()
            if not token:
                raise TMDBError("No hay un token TMDB guardado.")
            client = TMDBClient(token)
            details = client.movie_details(tmdb_id)
            warnings = apply_movie_metadata(
                self.database, local_movie_id, details, self.database.data_dir, client
            )
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo identificar la película", str(exc))
            return
        self.refresh_movie_table()
        self.refresh_dashboard()
        self.tmdb_status.setText(
            f"Ficha identificada correctamente con TMDB ID {tmdb_id}."
        )
        if warnings:
            QMessageBox.warning(
                self, "Identificación completada con advertencias", "\n".join(warnings)
            )
        else:
            QMessageBox.information(
                self, "Identificación completada",
                "Los metadatos se han importado. Los archivos originales permanecen intactos."
            )

    def refresh_unassigned_files(self):
        files = self.library_intake.list_unassigned_files()
        self.unassigned_table.setRowCount(len(files))
        for row, item in enumerate(files):
            width, height = item["width"] or "?", item["height"] or "?"
            resolution = f"{width} × {height}"
            duration = f"{item['duration_seconds'] / 60:.1f} min" if item["duration_seconds"] else "—"
            values = [str(item["id"]), item["filename"], item["folder"], resolution, duration]
            for column, value in enumerate(values):
                self.unassigned_table.setItem(row, column, QTableWidgetItem(value))

    def create_movie_from_selected_files(self):
        selected_rows = sorted({
            index.row() for index in self.unassigned_table.selectionModel().selectedRows()
        })
        if not selected_rows:
            QMessageBox.information(
                self, "Selecciona archivos", "Selecciona uno o varios archivos sin ficha."
            )
            return
        file_ids = [
            int(self.unassigned_table.item(row, 0).text()) for row in selected_rows
        ]
        title, accepted = QInputDialog.getText(self, "Crear película", "Título de la película:")
        if not accepted or not title.strip():
            return
        year, accepted_year = QInputDialog.getInt(
            self, "Año de estreno", "Año (0 si se desconoce):", 0, 0, 2200
        )
        if not accepted_year:
            return
        try:
            self.library_intake.create_movie_from_files(file_ids, title, year or None)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo crear la película", str(exc))
            return
        self.refresh_movie_table()
        self.refresh_unassigned_files()
        self.refresh_dashboard()
        QMessageBox.information(
            self, "Película creada",
            f"Se creó «{title.strip()}» y se asociaron {len(file_ids)} archivo(s). "
            "Los originales no se modificaron."
        )

    def refresh_movie_table(self):
        from sqlalchemy import select
        from archivum.models.schema import Movie

        with self.database.Session() as session:
            movies = session.scalars(select(Movie).order_by(Movie.title)).all()
            self.movie_table.setRowCount(len(movies))
            for row, movie in enumerate(movies):
                values = [str(movie.id), movie.title, movie.original_title or "", str(movie.year or ""), movie.status]
                for column, value in enumerate(values):
                    self.movie_table.setItem(row, column, QTableWidgetItem(value))

    def filter_library(self, query: str):
        query = query.casefold().strip()
        for row in range(self.movie_table.rowCount()):
            title = self.movie_table.item(row, 1).text().casefold()
            original = self.movie_table.item(row, 2).text().casefold()
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

        tmdb_label = QLabel("Conexión con The Movie Database (TMDB)")
        tmdb_label.setStyleSheet("font-weight: 650;")
        form.addWidget(tmdb_label)
        tmdb_description = QLabel(
            "Pega el API Read Access Token de TMDB. Se guarda en el almacén seguro de credenciales "
            "del sistema operativo; no se escribe en settings.json ni en la base de datos."
        )
        tmdb_description.setObjectName("Muted")
        tmdb_description.setWordWrap(True)
        form.addWidget(tmdb_description)
        token_row = QHBoxLayout()
        self.tmdb_token_edit = QLineEdit()
        self.tmdb_token_edit.setEchoMode(QLineEdit.Password)
        self.tmdb_token_edit.setPlaceholderText("API Read Access Token")
        token_row.addWidget(self.tmdb_token_edit, 1)
        save_token = QPushButton("Guardar token")
        save_token.setObjectName("Primary")
        save_token.clicked.connect(self.save_tmdb_token)
        token_row.addWidget(save_token)
        test_token = QPushButton("Probar conexión")
        test_token.clicked.connect(self.test_tmdb_connection)
        token_row.addWidget(test_token)
        delete_token = QPushButton("Eliminar")
        delete_token.clicked.connect(self.delete_tmdb_token)
        token_row.addWidget(delete_token)
        form.addLayout(token_row)
        self.tmdb_credentials_status = QLabel("Estado de credenciales: comprobando…")
        self.tmdb_credentials_status.setObjectName("Muted")
        form.addWidget(self.tmdb_credentials_status)
        self.refresh_tmdb_credential_status()

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

    def refresh_tmdb_credential_status(self):
        try:
            configured = bool(TMDBCredentials.load())
            self.tmdb_credentials_status.setText(
                "Estado de credenciales: token guardado." if configured
                else "Estado de credenciales: sin configurar."
            )
        except Exception as exc:
            self.tmdb_credentials_status.setText(f"Almacén de credenciales no disponible: {exc}")

    def save_tmdb_token(self):
        token = self.tmdb_token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "Token vacío", "Pega primero el Read Access Token de TMDB.")
            return
        try:
            TMDBCredentials.save(token)
            self.tmdb_token_edit.clear()
            self.refresh_tmdb_credential_status()
            QMessageBox.information(
                self, "Token guardado",
                "El token se ha guardado en el almacén seguro de credenciales del sistema."
            )
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo guardar el token", str(exc))

    def test_tmdb_connection(self):
        try:
            token = self.tmdb_token_edit.text().strip() or TMDBCredentials.load()
            if not token:
                raise TMDBError("Guarda o introduce primero el Read Access Token.")
            if TMDBClient(token).test_connection():
                QMessageBox.information(self, "TMDB conectado", "La autenticación con TMDB funciona.")
        except Exception as exc:
            QMessageBox.warning(self, "Error de conexión TMDB", str(exc))

    def delete_tmdb_token(self):
        answer = QMessageBox.question(
            self, "Eliminar token TMDB",
            "¿Eliminar el token guardado en el almacén de credenciales del sistema?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            TMDBCredentials.delete()
            self.refresh_tmdb_credential_status()
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo eliminar el token", str(exc))

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
