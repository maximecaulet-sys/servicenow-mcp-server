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

Importer le fichier `mcp_user.xml` présent dans le repo, dans la table `sys_user`.

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

## Configuration locale sans Railway

Il est possible de faire tourner le serveur MCP directement sur ta machine, sans passer par Railway. Utile pour le développement, les tests, ou si tu ne veux pas héberger le serveur en ligne.

Dans ce mode, Claude Desktop lance `servicenow_mcp_server.py` directement en stdio — le proxy n'est pas nécessaire, et le `MCP_SECRET_TOKEN` non plus (le serveur est local, la sécurité réseau ne s'applique pas).

### 1. Créer le fichier `.env` local

Le fichier `.env` doit contenir les credentials ServiceNow (et non plus seulement le token) :

```
SERVICENOW_INSTANCE_URL=https://ton-instance.service-now.com
SERVICENOW_CLIENT_ID=ton_client_id
SERVICENOW_CLIENT_SECRET=ton_client_secret
SERVICENOW_USERNAME=mcp.integration
SERVICENOW_PASSWORD=ton_mot_de_passe
```

### 2. Installer les dépendances

```bash
pip3 install "mcp[cli]" httpx python-dotenv
```

### 3. Configurer Claude Desktop

Dans `claude_desktop_config.json`, pointer directement vers le serveur (pas le proxy) :

```json
"mcpServers": {
  "servicenow": {
    "command": "python3",
    "args": ["/chemin/absolu/vers/servicenow_mcp_server.py"]
  }
}
```

Claude Desktop lance le serveur en mode stdio au démarrage. Le serveur détecte automatiquement l'absence de `TRANSPORT=sse` et démarre en mode local.

### Comparaison des deux modes

| | Mode Railway (recommandé) | Mode local |
|---|---|---|
| Serveur | Hébergé sur Railway | Sur ta machine |
| Proxy | `servicenow_mcp_proxy.py` requis | Non nécessaire |
| `MCP_SECRET_TOKEN` | Requis | Non nécessaire |
| Credentials ServiceNow dans `.env` | Non (côté Railway) | Oui |
| Disponible si laptop éteint | ✅ | ❌ |
| Partageable avec des collègues | ✅ | ❌ |
| Idéal pour | Production / usage quotidien | Développement / tests |

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
Le proxy se reconnecte automatiquement au serveur Railway en cas de coupure (redéploiement, timeout réseau). Si le problème persiste après quelques secondes, redémarre Claude Desktop.

**`401 Unauthorized` / `{"error":"server_error","error_description":"access_denied"}` sur `/oauth_token.do`**
Message générique côté ServiceNow qui masque la vraie cause. Vérifier dans cet ordre :
1. Les variables d'environnement locales (`export SERVICENOW_...` dans le terminal, ou `.env`)
   correspondent bien à l'instance visée — surtout après un changement d'instance sur
   Railway, où les anciennes valeurs exportées dans un terminal resté ouvert peuvent
   pointer vers une instance différente sans que l'erreur ne le dise explicitement.
2. Le compte de service (`mcp.integration`) est actif, non verrouillé, mot de passe non
   expiré, sans MFA activé (le grant `password` ne gère pas de second facteur).
3. L'Application Registry existe et est active sur **cette** instance précise — un
   `client_id`/`client_secret` créé sur une instance ne fonctionne jamais sur une autre.
4. **L'Auth Scope de l'Application Registry est bien `useraccount`** (voir section
   "Créer l'Application Registry OAuth" plus haut) — un scope manquant ou incorrect peut
   produire ce même message générique selon la version de l'instance.
5. En dernier recours, consulter **System Logs > All** filtré sur `oauth` : ServiceNow y
   logue en interne une cause plus précise que celle renvoyée par l'API.

**Tester `aggregate_records` isolément, sans terminal, une fois le serveur redéployé**
Poser directement une question dans Claude Desktop (ou tout client connecté au serveur) :
```
Utilise aggregate_records sur sc_req_item, groupé par cat_item et cat_item.category
```
Si l'outil n'apparaît pas dans la liste des tools, le déploiement Railway n'a probablement
pas pris en compte le dernier `git push` (vérifier les logs de build Railway).

---

## Fichiers du projet

| Fichier | Rôle |
|---|---|
| `servicenow_mcp_server.py` | Serveur MCP hébergé sur Railway — connecté à ServiceNow |
| `servicenow_mcp_proxy.py` | Proxy local — relie Claude Desktop au serveur Railway |
| `aggregate_tool.py` | Outil `aggregate_records` — enregistré dans `servicenow_mcp_server.py`, whitelist de tables propre et indépendante |
| `requirements.txt` | Dépendances Python du serveur Railway |
| `.env` | Variables locales (non commité dans Git) |

---

## Outils disponibles

| Outil | Paramètres | Description |
|---|---|---|
| `search_records` | `table`, `query`, `limit`, `offset`, `fields` | Recherche des enregistrements dans une table |
| `get_record` | `table`, `sys_id` | Récupère un enregistrement complet par son sys_id |
| `aggregate_records` | `table`, `group_by`, `query`, `count` | Agrège des enregistrements (équivalent `GlideAggregate`) via l'Aggregate API ServiceNow — un seul appel serveur, pas de pagination |

> `search_records` supporte la **pagination** via `offset` (ex: `limit=50, offset=50` → résultats 51 à 100)
> et la **sélection de champs** via `fields` (ex: `fields="number,short_description,priority"`) pour des réponses plus légères.

> `aggregate_records` évite de devoir paginer des tables volumineuses (ex: `sc_req_item`
> avec des dizaines de milliers de lignes) juste pour compter des occurrences. Exemple :
> `aggregate_records(table="sc_req_item", group_by="cat_item,cat_item.category")` renvoie
> directement, par item de catalogue, le nombre de demandes et la catégorie associée
> (dot-walk supporté dans `group_by`), sans avoir à parcourir chaque enregistrement.
> Utilisé notamment par le skill Claude "iteo-sn-taxonomy-analysis" (analyse de taxonomie
> de catalogue).
>
> Cet outil a sa **propre whitelist de tables**, séparée et plus restreinte que
> `ALLOWED_TABLES` (qui couvre `search_records`/`get_record`) : seules les tables de
> volumétrie légitimes pour une agrégation (`sc_req_item`, `sc_request`, `sc_task`,
> `incident`, `incident_task`, `change_request`, `change_task`, `problem`, `problem_task`)
> y sont autorisées. Les tables sensibles ou techniques (`sys_user`, `sys_security_acl`,
> `sys_properties`...) — autorisées en lecture enregistrement-par-enregistrement — ne
> sont volontairement **pas** agrégeables. Pour ajouter une table à l'agrégation,
> modifier `AGGREGATE_ALLOWED_TABLES` dans `aggregate_tool.py` (indépendant de
> `ALLOWED_TABLES` dans `servicenow_mcp_server.py`).

Les outils d'écriture (`create_record`, `update_record`, `add_comment`) sont présents dans le code mais désactivés volontairement — l'instance est actuellement en lecture seule. Pour les activer, décommenter les fonctions correspondantes dans `servicenow_mcp_server.py` et pousser sur GitHub.

**Tables autorisées** (extraits principaux) :

| Domaine | Tables |
|---|---|
| ITSM | `incident`, `incident_task`, `change_request`, `change_task`, `sc_request`, `sc_req_item`, `sc_task`, `sc_cat_item`, `problem`, `problem_task`, `task_sla` |
| Knowledge | `kb_knowledge`, `kb_knowledge_base`, `kb_category`, `kb_feedback` |
| CMDB | `cmdb_ci`, `cmdb_ci_service`, `cmdb_rel_ci`, `cmdb_ci_class` |
| Assets | `alm_hardware`, `alm_asset`, `alm_license`, `ast_contract` |
| ITOM | `em_event`, `em_alert` |
| Intégration | `sys_rest_message`, `sys_web_service`, `sys_data_source`, `sys_transform_map` |
| Configuration | `sys_script`, `sys_script_include`, `sys_ui_policy`, `wf_workflow`, `sys_update_set` |

Pour ajouter ou retirer des tables, modifier `ALLOWED_TABLES` dans `servicenow_mcp_server.py` et pousser sur GitHub.

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