from mcp_oracle_poc.config import load_config
from mcp_oracle_poc.oracle import init_oracle, get_connection, close_oracle

init_oracle(load_config())
with get_connection() as conn:
    cur = conn.cursor()
    try:
        cur.execute("DROP TABLE demo_clients")
    except Exception:
        pass
    cur.execute("CREATE TABLE demo_clients (id NUMBER PRIMARY KEY, nom VARCHAR2(50), ville VARCHAR2(50))")
    cur.execute("INSERT INTO demo_clients VALUES (1, 'Alice', 'Paris')")
    cur.execute("INSERT INTO demo_clients VALUES (2, 'Bob', 'Lyon')")
    cur.execute("INSERT INTO demo_clients VALUES (3, 'Chloe', 'Paris')")
    conn.commit()
    print("✅ Table demo_clients créée avec 3 lignes.")
close_oracle()