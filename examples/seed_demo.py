"""Create and populate a small demo table (`demo_clients`) to try the tools.

The MCP server itself cannot create tables (DDL is blocked on purpose), so this
standalone helper talks to Oracle directly to seed a bit of demo data. Once the
table exists you can explore it through the MCP tools (list_tables,
execute_query, execute_dml).

Run from the project root (virtualenv active, `.env` filled in):

    python examples/seed_demo.py
"""

from __future__ import annotations

from mcp_oracle_poc.config import load_config
from mcp_oracle_poc.oracle import close_oracle, get_connection, init_oracle


def main() -> None:
    init_oracle(load_config())
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Drop the table if it already exists (ignore the error otherwise).
            try:
                cursor.execute("DROP TABLE demo_clients")
            except Exception:
                pass

            cursor.execute(
                "CREATE TABLE demo_clients ("
                "  id   NUMBER PRIMARY KEY,"
                "  name VARCHAR2(50),"
                "  city VARCHAR2(50)"
                ")"
            )
            cursor.executemany(
                "INSERT INTO demo_clients (id, name, city) VALUES (:1, :2, :3)",
                [
                    (1, "Alice", "Paris"),
                    (2, "Bob", "Lyon"),
                    (3, "Chloe", "Paris"),
                ],
            )
            conn.commit()
            print("Created table demo_clients with 3 rows.")
    finally:
        close_oracle()


if __name__ == "__main__":
    main()
