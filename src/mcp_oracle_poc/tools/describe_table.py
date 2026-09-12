"""Outil `describe_table` : décrit les colonnes d'une table. Lecture seule."""

from __future__ import annotations

import re
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..config import AppConfig
from ..logging_config import get_logger
from ..oracle import get_connection
from .common import to_json

logger = get_logger("tools.describe_table")

# Identifiant Oracle sûr (nom de table / schéma) : évite toute injection.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$#]*$")


def _valid_identifier(value: str) -> bool:
    return bool(value) and len(value) <= 128 and _IDENTIFIER_RE.match(value) is not None


def _format_type(row: dict[str, Any]) -> str:
    """Représentation lisible du type, ex. NUMBER(10,2) ou VARCHAR2(255)."""
    t = row["DATA_TYPE"]
    if t == "NUMBER":
        if row["DATA_PRECISION"] is not None:
            if row["DATA_SCALE"]:
                return f"NUMBER({row['DATA_PRECISION']},{row['DATA_SCALE']})"
            return f"NUMBER({row['DATA_PRECISION']})"
        return "NUMBER"
    if t in ("VARCHAR2", "CHAR", "NVARCHAR2", "NCHAR", "RAW"):
        return f"{t}({row['DATA_LENGTH']})"
    return t


def register(mcp: FastMCP, _config: AppConfig) -> None:
    @mcp.tool()
    def describe_table(
        table_name: Annotated[str, Field(description="Nom de la table à décrire.")],
        owner: Annotated[
            str | None,
            Field(description="Schéma propriétaire. Par défaut : l'utilisateur courant."),
        ] = None,
    ) -> str:
        """Décrit les colonnes d'une table : nom, type, nullabilité (lecture seule)."""
        # Validation stricte des identifiants.
        if not _valid_identifier(table_name):
            return to_json({"error": f"Nom de table invalide : {table_name!r}."})
        if owner is not None and not _valid_identifier(owner):
            return to_json({"error": f"Nom de schéma invalide : {owner!r}."})

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT column_id, column_name, data_type, data_length,
                           data_precision, data_scale, nullable
                      FROM all_tab_columns
                     WHERE table_name = UPPER(:table_name)
                       AND owner = UPPER(NVL(:owner, USER))
                     ORDER BY column_id
                    """,
                    {"table_name": table_name, "owner": owner},
                )
                cols = [c[0] for c in cursor.description]
                raw_rows = [dict(zip(cols, r)) for r in cursor.fetchall()]

            logger.info(
                "describe_table : %s (owner=%s) -> %d colonne(s)",
                table_name, owner or "(courant)", len(raw_rows),
            )

            if not raw_rows:
                target = f"{owner + '.' if owner else ''}{table_name}"
                return to_json(
                    {"error": f"Table introuvable ou sans colonnes : {target}. "
                              "Vérifiez le nom (insensible à la casse)."}
                )

            columns = [
                {
                    "position": r["COLUMN_ID"],
                    "name": r["COLUMN_NAME"],
                    "type": _format_type(r),
                    "nullable": r["NULLABLE"] == "Y",
                }
                for r in raw_rows
            ]
            table_label = f"{(owner or '').upper() + '.' if owner else ''}{table_name.upper()}"
            return to_json(
                {"table": table_label, "columnCount": len(columns), "columns": columns}
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur dans describe_table")
            return to_json({"error": f"Erreur lors de la description de la table : {exc}"})
