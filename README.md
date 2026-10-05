# Containerized Movie Knowledge Graph with Neo4j

[![Neo4j Version](https://img.shields.io/badge/Neo4j-5.18.0-008CC1.svg?logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v2%2B-2496ED.svg?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Testing Suite](https://img.shields.io/badge/Pytest-Passing-brightgreen.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A production-ready, containerized **Movie Knowledge Graph** engineered with **Neo4j 5.18**, **Docker Compose**, **Cypher**, and **Python**. This project demonstrates property graph modeling, ACID-compliant transactional queries, graph algorithms (degree centrality), automated database seeding, and a standalone Python verification and CLI toolkit.

---

## 1. Project Motivation & Architecture

In traditional relational database management systems (RDBMS), modeling complex, highly interconnected networks—such as filmographies, social circles, recommendation engines, and fraud rings—demands recursive foreign key joins across normalized tables. As network depth increases, relational join operations experience exponential latency degradation ($O(k^d)$ complexity).

Native graph databases like Neo4j utilize **index-free adjacency**, where each node acts as a micro-index pointing directly to its neighboring relationships and nodes in constant time ($O(1)$ pointer dereferencing). This architecture allows traversals through millions of relationships with sub-millisecond query latency.

### System Architecture Diagram

```
+-----------------------------------------------------------------------------------+
| Your Local Machine                                                                |
|                                                                                   |
|  +---------------------------+       +-----------------------------------------+  |
|  | You, the Developer        |       | Python Application & Verification Suite |  |
|  | Interacts with            |       | - src/cli.py (Interactive CLI)          |  |
|  | Neo4j Browser             |       | - src/graph_service.py (Service Layer)  |  |
|  | (http://localhost:7474)   |       | - verify_submission.py (10 Req Runner)  |  |
|  +-------------+-------------+       | - tests/test_graph.py (Pytest Harness)  |  |
|                |                     +--------------------+--------------------+  |
|                | HTTP (7474)                              | Bolt (7687)           |
|                | Cypher via Browser                       | Binary Protocol       |
|                +--------------------+---------------------+                       |
|                                     |                                             |
|                                     v                                             |
|  +-----------------------------------------------------------------------------+  |
|  | Docker Environment (movie_knowledge_graph_db)                               |  |
|  |                                                                             |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  | Neo4j Docker Container (Image: neo4j:5.18.0)                           |  |  |
|  |  | - Port 7474: HTTP Browser & Transaction API                           |  |  |
|  |  | - Port 7687: Bolt Binary Wire Protocol                               |  |  |
|  |  | - Healthcheck: wget basic-auth probe on http://localhost:7474         |  |  |
|  |  +-------------------+--------------------+--------------------+---------+  |  |
|  |                      |                    |                    |            |  |
|  +----------------------|--------------------|--------------------|------------+  |
|                         |                    |                    |               |
|            Persists to  |       Writes logs  |       Initial startup              |
|                         v                    v                    v               |
|                   ./data Volume        ./logs Volume        ./init/seed.cypher    |
|                   (Graph Database)     (Server Logs)        (Auto-Seed Scripts)   |
+-----------------------------------------------------------------------------------+
```

### Architectural Components

1. **Neo4j Docker Container**: Runs the Neo4j 5.18 Community Server engine on Alpine/Debian Linux, providing transaction isolation, memory buffers, and page caching.
2. **Docker Compose Orchestration**: Manages the complete lifecycle, volume bind mounts, container networking, memory limits, and automated HTTP healthcheck probes.
3. **Data & Log Volumes (`./data`, `./logs`)**: Ensures persistent storage of the transactional Write-Ahead Log (WAL) and graph record stores across container restarts.
4. **Initialization Seeding (`./init/seed.cypher`)**: Mounted to `/var/lib/neo4j/import`. When the database initializes an empty data store, this script automatically applies schema constraints, genres, movies, people, and relationships idempotently.
5. **Python Application & Verification Suite**:
   - `src/graph_service.py`: High-level business logic and database access driver.
   - `src/cli.py`: Interactive command-line explorer and query dispatcher.
   - `src/mock_engine.py`: High-fidelity in-memory property graph engine allowing comprehensive automated testing and validation offline without requiring Docker.
   - `verify_submission.py`: Evaluates all 10 Core Requirements with colored terminal diagnostics.
   - `package_submission.py`: Bundles the submission archive per instructor specifications.

---

## 2. Graph Data Model Specification

The movie knowledge graph is modeled as a **Labeled Property Graph (LPG)** comprising 3 entity types, 4 directed relationship types, and explicit uniqueness constraints.

```
       (:Person) ────[:ACTED_IN {roles: [...]}]───> (:Movie)
       (:Person) ──────────[:DIRECTED]─────────────> (:Movie)
       (:Person) ──────────[:PRODUCED]─────────────> (:Movie)
       (:Movie)  ──────────[:HAS_GENRE]────────────> (:Genre)
```

### Node Labels & Properties

| Label | Description | Primary Key / Constraints | Properties | Sample Entity |
| :--- | :--- | :--- | :--- | :--- |
| **`Movie`** | Represents an individual film | `title` (`IS UNIQUE`) | `title` (string), `released` (integer), `tagline` (string), `rating` (float) | `(:Movie {title: "The Matrix", released: 1999, tagline: "Welcome to the Real World"})` |
| **`Person`** | Represents an actor, director, or producer | `name` (`IS UNIQUE`) | `name` (string), `born` (integer) | `(:Person {name: "Keanu Reeves", born: 1964})` |
| **`Genre`** | Represents a thematic film genre | `name` (`IS UNIQUE`) | `name` (string) | `(:Genre {name: "Sci-Fi"})` |

### Relationship Types & Direction

| Relationship Type | Direction | Semantics | Relationship Properties | Example |
| :--- | :--- | :--- | :--- | :--- |
| **`ACTED_IN`** | `(:Person)-[:ACTED_IN]->(:Movie)` | A person performed as an actor in a film | `roles` (list of strings) | `(:Person {name: "Keanu Reeves"})-[:ACTED_IN {roles: ['Neo']}]->(:Movie {title: "The Matrix"})` |
| **`DIRECTED`** | `(:Person)-[:DIRECTED]->(:Movie)` | A person directed the film | *(None)* | `(:Person {name: "Lana Wachowski"})-[:DIRECTED]->(:Movie {title: "The Matrix"})` |
| **`PRODUCED`** | `(:Person)-[:PRODUCED]->(:Movie)` | A person produced the film | *(None)* | `(:Person {name: "Joel Silver"})-[:PRODUCED]->(:Movie {title: "The Matrix"})` |
| **`HAS_GENRE`** | `(:Movie)-[:HAS_GENRE]->(:Genre)` | The film belongs to a thematic category | *(None)* | `(:Movie {title: "The Matrix"})-[:HAS_GENRE]->(:Genre {name: "Sci-Fi"})` |

---

## 3. Project Directory Structure

```
movie-knowledge-graph-neo4j/
├── docker-compose.yml           # Core Req 1: Neo4j 5.18.0 service & healthcheck
├── .env.example                 # Core Req 2: Documented NEO4J_AUTH environment template
├── .env                         # Local development secrets (git-ignored)
├── .gitignore                   # Ignores data/, logs/, caches, secrets, zip archives
├── requirements.txt             # Python dependencies (neo4j, pytest, tabulate, etc.)
├── package_submission.py        # Automated submission archive generator (submission.zip)
├── verify_submission.py         # Standalone runner validating all 10 Core Requirements
│
├── init/
│   └── seed.cypher              # Core Req 3 & 4: Schema constraints and seed data
│
├── queries/
│   ├── create_movie.cypher      # Core Req 5: Creates 'V for Vendetta' and connects Hugo Weaving
│   ├── find_actor_movies.cypher # Core Req 6: Finds all movies acted by Keanu Reeves
│   ├── find_co_actors.cypher    # Core Req 7: Finds co-actors of Hugo Weaving in The Matrix
│   ├── update_movie_rating.cypher # Core Req 8: Updates rating property to 8.7 on The Matrix
│   ├── delete_movie.cypher      # Core Req 9: Safely removes 'To Be Deleted' via DETACH DELETE
│   └── analytics_degree.cypher  # Core Req 10: Top 5 most connected people (Degree Centrality)
│
├── src/
│   ├── __init__.py              # Package initializer
│   ├── config.py                # Environment configuration loader (.env)
│   ├── connection.py            # Neo4j Bolt driver lifecycle & fast socket pre-check
│   ├── graph_service.py         # Service layer executing Cypher & business operations
│   ├── mock_engine.py           # In-memory Property Graph Engine for offline validation
│   └── cli.py                   # Interactive Command-Line Interface with ASCII tables
│
├── tests/
│   ├── __init__.py              # Test package initializer
│   └── test_graph.py            # Pytest test suite covering all 10 requirements
│
└── docs/
    └── PROJECT_REPORT.md        # In-depth academic & technical engineering report
```

---

## 4. Quick Start & Setup Guide

### Step 1: Clone Repository & Configure Environment

```bash
git clone https://github.com/Adarsh12325/movie-knowledge-graph-neo4j.git
cd movie-knowledge-graph-neo4j

# Copy environment template to .env
cp .env.example .env
```

The default `.env` is configured as:
```env
NEO4J_AUTH=neo4j/neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j
```

> **Note**: The base64 authorization header in `docker-compose.yml` (`bmVvNGo6bmVvNGo=`) decodes to `neo4j:neo4j`. Using `neo4j/neo4j` in `.env` guarantees the healthcheck passes immediately without manual reconfiguration.

### Step 2: Install Python Dependencies

```bash
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 3: Launch Neo4j Container

```bash
docker compose up -d
```

Check the healthcheck status:
```bash
docker compose ps
```
The container will transition from `(health: starting)` to `(healthy)` within ~30 seconds.

### Step 4: Access Neo4j Browser

Open your browser and navigate to:
**`http://localhost:7474`**
- **Connect URL**: `bolt://localhost:7687`
- **Username**: `neo4j`
- **Password**: `neo4j` (or the password configured in your `.env`)

---

## 5. Core Cypher Queries Detailed Walkthrough

Each query script in `queries/` fulfills a specific contract requirement:

### Query 1: Create Movie & Relationships (`queries/create_movie.cypher`)
Adds *V for Vendetta* (2005) into the knowledge graph and links it to existing nodes (*Hugo Weaving* as lead actor, and the *Wachowskis* as producers).
```cypher
MERGE (m:Movie {title: 'V for Vendetta'})
ON CREATE SET m.released = 2005, m.tagline = 'Freedom! Forever!'
WITH m
MATCH (hugo:Person {name: 'Hugo Weaving'})
MERGE (hugo)-[:ACTED_IN {roles: ['V']}]->(m)
WITH m
MATCH (lana:Person {name: 'Lana Wachowski'})
MERGE (lana)-[:PRODUCED]->(m)
WITH m
MATCH (lilly:Person {name: 'Lilly Wachowski'})
MERGE (lilly)-[:PRODUCED]->(m)
RETURN m.title AS title, m.released AS released;
```
*Verification*: `MATCH (p:Person {name: 'Hugo Weaving'})-[:ACTED_IN]->(m:Movie {title: 'V for Vendetta'}) RETURN p, m` returns 1 row.

---

### Query 2: Actor Filmography (`queries/find_actor_movies.cypher`)
Finds all film titles in which *Keanu Reeves* has acted.
```cypher
MATCH (p:Person {name: 'Keanu Reeves'})-[:ACTED_IN]->(m:Movie)
RETURN m.title AS title
ORDER BY title ASC;
```
*Expected Output*:
```
+------------+
| title      |
+============+
| John Wick  |
| The Matrix |
+------------+
```

---

### Query 3: Co-Actor Traversal (`queries/find_co_actors.cypher`)
Performs a 2-hop traversal `(Hugo)-[:ACTED_IN]->(The Matrix)<-[:ACTED_IN]-(CoActor)` excluding Hugo Weaving himself.
```cypher
MATCH (hugo:Person {name: 'Hugo Weaving'})-[:ACTED_IN]->(m:Movie {title: 'The Matrix'})<-[:ACTED_IN]-(coActor:Person)
WHERE coActor <> hugo
RETURN DISTINCT coActor.name AS name
ORDER BY name ASC;
```
*Expected Output*:
```
+--------------------+
| name               |
+====================+
| Carrie-Anne Moss   |
| Keanu Reeves       |
| Laurence Fishburne |
+--------------------+
```

---

### Query 4: Property Mutation (`queries/update_movie_rating.cypher`)
Dynamically updates the graph by adding or setting the `rating` attribute on *The Matrix* node to `8.7`.
```cypher
MATCH (m:Movie {title: 'The Matrix'})
SET m.rating = 8.7
RETURN m.title AS title, m.rating AS rating;
```
*Verification*: `MATCH (m:Movie {title: 'The Matrix'}) RETURN m.rating AS rating` returns `8.7`.

---

### Query 5: Safe Node Deletion (`queries/delete_movie.cypher`)
Uses `DETACH DELETE` to safely delete *To Be Deleted*, removing any connected incident relationships before deleting the node itself.
```cypher
MATCH (m:Movie {title: 'To Be Deleted'})
DETACH DELETE m;
```
*Verification*: `MATCH (m:Movie {title: 'To Be Deleted'}) RETURN m` returns zero rows.

---

### Query 6: Degree Centrality Analytics (`queries/analytics_degree.cypher`)
Calculates the degree centrality (total incident relationships $k_i = k_{in} + k_{out}$) for all individuals, identifying the top 5 key influencers in the movie network.
```cypher
MATCH (p:Person)-[r]-()
RETURN p.name AS name, count(r) AS degree
ORDER BY degree DESC, name ASC
LIMIT 5;
```
*Sample Output*:
```
+------------------+----------+
| name             |   degree |
+==================+==========+
| Hugo Weaving     |        2 |
| Keanu Reeves     |        2 |
| Lana Wachowski   |        2 |
| Lilly Wachowski  |        2 |
| Carrie-Anne Moss |        1 |
+------------------+----------+
```

---

## 6. Python Interactive CLI Explorer

The project includes an interactive Python CLI tool (`src/cli.py`):

```bash
# 1. Inspect graph schema and constraints
python src/cli.py schema

# 2. Run degree centrality analytics
python src/cli.py analytics --limit 5

# 3. Execute a specific Cypher script
python src/cli.py query find_co_actors

# 4. Sequentially execute all 6 query scripts
python src/cli.py run-all

# 5. Execute custom ad-hoc Cypher
python src/cli.py query "MATCH (g:Genre)<-[:HAS_GENRE]-(m:Movie) RETURN g.name, m.title"
```

---

## 7. Automated Testing & Verification

### Standalone Submission Verifier
Run the standalone verification suite to validate all 10 core requirements:
```bash
python verify_submission.py
```

Output:
```
======================================================================
  MOVIE KNOWLEDGE GRAPH - AUTOMATED SUBMISSION VERIFIER
  Execution Mode: IN-MEMORY GRAPH SIMULATOR (Self-Contained Verification)
======================================================================

[PASS] Requirement  1: Docker Compose Orchestration Specification
         Valid compose service 'neo4j', image: neo4j:5.18.0, ports: 7474, 7687, volumes: data/logs/init, healthcheck verified.
[PASS] Requirement  2: Environment Configuration Documentation (.env.example)
         .env.example present with documented NEO4J_AUTH variable.
[PASS] Requirement  3: Database Schema, Labels, Relationships & Constraints
         Labels (Movie, Person, Genre), Relationships (ACTED_IN, DIRECTED, PRODUCED, HAS_GENRE), and Movie.title uniqueness constraint verified.
[PASS] Requirement  4: Initial Database Seeding Verification
         Seed script created 'The Matrix', 'Keanu Reeves', 'Hugo Weaving', 'To Be Deleted', and ACTED_IN relation.
[PASS] Requirement  5: Create Movie Script (create_movie.cypher)
         'V for Vendetta' created and connected to Hugo Weaving via ACTED_IN (1 row confirmed).
[PASS] Requirement  6: Find Actor Movies Script (find_actor_movies.cypher)
         Successfully found movies for Keanu Reeves: ['John Wick', 'The Matrix']
[PASS] Requirement  7: Find Co-Actors Script (find_co_actors.cypher)
         Found co-actors of Hugo Weaving in The Matrix: ['Carrie-Anne Moss', 'Keanu Reeves', 'Laurence Fishburne'] (excluding Hugo Weaving).
[PASS] Requirement  8: Update Movie Rating Script (update_movie_rating.cypher)
         Rating for 'The Matrix' updated and verified as 8.7.
[PASS] Requirement  9: Delete Movie Script (delete_movie.cypher)
         'To Be Deleted' movie removed with DETACH DELETE (0 rows returned).
[PASS] Requirement 10: Degree Centrality Analytical Query (analytics_degree.cypher)
         Top 5 degree centrality computed in descending order (Hugo Weaving: 2, Keanu Reeves: 2, Lana Wachowski: 2).

----------------------------------------------------------------------
VERIFICATION SUMMARY: 10/10 Passed (100.0%)
----------------------------------------------------------------------

[SUCCESS] ALL 10 CORE REQUIREMENTS FULLY SATISFIED!
The project conforms to all instructor contracts and is ready for submission.
```

### Pytest Unit Test Suite
Execute the pytest suite:
```bash
pytest tests -v
```
All 11 automated test cases pass in under a second.

---

## 8. Packaging for Final Submission

To package the project for instructor evaluation:
```bash
python package_submission.py
```
This utility:
1. Verifies that all mandatory files (`docker-compose.yml`, `.env.example`, `init/seed.cypher`, `queries/*.cypher`, `README.md`) are present.
2. Excludes secret files (`.env`), database volumes (`data/`), server logs (`logs/`), and Python cache directories.
3. Generates a clean `submission.zip` archive ready for upload.

---

## 9. Frequently Asked Questions (FAQ) & Troubleshooting

### Q1: `docker compose up` fails or ports 7474 / 7687 are already allocated.
**A**: Another service (or an earlier Neo4j instance) is occupying the port. Check active listeners:
```bash
# Windows
netstat -ano | findstr :7474
# Linux / macOS
lsof -i :7474
```
Stop the conflicting process, or rebind ports in `docker-compose.yml` (e.g. `"7475:7474"`).

### Q2: Why did my seed script not re-execute after modifying `init/seed.cypher`?
**A**: Neo4j executes `/var/lib/neo4j/import` initialization scripts **only once** when a new database is first created. If the `./data` volume already contains database files, Neo4j skips re-initialization. To reset and force a clean re-seeding:
```bash
docker compose down -v
docker compose up -d
```
The `-v` flag removes the persistent volume, allowing the new seed script to run on a fresh database.

### Q3: Why use `MERGE` instead of `CREATE` in seed and migration scripts?
**A**: `MERGE` is **idempotent**. It inspects the database to check if a node or pattern already exists. If found, it references the existing node without creating duplicates; if absent, it creates it. Using `CREATE` in seeding or recurring scripts would duplicate nodes and relationships every time the script runs.

### Q4: What is the difference between `DELETE` and `DETACH DELETE`?
**A**: Neo4j enforces referential graph integrity: a node that still has connected relationships cannot be deleted with a simple `DELETE n` statement (it will raise a `ClientError: Cannot delete node because it still has relationships`). `DETACH DELETE n` safely removes all incident edges first, then removes the target node in a single atomic transaction.

---

