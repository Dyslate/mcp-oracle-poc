"""Outil `list_tables` : liste les tables du schéma courant (ou d'un schéma donné).

Purement en lecture seule.
"""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..config import AppConfig
from ..logging_config import get_logger
from ..oracle import get_connection
from .common import rows_to_dicts, to_json

logger = get_logger("tools.list_tables")


def register(mcp: FastMCP, _config: AppConfig) -> None:
    @mcp.tool()
    def list_tables(
        owner: Annotated[
            str | None,
            Field(description="Schéma dont lister les tables. Par défaut : l'utilisateur courant."),
        ] = None,
    ) -> str:
        """Liste les tables du schéma (lecture seule).

        Si 'owner' est fourni, liste les tables de ce schéma (ALL_TABLES) ;
        sinon liste les tables de l'utilisateur courant (USER_TABLES).
        """
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                if owner:
                    # Bind variable pour éviter l'injection.
                    cursor.execute(
                        "SELECT owner, table_name FROM all_tables "
                        "WHERE owner = UPPER(:owner) ORDER BY table_name",
                        {"owner": owner},
                    )
                else:
                    cursor.execute(
                        "SELECT table_name FROM user_tables ORDER BY table_name"
                    )
                rows = rows_to_dicts(cursor, cursor.fetchall())

            logger.info("list_tables : %d table(s) (owner=%s)", len(rows), owner or "(courant)")
            if not rows:
                suffix = f" pour le schéma {owner}" if owner else ""
                return f"Aucune table trouvée{suffix}."
            return to_json({"count": len(rows), "tables": rows})
        except Exception as exc:  # noqa: BLE001 (on renvoie l'erreur au client MCP)
            logger.exception("Erreur dans list_tables")
            return to_json({"error": f"Erreur lors de la récupération des tables : {exc}"})
