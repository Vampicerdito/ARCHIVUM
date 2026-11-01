from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from archivum.models.schema import Base


class Database:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir).expanduser()
        self.db_path = self.data_dir / "database" / "archivum.db"
        self.engine: Engine | None = None
        self.Session = None

    def initialize(self) -> None:
        self._create_directories()
        self._create_engine()
        Base.metadata.create_all(self.engine)
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Apply additive migrations to databases created by earlier versions."""
        with self.engine.begin() as connection:
            columns = {
                row[1] for row in connection.exec_driver_sql("PRAGMA table_info(media_files)")
            }
            if "modified_at" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE media_files ADD COLUMN modified_at DATETIME"
                )

    def _create_directories(self) -> None:
        for relative in (
            "database",
            "artwork/posters",
            "artwork/backdrops",
            "artwork/logos",
            "artwork/banners",
            "cache",
            "backups",
            "exports",
            "logs",
        ):
            (self.data_dir / relative).mkdir(parents=True, exist_ok=True)

    def _create_engine(self) -> None:
        if self.engine is not None:
            self.engine.dispose()

        self.engine = create_engine(
            f"sqlite:///{self.db_path.as_posix()}",
            future=True,
            connect_args={"check_same_thread": False, "timeout": 30},
        )

        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

        self.Session = sessionmaker(
            bind=self.engine, autoflush=False, expire_on_commit=False, future=True
        )

    def change_location(self, new_data_dir: Path) -> None:
        """Switch to a data directory, creating an empty DB if needed.

        Existing data is never moved or deleted automatically.
        """
        self.data_dir = Path(new_data_dir).expanduser()
        self.db_path = self.data_dir / "database" / "archivum.db"
        self._create_directories()
        self._create_engine()
        Base.metadata.create_all(self.engine)

    def health_check(self) -> bool:
        if self.engine is None:
            return False
        with self.engine.connect() as connection:
            return connection.execute(text("PRAGMA integrity_check")).scalar() == "ok"

    def counts(self) -> dict[str, int]:
        if self.engine is None:
            return {"movies": 0, "media_files": 0, "tasks": 0}
        with self.engine.connect() as connection:
            result = {}
            for table, key in (
                ("movies", "movies"),
                ("media_files", "media_files"),
                ("tasks", "tasks"),
            ):
                result[key] = int(
                    connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
                )
            return result
