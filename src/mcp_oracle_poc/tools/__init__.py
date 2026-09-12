"""Agrégation des outils : enregistre tous les tools sur le serveur MCP."""

from __future__ import annotations

from fastmcp import FastMCP

from ..config import AppConfig
from ..logging_config import get_logger
from . import describe_table, execute_dml, execute_query, list_tables

logger = get_logger("tools")


def register_all_tools(mcp: FastMCP, config: AppConfig) -> None:
    """Enregistre l'ensemble des outils MCP sur le serveur."""
    list_tables.register(mcp, config)
    describe_table.register(mcp, config)
    execute_query.register(mcp, config)
    execute_dml.register(mcp, config)
    logger.info(
        "Outils MCP enregistrés : list_tables, describe_table, execute_query, "
        "execute_dml (DML activé=%s)",
        config.allow_dml,
    )
