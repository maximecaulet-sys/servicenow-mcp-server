# ServiceNow MCP Client

Interface en ligne de commande pour interroger ServiceNow en langage naturel, propulsée par Claude (Anthropic).

## Prérequis

- Python 3.10 ou supérieur
- Un compte Anthropic avec une clé API ([console.anthropic.com](https://console.anthropic.com))
- Accès au repo GitHub (demander à l'administrateur)

## Installation

### 1. Cloner le repo

```bash
git clone https://github.com/maximecaulet/servicenow-mcp-server.git
cd servicenow-mcp-server
```

### 2. Installer les dépendances

```bash
pip install anthropic python-dotenv
```

### 3. Créer le fichier `.env`

Crée un fichier `.env` à la racine du projet :

```bash
touch .env
```

Ouvre-le et ajoute ta clé API Anthropic :

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

> 💡 Pour obtenir ta clé API : connecte-toi sur [console.anthropic.com](https://console.anthropic.com) > **API Keys** > **Create Key**.

### 4. Lancer le client

```bash
python3 servicenow_api_client.py
```

## Utilisation

Une fois lancé, le script affiche un prompt interactif dans le terminal :

```
============================================================
 Assistant ServiceNow — propulsé par Claude
 Tapez votre question en langage naturel.
 Commandes : 'quitter' ou 'exit' pour arrêter.
============================================================

Vous : Cherche les 5 derniers incidents actifs
Claude : ...

Vous : Donne-moi le détail de INC0010001
Claude : ...

Vous : quitter
Au revoir !
```

> ⚠️ **Les questions se posent dans le terminal**, pas dans une interface graphique ou dans Claude.ai. C'est une interface en ligne de commande uniquement.

Tape ta question en langage naturel et appuie sur Entrée. Claude interroge ServiceNow et te répond directement. Pour terminer la session, tape `quitter` ou `exit`.

## Exemples de questions

```
Cherche les 5 derniers incidents actifs avec leur priorité
Donne-moi le détail de l'incident INC0010001
Liste les demandes de changement ouvertes
Y a-t-il des incidents de priorité 1 en cours ?
Combien d'incidents actifs y a-t-il en ce moment ?
Crée un incident avec la description "Problème réseau" et la priorité 2
```

## Architecture

Ce projet propose deux façons d'interroger ServiceNow, toutes les deux via le terminal :

```
─── Option 1 : Client Python → Railway (recommandé) ───────────────

servicenow_api_client.py  →  API Anthropic (Claude)  →  Serveur MCP Railway  →  ServiceNow
     (ton terminal)               (cloud)                   (cloud)               (cloud)

─── Option 2 : Serveur local (Claude Desktop uniquement) ───────────

Claude Desktop  →  servicenow_mcp_server.py (local)  →  ServiceNow
  (questions                 (ton Mac)                   (cloud)
 dans le chat)
```

**Option 1 — `servicenow_api_client.py` (ce README)**
Tu lances le script dans ton terminal, tu poses tes questions en langage naturel, Claude répond. Le serveur MCP tourne sur Railway — tu n'as pas à t'en occuper. C'est la méthode recommandée pour tous les utilisateurs.

**Option 2 — Claude Desktop**
Réservée à l'administrateur du projet. Nécessite d'avoir Python et le repo installés localement, et une configuration spécifique de Claude Desktop (`claude_desktop_config.json`). Permet de poser les questions directement dans l'interface Claude Desktop plutôt que dans le terminal.

> Dans les deux cas, **les questions se posent en ligne de commande ou dans Claude Desktop** — il n'y a pas d'interface web disponible pour l'instant.

## Dépannage

**`ModuleNotFoundError: No module named 'anthropic'`**
```bash
pip install anthropic python-dotenv
```

**`RuntimeError: Variable ANTHROPIC_API_KEY manquante`**
Vérifie que ton fichier `.env` existe à la racine du projet et contient bien `ANTHROPIC_API_KEY=...`.

**`Erreur API Anthropic : 401`**
Ta clé API est invalide ou expirée. Génères-en une nouvelle sur [console.anthropic.com](https://console.anthropic.com).

**`Erreur API Anthropic : 400 - Error while communicating with MCP server`**
Le serveur MCP Railway est peut-être temporairement indisponible. Réessaie dans quelques instants.

**La réponse est vide ou incohérente**
Le serveur MCP Railway est peut-être en train de redémarrer. Attends 30 secondes et réessaie.

## Contact

Pour toute question ou problème d'accès, contacte l'administrateur du repo.