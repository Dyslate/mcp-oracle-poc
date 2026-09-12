# MCP Oracle POC (Python)

Serveur **MCP (Model Context Protocol)** en **Python**, bâti avec la
bibliothèque **[FastMCP](https://github.com/jlowin/fastmcp)** (v2), qui expose à
Claude des outils pour interagir avec une base de données **Oracle** : lister
les tables, décrire une table, exécuter des `SELECT` en lecture seule, et
effectuer des écritures `INSERT`/`UPDATE`/`DELETE` avec un mécanisme de
confirmation.

> POC pédagogique : conçu pour être testé rapidement, avec des garde-fous de
> sécurité raisonnables. À durcir avant tout usage en production.

## Démonstration

Le serveur MCP connecté à **Claude Desktop**, répondant à des questions en
langage naturel sur une vraie base **Oracle** — de bout en bout.

**1. Le serveur `oracle` chargé dans Claude Desktop** (Paramètres → Développeur →
Local MCP servers) :

![Serveur MCP oracle dans Claude Desktop](image/developer_settings_claude.png)

**2. Interroger la base en langage naturel** — Claude appelle l'outil
`execute_query` sous le capot :

![Exemple de requête via Claude](image/example_of_query.png)

**3. « Qui habite à Paris ? »** — Claude traduit la question en
`SELECT name FROM demo_clients WHERE city = :ville` (avec une *bind variable*,
donc protégé contre l'injection SQL), l'exécute et répond :

![Qui habite à Paris](image/exemple_of_who_lives_in_paris.png)

---

## Sommaire

- [Démonstration](#démonstration)
- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration Oracle](#configuration-oracle)
- [Lancer une base Oracle de test](#lancer-une-base-oracle-de-test)
- [Exécution](#exécution)
- [Tester rapidement](#tester-rapidement)
- [Configurer Claude Desktop](#configurer-claude-desktop)
- [Configurer Claude Code](#configurer-claude-code)
- [Outils exposés](#outils-exposés)
- [Sécurité](#sécurité)
- [Dépannage](#dépannage)

---

## Fonctionnalités

- **4 outils MCP** : `list_tables`, `describe_table`, `execute_query`, `execute_dml`.
- **Framework `FastMCP` (v2)** : outils déclarés par décorateur `@mcp.tool()`,
  schéma d'entrée inféré depuis les annotations de type + `pydantic.Field`.
- **Pool de connexions** `python-oracledb` (emprunt/restitution via context manager).
- **Mode Thin par défaut** : aucun client Oracle natif à installer.
- **Garde-fous de sécurité** : lecture seule stricte pour les requêtes,
  confirmation en deux temps pour les écritures, blocage du DDL, plafonnement
  du nombre de lignes, bind variables.
- **Logging clair** sur `stderr` (sans polluer le canal MCP stdout).
- **Configuration via `.env`**, typée et validée au démarrage (fail-fast).

## Architecture

```
POC_MCP_ORACLE/
├── src/mcp_oracle_poc/
│   ├── __init__.py
│   ├── __main__.py            # `python -m mcp_oracle_poc`
│   ├── server.py             # Point d'entrée : démarre le serveur MCP (stdio)
│   ├── config.py             # Chargement + validation des variables d'env
│   ├── logging_config.py     # Logger (stderr uniquement)
│   ├── oracle.py             # Pool de connexions + helpers de sécurité SQL
│   └── tools/
│       ├── __init__.py       # Enregistre tous les outils
│       ├── common.py         # Helpers (conversion lignes, JSON, LOB)
│       ├── list_tables.py    # Outil list_tables
│       ├── describe_table.py # Outil describe_table
│       ├── execute_query.py  # Outil execute_query (SELECT)
│       └── execute_dml.py    # Outil execute_dml (INSERT/UPDATE/DELETE)
├── demo_setup.py             # Crée une petite table de démo (demo_clients)
├── show_tables.py            # Affiche les tables + demo_clients dans le terminal
├── test_connexion.py         # Test rapide de connexion Oracle
├── test_mcp.py               # Test des outils via un client MCP en mémoire
├── test_dml.py               # Démo du dry-run/COMMIT sur execute_dml
├── image/                    # Captures d'écran de la démo
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```

## Prérequis

- **Python ≥ 3.10**
- Une base **Oracle** accessible (installée localement, via Docker, ou distante).
- `python-oracledb` fonctionne en **mode Thin** sans Instant Client. Le mode
  Thick (client natif) n'est nécessaire que pour des fonctionnalités avancées.

## Installation

```bash
# 1. (Recommandé) Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate

# 2. Installer le projet dans CET environnement
pip install -e .

# 3. Créer votre fichier de configuration
cp .env.example .env               # Windows : copy .env.example .env
# puis éditez .env avec vos identifiants Oracle
```

> **Important :** installez le projet dans le **même** interpréteur Python que
> celui que le client MCP lancera. Si vous créez un venv, faites `pip install -e .`
> dedans (ex. sous Windows : `.venv\Scripts\python.exe -m pip install -e .`).
> Sinon vous obtiendrez `No module named mcp_oracle_poc`.

## Configuration Oracle

Renseignez ces variables dans `.env` (voir `.env.example`) :

| Variable                   | Obligatoire | Description                                                        |
| -------------------------- | :---------: | ----------------------------------------------------------------- |
| `ORACLE_USER`              |     oui     | Utilisateur Oracle.                                               |
| `ORACLE_PASSWORD`          |     oui     | Mot de passe.                                                     |
| `ORACLE_CONNECTION_STRING` |     oui     | Easy Connect `host:port/service` ou alias tnsnames.              |
| `ORACLE_POOL_MIN`          |     non     | Connexions minimales du pool (défaut `0`).                       |
| `ORACLE_POOL_MAX`          |     non     | Connexions maximales du pool (défaut `4`).                       |
| `QUERY_MAX_ROWS`           |     non     | Plafond de lignes pour `execute_query` (défaut `100`).           |
| `ALLOW_DML`                |     non     | `false` pour un serveur strictement en lecture seule (défaut `true`). |
| `ORACLE_CLIENT_LIB_DIR`    |     non     | Chemin Instant Client pour activer le mode Thick.                |
| `LOG_LEVEL`                |     non     | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` (défaut `INFO`).        |

**Exemple de `ORACLE_CONNECTION_STRING`** (Easy Connect) : `localhost:1521/FREEPDB1`

## Lancer une base Oracle de test

Deux options simples pour une base locale :

**Installeur natif (Windows/Linux)** — téléchargez **Oracle Database Free** sur
<https://www.oracle.com/database/free/>. L'installeur crée automatiquement une
base prête à l'emploi (service `FREEPDB1`) ; renseignez le mot de passe que vous
avez choisi pendant l'installation.

**Docker** — image communautaire, sans compte Oracle :

```bash
docker run -d --name oracle-free -p 1521:1521 -e ORACLE_PASSWORD=change_me gvenzl/oracle-free
```

Puis dans `.env` :

```
ORACLE_USER=system
ORACLE_PASSWORD=change_me
ORACLE_CONNECTION_STRING=localhost:1521/FREEPDB1
```

## Exécution

```bash
python -m mcp_oracle_poc
# ou, si installé en package :
mcp-oracle-poc
```

Le serveur écrit ses logs sur **stderr** et parle MCP sur **stdout** ; c'est
normal qu'il « attende » : il est piloté par un client MCP.

## Tester rapidement

Plusieurs scripts utilitaires sont fournis (venv actif, `.env` renseigné) :

```bash
python demo_setup.py       # crée une table de démo demo_clients (3 lignes)
python show_tables.py      # affiche les tables + le contenu de demo_clients
python test_connexion.py   # vérifie la connexion Oracle
python test_mcp.py         # appelle les outils via un client MCP en mémoire
python test_dml.py         # montre la simulation (dry-run) puis le COMMIT réel
```

Vous pouvez aussi lancer le **MCP Inspector** via FastMCP (nécessite Node.js) :

```bash
fastmcp dev src/mcp_oracle_poc/server.py
```

## Configurer Claude Desktop

Ouvrez **Paramètres → Développeur → Edit config** et ajoutez le serveur `oracle`
(utilisez des **chemins absolus**, et le Python de votre venv) :

```json
{
  "mcpServers": {
    "oracle": {
      "command": "C:\\POC_MCP_ORACLE\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_oracle_poc"],
      "env": {
        "ORACLE_USER": "system",
        "ORACLE_PASSWORD": "change_me",
        "ORACLE_CONNECTION_STRING": "localhost:1521/FREEPDB1",
        "QUERY_MAX_ROWS": "100",
        "ALLOW_DML": "true"
      }
    }
  }
}
```

Sous Windows, les chemins prennent des **doubles antislashs** `\\`. Quittez
complètement Claude Desktop puis rouvrez-le : le serveur `oracle` apparaît sous
**Paramètres → Développeur → Local MCP servers**. Demandez alors :
*« Liste les tables de ma base Oracle »*.

> Les serveurs MCP **locaux** (stdio) se configurent via ce fichier — **pas**
> via « Add custom connector », qui est réservé aux serveurs distants en HTTPS.

## Configurer Claude Code

```bash
claude mcp add oracle -- python -m mcp_oracle_poc
```

Ou via `.mcp.json` à la racine du projet :

```json
{
  "mcpServers": {
    "oracle": {
      "command": "python",
      "args": ["-m", "mcp_oracle_poc"]
    }
  }
}
```

## Outils exposés

### `list_tables`

Liste les tables du schéma courant, ou d'un schéma donné.

```jsonc
{ "owner": "HR" }   // optionnel ; par défaut = utilisateur courant
```

### `describe_table`

Décrit les colonnes d'une table (nom, type, nullabilité).

```jsonc
{ "table_name": "EMPLOYEES", "owner": "HR" }  // owner optionnel
```

### `execute_query`

Exécute un `SELECT` (ou `WITH ... SELECT`) en **lecture seule**, avec bind
variables et plafonnement du nombre de lignes.

```jsonc
{
  "sql": "SELECT * FROM employees WHERE department_id = :dep",
  "binds": { "dep": 10 },
  "max_rows": 50
}
```

### `execute_dml`

Exécute `INSERT` / `UPDATE` / `DELETE` avec **confirmation en deux temps** :

- `confirm` absent ou `false` → **simulation** (dry-run) : indique le nombre de
  lignes qui seraient impactées, puis `ROLLBACK` (rien n'est modifié).
- `confirm: true` → exécution réelle avec `COMMIT`.

```jsonc
// 1) simulation
{ "sql": "UPDATE employees SET salary = salary * 1.1 WHERE department_id = :d", "binds": { "d": 10 } }

// 2) exécution réelle (après validation de l'utilisateur)
{ "sql": "UPDATE employees SET salary = salary * 1.1 WHERE department_id = :d", "binds": { "d": 10 }, "confirm": true }
```

## Sécurité

Ce POC applique plusieurs garde-fous :

- **Séparation lecture / écriture** : `execute_query` refuse tout ce qui n'est
  pas `SELECT`/`WITH` ; `execute_dml` n'accepte que `INSERT`/`UPDATE`/`DELETE`.
- **Interdiction du DDL et du PL/SQL** : `DROP`, `TRUNCATE`, `ALTER`, `CREATE`,
  `GRANT`, `MERGE`, `BEGIN`, `EXECUTE`, etc. sont bloqués partout.
- **Anti "stacked queries"** : une seule instruction par appel.
- **Confirmation des écritures** : dry-run + `ROLLBACK` par défaut, `COMMIT`
  seulement sur `confirm: true`.
- **Avertissement `WHERE` manquant** sur `UPDATE`/`DELETE`.
- **Plafond de lignes** (`QUERY_MAX_ROWS`) pour éviter les dumps.
- **Bind variables** pour prévenir l'injection SQL.
- **Kill switch** : `ALLOW_DML=false` rend le serveur strictement en lecture seule.

**Pour aller plus loin** : créer un utilisateur Oracle dédié avec des privilèges
minimaux (idéalement lecture seule) plutôt que `system`, activer l'audit Oracle,
et restreindre le réseau. Les garde-fous applicatifs ne remplacent pas des
privilèges base de données bien configurés.

## Dépannage

- **`ORA-01017` (identifiants invalides)** : vérifiez `ORACLE_USER` /
  `ORACLE_PASSWORD`.
- **`ORA-12514` (service inconnu)** : vérifiez le service dans
  `ORACLE_CONNECTION_STRING` (ex. `FREEPDB1`).
- **`DPY-6005` / connexion refusée (`WinError 10061`)** : rien n'écoute sur
  l'hôte/port indiqué. Vérifiez l'adresse d'écoute du listener
  (`netstat -ano | findstr 1521`) : s'il n'écoute que sur l'IP LAN de la machine
  (ex. `192.168.1.20`), mettez **cette IP** dans `ORACLE_CONNECTION_STRING` au
  lieu de `localhost`.
- **`No module named mcp_oracle_poc`** : le paquet n'est pas installé dans le
  Python lancé — faites `pip install -e .` dans **ce** même environnement (venv).
- **Claude Desktop affiche « Server disconnected »** : en général un plantage au
  démarrage (voir les points ci-dessus) ou une pollution de stdout — ce projet
  démarre FastMCP avec `show_banner=False` pour garder le canal stdio propre.
- **Le serveur « ne fait rien »** : c'est normal, il attend un client MCP.

---

## Licence

MIT — POC fourni à titre d'exemple.
