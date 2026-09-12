"""Chargement et validation de la configuration (variables d'environnement / .env).

On centralise ici pour typer fortement la configuration et échouer tôt
(fail-fast) si une variable obligatoire manque.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .logging_config import get_logger

logger = get_logger("config")


class ConfigError(RuntimeError):
    """Erreur de configuration (variable manquante ou invalide)."""


@dataclass(frozen=True)
class OracleConfig:
    user: str
    password: str
    connection_string: str
    pool_min: int
    pool_max: int
    pool_increment: int
    client_lib_dir: str | None  # mode Thick (optionnel)


@dataclass(frozen=True)
class AppConfig:
    oracle: OracleConfig
    query_max_rows: int  # plafond de lignes pour execute_query
    allow_dml: bool  # autorise ou non INSERT/UPDATE/DELETE


def _require_env(name: str) -> str:
    """Lit une variable obligatoire ; lève ConfigError si absente/vide."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        raise ConfigError(
            f"Variable d'environnement manquante : {name}. "
            f"Renseignez-la dans votre fichier .env (voir .env.example)."
        )
    return value


def _int_env(name: str, fallback: int) -> int:
    """Lit une variable entière optionnelle avec valeur par défaut."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return fallback
    try:
        return int(raw)
    except ValueError:
        logger.warning(
            "La variable %s=%r n'est pas un entier valide, "
            "utilisation de la valeur par défaut %d.",
            name,
            raw,
            fallback,
        )
        return fallback


def _bool_env(name: str, fallback: bool) -> bool:
    """Lit une variable booléenne optionnelle ('true'/'false')."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return fallback
    return raw.strip().lower() == "true"


def load_config() -> AppConfig:
    """Construit et valide la configuration. À appeler une fois au démarrage.

    Raises:
        ConfigError: si une variable obligatoire est absente.
    """
    load_dotenv()  # charge le .env s'il existe (sans écraser l'environnement réel)

    config = AppConfig(
        oracle=OracleConfig(
            user=_require_env("ORACLE_USER"),
            password=_require_env("ORACLE_PASSWORD"),
            connection_string=_require_env("ORACLE_CONNECTION_STRING"),
            pool_min=_int_env("ORACLE_POOL_MIN", 0),
            pool_max=_int_env("ORACLE_POOL_MAX", 4),
            pool_increment=_int_env("ORACLE_POOL_INCREMENT", 1),
            client_lib_dir=os.environ.get("ORACLE_CLIENT_LIB_DIR") or None,
        ),
        query_max_rows=_int_env("QUERY_MAX_ROWS", 100),
        allow_dml=_bool_env("ALLOW_DML", True),
    )

    # On ne loggue évidemment jamais le mot de passe.
    logger.debug(
        "Configuration chargée : user=%s, dsn=%s, pool=%d..%d, max_rows=%d, allow_dml=%s",
        config.oracle.user,
        config.oracle.connection_string,
        config.oracle.pool_min,
        config.oracle.pool_max,
        config.query_max_rows,
        config.allow_dml,
    )
    return config
