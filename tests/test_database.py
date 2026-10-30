from pathlib import Path

from archivum.core.database import Database
from archivum.models.schema import Movie


def test_database_initializes_and_integrity_is_ok(tmp_path: Path):
    database = Database(tmp_path / "archivum-data")
    database.initialize()

    assert database.db_path.exists()
    assert database.health_check()
    assert database.counts() == {"movies": 0, "media_files": 0, "tasks": 0}


def test_movie_can_be_persisted(tmp_path: Path):
    database = Database(tmp_path / "archivum-data")
    database.initialize()

    with database.Session() as session:
        session.add(Movie(title="The Godfather", year=1972))
        session.commit()

    assert database.counts()["movies"] == 1
