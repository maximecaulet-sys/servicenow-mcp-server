"""
Serveur MCP pour intégrer Claude à ServiceNow.

Prérequis :
    pip install mcp httpx python-dotenv

Variables d'environnement :
    SERVICENOW_INSTANCE_URL
    SERVICENOW_CLIENT_ID
    SERVICENOW_CLIENT_SECRET
    SERVICENOW_USERNAME
    SERVICENOW_PASSWORD
    MCP_SECRET_TOKEN   token Bearer (obligatoire en production, ignoré en stdio)
    PORT               port d'écoute (fourni automatiquement par Railway)

Lancement local   : python3 servicenow_mcp_server.py
Lancement prod    : TRANSPORT=sse python servicenow_mcp_server.py
"""

import os
import time
import httpx
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

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
        "MCP_SECRET_TOKEN est obligatoire en mode production. "
        "Ajoutez cette variable dans vos variables d'environnement Railway."
    )

ALLOWED_TABLES = {
                    # --- General ---
                    "sys_db_object", "sys_plugin", "sys_app",
                    "sys_user", "sys_dictionary",
                    "sys_script_client", "sys_script_include", "sys_script", "sys_ui_policy", "catalog_ui_policy_action_list", "sys_ui_action", "sys_ui_script",
                    "sys_update_set", "wf_workflow", "sys_user_has_license", "sys_update_xml", "sys_history_set", "sys_history_line",
                    "discovery_log_list",
                    # --- ITSM : Service Management ---
                    "task",
                    "incident", "incident_task", "task_sla",
                    "change_request", "change_task", "std_change_record_producer",
                    "sc_request", "sc_req_item", "sc_task", "sc_cat_item", "sc_category",
                    "problem", "problem_task",
                    "kb_knowledge", "kb_knowledge_base", "kb_category", "kb_feedback", "kb_submission",
                    # --- ITOM : Event Management ---
                    "em_event", "em_alert",
                    # --- ITAM : Asset Management ---
                    "alm_hardware", "alm_asset", "alm_license", "ast_contract",
                    # --- CMDB ---
                    "cmdb_ci_service", "cmdb_ci_service_business", "cmdb_ci", "cmdb_rel_ci", "cmdb_ci_class",
                    # --- Security ---
                    "sys_security_acl", "sys_user_has_role", "sys_user_role", "sys_user_group", "sys_properties",
                    # --- Automatisation ---
                    "sys_hub_flow", "sys_hub_action_type_definition", "sysauto_script", "sys_trigger",
                    # --- Integration ---
                    "sys_rest_message", "sys_web_service", "ecc_queue", "sys_data_source", "sys_transform_map", "sys_email_account",
                    # --- Technical debt ---
                    "sys_store_app", "sys_upgrade_history", "sys_choice",
                    # --- Notification ---
                    "sysevent_email_action", "sysevent"
                  }

# --- OAuth ServiceNow ------------------------------------------------------

_token_cache = {"access_token": None, "expires_at": 0}

def get_access_token() -> str:
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]

    payload = {
        "grant_type": "password" if SERVICENOW_USERNAME else "client_credentials",
        "client_id": SERVICENOW_CLIENT_ID,
        "client_secret": SERVICENOW_CLIENT_SECRET,
    }
    if SERVICENOW_USERNAME:
        payload["username"] = SERVICENOW_USERNAME
        payload["password"] = SERVICENOW_PASSWORD

    try:
        resp = httpx.post(
            f"{SERVICENOW_INSTANCE_URL}/oauth_token.do",
            data=payload,
            timeout=10,
        )
        resp.raise_for_status()
    except httpx.TimeoutException:
        raise RuntimeError(
            f"Impossible de contacter ServiceNow ({SERVICENOW_INSTANCE_URL}) : timeout. "
            "Vérifiez que l'instance est accessible."
        )
    except httpx.ConnectError:
        raise RuntimeError(
            f"Impossible de se connecter à ServiceNow ({SERVICENOW_INSTANCE_URL}). "
            "Vérifiez l'URL de l'instance et la connectivité réseau."
        )
    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"Échec de l'authentification OAuth ServiceNow (HTTP {e.response.status_code}). "
            "Vérifiez le Client ID, Client Secret, et que le scope 'useraccount' est activé."
        )

    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(
            f"Réponse OAuth invalide — token absent. Réponse : {str(data)[:200]}"
        )

    expires_in = int(data.get("expires_in") or 1800)
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + expires_in
    return _token_cache["access_token"]


def sn_request(method: str, path: str, **kwargs) -> dict:
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {get_access_token()}"
    headers["Accept"] = "application/json"
    url = f"{SERVICENOW_INSTANCE_URL}{path}"

    try:
        resp = httpx.request(method, url, headers=headers, timeout=15, **kwargs)
    except httpx.TimeoutException:
        raise RuntimeError(
            f"La requête vers ServiceNow a expiré ({url}). "
            "L'instance est peut-être surchargée, réessayez dans quelques instants."
        )
    except httpx.ConnectError:
        raise RuntimeError(
            f"Impossible de se connecter à ServiceNow ({SERVICENOW_INSTANCE_URL}). "
            "Vérifiez la connectivité réseau."
        )

    if resp.status_code == 401:
        # Token expiré ou révoqué — on vide le cache pour forcer un renouvellement
        _token_cache["access_token"] = None
        _token_cache["expires_at"] = 0
        raise RuntimeError(
            "Token OAuth expiré ou révoqué. La prochaine requête renouvellera automatiquement le token."
        )
    if resp.status_code == 403:
        raise RuntimeError(
            f"Accès refusé à {path}. Le compte de service n'a pas les droits suffisants sur cette table."
        )
    if resp.status_code == 404:
        raise RuntimeError(
            f"Ressource introuvable : {path}. Vérifiez le nom de la table ou le sys_id."
        )
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Erreur ServiceNow {resp.status_code} sur {path} : {resp.text[:300]}"
        )

    return resp.json()

def check_table_allowed(table: str) -> None:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' non autorisée. Tables disponibles : {sorted(ALLOWED_TABLES)}")

# --- Middleware ASGI d'authentification ------------------------------------

class TokenAuthMiddleware:
    """
    Middleware ASGI pur qui vérifie le token avant chaque requête HTTP.
    Accepte le token via :
      - query parameter : ?token=<token>
      - header          : Authorization: Bearer <token>
    Désactivé automatiquement en mode stdio (local).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Ne filtre que les requêtes HTTP (pas les websockets ou lifespan)
        if scope["type"] == "http":
            # Extraire le token du query string
            query = scope.get("query_string", b"").decode()
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            token = params.get("token", "")

            # Ou depuis le header Authorization
            if not token:
                headers = dict(scope.get("headers", []))
                auth = headers.get(b"authorization", b"").decode()
                if auth.startswith("Bearer "):
                    token = auth.removeprefix("Bearer ").strip()

            if token != MCP_SECRET_TOKEN:
                response = (
                    b"HTTP/1.1 401 Unauthorized\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Content-Length: 45\r\n\r\n"
                    b'{"error":"Unauthorized","detail":"Token invalide"}'
                )
                await send({"type": "http.response.start", "status": 401,
                            "headers": [[b"content-type", b"application/json"]]})
                await send({"type": "http.response.body",
                            "body": b'{"error":"Unauthorized","detail":"Token invalide"}'})
                return

        await self.app(scope, receive, send)

# --- Serveur MCP -----------------------------------------------------------

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
    return sn_request("GET", f"/api/now/table/{table}", params=params).get("result", [])

@mcp.tool()
def get_record(table: str, sys_id: str) -> dict:
    """
    Récupère un enregistrement précis par son sys_id.

    Args:
        table: nom de la table.
        sys_id: identifiant unique de l'enregistrement.
    """
    check_table_allowed(table)
    return sn_request("GET", f"/api/now/table/{table}/{sys_id}").get("result", {})

# @mcp.tool()
# def create_record(table: str, fields: dict) -> dict:
#     """
#     Crée un nouvel enregistrement (ex: un incident).

#     Args:
#         table: nom de la table.
#         fields: dictionnaire des champs (ex: {"short_description": "...", "priority": "2"}).
#     """
#     check_table_allowed(table)
#     return sn_request("POST", f"/api/now/table/{table}", json=fields).get("result", {})

# @mcp.tool()
# def update_record(table: str, sys_id: str, fields: dict) -> dict:
#     """
#     Met à jour un enregistrement existant.

#     Args:
#         table: nom de la table.
#         sys_id: identifiant unique de l'enregistrement.
#         fields: champs à mettre à jour.
#     """
#     check_table_allowed(table)
#     return sn_request("PATCH", f"/api/now/table/{table}/{sys_id}", json=fields).get("result", {})

# @mcp.tool()
# def add_comment(table: str, sys_id: str, comment: str) -> dict:
#     """
#     Ajoute un commentaire à un enregistrement.

#     Args:
#         table: nom de la table.
#         sys_id: identifiant unique de l'enregistrement.
#         comment: texte du commentaire.
#     """
#     check_table_allowed(table)
#     return sn_request("PATCH", f"/api/now/table/{table}/{sys_id}", json={"comments": comment}).get("result", {})

# --- Démarrage -------------------------------------------------------------

if __name__ == "__main__":
    if TRANSPORT == "sse":
        # On injecte le middleware ASGI directement dans FastMCP
        # avant qu'il démarre son propre serveur uvicorn
        original_streamable = mcp.streamable_http_app

        def patched_streamable_http_app():
            return TokenAuthMiddleware(original_streamable())

        mcp.streamable_http_app = patched_streamable_http_app
        mcp.run(transport="streamable-http")
    else:
        mcp.run()