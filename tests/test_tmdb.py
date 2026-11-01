from pathlib import Path

import pytest
from sqlalchemy import select

from archivum.core.database import Database
from archivum.core.tmdb import TMDBClient, TMDBError, apply_movie_metadata
from archivum.models.schema import (
    Artwork, Genre, Identifier, Movie, MovieCredit, Person,
)


def make_database(tmp_path: Path):
    database = Database(tmp_path / "data")
    database.initialize()
    with database.Session() as session:
        movie = Movie(title="Título provisional", year=2020, status="unidentified")
        session.add(movie)
        session.commit()
        return database, movie.id


def test_tmdb_search_builds_expected_query(monkeypatch):
    client = TMDBClient("test-token")
    captured = {}

    def fake_get(endpoint, params=None):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {"results": [{
            "id": 123, "title": "La película", "original_title": "The Film",
            "release_date": "2020-04-02",
        }]}

    monkeypatch.setattr(client, "_get", fake_get)
    results = client.search_movies("La película", 2020)

    assert captured["endpoint"] == "search/movie"
    assert captured["params"]["year"] == 2020
    assert results[0]["id"] == 123


def test_tmdb_metadata_imports_identifiers_genres_credits_and_artwork(tmp_path):
    database, movie_id = make_database(tmp_path)
    details = {
        "id": 456,
        "title": "The Film",
        "original_title": "Film Original",
        "release_date": "2020-04-02",
        "overview": "Sinopsis de prueba",
        "runtime": 110,
        "original_language": "en",
        "vote_average": 7.5,
        "production_countries": [{"name": "United States"}],
        "genres": [{"id": 18, "name": "Drama"}],
        "poster_path": "/poster.jpg",
        "backdrop_path": "/backdrop.jpg",
        "external_ids": {"imdb_id": "tt1234567"},
        "credits": {
            "cast": [{"id": 11, "name": "Actor Uno", "character": "Protagonista", "order": 0}],
            "crew": [{"id": 22, "name": "Directora Uno", "job": "Director"}],
        },
    }

    warnings = apply_movie_metadata(database, movie_id, details, tmp_path / "data")

    with database.Session() as session:
        movie = session.get(Movie, movie_id)
        assert movie.title == "The Film"
        assert movie.original_title == "Film Original"
        assert movie.year == 2020
        assert movie.runtime_minutes == 110
        assert movie.status == "identified"
        assert session.scalar(select(Identifier).where(Identifier.provider == "tmdb")).value == "456"
        assert session.scalar(select(Identifier).where(Identifier.provider == "imdb")).value == "tt1234567"
        assert session.scalar(select(Genre).where(Genre.name == "Drama")) is not None
        assert session.scalar(select(Person).where(Person.tmdb_id == 11)) is not None
        assert session.scalar(select(Person).where(Person.tmdb_id == 22)) is not None
        assert len(session.scalars(select(MovieCredit).where(MovieCredit.movie_id == movie_id)).all()) == 2
        assert len(session.scalars(select(Artwork).where(Artwork.movie_id == movie_id)).all()) == 2
    assert warnings == []


def test_tmdb_id_cannot_be_assigned_to_two_local_movies(tmp_path):
    database, first_id = make_database(tmp_path)
    with database.Session() as session:
        second = Movie(title="Otra ficha")
        session.add(second)
        session.flush()
        second_id = second.id
        session.add(Identifier(movie_id=first_id, provider="tmdb", value="999"))
        session.commit()

    with pytest.raises(TMDBError, match="otra ficha"):
        apply_movie_metadata(
            database, second_id,
            {"id": 999, "title": "The Film"},
            tmp_path / "data",
        )


def test_tmdb_requires_non_empty_search_and_token():
    with pytest.raises(TMDBError):
        TMDBClient(" ")
    client = TMDBClient("test-token")
    with pytest.raises(TMDBError, match="título"):
        client.search_movies(" ")
