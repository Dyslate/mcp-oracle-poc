"""Configuration du logging.

IMPORTANT (contrainte MCP stdio) :
Un serveur MCP qui communique via stdio utilise **stdout** pour le protocole
JSON-RPC. On ne doit donc JAMAIS écrire de logs sur stdout, sous peine de
corrompre les messages échangés avec le client (Claude Desktop / Claude Code).
On force donc tous les logs sur **stderr**.
"""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def setup_logging() -> logging.Logger:
    """Configure et renvoie le logger racine du serveur (sortie sur stderr)."""
    global _CONFIGURED
    logger = logging.getLogger("mcp_oracle_poc")

    if not _CONFIGURED:
        level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)

        handler = logging.StreamHandler(stream=sys.stderr)  # stderr uniquement
        handler.setFormatter(
            logging.Formatter(
                fmt="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        logger.setLevel(level)
        logger.addHandler(handler)
        logger.propagate = False  # évite la double émission via le root logger
        _CONFIGURED = True

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Renvoie un logger enfant du logger du serveur."""
    base = setup_logging()
    return base.getChild(name) if name else base
