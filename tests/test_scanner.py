from pathlib import Path

from archivum.core.database import Database
from archivum.core.scanner import MediaScanner
from archivum.models.schema import MediaFile


def make_video(path: Path, payload: bytes = b"test-video-content"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_scanner_registers_source_and_indexes_video_files(tmp_path: Path):
    root = tmp_path / "movies"
    make_video(root / "Film A" / "film-a.mkv")
    make_video(root / "film-b.mp4", b"another-file")

    database = Database(tmp_path / "archive-data")
    database.initialize()
    scanner = MediaScanner(database)

    source = scanner.add_source(root)
    result = scanner.scan_source(source["id"])

    assert result.files_found == 2
    assert result.files_added == 2
    assert result.files_missing == 0
    assert len(scanner.list_sources()) == 1


def test_repeated_scan_does_not_create_duplicate_rows(tmp_path: Path):
    root = tmp_path / "movies"
    make_video(root / "film.mkv")
    database = Database(tmp_path / "archive-data")
    database.initialize()
    scanner = MediaScanner(database)
    source = scanner.add_source(root)

    first = scanner.scan_source(source["id"])
    second = scanner.scan_source(source["id"])

    assert first.files_added == 1
    assert second.files_added == 0
    assert second.files_updated == 0
    assert database.counts()["media_files"] == 1


def test_missing_file_is_marked_but_not_deleted(tmp_path: Path):
    root = tmp_path / "movies"
    video = make_video(root / "film.mkv")
    database = Database(tmp_path / "archive-data")
    database.initialize()
    scanner = MediaScanner(database)
    source = scanner.add_source(root)
    scanner.scan_source(source["id"])

    video.unlink()
    result = scanner.scan_source(source["id"])

    assert result.files_missing == 1
    with database.Session() as session:
        row = session.query(MediaFile).one()
        assert row.availability == "missing"


def test_offline_source_does_not_mark_files_missing(tmp_path: Path):
    root = tmp_path / "movies"
    make_video(root / "film.mkv")
    database = Database(tmp_path / "archive-data")
    database.initialize()
    scanner = MediaScanner(database)
    source = scanner.add_source(root)
    scanner.scan_source(source["id"])

    import shutil
    shutil.rmtree(root)
    result = scanner.scan_source(source["id"])

    assert result.files_missing == 0
    with database.Session() as session:
        row = session.query(MediaFile).one()
        assert row.availability == "available"
