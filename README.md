# ServiceNow MCP — Assistant Claude

Interface en langage naturel pour interroger ServiceNow, propulsée par Claude (Anthropic).

Deux modes d'utilisation :
- **Claude Desktop** — questions directement dans l'interface Claude via un proxy local
- **Terminal** — script Python interactif en ligne de commande

## Architecture

```
─── Mode Claude Desktop (recommandé) ──────────────────────────────

Claude Desktop  →  servicenow_mcp_proxy.py  →  Railway MCP server  →  ServiceNow
  (questions          (local, stdio)            (cloud, sécurisé)
 dans le chat)

─── Mode Terminal ──────────────────────────────────────────────────

servicenow_api_client.py  →  API Anthropic  →  Railway MCP server  →  ServiceNow
     (ton terminal)              (cloud)         (cloud, sécurisé)
```

Le serveur MCP Railway est partagé entre les deux modes — une seule instance hébergée, accessible par token.

## Prérequis

- Python 3.10 ou supérieur
- Un compte Anthropic avec une clé API ([console.anthropic.com](https://console.anthropic.com))
- Le token secret du serveur MCP (demander à l'administrateur)
- Accès au repo GitHub (demander à l'administrateur)

## Installation

### 1. Cloner le repo

```bash
git clone https://github.com/maximecaulet/servicenow-mcp-server.git
cd servicenow-mcp-server
```

### 2. Installer les dépendances

```bash
pip3 install "mcp[cli]" anthropic httpx python-dotenv
```

### 3. Créer le fichier `.env`

```bash
touch .env
```

Ajouter les deux variables :

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
MCP_SECRET_TOKEN=token_fourni_par_l_administrateur
```

> 💡 **`ANTHROPIC_API_KEY`** : [console.anthropic.com](https://console.anthropic.com) > **API Keys** > **Create Key**
>
> 💡 **`MCP_SECRET_TOKEN`** : fourni par l'administrateur — ne pas partager, ne jamais committer dans Git

---

## Mode 1 — Claude Desktop (recommandé)

Pose tes questions directement dans l'interface Claude Desktop. Claude interroge ServiceNow en temps réel et répond en langage naturel.

### Configuration

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
> Sur Mac : `/Users/ton_nom/Claude integration/servicenow_mcp_proxy.py`

Quitte Claude Desktop (**Cmd+Q**) puis relance-le.

### Utilisation

Une fois configuré, pose tes questions directement dans Claude Desktop :

```
Cherche les 5 derniers incidents actifs de priorité 1
Donne-moi le détail de l'incident INC0010001
Liste les demandes de changement ouvertes
Combien d'incidents actifs sans assigné en ce moment ?
Crée un incident pour une panne réseau, priorité 2
```

Claude appelle ServiceNow automatiquement et te répond dans le chat.

> **Pourquoi un proxy et pas une URL directe ?**
> Claude Desktop ne supporte pas encore le format `"url"` pour les serveurs MCP distants
> (disponible uniquement dans l'API Anthropic). Le proxy `servicenow_mcp_proxy.py` fait le
> pont : il parle stdio avec Claude Desktop, et streamable-HTTP avec Railway.
> Quand Claude Desktop supportera les URLs distantes, le proxy ne sera plus nécessaire.

---

## Mode 2 — Terminal

Pour les utilisateurs sans Claude Desktop, ou pour des scripts automatisés.

```bash
python3 servicenow_api_client.py
```

Interface interactive dans le terminal :

```
============================================================
 Assistant ServiceNow — propulsé par Claude
 Tapez votre question en langage naturel.
 Commandes : 'quitter' ou 'exit' pour arrêter.
============================================================

Vous : Cherche les 5 derniers incidents actifs
Claude : ...

Vous : quitter
Au revoir !
```

---

## Exemples de questions

```
Cherche les 5 derniers incidents actifs avec leur priorité
Donne-moi le détail de l'incident INC0010001
Liste les demandes de changement ouvertes
Y a-t-il des incidents de priorité 1 en cours ?
Combien d'incidents actifs y a-t-il en ce moment ?
Crée un incident avec la description "Problème réseau" et la priorité 2
Quels sont les problèmes ouverts sans assigné ?
```

---

## Dépannage

**`ModuleNotFoundError: No module named 'mcp'`**
```bash
pip3 install "mcp[cli]" anthropic httpx python-dotenv
```

**`RuntimeError: Variable ANTHROPIC_API_KEY manquante`**
Vérifie que le fichier `.env` existe à la racine du projet et contient `ANTHROPIC_API_KEY=...`.

**`RuntimeError: Variable MCP_SECRET_TOKEN manquante`**
Le token secret est requis. Demande-le à l'administrateur et ajoute-le dans le `.env`.

**Claude Desktop — "Certains serveurs MCP n'ont pas pu être chargés"**
Le chemin dans `claude_desktop_config.json` est incorrect ou le fichier `.env` est absent.
Vérifie que le chemin est absolu et que le `.env` est dans le même dossier que le proxy.

**Claude Desktop — pas de réponse ServiceNow**
Le proxy se connecte au serveur Railway au démarrage de Claude Desktop.
Si Railway redéploie pendant que Claude Desktop tourne, redémarre Claude Desktop.

**`Erreur API Anthropic : 400 - Connection error`**
Le token `MCP_SECRET_TOKEN` est incorrect, ou le serveur Railway est indisponible.
Vérifie le token puis réessaie dans quelques instants.

**`Erreur API Anthropic : 401`**
La clé API Anthropic est invalide ou expirée.
Génères-en une nouvelle sur [console.anthropic.com](https://console.anthropic.com).

---

## Fichiers du projet

| Fichier | Rôle |
|---|---|
| `servicenow_mcp_server.py` | Serveur MCP hébergé sur Railway — connecté à ServiceNow |
| `servicenow_mcp_proxy.py` | Proxy local — relie Claude Desktop au serveur Railway |
| `servicenow_api_client.py` | Client terminal — interface interactive en ligne de commande |
| `requirements.txt` | Dépendances Python du serveur Railway |
| `.env` | Variables locales (non commité dans Git) |

---

## Changer d'instance ServiceNow

L'instance cible est entièrement configurée côté Railway. Pour basculer vers une autre
instance, il suffit de mettre à jour les variables d'environnement du service
`servicenow-mcp-server` dans Railway — sans toucher au code ni aux fichiers locaux.

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

## Contact

Pour toute question, problème d'accès, ou pour obtenir le `MCP_SECRET_TOKEN`,
contacte l'administrateur du repo.

---

## Roadmap

### ✅ 1. Sécuriser l'accès au serveur

Token Bearer implémenté. Chaque requête vers Railway est authentifiée.
- Token vérifié côté serveur (query parameter `?token=...`)
- Client terminal et proxy local envoient le token automatiquement depuis le `.env`
- En mode local (stdio), la vérification est désactivée

### ✅ 2. Connecter Claude Desktop via proxy local

Le proxy `servicenow_mcp_proxy.py` permet à Claude Desktop de parler au serveur Railway
sans supporter nativement les URLs distantes. Claude peut interroger ServiceNow
directement depuis l'interface de chat.

Quand Claude Desktop supportera le format `"url"` nativement, la config deviendra :
```json
"mcpServers": {
  "servicenow": {
    "url": "https://servicenow-mcp-server-production-b9fb.up.railway.app/mcp?token=..."
  }
}
```

### 3. Étendre les fonctionnalités

Tables actuellement autorisées : `incident`, `change_request`, `sc_request`, `problem`.

Évolutions possibles :
- Ajouter de nouvelles tables selon les besoins (`kb_knowledge`, `cmdb_ci`, etc.)
- Filtrer les champs retournés pour alléger les réponses
- Ajouter la pagination pour les recherches volumineuses
- Gérer plusieurs instances ServiceNow depuis le même serveur