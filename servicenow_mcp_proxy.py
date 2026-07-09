"""
Proxy MCP local : relie Claude Desktop (stdio) au serveur MCP Railway (HTTP).

Architecture :
    Claude Desktop  →  servicenow_mcp_proxy.py (local, stdio)
                               ↓
                    Railway MCP server (HTTP, sécurisé)
                               ↓
                        ServiceNow

Installation :
    pip install mcp httpx python-dotenv

Variables .env requises :
    MCP_SECRET_TOKEN=...
    MCP_SERVER_URL=...  (optionnel)

claude_desktop_config.json :
    "mcpServers": {
      "servicenow": {
        "command": "python3",
        "args": ["/chemin/absolu/vers/servicenow_mcp_proxy.py"]
      }
    }
"""

import asyncio
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import mcp.types as types

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("servicenow-proxy")

# --- Configuration ---------------------------------------------------------

MCP_SECRET_TOKEN = os.environ.get("MCP_SECRET_TOKEN")
if not MCP_SECRET_TOKEN:
    raise RuntimeError(
        "MCP_SECRET_TOKEN manquant dans le .env.\n"
        "Récupérez ce token auprès de l'administrateur."
    )

MCP_SERVER_URL = os.environ.get(
    "MCP_SERVER_URL",
    "https://servicenow-mcp-server-production-b9fb.up.railway.app/mcp"
)
REMOTE_URL = f"{MCP_SERVER_URL}?token={MCP_SECRET_TOKEN}"
RETRY_DELAYS = [2, 5, 15, 30]  # secondes entre chaque tentative de reconnexion


async def connect_to_remote() -> tuple[ClientSession, any]:
    """
    Tente de se connecter au serveur Railway.
    Réessaie automatiquement avec des délais croissants en cas d'échec.
    """
    for attempt, delay in enumerate(RETRY_DELAYS + [None], start=1):
        try:
            logger.info(f"Connexion au serveur MCP Railway (tentative {attempt})...")
            ctx = streamablehttp_client(REMOTE_URL)
            read, write, _ = await ctx.__aenter__()
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()
            logger.info("Connecté au serveur MCP Railway.")
            return session, ctx
        except Exception as e:
            if delay is None:
                raise RuntimeError(
                    f"Impossible de se connecter au serveur MCP Railway après {len(RETRY_DELAYS)+1} tentatives. "
                    f"Vérifiez que le serveur est démarré et que MCP_SECRET_TOKEN est correct. Erreur : {e}"
                )
            logger.warning(f"Échec de connexion ({e}), nouvelle tentative dans {delay}s...")
            await asyncio.sleep(delay)


async def main():
    local = Server("servicenow-proxy")
    session_holder: dict = {"session": None, "ctx": None}

    async def get_session() -> ClientSession:
        """Retourne la session active, en se reconnectant si nécessaire."""
        if session_holder["session"] is None:
            session_holder["session"], session_holder["ctx"] = await connect_to_remote()
        return session_holder["session"]

    async def reset_session():
        """Ferme proprement la session courante pour forcer une reconnexion."""
        try:
            if session_holder["session"]:
                await session_holder["session"].__aexit__(None, None, None)
            if session_holder["ctx"]:
                await session_holder["ctx"].__aexit__(None, None, None)
        except Exception:
            pass
        session_holder["session"] = None
        session_holder["ctx"] = None

    @local.list_tools()
    async def list_tools() -> list[types.Tool]:
        for attempt in range(2):
            try:
                remote = await get_session()
                result = await remote.list_tools()
                sanitized = []
                for tool in result.tools:
                    sanitized.append(types.Tool(
                        name=tool.name,
                        description=tool.description,
                        inputSchema=tool.inputSchema,
                        # outputSchema omis — le proxy retourne du texte brut
                    ))
                return sanitized
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"Erreur list_tools, reconnexion... ({e})")
                    await reset_session()
                else:
                    raise RuntimeError(f"Impossible de récupérer la liste des outils : {e}")

    @local.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        for attempt in range(2):
            try:
                remote = await get_session()
                result = await remote.call_tool(name, arguments)

                texts = []
                for block in result.content:
                    if isinstance(block, types.TextContent):
                        texts.append(block)
                    elif hasattr(block, "text"):
                        texts.append(types.TextContent(type="text", text=block.text))
                    else:
                        texts.append(types.TextContent(
                            type="text",
                            text=json.dumps(
                                block.model_dump() if hasattr(block, "model_dump") else str(block),
                                ensure_ascii=False,
                                indent=2,
                            )
                        ))
                return texts
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"Erreur call_tool '{name}', reconnexion... ({e})")
                    await reset_session()
                else:
                    raise RuntimeError(
                        f"Erreur lors de l'exécution de '{name}' : {e}. "
                        "Le serveur Railway est peut-être indisponible."
                    )

    # Connexion initiale au démarrage
    await get_session()

    async with stdio_server() as (read_stream, write_stream):
        await local.run(
            read_stream,
            write_stream,
            local.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())