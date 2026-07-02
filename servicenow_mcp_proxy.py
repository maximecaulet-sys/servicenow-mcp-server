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
from pathlib import Path
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import mcp.types as types

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

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


# --- Proxy -----------------------------------------------------------------

async def main():
    async with streamablehttp_client(REMOTE_URL) as (read, write, _):
        async with ClientSession(read, write) as remote:
            await remote.initialize()

            local = Server("servicenow-proxy")

            @local.list_tools()
            async def list_tools() -> list[types.Tool]:
                """
                Récupère les outils depuis Railway.
                Supprime outputSchema pour éviter les erreurs de validation
                du proxy (le contenu est retourné en texte brut).
                """
                result = await remote.list_tools()
                sanitized = []
                for tool in result.tools:
                    sanitized.append(types.Tool(
                        name=tool.name,
                        description=tool.description,
                        inputSchema=tool.inputSchema,
                        # outputSchema volontairement omis — le proxy retourne
                        # du texte, pas du JSON structuré
                    ))
                return sanitized

            @local.call_tool()
            async def call_tool(
                name: str,
                arguments: dict,
            ) -> list[types.TextContent]:
                """Exécute un outil sur Railway et retransmet le résultat en texte."""
                result = await remote.call_tool(name, arguments)

                # Normalise tout le contenu en TextContent pour éviter les
                # problèmes de validation liés à outputSchema
                texts = []
                for block in result.content:
                    if isinstance(block, types.TextContent):
                        texts.append(block)
                    elif hasattr(block, "text"):
                        texts.append(types.TextContent(type="text", text=block.text))
                    else:
                        # Fallback : sérialise en JSON lisible
                        import json
                        texts.append(types.TextContent(
                            type="text",
                            text=json.dumps(
                                block.model_dump() if hasattr(block, "model_dump") else str(block),
                                ensure_ascii=False,
                                indent=2,
                            )
                        ))

                return texts

            async with stdio_server() as (read_stream, write_stream):
                await local.run(
                    read_stream,
                    write_stream,
                    local.create_initialization_options(),
                )


if __name__ == "__main__":
    asyncio.run(main())