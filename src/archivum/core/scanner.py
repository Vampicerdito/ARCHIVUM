from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from archivum.models.schema import MediaFile, MediaSource


VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".mov", ".m4v", ".mpg", ".mpeg",
    ".ts", ".m2ts", ".wmv", ".webm", ".ogv", ".vob",
}


@dataclass
class ScanResult:
    source_id: int
    files_found: int = 0
    files_added: int = 0
    files_updated: int = 0
    files_missing: int = 0
    duplicate_groups: int = 0
    probe_errors: int = 0
    warnings: list[str] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_path(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def quick_fingerprint(path: Path, size: int, chunk_size: int = 1024 * 1024) -> str:
    """Fingerprint first/last chunks to group duplicate candidates; not a full hash."""
    digest = hashlib.sha256()
    digest.update(str(size).encode("ascii"))
    with path.open("rb") as stream:
        digest.update(stream.read(chunk_size))
        if size > chunk_size:
            stream.seek(max(0, size - chunk_size))
            digest.update(stream.read(chunk_size))
    return "quick-sha256:" + digest.hexdigest()


def probe_media(path: Path, executable: str | None = None) -> dict:
    ffprobe = executable or shutil.which("ffprobe")
    if not ffprobe:
        return {}
    completed = subprocess.run(
        [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=30, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "FFprobe no pudo analizar el archivo")
    payload = json.loads(completed.stdout or "{}")
    streams = payload.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), {})
    audios = sorted({
        item.get("codec_name", "") for item in streams
        if item.get("codec_type") == "audio" and item.get("codec_name")
    })
    fmt = payload.get("format", {})
    fps = None
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate")
    if rate and rate != "0/0":
        try:
            numerator, denominator = rate.split("/", 1)
            fps = float(numerator) / float(denominator)
        except (ValueError, ZeroDivisionError):
            pass
    duration, bitrate = fmt.get("duration"), fmt.get("bit_rate")
    return {
        "container": (fmt.get("format_name") or "").split(",")[0] or None,
        "video_codec": video.get("codec_name"),
        "audio_codecs": ", ".join(audios) or None,
        "width": video.get("width"), "height": video.get("height"),
        "frame_rate": fps,
        "bitrate": int(bitrate) if str(bitrate or "").isdigit() else None,
        "duration_seconds": float(duration) if duration else None,
    }


class MediaScanner:
    def __init__(self, database):
        self.database = database

    def add_source(self, path: Path, name: str | None = None) -> dict:
        root = Path(path).expanduser()
        if not root.is_absolute():
            raise ValueError("La ruta debe ser absoluta.")
        if not root.exists() or not root.is_dir():
            raise ValueError("La ubicación no existe o no es una carpeta accesible.")
        normalized = normalize_path(root)
        with self.database.Session() as session:
            for source in session.scalars(select(MediaSource)).all():
                if normalize_path(Path(source.root_path)) == normalized:
                    return self._source_dict(source)
            source = MediaSource(
                name=(name or root.name or str(root))[:160],
                root_path=str(root.resolve()), source_type="local", status="pending",
            )
            session.add(source)
            session.commit()
            session.refresh(source)
            return self._source_dict(source)

    @staticmethod
    def _source_dict(source: MediaSource) -> dict:
        return {
            "id": source.id, "name": source.name, "root_path": source.root_path,
            "status": source.status,
            "last_scanned_at": source.last_scanned_at.isoformat() if source.last_scanned_at else "",
        }

    def list_sources(self) -> list[dict]:
        with self.database.Session() as session:
            return [
                self._source_dict(source)
                for source in session.scalars(select(MediaSource).order_by(MediaSource.name)).all()
            ]

    def scan_source(self, source_id: int) -> ScanResult:
        result = ScanResult(source_id=source_id, warnings=[])
        with self.database.Session() as session:
            source = session.get(MediaSource, source_id)
            if source is None:
                raise ValueError("La ubicación seleccionada ya no existe.")
            root = Path(source.root_path)
            if not root.exists() or not root.is_dir():
                source.status = "offline"
                session.commit()
                result.warnings.append(
                    "La unidad no está disponible. No se modificó la disponibilidad de sus archivos."
                )
                return result
            source.status = "scanning"
            session.commit()

        try:
            self._scan_accessible_root(source_id, root, result)
        except Exception:
            with self.database.Session() as session:
                source = session.get(MediaSource, source_id)
                if source:
                    source.status = "error"
                    session.commit()
            raise
        return result

    def _scan_accessible_root(self, source_id: int, root: Path, result: ScanResult) -> None:
        with self.database.Session() as session:
            existing = session.scalars(
                select(MediaFile).where(MediaFile.source_id == source_id)
            ).all()
            by_path = {normalize_path(Path(item.path)): item for item in existing}
            seen: set[str] = set()
            now = datetime.now(timezone.utc)

            traversal_errors: list[str] = []

            def on_walk_error(error):
                traversal_errors.append(str(error))
                result.warnings.append(f"No se pudo recorrer una carpeta: {error}")

            for directory, dirnames, filenames in os.walk(
                root, followlinks=False, onerror=on_walk_error
            ):
                dirnames[:] = [
                    name for name in dirnames if not (Path(directory) / name).is_symlink()
                ]
                for filename in filenames:
                    path = Path(directory) / filename
                    if path.suffix.lower() not in VIDEO_EXTENSIONS or path.is_symlink():
                        continue
                    try:
                        stat = path.stat()
                    except OSError as exc:
                        result.warnings.append(f"No se pudo leer {path}: {exc}")
                        continue
                    normalized = normalize_path(path)
                    seen.add(normalized)
                    result.files_found += 1
                    modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                    item = by_path.get(normalized)
                    is_new = item is None
                    previous_modified = item.modified_at if item else None
                    if previous_modified and previous_modified.tzinfo is None:
                        previous_modified = previous_modified.replace(tzinfo=timezone.utc)
                    is_changed = bool(item and (
                        item.size_bytes != stat.st_size or previous_modified != modified
                    ))
                    if is_new:
                        item = MediaFile(
                            source_id=source_id, path=str(path.resolve()), filename=path.name,
                            extension=path.suffix.lower(), availability="available",
                        )
                        session.add(item)
                        result.files_added += 1
                    elif is_changed:
                        result.files_updated += 1
                    if is_new or is_changed:
                        item.filename = path.name
                        item.extension = path.suffix.lower()
                        item.size_bytes = stat.st_size
                        item.modified_at = modified
                        try:
                            item.file_hash = quick_fingerprint(path, stat.st_size)
                        except OSError as exc:
                            result.warnings.append(f"No se pudo calcular huella de {path}: {exc}")
                        try:
                            for key, value in probe_media(path).items():
                                setattr(item, key, value)
                        except (OSError, RuntimeError, ValueError, json.JSONDecodeError,
                                subprocess.TimeoutExpired) as exc:
                            result.probe_errors += 1
                            result.warnings.append(f"FFprobe: {path.name}: {exc}")
                    item.availability = "available"
                    item.last_seen_at = now

            # A partial traversal must never mark unseen files as missing.
            if not traversal_errors:
                for item in existing:
                    if normalize_path(Path(item.path)) not in seen:
                        item.availability = "missing"
                        result.files_missing += 1

            source = session.get(MediaSource, source_id)
            source.status = "partial" if traversal_errors else "online"
            source.last_scanned_at = now
            session.commit()
        result.duplicate_groups = self._count_duplicate_groups()

    def _count_duplicate_groups(self) -> int:
        with self.database.Session() as session:
            rows = session.scalars(select(MediaFile).where(
                MediaFile.availability == "available",
                MediaFile.file_hash.is_not(None),
                MediaFile.size_bytes.is_not(None),
            )).all()
            groups: dict[tuple[int, str], int] = {}
            for item in rows:
                key = (item.size_bytes, item.file_hash)
                groups[key] = groups.get(key, 0) + 1
            return sum(count > 1 for count in groups.values())
