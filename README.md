# ServiceNow MCP Client

Interface en ligne de commande pour interroger ServiceNow en langage naturel, propulsée par Claude (Anthropic).

## Prérequis

- Python 3.10 ou supérieur
- Un compte Anthropic avec une clé API ([console.anthropic.com](https://console.anthropic.com))
- Accès au repo GitHub (demander à l'administrateur)

## Installation

### 1. Cloner le repo

```bash
git clone https://github.com/TON_USERNAME/servicenow-mcp-server.git
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

Le script exécute automatiquement plusieurs exemples de requêtes sur ServiceNow :
- Liste des derniers incidents actifs
- Recherche de demandes (requests)
- Comptage d'incidents par priorité

Pour personnaliser les questions, ouvre `servicenow_api_client.py` et modifie la liste `exemples` en bas du fichier :

```python
exemples = [
    "Cherche les 10 derniers incidents de priorité 1",
    "Y a-t-il des problèmes ouverts non assignés ?",
    "Liste les demandes en attente depuis plus d'une semaine",
]
```

## Exemples de questions

Voici quelques exemples de questions que tu peux poser :

```
"Cherche les 5 derniers incidents actifs avec leur priorité"
"Donne-moi le détail de l'incident INC0010001"
"Liste les demandes de changement ouvertes"
"Y a-t-il des incidents de priorité 1 en cours ?"
"Combien d'incidents actifs y a-t-il en ce moment ?"
```

## Architecture

```
servicenow_api_client.py   →   API Anthropic (Claude)   →   Serveur MCP (Railway)   →   ServiceNow
      (ta machine)                   (cloud)                     (cloud)                   (cloud)
```

- **Le client** (`servicenow_api_client.py`) tourne sur ta machine et envoie tes questions à Claude.
- **Le serveur MCP** tourne sur Railway et fait le lien avec ServiceNow. Tu n'as pas à t'en occuper.
- **Les credentials ServiceNow** sont gérés côté serveur — tu n'as besoin que de ta clé API Anthropic.

## Dépannage

**`ModuleNotFoundError: No module named 'anthropic'`**
```bash
pip install anthropic python-dotenv
```

**`RuntimeError: Variable ANTHROPIC_API_KEY manquante`**
Vérifie que ton fichier `.env` existe à la racine du projet et contient bien `ANTHROPIC_API_KEY=...`.

**`Erreur API Anthropic : 401`**
Ta clé API est invalide ou expirée. Génères-en une nouvelle sur [console.anthropic.com](https://console.anthropic.com).

**La réponse est vide ou incohérente**
Le serveur MCP Railway est peut-être temporairement indisponible. Réessaie dans quelques instants.

## Contact

Pour toute question ou problème d'accès, contacte l'administrateur du repo.