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

## Roadmap — Prochaines étapes

### 1. Sécuriser l'accès au serveur (prioritaire)

Le serveur MCP Railway est actuellement **ouvert publiquement** — n'importe qui connaissant l'URL peut interroger ServiceNow. Avant tout déploiement plus large, il faut ajouter une authentification.

**Ce qui est à faire :**
- Générer un token secret (longue chaîne aléatoire)
- Ajouter une vérification de ce token dans `servicenow_mcp_server.py` (header `Authorization: Bearer ...`)
- Ajouter ce token en variable d'environnement sur Railway (`MCP_SECRET_TOKEN`)
- Ajouter ce token dans le `.env` de chaque utilisateur autorisé (`MCP_SECRET_TOKEN=...`)

Sans cette étape, l'URL du serveur ne doit pas être partagée publiquement.

---

### 2. Rendre l'accès plus simple (choisir une option)

Aujourd'hui l'utilisation nécessite Python et un terminal. Deux pistes pour simplifier l'accès :

#### Option A — Intégration dans Claude Desktop / Claude.ai

Quand Anthropic supportera nativement les serveurs MCP distants via URL dans Claude Desktop et claude.ai (fonctionnalité en cours de déploiement), il suffira d'ajouter l'URL du serveur Railway dans les paramètres de chaque utilisateur :

```json
"mcpServers": {
  "servicenow": {
    "url": "https://servicenow-mcp-server-production-b9fb.up.railway.app/mcp",
    "headers": {
      "Authorization": "Bearer TON_SECRET_TOKEN"
    }
  }
}
```

Chaque utilisateur pourra alors poser ses questions directement dans l'interface Claude, sans script Python ni terminal. C'est la solution la plus élégante à terme — à surveiller lors des mises à jour de Claude Desktop.

#### Option B — Interface web dédiée

Créer une petite application web (Flask ou FastAPI) hébergée sur Railway qui expose une interface simple dans le navigateur : un champ de texte pour poser une question, une zone de réponse. En arrière-plan, l'app appelle l'API Anthropic + le serveur MCP Railway.

**Avantages :** accessible depuis n'importe quel navigateur, aucune installation requise pour les utilisateurs, contrôle total sur l'authentification et les droits d'accès.

**Effort estimé :** 1 journée de développement.

---

### 3. Étendre les fonctionnalités du serveur MCP

Le serveur actuel couvre 4 tables (`incident`, `change_request`, `sc_request`, `problem`) et 5 outils de base. Des évolutions possibles :

- Ajouter de nouvelles tables (`kb_knowledge`, `cmdb_ci`, `sys_user`, etc.)
- Ajouter un outil de suppression avec confirmation explicite
- Filtrer les champs retournés par ServiceNow pour alléger les réponses
- Ajouter de la pagination pour les recherches avec beaucoup de résultats
- Gérer plusieurs instances ServiceNow depuis le même serveur MCP