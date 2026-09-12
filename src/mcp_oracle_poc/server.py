"""Point d'entrée du serveur MCP Oracle (basé sur FastMCP v2).

Le serveur communique avec le client (Claude Desktop / Claude Code) via **stdio**
(stdin/stdout) en JSON-RPC.

Architecture FastMCP idiomatique :
  - l'instance `mcp` est créée au niveau module (elle est ainsi repérable par
    les commandes `fastmcp run` / `fastmcp dev`) ;
  - le cycle de vie de la ressource externe (le pool Oracle) est géré par un
    **lifespan** : le pool est créé au démarrage du serveur et fermé à l'arrêt ;
  - les 4 outils sont enregistrés au chargement du module.

Lancement :
  - `python -m mcp_oracle_poc`               (appelle main())
  - `fastmcp run src/mcp_oracle_poc/server.py`
  - `fastmcp dev src/mcp_oracle_poc/server.py`   (ouvre le MCP Inspector)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from .config import load_config
from .logging_config import get_logger
from .oracle import close_oracle, init_oracle
from .tools import register_all_tools

logger = get_logger("server")

# 1) Configuration (fail-fast : lève ConfigError si une variable manque).
#    Chargée au niveau module pour être disponible dès l'enregistrement des outils.
config = load_config()


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
    """Ouvre le pool Oracle au démarrage et le ferme proprement à l'arrêt."""
    init_oracle(config)  # crée le pool + test de connectivité (fail-fast)
    logger.info("Serveur MCP Oracle prêt (stdio). En attente de requêtes...")
    try:
        yield
    finally:
        close_oracle()


# 2) Serveur FastMCP (instance module-level, repérable par la CLI fastmcp).
mcp = FastMCP("mcp-oracle-poc", lifespan=lifespan)

# 3) Enregistrement des outils.
register_all_tools(mcp, config)


def main() -> None:
    """Démarre le serveur en transport stdio (utilisé par `python -m mcp_oracle_poc`)."""
    mcp.run(show_banner=False)

if __name__ == "__main__":
    main()
