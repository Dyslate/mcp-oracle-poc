import asyncio
from fastmcp import Client
from mcp_oracle_poc.server import mcp, config
from mcp_oracle_poc.oracle import init_oracle


def afficher(res):
    if getattr(res, "data", None) is not None:
        return res.data
    return "\n".join(getattr(c, "text", str(c)) for c in (res.content or []))


async def lire(client):
    return afficher(await client.call_tool("execute_query",
        {"sql": "SELECT id, nom, ville FROM demo_clients ORDER BY id"}))


async def main():
    init_oracle(config)
    params = {"sql": "UPDATE demo_clients SET ville = :v WHERE ville = 'Paris'",
              "binds": {"v": "PARIS"}}
    async with Client(mcp) as client:
        print("=== AVANT ===");                     print(await lire(client))
        print("\n=== SIMULATION (dry-run) ===");     print(afficher(await client.call_tool("execute_dml", params)))
        print("\n=== APRES SIMULATION (inchange) ==="); print(await lire(client))
        print("\n=== EXECUTION REELLE (confirm=true) ==="); print(afficher(await client.call_tool("execute_dml", {**params, "confirm": True})))
        print("\n=== APRES EXECUTION (Paris -> PARIS) ==="); print(await lire(client))


asyncio.run(main())