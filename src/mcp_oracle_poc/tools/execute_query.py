"""Outil `execute_query` : exécute une requête SELECT en lecture seule.

Garde-fous :
  - seuls SELECT / WITH sont autorisés ;
  - une seule instruction (pas de 'stacked queries') ;
  - aucun mot-clé dangereux (DROP, DELETE, ...) ;
  - nombre de lignes plafonné (max_rows / QUERY_MAX_ROWS) ;
  - bind variables pour éviter l'injection SQL.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..config import AppConfig
from ..logging_config import get_logger
from ..oracle import (
    contains_forbidden_keyword,
    get_connection,
    is_read_only_query,
    is_single_statement,
    normalize_sql,
)
from .common import output_type_handler, rows_to_dicts, to_json

logger = get_logger("tools.execute_query")


def register(mcp: FastMCP, config: AppConfig) -> None:
    @mcp.tool()
    def execute_query(
        sql: Annotated[
            str,
            Field(description="Requête SELECT (ou WITH ... SELECT). Une seule instruction. "
                              "Utilisez des bind variables (:nom) pour les valeurs."),
        ],
        binds: Annotated[
            dict[str, Any] | None,
            Field(description='Valeurs des bind variables, ex. {"id": 42}.'),
        ] = None,
        max_rows: Annotated[
            int | None,
            Field(description="Plafond de lignes (borné par QUERY_MAX_ROWS)."),
        ] = None,
    ) -> str:
        """Exécute une requête en LECTURE SEULE (SELECT / WITH). Refuse tout DML/DDL.

        Le nombre de lignes est plafonné pour éviter les dumps massifs.
        """
        normalized = normalize_sql(sql)

        # --- Garde-fous de sécurité --------------------------------------
        if not is_single_statement(sql):
            return to_json({"error": "Refusé : une seule instruction SQL est autorisée "
                                     "(pas de ';' multiples)."})
        if not is_read_only_query(normalized):
            return to_json({"error": "Refusé : seules les requêtes SELECT (ou WITH ... SELECT) "
                                     "sont autorisées ici. Pour INSERT/UPDATE/DELETE, "
                                     "utilisez execute_dml."})
        forbidden = contains_forbidden_keyword(normalized)
        if forbidden:
            return to_json({"error": f"Refusé : mot-clé interdit détecté ({forbidden})."})
        # -----------------------------------------------------------------

        cap = config.query_max_rows
        limit = min(max_rows or cap, cap)

        try:
            with get_connection() as conn:
                conn.outputtypehandler = output_type_handler  # LOB -> str/bytes
                cursor = conn.cursor()
                cursor.execute(normalized, binds or {})
                fetched = cursor.fetchmany(limit)
                rows = rows_to_dicts(cursor, fetched)
                columns = [c[0] for c in cursor.description]
                # Y a-t-il potentiellement plus de lignes que le plafond ?
                truncated = len(fetched) >= limit and cursor.fetchone() is not None

            logger.info("execute_query : %d ligne(s), tronqué=%s", len(rows), truncated)
            payload: dict[str, Any] = {
                "rowCount": len(rows),
                "columns": columns,
                "truncated": truncated,
                "rows": rows,
            }
            if truncated:
                payload["note"] = (
                    f"Résultat tronqué à {limit} lignes (garde-fou). "
                    "Affinez la requête (WHERE, FETCH FIRST n ROWS ONLY)."
                )
            return to_json(payload)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur dans execute_query")
            return to_json({"error": f"Erreur lors de l'exécution de la requête : {exc}"})
