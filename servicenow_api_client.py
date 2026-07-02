"""
Client API Anthropic avec serveur MCP ServiceNow hébergé sur Railway.

Prérequis :
    pip install anthropic python-dotenv

Variables d'environnement (.env) :
    ANTHROPIC_API_KEY   votre clé API Anthropic (console.anthropic.com)
    MCP_SERVER_URL      URL du serveur MCP Railway (optionnel, sinon défaut ci-dessous)

Utilisation :
    python servicenow_api_client.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import anthropic

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# --- Configuration -----------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("Variable ANTHROPIC_API_KEY manquante dans le .env")

MCP_SERVER_URL = os.environ.get(
    "MCP_SERVER_URL",
    "https://servicenow-mcp-server-production-b9fb.up.railway.app/mcp"
)

MODEL = "claude-sonnet-4-6"

# --- Client ------------------------------------------------------------------

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

MCP_SERVERS = [
    {
        "type": "url",
        "url": MCP_SERVER_URL,
        "name": "servicenow",
    }
]


def ask(question: str) -> str:
    """
    Envoie une question à Claude avec accès au serveur MCP ServiceNow.
    Retourne la réponse textuelle complète.
    """
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=2048,
        mcp_servers=MCP_SERVERS,
        messages=[{"role": "user", "content": question}],
        betas=["mcp-client-2025-04-04"],
    )

    # Extraire le texte de la réponse (peut contenir plusieurs blocs)
    texts = [block.text for block in response.content if hasattr(block, "text")]
    return "\n".join(texts)


# --- Exemples de requêtes ----------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print(" Assistant ServiceNow — propulsé par Claude")
    print(" Tapez votre question en langage naturel.")
    print(" Commandes : 'quitter' ou 'exit' pour arrêter.")
    print("=" * 60)

    while True:
        try:
            question = input("\nVous : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir !")
            break

        if not question:
            continue

        if question.lower() in ("quitter", "exit", "quit"):
            print("Au revoir !")
            break

        print("\nClaude : ", end="", flush=True)
        try:
            reponse = ask(question)
            print(reponse)
        except anthropic.APIError as e:
            print(f"Erreur API Anthropic : {e}")
        except Exception as e:
            print(f"Erreur : {e}")