"""
Comprehensive Automated Verification Suite for Movie Knowledge Graph Submission.
Validates all 10 Core Requirements and Contract Specifications defined in the prompt.
Can be run directly from terminal: python verify_submission.py
"""

import sys
import os
import re
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from src.mock_engine import InMemoryGraphEngine
from src.connection import connection_manager


class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_pass(req_num: int, title: str, details: str = ""):
    msg = f"[{Color.GREEN}PASS{Color.RESET}] Requirement {req_num:2d}: {title}"
    if details:
        msg += f"\n         {Color.CYAN}{details}{Color.RESET}"
    print(msg)


def print_fail(req_num: int, title: str, reason: str):
    print(f"[{Color.RED}FAIL{Color.RESET}] Requirement {req_num:2d}: {title}\n         -> Reason: {reason}")


class SubmissionVerifier:
    def __init__(self):
        self.passed_count = 0
        self.failed_count = 0
        self.engine = InMemoryGraphEngine()
        self.use_live = connection_manager.verify_connectivity()

    def run_query(self, cypher: str) -> List[Dict[str, Any]]:
        """Run Cypher query against live Neo4j if available, else mock engine."""
        if self.use_live:
            with connection_manager.get_session() as session:
                res = session.run(cypher)
                return [r.data() for r in res]
        return self.engine.run_cypher_statement(cypher)

    def execute_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Execute a .cypher file against live Neo4j or mock engine."""
        content = file_path.read_text(encoding="utf-8")
        if self.use_live:
            statements = [s.strip() for s in content.split(";") if s.strip() and not s.strip().startswith("//")]
            results = []
            with connection_manager.get_session() as session:
                for s in statements:
                    res = session.run(s)
                    records = [r.data() for r in res]
                    if records:
                        results.extend(records)
            return results
        return self.engine.run_cypher_statement(content)

    # -------------------------------------------------------------
    # Requirement 1: docker-compose.yml Specification
    # -------------------------------------------------------------
    def verify_req_1(self) -> bool:
        req_num = 1
        title = "Docker Compose Orchestration Specification"
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        if not compose_file.exists():
            print_fail(req_num, title, "docker-compose.yml not found at project root.")
            return False

        try:
            with open(compose_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            services = data.get("services", {})
            if "neo4j" not in services:
                print_fail(req_num, title, "Missing 'neo4j' service definition.")
                return False

            neo4j_svc = services["neo4j"]
            image = neo4j_svc.get("image", "")
            if not image.startswith("neo4j"):
                print_fail(req_num, title, f"Invalid image '{image}'. Must be a neo4j image (e.g., neo4j:5.18.0).")
                return False

            # Check ports
            ports = [str(p) for p in neo4j_svc.get("ports", [])]
            has_7474 = any("7474" in p for p in ports)
            has_7687 = any("7687" in p for p in ports)
            if not (has_7474 and has_7687):
                print_fail(req_num, title, f"Must expose ports 7474 and 7687. Found ports: {ports}")
                return False

            # Check environment
            env_vars = neo4j_svc.get("environment", [])
            env_str = " ".join(str(e) for e in env_vars)
            if "NEO4J_AUTH" not in env_str:
                print_fail(req_num, title, "Must load NEO4J_AUTH in environment.")
                return False

            # Check volumes
            vols = [str(v) for v in neo4j_svc.get("volumes", [])]
            has_data = any("./data:/data" in v for v in vols)
            has_logs = any("./logs:/logs" in v for v in vols)
            has_init = any("./init:/var/lib/neo4j/import" in v for v in vols)
            if not (has_data and has_logs and has_init):
                print_fail(req_num, title, f"Missing required volume mounts. Found: {vols}")
                return False

            # Check healthcheck
            health = neo4j_svc.get("healthcheck", {})
            if not health or "test" not in health:
                print_fail(req_num, title, "Healthcheck test is missing.")
                return False

            print_pass(req_num, title, f"Valid compose service 'neo4j', image: {image}, ports: 7474, 7687, volumes: data/logs/init, healthcheck verified.")
            return True
        except Exception as e:
            print_fail(req_num, title, f"Error parsing docker-compose.yml: {e}")
            return False

    # -------------------------------------------------------------
    # Requirement 2: .env.example Specification
    # -------------------------------------------------------------
    def verify_req_2(self) -> bool:
        req_num = 2
        title = "Environment Configuration Documentation (.env.example)"
        env_example = PROJECT_ROOT / ".env.example"
        if not env_example.exists():
            print_fail(req_num, title, ".env.example not found at project root.")
            return False

        content = env_example.read_text(encoding="utf-8")
        if "NEO4J_AUTH=" not in content:
            print_fail(req_num, title, "NEO4J_AUTH key is missing from .env.example.")
            return False

        print_pass(req_num, title, ".env.example present with documented NEO4J_AUTH variable.")
        return True

    # -------------------------------------------------------------
    # Requirement 3: Database Schema & Uniqueness Constraints
    # -------------------------------------------------------------
    def verify_req_3(self) -> bool:
        req_num = 3
        title = "Database Schema, Labels, Relationships & Constraints"
        seed_path = PROJECT_ROOT / "init" / "seed.cypher"
        if not seed_path.exists():
            print_fail(req_num, title, "init/seed.cypher not found.")
            return False

        # Load seed data into mock engine or verify live
        if not self.use_live:
            self.engine.execute_seed()
        else:
            self.execute_file(seed_path)

        constraints = self.run_query("SHOW CONSTRAINTS")
        has_movie_title_unique = False
        for c in constraints:
            labels = c.get("labelsOrTypes", [c.get("label")])
            props = c.get("properties", [c.get("property")])
            c_type = c.get("type", "")
            if "Movie" in labels and "title" in props and ("UNIQUE" in c_type or c_type == "UNIQUENESS"):
                has_movie_title_unique = True
                break

        if not has_movie_title_unique:
            print_fail(req_num, title, "Uniqueness constraint on (:Movie).title not found.")
            return False

        schema_res = self.run_query("CALL db.schema.visualization()")
        if schema_res:
            row = schema_res[0]
            nodes = set(row.get("nodes", []))
            rels = set(row.get("relationships", []))
            required_nodes = {"Movie", "Person", "Genre"}
            required_rels = {"ACTED_IN", "DIRECTED", "PRODUCED", "HAS_GENRE"}

            if not required_nodes.issubset(nodes):
                print_fail(req_num, title, f"Missing required node labels. Expected {required_nodes}, found {nodes}")
                return False
            if not required_rels.issubset(rels):
                print_fail(req_num, title, f"Missing required relationship types. Expected {required_rels}, found {rels}")
                return False

        print_pass(req_num, title, "Labels (Movie, Person, Genre), Relationships (ACTED_IN, DIRECTED, PRODUCED, HAS_GENRE), and Movie.title uniqueness constraint verified.")
        return True

    # -------------------------------------------------------------
    # Requirement 4: Automated Database Seeding
    # -------------------------------------------------------------
    def verify_req_4(self) -> bool:
        req_num = 4
        title = "Initial Database Seeding Verification"
        cypher = "MATCH (p:Person {name: 'Keanu Reeves'})-[:ACTED_IN]->(m:Movie {title: 'The Matrix'}) RETURN p, m"
        results = self.run_query(cypher)
        if len(results) != 1:
            print_fail(req_num, title, f"Expected exactly 1 row for Keanu Reeves ACTED_IN The Matrix, got {len(results)}")
            return False

        # Verify Hugo Weaving and 'To Be Deleted'
        hugo_res = self.run_query("MATCH (p:Person {name: 'Hugo Weaving'}) RETURN p")
        del_movie_res = self.run_query("MATCH (m:Movie {title: 'To Be Deleted'}) RETURN m")
        if not hugo_res or not del_movie_res:
            print_fail(req_num, title, "Required seed nodes 'Hugo Weaving' or 'To Be Deleted' not found.")
            return False

        print_pass(req_num, title, "Seed script created 'The Matrix', 'Keanu Reeves', 'Hugo Weaving', 'To Be Deleted', and ACTED_IN relation.")
        return True

    # -------------------------------------------------------------
    # Requirement 5: create_movie.cypher
    # -------------------------------------------------------------
    def verify_req_5(self) -> bool:
        req_num = 5
        title = "Create Movie Script (create_movie.cypher)"
        script_path = PROJECT_ROOT / "queries" / "create_movie.cypher"
        if not script_path.exists():
            print_fail(req_num, title, "queries/create_movie.cypher not found.")
            return False

        self.execute_file(script_path)
        verif_cypher = "MATCH (p:Person {name: 'Hugo Weaving'})-[:ACTED_IN]->(m:Movie {title: 'V for Vendetta'}) RETURN p, m"
        rows = self.run_query(verif_cypher)
        if len(rows) != 1:
            print_fail(req_num, title, f"Verification query returned {len(rows)} rows, expected 1.")
            return False

        print_pass(req_num, title, "'V for Vendetta' created and connected to Hugo Weaving via ACTED_IN (1 row confirmed).")
        return True

    # -------------------------------------------------------------
    # Requirement 6: find_actor_movies.cypher
    # -------------------------------------------------------------
    def verify_req_6(self) -> bool:
        req_num = 6
        title = "Find Actor Movies Script (find_actor_movies.cypher)"
        script_path = PROJECT_ROOT / "queries" / "find_actor_movies.cypher"
        if not script_path.exists():
            print_fail(req_num, title, "queries/find_actor_movies.cypher not found.")
            return False

        rows = self.execute_file(script_path)
        titles = [r.get("title", r.get("m.title")) for r in rows if "title" in r or "m.title" in r]
        if "The Matrix" not in titles or "John Wick" not in titles:
            print_fail(req_num, title, f"Expected 'The Matrix' and 'John Wick' in titles. Got: {titles}")
            return False

        print_pass(req_num, title, f"Successfully found movies for Keanu Reeves: {titles}")
        return True

    # -------------------------------------------------------------
    # Requirement 7: find_co_actors.cypher
    # -------------------------------------------------------------
    def verify_req_7(self) -> bool:
        req_num = 7
        title = "Find Co-Actors Script (find_co_actors.cypher)"
        script_path = PROJECT_ROOT / "queries" / "find_co_actors.cypher"
        if not script_path.exists():
            print_fail(req_num, title, "queries/find_co_actors.cypher not found.")
            return False

        rows = self.execute_file(script_path)
        names = [r.get("name", r.get("coActor.name")) for r in rows if "name" in r or "coActor.name" in r]
        expected = {"Keanu Reeves", "Carrie-Anne Moss", "Laurence Fishburne"}

        if not expected.issubset(set(names)):
            print_fail(req_num, title, f"Expected co-actors {expected}, got {names}")
            return False
        if "Hugo Weaving" in names:
            print_fail(req_num, title, "Hugo Weaving must NOT be included in the co-actor results.")
            return False

        print_pass(req_num, title, f"Found co-actors of Hugo Weaving in The Matrix: {names} (excluding Hugo Weaving).")
        return True

    # -------------------------------------------------------------
    # Requirement 8: update_movie_rating.cypher
    # -------------------------------------------------------------
    def verify_req_8(self) -> bool:
        req_num = 8
        title = "Update Movie Rating Script (update_movie_rating.cypher)"
        script_path = PROJECT_ROOT / "queries" / "update_movie_rating.cypher"
        if not script_path.exists():
            print_fail(req_num, title, "queries/update_movie_rating.cypher not found.")
            return False

        self.execute_file(script_path)
        verif_cypher = "MATCH (m:Movie {title: 'The Matrix'}) RETURN m.rating AS rating"
        rows = self.run_query(verif_cypher)
        if not rows:
            print_fail(req_num, title, "No rows returned for rating check.")
            return False

        rating = rows[0].get("rating")
        if rating != 8.7:
            print_fail(req_num, title, f"Expected rating 8.7, got {rating}")
            return False

        print_pass(req_num, title, "Rating for 'The Matrix' updated and verified as 8.7.")
        return True

    # -------------------------------------------------------------
    # Requirement 9: delete_movie.cypher
    # -------------------------------------------------------------
    def verify_req_9(self) -> bool:
        req_num = 9
        title = "Delete Movie Script (delete_movie.cypher)"
        script_path = PROJECT_ROOT / "queries" / "delete_movie.cypher"
        if not script_path.exists():
            print_fail(req_num, title, "queries/delete_movie.cypher not found.")
            return False

        # Check script uses DETACH DELETE
        content = script_path.read_text(encoding="utf-8").upper()
        if "DETACH DELETE" not in content:
            print_fail(req_num, title, "Script must use 'DETACH DELETE'.")
            return False

        self.execute_file(script_path)
        verif_cypher = "MATCH (m:Movie {title: 'To Be Deleted'}) RETURN m"
        rows = self.run_query(verif_cypher)
        if len(rows) != 0:
            print_fail(req_num, title, f"Expected 0 rows after delete, got {len(rows)}")
            return False

        print_pass(req_num, title, "'To Be Deleted' movie removed with DETACH DELETE (0 rows returned).")
        return True

    # -------------------------------------------------------------
    # Requirement 10: analytics_degree.cypher
    # -------------------------------------------------------------
    def verify_req_10(self) -> bool:
        req_num = 10
        title = "Degree Centrality Analytical Query (analytics_degree.cypher)"
        script_path = PROJECT_ROOT / "queries" / "analytics_degree.cypher"
        if not script_path.exists():
            print_fail(req_num, title, "queries/analytics_degree.cypher not found.")
            return False

        rows = self.execute_file(script_path)
        if not rows:
            print_fail(req_num, title, "No rows returned by analytics query.")
            return False
        if len(rows) > 5:
            print_fail(req_num, title, f"Expected at most 5 rows (LIMIT 5), got {len(rows)}")
            return False

        # Verify two columns present (name and degree)
        for r in rows:
            if "name" not in r or "degree" not in r:
                print_fail(req_num, title, f"Result row missing required columns ('name', 'degree'): {r}")
                return False

        # Verify descending order
        degrees = [r["degree"] for r in rows]
        if degrees != sorted(degrees, reverse=True):
            print_fail(req_num, title, f"Results not ordered by degree descending: {degrees}")
            return False

        sample_summary = ", ".join(f"{r['name']}: {r['degree']}" for r in rows[:3])
        print_pass(req_num, title, f"Top {len(rows)} degree centrality computed in descending order ({sample_summary}).")
        return True

    def run_all(self) -> bool:
        print("\n" + "=" * 70)
        mode = "LIVE NEO4J DATABASE (Bolt)" if self.use_live else "IN-MEMORY GRAPH SIMULATOR (Self-Contained Verification)"
        print(f"  MOVIE KNOWLEDGE GRAPH - AUTOMATED SUBMISSION VERIFIER")
        print(f"  Execution Mode: {mode}")
        print("=" * 70 + "\n")

        tests = [
            self.verify_req_1,
            self.verify_req_2,
            self.verify_req_3,
            self.verify_req_4,
            self.verify_req_5,
            self.verify_req_6,
            self.verify_req_7,
            self.verify_req_8,
            self.verify_req_9,
            self.verify_req_10,
        ]

        for test_fn in tests:
            if test_fn():
                self.passed_count += 1
            else:
                self.failed_count += 1

        print("\n" + "-" * 70)
        total = self.passed_count + self.failed_count
        score_pct = (self.passed_count / total) * 100 if total > 0 else 0
        print(f"VERIFICATION SUMMARY: {self.passed_count}/{total} Passed ({score_pct:.1f}%)")
        print("-" * 70)

        if self.failed_count == 0:
            print(f"\n{Color.GREEN}{Color.BOLD}[SUCCESS] ALL 10 CORE REQUIREMENTS FULLY SATISFIED!{Color.RESET}")
            print(f"The project conforms to all instructor contracts and is ready for submission.\n")
            return True
        else:
            print(f"\n{Color.RED}{Color.BOLD}[FAILURE] {self.failed_count} REQUIREMENTS FAILED.{Color.RESET}\n")
            return False


if __name__ == "__main__":
    verifier = SubmissionVerifier()
    success = verifier.run_all()
    sys.exit(0 if success else 1)
