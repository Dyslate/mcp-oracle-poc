"""Outil `execute_dml` : exécute INSERT / UPDATE / DELETE avec confirmation.

Mécanisme de **confirmation en deux temps** :
  1. Par défaut (confirm=False), l'outil fait un dry-run : il exécute la requête
     dans une transaction NON validée, mesure les lignes impactées, puis ROLLBACK.
     Rien n'est modifié durablement.
  2. Avec confirm=True, il ré-exécute et fait un COMMIT.

Garde-fous : désactivable via ALLOW_DML=false ; seuls INSERT/UPDATE/DELETE ;
une seule instruction ; pas de mots-clés dangereux ; avertissement si
UPDATE/DELETE sans WHERE ; bind variables recommandées.
"""

from __future__ import annotations

import re
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..config import AppConfig
from ..logging_config import get_logger
from ..oracle import (
    contains_forbidden_keyword,
    first_keyword,
    get_connection,
    is_allowed_dml,
    is_single_statement,
    normalize_sql,
)
from .common import to_json

logger = get_logger("tools.execute_dml")


def register(mcp: FastMCP, config: AppConfig) -> None:
    @mcp.tool()
    def execute_dml(
        sql: Annotated[
            str,
            Field(description="Instruction INSERT / UPDATE / DELETE. Une seule instruction. "
                              "Utilisez impérativement des bind variables (:nom)."),
        ],
        binds: Annotated[
            dict[str, Any] | None,
            Field(description='Valeurs des bind variables, ex. {"id": 42, "nom": "Alice"}.'),
        ] = None,
        confirm: Annotated[
            bool,
            Field(description="False (défaut) = simulation (dry-run + ROLLBACK, aucune "
                              "modification). True = exécution réelle (COMMIT). "
                              "Toujours simuler d'abord."),
        ] = False,
    ) -> str:
        """Exécute une écriture INSERT/UPDATE/DELETE.

        Par défaut effectue une SIMULATION (dry-run) indiquant le nombre de lignes
        impactées sans rien modifier. Passez confirm=True UNIQUEMENT après
        validation explicite de l'utilisateur pour appliquer réellement (COMMIT).
        """
        # Garde-fou global.
        if not config.allow_dml:
            return to_json({"error": "Refusé : les DML sont désactivés sur ce serveur "
                                     "(ALLOW_DML=false)."})

        normalized = normalize_sql(sql)

        # --- Garde-fous de sécurité --------------------------------------
        if not is_single_statement(sql):
            return to_json({"error": "Refusé : une seule instruction SQL est autorisée "
                                     "(pas de ';' multiples)."})
        if not is_allowed_dml(normalized):
            return to_json({"error": "Refusé : seuls INSERT, UPDATE et DELETE sont autorisés "
                                     "via execute_dml."})
        forbidden = contains_forbidden_keyword(normalized)
        if forbidden:
            return to_json({"error": f"Refusé : mot-clé interdit détecté ({forbidden})."})
        # -----------------------------------------------------------------

        kw = first_keyword(normalized)
        # Avertissement fort : UPDATE/DELETE sans WHERE = impact potentiellement massif.
        missing_where = kw in ("UPDATE", "DELETE") and not re.search(
            r"\bWHERE\b", normalized, re.IGNORECASE
        )

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(normalized, binds or {})
                rows_affected = cursor.rowcount
                if confirm:
                    conn.commit()
                else:
                    conn.rollback()  # dry-run : on annule tout

            logger.info(
                "execute_dml : op=%s, confirm=%s, lignes=%d, sans_where=%s",
                kw, confirm, rows_affected, missing_where,
            )

            if not confirm:
                payload: dict[str, Any] = {
                    "mode": "SIMULATION (dry-run)",
                    "operation": kw,
                    "rowsWouldBeAffected": rows_affected,
                    "committed": False,
                    "nextStep": (
                        "Aucune modification appliquée. Pour exécuter réellement, "
                        "rappelez execute_dml avec les mêmes paramètres et confirm=true, "
                        "après confirmation explicite de l'utilisateur."
                    ),
                }
                if missing_where:
                    payload["warning"] = (
                        f"ATTENTION : {kw} SANS clause WHERE — "
                        f"{rows_affected} ligne(s) seraient impactées."
                    )
                return to_json(payload)

            return to_json(
                {"mode": "EXÉCUTÉ", "operation": kw,
                 "rowsAffected": rows_affected, "committed": True}
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur dans execute_dml")
            return to_json({"error": f"Erreur lors de l'exécution du DML : {exc}"})
