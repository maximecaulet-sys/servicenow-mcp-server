"""
Serveur MCP pour intégrer Claude à ServiceNow.

Prérequis :
    pip install mcp httpx python-dotenv starlette

Variables d'environnement :
    SERVICENOW_INSTANCE_URL   ex: https://votreinstance.service-now.com
    SERVICENOW_CLIENT_ID
    SERVICENOW_CLIENT_SECRET
    SERVICENOW_USERNAME
    SERVICENOW_PASSWORD
    MCP_SECRET_TOKEN          token Bearer pour sécuriser l'endpoint HTTP
                              (obligatoire en mode production, ignoré en stdio)
    PORT                      port d'écoute (fourni automatiquement par Railway)

Lancement local (stdio, pas d'auth nécessaire) :
    python servicenow_mcp_server.py

Lancement en production (streamable-http avec auth) :
    TRANSPORT=sse python servicenow_mcp_server.py
"""

import os
import time
import httpx
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Charge le .env en local (ignoré en production où les variables sont injectées)
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# --- Configuration ---------------------------------------------------------

SERVICENOW_INSTANCE_URL  = os.environ["SERVICENOW_INSTANCE_URL"].rstrip("/")
SERVICENOW_CLIENT_ID     = os.environ["SERVICENOW_CLIENT_ID"]
SERVICENOW_CLIENT_SECRET = os.environ["SERVICENOW_CLIENT_SECRET"]
SERVICENOW_USERNAME      = os.environ.get("SERVICENOW_USERNAME")
SERVICENOW_PASSWORD      = os.environ.get("SERVICENOW_PASSWORD")

TRANSPORT        = os.environ.get("TRANSPORT", "stdio")
PORT             = int(os.environ.get("PORT", 8000))
MCP_SECRET_TOKEN = os.environ.get("MCP_SECRET_TOKEN")

if TRANSPORT == "sse" and not MCP_SECRET_TOKEN:
    raise RuntimeError(
        "MCP_SECRET_TOKEN est obligatoire en mode production (TRANSPORT=sse). "
        "Ajoutez cette variable dans vos variables d'environnement Railway."
    )

# Tables autorisées
ALLOWED_TABLES = {"incident", "change_request", "sc_request", "problem"}

# --- Gestion du token OAuth ServiceNow ------------------------------------

_token_cache = {"access_token": None, "expires_at": 0}


def get_access_token() -> str:
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]

    token_url = f"{SERVICENOW_INSTANCE_URL}/oauth_token.do"
    payload = {
        "grant_type": "password" if SERVICENOW_USERNAME else "client_credentials",
        "client_id": SERVICENOW_CLIENT_ID,
        "client_secret": SERVICENOW_CLIENT_SECRET,
    }
    if SERVICENOW_USERNAME:
        payload["username"] = SERVICENOW_USERNAME
        payload["password"] = SERVICENOW_PASSWORD

    resp = httpx.post(token_url, data=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + int(data.get("expires_in", 1800))
    return _token_cache["access_token"]


def sn_request(method: str, path: str, **kwargs) -> dict:
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {get_access_token()}"
    headers["Accept"] = "application/json"
    url = f"{SERVICENOW_INSTANCE_URL}{path}"

    resp = httpx.request(method, url, headers=headers, timeout=15, **kwargs)
    if resp.status_code >= 400:
        raise RuntimeError(f"ServiceNow API error {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def check_table_allowed(table: str) -> None:
    if table not in ALLOWED_TABLES:
        raise ValueError(
            f"Table '{table}' non autorisée. Tables disponibles : {sorted(ALLOWED_TABLES)}"
        )


# --- Serveur MCP -----------------------------------------------------------

# FastMCP sans auth= (le paramètre attend un AuthSettings, pas une fonction)
# L'authentification est gérée par un middleware Starlette en mode production
mcp = FastMCP(
    "servicenow",
    host="0.0.0.0" if TRANSPORT == "sse" else "127.0.0.1",
    port=PORT,
)


@mcp.tool()
def search_records(table: str, query: str = "", limit: int = 10) -> list[dict]:
    """
    Recherche des enregistrements dans une table ServiceNow.

    Args:
        table: nom de la table (ex: 'incident', 'change_request').
        query: requête encodée ServiceNow (ex: 'active=true^priority=1').
        limit: nombre maximum de résultats (par défaut 10, max 50).
    """
    check_table_allowed(table)
    limit = min(limit, 50)
    params = {"sysparm_limit": limit}
    if query:
        params["sysparm_query"] = query
    data = sn_request("GET", f"/api/now/table/{table}", params=params)
    return data.get("result", [])


@mcp.tool()
def get_record(table: str, sys_id: str) -> dict:
    """
    Récupère un enregistrement précis par son sys_id.

    Args:
        table: nom de la table.
        sys_id: identifiant unique de l'enregistrement.
    """
    check_table_allowed(table)
    data = sn_request("GET", f"/api/now/table/{table}/{sys_id}")
    return data.get("result", {})


@mcp.tool()
def create_record(table: str, fields: dict) -> dict:
    """
    Crée un nouvel enregistrement (ex: un incident).

    Args:
        table: nom de la table.
        fields: dictionnaire des champs (ex: {"short_description": "...", "priority": "2"}).
    """
    check_table_allowed(table)
    data = sn_request("POST", f"/api/now/table/{table}", json=fields)
    return data.get("result", {})


@mcp.tool()
def update_record(table: str, sys_id: str, fields: dict) -> dict:
    """
    Met à jour un enregistrement existant.

    Args:
        table: nom de la table.
        sys_id: identifiant unique de l'enregistrement.
        fields: champs à mettre à jour.
    """
    check_table_allowed(table)
    data = sn_request("PATCH", f"/api/now/table/{table}/{sys_id}", json=fields)
    return data.get("result", {})


@mcp.tool()
def add_comment(table: str, sys_id: str, comment: str) -> dict:
    """
    Ajoute un commentaire à un enregistrement.

    Args:
        table: nom de la table.
        sys_id: identifiant unique de l'enregistrement.
        comment: texte du commentaire.
    """
    check_table_allowed(table)
    data = sn_request("PATCH", f"/api/now/table/{table}/{sys_id}", json={"comments": comment})
    return data.get("result", {})


# --- Middleware d'authentification (mode production uniquement) -------------

def build_app_with_auth():
    """
    Enveloppe l'app ASGI de FastMCP dans un middleware Starlette
    qui vérifie le token sur chaque requête.
    Accepte le token :
      - en query parameter : ?token=<token>
      - en header          : Authorization: Bearer <token>
    """
    from starlette.applications import Starlette
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    class TokenAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            # Méthode 1 : query parameter ?token=...
            token = request.query_params.get("token", "")

            # Méthode 2 : header Authorization: Bearer ...
            if not token:
                auth = request.headers.get("authorization", "")
                if auth.startswith("Bearer "):
                    token = auth.removeprefix("Bearer ").strip()

            if token != MCP_SECRET_TOKEN:
                return JSONResponse(
                    {"error": "Unauthorized", "detail": "Token invalide ou manquant."},
                    status_code=401,
                )
            return await call_next(request)

    # Récupère l'app ASGI interne de FastMCP
    inner_app = mcp.streamable_http_app()

    app = Starlette()
    app.add_middleware(TokenAuthMiddleware)
    app.mount("/", inner_app)
    return app


if __name__ == "__main__":
    if TRANSPORT == "sse":
        import uvicorn
        app = build_app_with_auth()
        uvicorn.run(app, host="0.0.0.0", port=PORT)
    else:
        mcp.run()