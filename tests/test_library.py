from pathlib import Path

import pytest

from archivum.core.database import Database
from archivum.core.library import LibraryIntake
from archivum.core.scanner import MediaScanner
from archivum.models.schema import MediaFile, Movie, OperationLog


def make_video(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-video")


def test_reviewed_intake_creates_movie_and_links_files(tmp_path: Path):
    root = tmp_path / "movies"
    make_video(root / "Film A" / "film-a.mkv")
    make_video(root / "Film A" / "film-a-extra.mp4")

    database = Database(tmp_path / "data")
    database.initialize()
    scanner = MediaScanner(database)
    source = scanner.add_source(root)
    scanner.scan_source(source["id"])

    intake = LibraryIntake(database)
    unassigned = intake.list_unassigned_files()
    movie_id = intake.create_movie_from_files(
        [item["id"] for item in unassigned], "Film A", 1999
    )

    with database.Session() as session:
        movie = session.get(Movie, movie_id)
        linked = session.query(MediaFile).filter_by(movie_id=movie_id).all()
        log = session.query(OperationLog).filter_by(operation_type="library_intake").one()
        assert movie.title == "Film A"
        assert movie.year == 1999
        assert len(linked) == 2
        assert log.status == "completed"
    assert intake.list_unassigned_files() == []


def test_intake_rejects_file_already_assigned(tmp_path: Path):
    root = tmp_path / "movies"
    make_video(root / "film.mkv")
    database = Database(tmp_path / "data")
    database.initialize()
    scanner = MediaScanner(database)
    source = scanner.add_source(root)
    scanner.scan_source(source["id"])
    intake = LibraryIntake(database)
    file_id = intake.list_unassigned_files()[0]["id"]

    intake.create_movie_from_files([file_id], "First movie")
    with pytest.raises(ValueError, match="pertenecen"):
        intake.create_movie_from_files([file_id], "Second movie")


def test_intake_rejects_empty_title_and_selection(tmp_path: Path):
    database = Database(tmp_path / "data")
    database.initialize()
    intake = LibraryIntake(database)
    with pytest.raises(ValueError, match="título"):
        intake.create_movie_from_files([1], " ")
    with pytest.raises(ValueError, match="Selecciona"):
        intake.create_movie_from_files([], "Film")
