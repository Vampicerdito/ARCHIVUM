from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from archivum.models.schema import MediaFile, Movie, OperationLog


class LibraryIntake:
    """Turns reviewed inventory files into a movie record without touching source files."""

    def __init__(self, database):
        self.database = database

    def list_unassigned_files(self) -> list[dict]:
        with self.database.Session() as session:
            files = session.scalars(
                select(MediaFile)
                .where(MediaFile.movie_id.is_(None), MediaFile.availability == "available")
                .order_by(MediaFile.path)
            ).all()
            return [
                {
                    "id": item.id,
                    "filename": item.filename,
                    "path": item.path,
                    "folder": Path(item.path).parent.name or str(Path(item.path).parent),
                    "size_bytes": item.size_bytes or 0,
                    "width": item.width,
                    "height": item.height,
                    "duration_seconds": item.duration_seconds,
                    "video_codec": item.video_codec,
                }
                for item in files
            ]

    def create_movie_from_files(
        self, file_ids: list[int], title: str, year: int | None = None
    ) -> int:
        clean_title = title.strip()
        unique_ids = list(dict.fromkeys(int(value) for value in file_ids))
        if not clean_title:
            raise ValueError("El título de la película no puede estar vacío.")
        if not unique_ids:
            raise ValueError("Selecciona al menos un archivo.")
        if year is not None and not 1880 <= year <= 2200:
            raise ValueError("El año debe estar entre 1880 y 2200.")

        with self.database.Session() as session:
            files = session.scalars(
                select(MediaFile).where(MediaFile.id.in_(unique_ids))
            ).all()
            if len(files) != len(unique_ids):
                raise ValueError("Uno o más archivos seleccionados ya no existen.")
            assigned = [item.filename for item in files if item.movie_id is not None]
            if assigned:
                raise ValueError(
                    "Algunos archivos ya pertenecen a otra película: " + ", ".join(assigned)
                )
            unavailable = [item.filename for item in files if item.availability != "available"]
            if unavailable:
                raise ValueError(
                    "Solo se pueden importar archivos disponibles: " + ", ".join(unavailable)
                )

            movie = Movie(title=clean_title, year=year, status="unidentified")
            session.add(movie)
            session.flush()
            for item in files:
                item.movie_id = movie.id

            session.add(OperationLog(
                operation_type="library_intake",
                status="completed",
                description=f"Creada la ficha «{clean_title}» con {len(files)} archivo(s).",
                details_json=json.dumps(
                    {"movie_id": movie.id, "media_file_ids": unique_ids},
                    ensure_ascii=False,
                ),
            ))
            session.commit()
            return movie.id
