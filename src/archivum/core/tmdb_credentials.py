from __future__ import annotations

import keyring
from keyring.errors import KeyringError

SERVICE_NAME = "ARCHIVUM"
TOKEN_KEY = "tmdb_access_token"


class TMDBCredentials:
    """Stores the TMDB API Read Access Token in the operating-system credential vault."""

    @staticmethod
    def save(token: str) -> None:
        clean = token.strip()
        if not clean:
            raise ValueError("El token de TMDB no puede estar vacío.")
        try:
            keyring.set_password(SERVICE_NAME, TOKEN_KEY, clean)
        except KeyringError as exc:
            raise RuntimeError(
                "No se pudo guardar el token en el almacén seguro de credenciales de Windows."
            ) from exc

    @staticmethod
    def load() -> str | None:
        try:
            return keyring.get_password(SERVICE_NAME, TOKEN_KEY)
        except KeyringError as exc:
            raise RuntimeError(
                "No se pudo acceder al almacén seguro de credenciales de Windows."
            ) from exc

    @staticmethod
    def delete() -> None:
        try:
            keyring.delete_password(SERVICE_NAME, TOKEN_KEY)
        except keyring.errors.PasswordDeleteError:
            pass
        except KeyringError as exc:
            raise RuntimeError("No se pudo eliminar el token guardado.") from exc
