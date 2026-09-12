"""Gestion de la connexion Oracle : pool, exécution, fermeture, helpers de sécurité SQL.

On utilise un **pool de connexions** python-oracledb : plutôt que d'ouvrir/fermer
une connexion à chaque appel d'outil, on emprunte une connexion au pool puis on
la restitue (via un context manager). C'est plus performant et plus robuste.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Iterator

import oracledb

from .config import AppConfig
from .logging_config import get_logger

logger = get_logger("oracle")

# Pool global (unique pour ce POC). Initialisé par init_oracle().
_pool: "oracledb.ConnectionPool | None" = None


def init_oracle(config: AppConfig) -> None:
    """Initialise le driver et crée le pool de connexions. À appeler au démarrage."""
    global _pool
    if _pool is not None:
        logger.warning("init_oracle appelé alors que le pool est déjà initialisé.")
        return

    # Mode Thick optionnel (uniquement si un Instant Client est fourni).
    if config.oracle.client_lib_dir:
        try:
            oracledb.init_oracle_client(lib_dir=config.oracle.client_lib_dir)
            logger.info("Mode Thick activé (Instant Client : %s)", config.oracle.client_lib_dir)
        except Exception:
            logger.exception(
                "Échec de l'initialisation du client Oracle (mode Thick). "
                "Vérifiez ORACLE_CLIENT_LIB_DIR."
            )
            raise
    else:
        logger.info("Mode Thin (aucun client Oracle natif requis).")

    try:
        _pool = oracledb.create_pool(
            user=config.oracle.user,
            password=config.oracle.password,
            dsn=config.oracle.connection_string,
            min=config.oracle.pool_min,
            max=config.oracle.pool_max,
            increment=config.oracle.pool_increment,
        )
        logger.info(
            "Pool de connexions Oracle créé (dsn=%s, min=%d, max=%d).",
            config.oracle.connection_string,
            config.oracle.pool_min,
            config.oracle.pool_max,
        )
    except Exception:
        logger.exception("Impossible de créer le pool de connexions Oracle.")
        raise

    # Test de connectivité immédiat : on veut échouer tôt si Oracle est injoignable.
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            cursor.fetchone()
        logger.info("Connexion Oracle vérifiée avec succès.")
    except Exception:
        logger.exception("Le test de connectivité Oracle a échoué.")
        raise


@contextmanager
def get_connection() -> Iterator["oracledb.Connection"]:
    """Emprunte une connexion au pool et la restitue toujours (try/finally)."""
    if _pool is None:
        raise RuntimeError("Le pool Oracle n'est pas initialisé (appelez init_oracle).")
    conn = _pool.acquire()
    try:
        yield conn
    finally:
        try:
            conn.close()  # restitue la connexion au pool
        except Exception:
            logger.warning("Échec de la restitution d'une connexion au pool.", exc_info=True)


def close_oracle() -> None:
    """Ferme proprement le pool. À appeler à l'arrêt du serveur."""
    global _pool
    if _pool is None:
        return
    try:
        _pool.close(force=True)
        logger.info("Pool de connexions Oracle fermé.")
    except Exception:
        logger.exception("Erreur lors de la fermeture du pool Oracle.")
    finally:
        _pool = None


# ============================================================================
# Helpers de sécurité SQL
# ============================================================================

# Mots-clés dangereux / interdits partout (DDL, PL/SQL, transactions...).
_FORBIDDEN_KEYWORDS = [
    "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE", "MERGE",
    "COMMIT", "ROLLBACK", "SAVEPOINT", "EXEC", "EXECUTE", "BEGIN",
    "DECLARE", "CALL",
]

_DML_KEYWORDS = {"INSERT", "UPDATE", "DELETE"}

# Regex de suppression des chaînes littérales '...' (gère les '' échappés),
# pour ne pas compter les ';' ou mots-clés qui s'y trouvent.
_STRING_LITERAL_RE = re.compile(r"'(?:[^']|'')*'")


def normalize_sql(sql: str) -> str:
    """Retire un éventuel point-virgule final et les espaces superflus."""
    return re.sub(r";+\s*$", "", sql.strip()).strip()


def _strip_strings(sql: str) -> str:
    """Remplace les chaînes littérales par des vides pour l'analyse."""
    return _STRING_LITERAL_RE.sub("''", sql)


def is_single_statement(sql: str) -> bool:
    """Vrai s'il n'y a qu'UNE instruction (protection anti 'stacked queries')."""
    inner = normalize_sql(_strip_strings(sql))
    return ";" not in inner


def first_keyword(sql: str) -> str:
    """Premier mot-clé SQL en majuscules (SELECT, INSERT, ...)."""
    match = re.match(r"\s*([A-Za-z]+)", normalize_sql(sql))
    return match.group(1).upper() if match else ""


def is_read_only_query(sql: str) -> bool:
    """Vrai si la requête est un SELECT (ou une CTE WITH ... SELECT)."""
    return first_keyword(sql) in {"SELECT", "WITH"}


def is_allowed_dml(sql: str) -> bool:
    """Vrai si la requête est un DML autorisé (INSERT/UPDATE/DELETE)."""
    return first_keyword(sql) in _DML_KEYWORDS


def contains_forbidden_keyword(sql: str) -> str | None:
    """Renvoie le premier mot-clé interdit détecté (mot entier), sinon None."""
    upper = _strip_strings(sql).upper()
    for kw in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper):
            return kw
    return None
