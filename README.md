# ServiceNow MCP — Assistant Claude

Interface en langage naturel pour interroger ServiceNow, propulsée par Claude (Anthropic) via Claude Desktop.

## Architecture

```
Claude Desktop  →  servicenow_mcp_proxy.py  →  Railway MCP server  →  ServiceNow
  (questions          (local, stdio)            (cloud, sécurisé)
 dans le chat)
```

Le serveur MCP tourne sur Railway — une seule instance hébergée, accessible par token.

---

## Prérequis

- Python 3.10 ou supérieur
- Claude Desktop installé ([claude.ai/download](https://claude.ai/download))
- Le token secret du serveur MCP (demander à l'administrateur)
- Accès au repo GitHub (demander à l'administrateur)

---

## Prérequis ServiceNow

Avant d'installer le projet, deux éléments doivent être configurés sur l'instance ServiceNow cible.

### 1. Créer le compte de service MCP

Un compte utilisateur dédié (`mcp.integration`) est utilisé par le serveur Railway pour s'authentifier sur ServiceNow. Il est fourni sous forme de fichier XML à importer directement dans l'instance.

Dans ServiceNow, aller dans **System Update Sets > Retrieved Update Sets > Import Update Set from XML**, importer le fichier `mcp_user.xml` présent dans le repo, puis prévisualiser et committer l'update set.

Vérifier ensuite que le compte possède bien les rôles suivants :
- `itil`
- `web_service_admin`
- `rest_service`

### 2. Créer l'Application Registry OAuth

Le serveur utilise OAuth 2.0 (grant_type password) pour s'authentifier. Aller dans **System OAuth > Application Registry > New**, choisir **Create an OAuth API endpoint for external clients**, et renseigner :

| Champ | Valeur |
|---|---|
| Name | MCP Integration |
| Client ID | (généré automatiquement — à copier dans Railway) |
| Client Secret | (généré automatiquement — à copier dans Railway) |
| **Auth Scope** | **`useraccount`** |

> ⚠️ Le scope `useraccount` est obligatoire. Sans lui, l'API retourne une erreur 403
> *"Access to unscoped api is not allowed"* et le serveur ne peut pas s'authentifier.

Une fois l'application créée, reporter le **Client ID** et le **Client Secret** dans les variables d'environnement Railway (`SERVICENOW_CLIENT_ID` et `SERVICENOW_CLIENT_SECRET`).

---

## Installation

### 1. Cloner le repo

```bash
git clone https://github.com/maximecaulet/servicenow-mcp-server.git
cd servicenow-mcp-server
```

### 2. Installer les dépendances

```bash
pip3 install "mcp[cli]" httpx python-dotenv
```

### 3. Créer le fichier `.env`

```bash
touch .env
```

Ajouter la variable :

```
MCP_SECRET_TOKEN=token_fourni_par_l_administrateur
```

> 💡 **`MCP_SECRET_TOKEN`** : fourni par l'administrateur — ne pas partager, ne jamais committer dans Git.

### 4. Configurer Claude Desktop

Ouvre le fichier `claude_desktop_config.json` :

```bash
open "/Users/ton_nom/Library/Application Support/Claude/claude_desktop_config.json"
```

Ajoute le bloc `mcpServers` en respectant la structure existante :

```json
{
  "...autres paramètres existants...",
  "mcpServers": {
    "servicenow": {
      "command": "python3",
      "args": ["/chemin/absolu/vers/servicenow_mcp_proxy.py"]
    }
  }
}
```

> ⚠️ Remplace `/chemin/absolu/vers/` par le chemin réel vers le dossier cloné.
> Exemple : `/Users/ton_nom/Claude integration/servicenow_mcp_proxy.py`

Quitte Claude Desktop (**Cmd+Q**) puis relance-le.

---

## Utilisation

Une fois configuré, pose tes questions directement dans Claude Desktop :

```
Cherche les 5 derniers incidents actifs de priorité 1
Donne-moi le détail de l'incident INC0010001
Liste les demandes de changement ouvertes
Combien d'incidents actifs sans assigné en ce moment ?
Crée un incident pour une panne réseau, priorité 2
Quels sont les problèmes ouverts sans assigné ?
```

Claude appelle ServiceNow automatiquement et répond dans le chat — aucune commande à lancer.

> **Pourquoi un proxy et pas une URL directe ?**
> Claude Desktop ne supporte pas encore le format `"url"` pour les serveurs MCP distants.
> Le proxy `servicenow_mcp_proxy.py` fait le pont : il parle stdio avec Claude Desktop,
> et streamable-HTTP avec Railway. Quand Claude Desktop supportera les URLs distantes,
> le proxy ne sera plus nécessaire — la config deviendra simplement :
> ```json
> "mcpServers": {
>   "servicenow": {
>     "url": "https://servicenow-mcp-server-production-b9fb.up.railway.app/mcp?token=..."
>   }
> }
> ```

---

## Dépannage

**`ModuleNotFoundError: No module named 'mcp'`**
```bash
pip3 install "mcp[cli]" httpx python-dotenv
```

**`RuntimeError: Variable MCP_SECRET_TOKEN manquante`**
Le token secret est requis. Demande-le à l'administrateur et ajoute-le dans le `.env`.

**Claude Desktop — "Certains serveurs MCP n'ont pas pu être chargés"**
Le chemin dans `claude_desktop_config.json` est incorrect ou le fichier `.env` est absent.
Vérifie que le chemin est absolu et que le `.env` est dans le même dossier que le proxy.

**Claude Desktop — pas de réponse ServiceNow**
Le proxy se connecte au serveur Railway au démarrage de Claude Desktop.
Si Railway redéploie pendant que Claude Desktop tourne, redémarre Claude Desktop.

---

## Fichiers du projet

| Fichier | Rôle |
|---|---|
| `servicenow_mcp_server.py` | Serveur MCP hébergé sur Railway — connecté à ServiceNow |
| `servicenow_mcp_proxy.py` | Proxy local — relie Claude Desktop au serveur Railway |
| `requirements.txt` | Dépendances Python du serveur Railway |
| `.env` | Variables locales (non commité dans Git) |

---

## Outils disponibles

| Outil | Description |
|---|---|
| `search_records` | Recherche des enregistrements dans une table |
| `get_record` | Récupère un enregistrement par son sys_id |
| `create_record` | Crée un nouvel enregistrement |
| `update_record` | Met à jour un enregistrement existant |
| `add_comment` | Ajoute un commentaire à un enregistrement |

Tables actuellement autorisées : `incident`, `change_request`, `sc_request`, `problem`.

Pour ajouter des tables ou des outils, modifier `servicenow_mcp_server.py` et pousser sur GitHub.

---

## Changer d'instance ServiceNow

L'instance cible est entièrement configurée côté Railway. Pour basculer vers une autre
instance, mettre à jour les variables d'environnement du service `servicenow-mcp-server`
dans Railway — sans toucher au code ni aux fichiers locaux.

**Variables à mettre à jour dans Railway :**

```
SERVICENOW_INSTANCE_URL   → https://nouvelle-instance.service-now.com
SERVICENOW_CLIENT_ID      → client ID OAuth de la nouvelle instance
SERVICENOW_CLIENT_SECRET  → secret OAuth de la nouvelle instance
SERVICENOW_USERNAME       → compte de service de la nouvelle instance
SERVICENOW_PASSWORD       → mot de passe du compte de service
```

**Ce qui ne change pas :**

- Le code du serveur Railway
- Le proxy local (`servicenow_mcp_proxy.py`)
- Le `claude_desktop_config.json`
- Le `.env` local
- Le `MCP_SECRET_TOKEN`

Railway redéploie automatiquement dès que tu sauvegardes les variables (~30 secondes).
Redémarre ensuite Claude Desktop pour que le proxy se reconnecte à la nouvelle instance.

---

## Accéder à plusieurs instances simultanément

Il est possible de connecter Claude Desktop à plusieurs instances ServiceNow en même temps.
Chaque instance a son propre service Railway, son propre token, et son propre proxy local.

**Côté Railway** — dupliquer le service pour chaque instance :

```
Railway
├── servicenow-mcp-demo      → iteoconsultingdemo10.service-now.com
├── servicenow-mcp-efitst    → efitst.service-now.com
└── servicenow-mcp-prod      → production.service-now.com
```

**Côté `claude_desktop_config.json`** — déclarer autant d'entrées que d'instances :

```json
"mcpServers": {
  "servicenow-demo": {
    "command": "python3",
    "args": ["/Users/ton_nom/Claude integration/proxy_demo.py"]
  },
  "servicenow-efitst": {
    "command": "python3",
    "args": ["/Users/ton_nom/Claude integration/proxy_efitst.py"]
  }
}
```

Claude voit alors les outils des deux instances simultanément et peut interroger
ou comparer les deux dans la même conversation.

---

## Contact

Pour toute question, problème d'accès, ou pour obtenir le `MCP_SECRET_TOKEN`,
contacte l'administrateur du repo.