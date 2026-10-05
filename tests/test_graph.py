"""
Comprehensive Pytest Test Suite for Movie Knowledge Graph.
Validates all requirements, schema constraints, seeding, Cypher queries,
and Python service methods.
"""

import sys
from pathlib import Path
import pytest
import yaml

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings
from src.mock_engine import InMemoryGraphEngine
from src.graph_service import MovieKnowledgeGraphService


@pytest.fixture
def engine():
    """Provides a freshly seeded in-memory graph engine for isolated testing."""
    eng = InMemoryGraphEngine()
    eng.execute_seed()
    return eng


@pytest.fixture
def service():
    """Provides an offline-mode service instance."""
    return MovieKnowledgeGraphService(force_mock=True)


class TestDockerAndConfigurationContract:
    """Validates Core Requirements 1 & 2: docker-compose and environment templates."""

    def test_docker_compose_structure(self):
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        assert compose_path.exists(), "docker-compose.yml must exist at project root"

        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "services" in data
        assert "neo4j" in data["services"]
        neo4j_svc = data["services"]["neo4j"]

        # Check image
        assert neo4j_svc["image"] == "neo4j:5.18.0"

        # Check ports
        ports = [str(p) for p in neo4j_svc["ports"]]
        assert any("7474" in p for p in ports)
        assert any("7687" in p for p in ports)

        # Check volumes
        vols = [str(v) for v in neo4j_svc["volumes"]]
        assert any("./data:/data" in v for v in vols)
        assert any("./logs:/logs" in v for v in vols)
        assert any("./init:/var/lib/neo4j/import" in v for v in vols)

        # Check healthcheck
        assert "healthcheck" in neo4j_svc
        assert "test" in neo4j_svc["healthcheck"]

    def test_env_example_contract(self):
        env_example = PROJECT_ROOT / ".env.example"
        assert env_example.exists(), ".env.example must exist at project root"
        content = env_example.read_text(encoding="utf-8")
        assert "NEO4J_AUTH=" in content, "NEO4J_AUTH variable must be documented"


class TestSchemaAndSeedingContract:
    """Validates Core Requirements 3 & 4: Schema constraints, node labels, and seeding."""

    def test_constraints_and_schema(self, engine):
        constraints = engine.get_constraints()
        constraint_labels = {c["label"] for c in constraints}
        constraint_props = {c["property"] for c in constraints}

        assert "Movie" in constraint_labels
        assert "title" in constraint_props

        # Check schema labels & relationships
        labels = {list(n.labels)[0] for n in engine.nodes.values() if n.labels}
        rel_types = {r.type for r in engine.relationships.values()}

        assert {"Movie", "Person", "Genre"}.issubset(labels)
        assert {"ACTED_IN", "DIRECTED", "PRODUCED", "HAS_GENRE"}.issubset(rel_types)

    def test_initial_seed_data(self, engine):
        # Movie node: The Matrix
        matrix = engine.find_node("Movie", {"title": "The Matrix"})
        assert matrix is not None
        assert matrix.properties.get("released") == 1999

        # Person nodes
        keanu = engine.find_node("Person", {"name": "Keanu Reeves"})
        hugo = engine.find_node("Person", {"name": "Hugo Weaving"})
        assert keanu is not None
        assert hugo is not None

        # ACTED_IN relation
        res = engine.run_cypher_statement(
            "MATCH (p:Person {name: 'Keanu Reeves'})-[:ACTED_IN]->(m:Movie {title: 'The Matrix'}) RETURN p, m"
        )
        assert len(res) == 1

        # Placeholder movie for deletion
        to_del = engine.find_node("Movie", {"title": "To Be Deleted"})
        assert to_del is not None


class TestCoreCypherQueries:
    """Validates Core Requirements 5 to 10: Individual query script behavior."""

    def test_req_5_create_movie(self, engine):
        create_file = PROJECT_ROOT / "queries" / "create_movie.cypher"
        assert create_file.exists()
        cypher = create_file.read_text(encoding="utf-8")
        engine.run_cypher_statement(cypher)

        # Verification query
        verif = engine.run_cypher_statement(
            "MATCH (p:Person {name: 'Hugo Weaving'})-[:ACTED_IN]->(m:Movie {title: 'V for Vendetta'}) RETURN p, m"
        )
        assert len(verif) == 1

    def test_req_6_find_actor_movies(self, engine):
        query_file = PROJECT_ROOT / "queries" / "find_actor_movies.cypher"
        assert query_file.exists()
        cypher = query_file.read_text(encoding="utf-8")
        rows = engine.run_cypher_statement(cypher)
        titles = [r["title"] for r in rows]

        assert "The Matrix" in titles
        assert "John Wick" in titles

    def test_req_7_find_co_actors(self, engine):
        query_file = PROJECT_ROOT / "queries" / "find_co_actors.cypher"
        assert query_file.exists()
        cypher = query_file.read_text(encoding="utf-8")
        rows = engine.run_cypher_statement(cypher)
        names = [r["name"] for r in rows]

        expected = {"Keanu Reeves", "Carrie-Anne Moss", "Laurence Fishburne"}
        assert expected.issubset(set(names))
        assert "Hugo Weaving" not in names

    def test_req_8_update_movie_rating(self, engine):
        query_file = PROJECT_ROOT / "queries" / "update_movie_rating.cypher"
        assert query_file.exists()
        cypher = query_file.read_text(encoding="utf-8")
        engine.run_cypher_statement(cypher)

        verif = engine.run_cypher_statement(
            "MATCH (m:Movie {title: 'The Matrix'}) RETURN m.rating AS rating"
        )
        assert len(verif) == 1
        assert verif[0]["rating"] == 8.7

    def test_req_9_delete_movie(self, engine):
        query_file = PROJECT_ROOT / "queries" / "delete_movie.cypher"
        assert query_file.exists()
        cypher = query_file.read_text(encoding="utf-8")
        assert "DETACH DELETE" in cypher.upper()

        engine.run_cypher_statement(cypher)

        verif = engine.run_cypher_statement("MATCH (m:Movie {title: 'To Be Deleted'}) RETURN m")
        assert len(verif) == 0

    def test_req_10_analytics_degree(self, engine):
        query_file = PROJECT_ROOT / "queries" / "analytics_degree.cypher"
        assert query_file.exists()
        cypher = query_file.read_text(encoding="utf-8")
        rows = engine.run_cypher_statement(cypher)

        assert len(rows) <= 5
        assert all("name" in r and "degree" in r for r in rows)

        degrees = [r["degree"] for r in rows]
        assert degrees == sorted(degrees, reverse=True)


class TestServiceLayer:
    """Validates Python MovieKnowledgeGraphService high-level API."""

    def test_service_queries(self, service):
        # Filmography query
        movies = service.find_actor_movies("Keanu Reeves")
        assert "The Matrix" in movies
        assert "John Wick" in movies

        # Co-actors query
        co_actors = service.find_co_actors("Hugo Weaving", "The Matrix")
        assert "Keanu Reeves" in co_actors
        assert "Hugo Weaving" not in co_actors

        # Update rating
        res = service.update_movie_rating("The Matrix", 8.7)
        assert res.get("rating") == 8.7

        # Degree centrality
        centrality = service.get_degree_centrality(limit=3)
        assert len(centrality) == 3
