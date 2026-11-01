from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class MediaSource(Base):
    __tablename__ = "media_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(30), default="local")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="source")


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        Index("ix_movies_title", "title"),
        Index("ix_movies_original_title", "original_title"),
        Index("ix_movies_year", "year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_title: Mapped[str | None] = mapped_column(String(500))
    sort_title: Mapped[str | None] = mapped_column(String(500))
    year: Mapped[int | None] = mapped_column(Integer)
    release_date: Mapped[Date | None] = mapped_column(Date)
    overview: Mapped[str | None] = mapped_column(Text)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer)
    original_language: Mapped[str | None] = mapped_column(String(12))
    country: Mapped[str | None] = mapped_column(String(120))
    certification: Mapped[str | None] = mapped_column(String(40))
    tmdb_rating: Mapped[float | None] = mapped_column(Float)
    user_rating: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="unidentified")
    metadata_source: Mapped[str | None] = mapped_column(String(80))
    metadata_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    media_files: Mapped[list["MediaFile"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )
    identifiers: Mapped[list["Identifier"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )
    artwork: Mapped[list["Artwork"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )
    credits: Mapped[list["MovieCredit"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )
    movie_genres: Mapped[list["MovieGenre"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )


class MediaFile(Base):
    __tablename__ = "media_files"
    __table_args__ = (
        UniqueConstraint("path", name="uq_media_files_path"),
        Index("ix_media_files_hash", "file_hash"),
        Index("ix_media_files_movie_id", "movie_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int | None] = mapped_column(ForeignKey("movies.id", ondelete="SET NULL"))
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_sources.id", ondelete="SET NULL")
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    extension: Mapped[str | None] = mapped_column(String(20))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    file_hash: Mapped[str | None] = mapped_column(String(128))
    container: Mapped[str | None] = mapped_column(String(40))
    video_codec: Mapped[str | None] = mapped_column(String(80))
    audio_codecs: Mapped[str | None] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    frame_rate: Mapped[float | None] = mapped_column(Float)
    bitrate: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    availability: Mapped[str] = mapped_column(String(30), default="unknown")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    movie: Mapped[Movie | None] = relationship(back_populates="media_files")
    source: Mapped[MediaSource | None] = relationship(back_populates="media_files")


class Identifier(Base):
    __tablename__ = "identifiers"
    __table_args__ = (UniqueConstraint("provider", "value", name="uq_identifier_provider_value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    movie: Mapped[Movie] = relationship(back_populates="identifiers")


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (Index("ix_people_name", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    imdb_id: Mapped[str | None] = mapped_column(String(30), unique=True)
    biography: Mapped[str | None] = mapped_column(Text)
    profile_path: Mapped[str | None] = mapped_column(Text)


class MovieCredit(Base):
    __tablename__ = "movie_credits"
    __table_args__ = (UniqueConstraint("movie_id", "person_id", "department", "role", name="uq_movie_credit"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"))
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[str | None] = mapped_column(String(300))
    display_order: Mapped[int | None] = mapped_column(Integer)
    movie: Mapped[Movie] = relationship(back_populates="credits")
    person: Mapped[Person] = relationship()


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)


class MovieGenre(Base):
    __tablename__ = "movie_genres"
    __table_args__ = (UniqueConstraint("movie_id", "genre_id", name="uq_movie_genre"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id", ondelete="CASCADE"))
    movie: Mapped[Movie] = relationship(back_populates="movie_genres")
    genre: Mapped[Genre] = relationship()


class Artwork(Base):
    __tablename__ = "artwork"
    __table_args__ = (Index("ix_artwork_movie_type", "movie_id", "artwork_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    artwork_type: Mapped[str] = mapped_column(String(40), nullable=False)
    local_path: Mapped[str | None] = mapped_column(Text)
    remote_path: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(12))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    movie: Mapped[Movie] = relationship(back_populates="artwork")


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CollectionItem(Base):
    __tablename__ = "collection_items"
    __table_args__ = (UniqueConstraint("collection_id", "movie_id", name="uq_collection_movie"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    payload_json: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
