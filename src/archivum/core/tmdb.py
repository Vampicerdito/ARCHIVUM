from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx
from sqlalchemy import select

from archivum.models.schema import (
    Artwork, Genre, Identifier, Movie, MovieGenre, OperationLog, Person, MovieCredit,
)

API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p"
KEYRING_SERVICE = "ARCHIVUM"
KEYRING_USERNAME = "tmdb_bearer_token"


class TMDBError(RuntimeError):
    pass


class TMDBClient:
    def __init__(self, token: str, timeout: float = 20.0):
        token = token.strip()
        if not token:
            raise TMDBError("No se ha configurado el token de lectura de TMDB.")
        self.token = token
        self.timeout = timeout

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        try:
            response = httpx.get(
                f"{API_BASE}/{endpoint.lstrip('/')}",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "accept": "application/json",
                },
                params=params or {},
                timeout=self.timeout,
            )
            if response.status_code == 401:
                raise TMDBError("TMDB rechazó el token. Comprueba el API Read Access Token.")
            if response.status_code == 429:
                raise TMDBError("TMDB ha limitado temporalmente las solicitudes. Inténtalo más tarde.")
            response.raise_for_status()
            return response.json()
        except TMDBError:
            raise
        except httpx.TimeoutException as exc:
            raise TMDBError("La conexión con TMDB agotó el tiempo de espera.") from exc
        except httpx.HTTPStatusError as exc:
            raise TMDBError(
                f"TMDB respondió con HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise TMDBError(f"No se pudo conectar con TMDB: {exc}") from exc
        except ValueError as exc:
            raise TMDBError("TMDB devolvió una respuesta JSON no válida.") from exc

    def test_connection(self) -> bool:
        payload = self._get("configuration")
        return bool(payload.get("images", {}).get("secure_base_url"))

    def search_movies(
        self, query: str, year: int | None = None, language: str = "es-ES"
    ) -> list[dict]:
        clean_query = query.strip()
        if not clean_query:
            raise TMDBError("Escribe un título para buscar.")
        params = {
            "query": clean_query,
            "language": language,
            "include_adult": "false",
            "page": 1,
        }
        if year:
            params["year"] = year
        payload = self._get("search/movie", params)
        return payload.get("results", [])[:20]

    def movie_details(self, tmdb_id: int, language: str = "es-ES") -> dict:
        return self._get(
            f"movie/{int(tmdb_id)}",
            {"language": language, "append_to_response": "external_ids,credits"},
        )

    def download_image(self, remote_path: str, destination: Path, size: str) -> Path:
        if not remote_path or not remote_path.startswith("/"):
            raise TMDBError("La ruta de imagen de TMDB no es válida.")
        url = f"{IMAGE_BASE}/{size}{quote(remote_path, safe='/')}"
        try:
            response = httpx.get(url, timeout=self.timeout, follow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise TMDBError("TMDB no devolvió un archivo de imagen.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            temporary.write_bytes(response.content)
            temporary.replace(destination)
            return destination
        except TMDBError:
            raise
        except (httpx.HTTPError, OSError) as exc:
            raise TMDBError(f"No se pudo descargar una imagen de TMDB: {exc}") from exc


def apply_movie_metadata(
    database,
    movie_id: int,
    details: dict,
    data_dir: Path,
    client: TMDBClient | None = None,
) -> list[str]:
    """Apply a user-confirmed TMDB match and cache available artwork locally."""
    warnings: list[str] = []
    tmdb_id = int(details["id"])
    release_text = details.get("release_date") or ""
    release_date = None
    if release_text:
        try:
            release_date = date.fromisoformat(release_text)
        except ValueError:
            warnings.append(f"Fecha de estreno no válida recibida de TMDB: {release_text}")

    with database.Session() as session:
        movie = session.get(Movie, movie_id)
        if movie is None:
            raise TMDBError("La ficha local ya no existe.")

        existing_identifier = session.scalar(
            select(Identifier).where(
                Identifier.provider == "tmdb", Identifier.value == str(tmdb_id)
            )
        )
        if existing_identifier and existing_identifier.movie_id != movie_id:
            raise TMDBError(
                "Esta película de TMDB ya está vinculada a otra ficha de ARCHIVUM."
            )

        movie.title = details.get("title") or movie.title
        movie.original_title = details.get("original_title") or movie.original_title
        movie.release_date = release_date
        movie.year = release_date.year if release_date else movie.year
        movie.overview = details.get("overview") or movie.overview
        movie.runtime_minutes = details.get("runtime") or movie.runtime_minutes
        movie.original_language = details.get("original_language") or movie.original_language
        countries = details.get("production_countries") or []
        if countries:
            movie.country = ", ".join(
                item.get("name", "") for item in countries if item.get("name")
            ) or movie.country
        rating = details.get("vote_average")
        if rating is not None:
            movie.tmdb_rating = float(rating)
        movie.status = "identified"
        movie.metadata_source = "tmdb"
        movie.metadata_updated_at = datetime.now(timezone.utc)

        if not existing_identifier:
            session.add(Identifier(
                movie_id=movie_id, provider="tmdb", value=str(tmdb_id)
            ))

        external_ids = details.get("external_ids") or {}
        imdb_id = external_ids.get("imdb_id")
        if imdb_id:
            imdb_existing = session.scalar(
                select(Identifier).where(
                    Identifier.provider == "imdb", Identifier.value == imdb_id
                )
            )
            if imdb_existing and imdb_existing.movie_id != movie_id:
                warnings.append("El identificador IMDb ya está asociado a otra ficha; se omitió.")
            elif not imdb_existing:
                session.add(Identifier(
                    movie_id=movie_id, provider="imdb", value=imdb_id
                ))

        for genre_data in details.get("genres") or []:
            name = (genre_data.get("name") or "").strip()
            if not name:
                continue
            genre = session.scalar(select(Genre).where(Genre.name == name))
            if genre is None:
                genre = Genre(name=name)
                session.add(genre)
                session.flush()
            linked = session.scalar(
                select(MovieGenre).where(
                    MovieGenre.movie_id == movie_id,
                    MovieGenre.genre_id == genre.id,
                )
            )
            if linked is None:
                session.add(MovieGenre(movie_id=movie_id, genre_id=genre.id))

        credits = details.get("credits") or {}
        credit_items = []
        for person_data in (credits.get("crew") or []):
            if person_data.get("job") == "Director":
                credit_items.append((person_data, "Directing", "Director", None))
        for person_data in (credits.get("cast") or [])[:20]:
            credit_items.append((
                person_data, "Acting", person_data.get("character") or "Cast",
                person_data.get("order"),
            ))
        for person_data, department, role, display_order in credit_items:
            person_tmdb_id = person_data.get("id")
            person_name = (person_data.get("name") or "").strip()
            if not person_tmdb_id or not person_name:
                continue
            person = session.scalar(
                select(Person).where(Person.tmdb_id == int(person_tmdb_id))
            )
            if person is None:
                person = Person(
                    name=person_name,
                    tmdb_id=int(person_tmdb_id),
                    profile_path=person_data.get("profile_path"),
                )
                session.add(person)
                session.flush()
            existing_credit = session.scalar(
                select(MovieCredit).where(
                    MovieCredit.movie_id == movie_id,
                    MovieCredit.person_id == person.id,
                    MovieCredit.department == department,
                    MovieCredit.role == role,
                )
            )
            if existing_credit is None:
                session.add(MovieCredit(
                    movie_id=movie_id,
                    person_id=person.id,
                    department=department,
                    role=role,
                    display_order=display_order,
                ))

        image_jobs = (
            ("poster", details.get("poster_path"), "posters", "w500"),
            ("backdrop", details.get("backdrop_path"), "backdrops", "w1280"),
        )
        for artwork_type, remote_path, folder, size in image_jobs:
            if not remote_path:
                continue
            existing_art = session.scalar(
                select(Artwork).where(
                    Artwork.movie_id == movie_id,
                    Artwork.artwork_type == artwork_type,
                    Artwork.remote_path == remote_path,
                )
            )
            if existing_art:
                continue
            local_path = None
            if client:
                suffix = Path(remote_path).suffix or ".jpg"
                destination = Path(data_dir) / "artwork" / folder / f"tmdb_{tmdb_id}{suffix}"
                try:
                    local_path = str(client.download_image(remote_path, destination, size))
                except TMDBError as exc:
                    warnings.append(str(exc))
            session.add(Artwork(
                movie_id=movie_id,
                artwork_type=artwork_type,
                local_path=local_path,
                remote_path=remote_path,
                language=details.get("original_language"),
                is_selected=(artwork_type == "poster"),
            ))

        session.add(OperationLog(
            operation_type="tmdb_identification",
            status="completed",
            description=f"Ficha «{movie.title}» identificada con TMDB ID {tmdb_id}.",
            details_json=f'{{"movie_id": {movie_id}, "tmdb_id": {tmdb_id}}}',
        ))
        session.commit()
    return warnings
