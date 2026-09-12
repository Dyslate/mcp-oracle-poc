from mcp_oracle_poc.config import load_config
from mcp_oracle_poc.oracle import init_oracle, get_connection, close_oracle

init_oracle(load_config())
with get_connection() as conn:
    cur = conn.cursor()

    print("=== Tables du schema ===")
    cur.execute("SELECT table_name FROM user_tables ORDER BY table_name")
    for (name,) in cur.fetchall():
        print("  -", name)

    print("\n=== Contenu de demo_clients ===")
    cur.execute("SELECT * FROM demo_clients ORDER BY id")
    cols = [c[0] for c in cur.description]
    print("  " + " | ".join(cols))
    for row in cur.fetchall():
        print("  " + " | ".join(str(v) for v in row))

close_oracle()