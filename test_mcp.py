import asyncio
from fastmcp import Client
from mcp_oracle_poc.server import mcp, config
from mcp_oracle_poc.oracle import init_oracle


def afficher(res):
    if getattr(res, "data", None) is not None:
        return res.data
    return "\n".join(getattr(c, "text", str(c)) for c in (res.content or []))


async def main():
    init_oracle(config)  # ouvre le pool Oracle (idempotent)
    async with Client(mcp) as client:
        outils = await client.list_tools()
        print("🔧 Outils MCP disponibles :", [t.name for t in outils])

        print("\n--- list_tables ---")
        print(afficher(await client.call_tool("list_tables", {})))

        print("\n--- execute_query ---")
        res = await client.call_tool("execute_query", {
            "sql": "SELECT table_name FROM all_tables FETCH FIRST 5 ROWS ONLY"
        })
        print(afficher(res))

        print("\n--- execute_dml (simulation) ---")
        res = await client.call_tool("execute_dml", {
            "sql": "DELETE FROM all_tables WHERE 1=0"
        })
        print(afficher(res))


asyncio.run(main())