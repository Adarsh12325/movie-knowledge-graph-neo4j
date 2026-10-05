"""
Service layer for Movie Knowledge Graph operations.
Provides high-level graph queries, schema inspection, degree centrality calculation,
and execution of project Cypher scripts with support for both live Neo4j and offline mock engine.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import settings
from src.connection import connection_manager
from src.mock_engine import InMemoryGraphEngine

logger = logging.getLogger(__name__)


class MovieKnowledgeGraphService:
    """
    High-level business service encapsulating Graph operations and Cypher script execution.
    Automatically handles live Bolt sessions or falls back to the in-memory engine.
    """
    def __init__(self, force_mock: bool = False):
        self.force_mock = force_mock
        self._mock_engine: Optional[InMemoryGraphEngine] = None

        if self.force_mock or not connection_manager.verify_connectivity():
            self._init_mock_engine()

    def _init_mock_engine(self) -> None:
        if self._mock_engine is None:
            self._mock_engine = InMemoryGraphEngine()
            self._mock_engine.execute_seed()

    @property
    def is_live(self) -> bool:
        """Returns True if connected to a live Neo4j database."""
        if self.force_mock:
            return False
        return connection_manager.verify_connectivity()

    def execute_cypher(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute arbitrary Cypher query and return list of result dictionaries."""
        if not self.is_live:
            self._init_mock_engine()
            query_str = cypher
            if parameters:
                for k, v in parameters.items():
                    if isinstance(v, str):
                        query_str = query_str.replace(f"${k}", f"'{v}'")
                    else:
                        query_str = query_str.replace(f"${k}", str(v))
            return self._mock_engine.run_cypher_statement(query_str)

        with connection_manager.get_session() as session:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]

    def execute_cypher_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read and execute a .cypher script file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Cypher file not found at: {file_path}")

        cypher_content = file_path.read_text(encoding="utf-8")
        
        if not self.is_live:
            self._init_mock_engine()
            return self._mock_engine.run_cypher_statement(cypher_content)

        # For live Neo4j, split multi-statement scripts by semicolon
        statements = [
            stmt.strip() for stmt in cypher_content.split(";")
            if stmt.strip() and not stmt.strip().startswith("//")
        ]
        
        results = []
        with connection_manager.get_session() as session:
            for stmt in statements:
                res = session.run(stmt)
                records = [record.data() for record in res]
                if records:
                    results.extend(records)
        return results

    def seed_database(self) -> None:
        """Execute the seed script against the database."""
        seed_path = settings.seed_file
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found at: {seed_path}")

        if not self.is_live:
            self._init_mock_engine()
            self._mock_engine.clear()
            self._mock_engine.execute_seed()
            return

        self.execute_cypher_file(seed_path)

    def get_constraints(self) -> List[Dict[str, Any]]:
        """Retrieve registered database constraints."""
        if not self.is_live:
            self._init_mock_engine()
            return self._mock_engine.get_constraints()

        cypher = "SHOW CONSTRAINTS"
        return self.execute_cypher(cypher)

    def get_schema_summary(self) -> Dict[str, Any]:
        """Inspect active node labels and relationship types."""
        if not self.is_live:
            self._init_mock_engine()
            labels = {list(n.labels)[0] for n in self._mock_engine.nodes.values() if n.labels}
            rel_types = {r.type for r in self._mock_engine.relationships.values()}
            return {
                "labels": sorted(labels),
                "relationship_types": sorted(rel_types),
                "total_nodes": len(self._mock_engine.nodes),
                "total_relationships": len(self._mock_engine.relationships)
            }

        with connection_manager.get_session() as session:
            labels_res = session.run("CALL db.labels()")
            labels = [r["label"] for r in labels_res]

            rels_res = session.run("CALL db.relationshipTypes()")
            rels = [r["relationshipType"] for r in rels_res]

            node_cnt_res = session.run("MATCH (n) RETURN count(n) AS count")
            total_nodes = node_cnt_res.single()["count"]

            rel_cnt_res = session.run("MATCH ()-[r]->() RETURN count(r) AS count")
            total_rels = rel_cnt_res.single()["count"]

            return {
                "labels": sorted(labels),
                "relationship_types": sorted(rels),
                "total_nodes": total_nodes,
                "total_relationships": total_rels
            }

    def find_actor_movies(self, actor_name: str = "Keanu Reeves") -> List[str]:
        """Find movie titles acted in by a specific actor."""
        cypher = """
        MATCH (p:Person {name: $actor_name})-[:ACTED_IN]->(m:Movie)
        RETURN m.title AS title
        ORDER BY title ASC;
        """
        results = self.execute_cypher(cypher, {"actor_name": actor_name})
        return [r["title"] for r in results]

    def find_co_actors(self, actor_name: str = "Hugo Weaving", movie_title: str = "The Matrix") -> List[str]:
        """Find co-actors who appeared in a movie with a given actor."""
        cypher = """
        MATCH (a:Person {name: $actor_name})-[:ACTED_IN]->(m:Movie {title: $movie_title})<-[:ACTED_IN]-(coActor:Person)
        WHERE coActor <> a
        RETURN DISTINCT coActor.name AS name
        ORDER BY name ASC;
        """
        results = self.execute_cypher(cypher, {"actor_name": actor_name, "movie_title": movie_title})
        return [r["name"] for r in results]

    def update_movie_rating(self, movie_title: str, rating: float) -> Dict[str, Any]:
        """Update or set the rating property of a movie."""
        cypher = """
        MATCH (m:Movie {title: $movie_title})
        SET m.rating = $rating
        RETURN m.title AS title, m.rating AS rating;
        """
        res = self.execute_cypher(cypher, {"movie_title": movie_title, "rating": rating})
        return res[0] if res else {}

    def delete_movie(self, movie_title: str) -> None:
        """Safely detach and delete a movie node and all associated relationships."""
        cypher = """
        MATCH (m:Movie {title: $movie_title})
        DETACH DELETE m;
        """
        self.execute_cypher(cypher, {"movie_title": movie_title})

    def get_degree_centrality(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Calculate degree centrality: most connected people in the graph."""
        cypher = """
        MATCH (p:Person)-[r]-()
        RETURN p.name AS name, count(r) AS degree
        ORDER BY degree DESC, name ASC
        LIMIT $limit;
        """
        return self.execute_cypher(cypher, {"limit": limit})
