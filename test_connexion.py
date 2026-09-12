from mcp_oracle_poc.config import load_config
from mcp_oracle_poc.oracle import init_oracle, get_connection, close_oracle

config = load_config()
init_oracle(config)  # crée le pool + fait un SELECT 1 FROM DUAL
with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM all_tables WHERE ROWNUM <= 5")
    tables = [r[0] for r in cur.fetchall()]
print("✅ Connexion OK. Exemple de tables :", tables)
close_oracle()