"""Helpers partagés par les outils : conversion de lignes et sérialisation JSON."""

from __future__ import annotations

import json
from typing import Any

import oracledb


def output_type_handler(cursor: "oracledb.Cursor", metadata: Any):
    """Fait remonter les LOB (CLOB/NCLOB/BLOB) comme valeurs simples (str/bytes)
    plutôt que comme objets LOB, pour une sérialisation JSON directe."""
    if metadata.type_code in (oracledb.DB_TYPE_CLOB, oracledb.DB_TYPE_NCLOB):
        return cursor.var(oracledb.DB_TYPE_LONG, arraysize=cursor.arraysize)
    if metadata.type_code == oracledb.DB_TYPE_BLOB:
        return cursor.var(oracledb.DB_TYPE_LONG_RAW, arraysize=cursor.arraysize)
    return None


def rows_to_dicts(cursor: "oracledb.Cursor", rows: list[tuple]) -> list[dict[str, Any]]:
    """Convertit des lignes positionnelles en dictionnaires {COLONNE: valeur}."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def to_json(data: Any) -> str:
    """Sérialise en JSON lisible. `default=str` gère dates, Decimal, etc."""
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)
