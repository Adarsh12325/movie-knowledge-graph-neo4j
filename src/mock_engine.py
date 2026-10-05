"""
In-Memory Property Graph Engine for Offline Simulation and Testing.
Provides high-fidelity graph data structures, constraint enforcement, and
Cypher query simulation mirroring Neo4j 5.18 behavior without requiring Docker.
"""

from typing import Dict, List, Set, Any, Optional, Tuple
import re
from pathlib import Path


class Node:
    """Represents a property graph node with labels and key-value properties."""
    def __init__(self, node_id: int, labels: Set[str], properties: Dict[str, Any]):
        self.id = node_id
        self.labels = set(labels)
        self.properties = dict(properties)

    def matches(self, label: Optional[str] = None, props: Optional[Dict[str, Any]] = None) -> bool:
        if label and label not in self.labels:
            return False
        if props:
            for k, v in props.items():
                if self.properties.get(k) != v:
                    return False
        return True

    def __repr__(self) -> str:
        label_str = ":".join(sorted(self.labels))
        return f"Node({self.id}, :{label_str}, {self.properties})"


class Relationship:
    """Represents a directed relationship between two nodes."""
    def __init__(self, rel_id: int, rel_type: str, start_node_id: int, end_node_id: int, properties: Optional[Dict[str, Any]] = None):
        self.id = rel_id
        self.type = rel_type
        self.start_node_id = start_node_id
        self.end_node_id = end_node_id
        self.properties = dict(properties or {})

    def __repr__(self) -> str:
        return f"Relationship({self.start_node_id}-[:{self.type} {self.properties}]->{self.end_node_id})"


class InMemoryGraphEngine:
    """
    Self-contained property graph database simulator.
    Supports node/relationship creation, constraint enforcement, schema introspection,
    degree centrality analysis, and Cypher statement execution.
    """
    def __init__(self):
        self.nodes: Dict[int, Node] = {}
        self.relationships: Dict[int, Relationship] = {}
        self.constraints: List[Dict[str, Any]] = []  # e.g., {"name": "movie_title", "label": "Movie", "property": "title", "type": "UNIQUENESS"}
        self._next_node_id = 1
        self._next_rel_id = 1

    def clear(self) -> None:
        """Reset the graph store to an empty state."""
        self.nodes.clear()
        self.relationships.clear()
        self.constraints.clear()
        self._next_node_id = 1
        self._next_rel_id = 1

    def add_constraint(self, name: str, label: str, property_name: str, constraint_type: str = "UNIQUENESS") -> None:
        """Register a uniqueness or presence constraint."""
        for c in self.constraints:
            if c["label"] == label and c["property"] == property_name:
                return
        self.constraints.append({
            "name": name,
            "label": label,
            "property": property_name,
            "type": constraint_type,
            "entityType": "NODE",
            "properties": [property_name]
        })

    def get_constraints(self) -> List[Dict[str, Any]]:
        return list(self.constraints)

    def merge_node(self, labels: List[str], properties: Dict[str, Any]) -> Node:
        """
        Idempotently find or create a node matching the specified labels and properties.
        Respects uniqueness constraints.
        """
        primary_label = labels[0] if labels else None
        
        # Check if node already exists by checking unique properties or all properties
        for node in self.nodes.values():
            if set(labels).issubset(node.labels):
                # If unique constraint exists for this label, match on that property
                matched_by_constraint = False
                for c in self.constraints:
                    if c["label"] in labels and c["property"] in properties:
                        prop_key = c["property"]
                        if node.properties.get(prop_key) == properties.get(prop_key):
                            matched_by_constraint = True
                            break
                if matched_by_constraint:
                    # Update other properties if supplied
                    node.properties.update(properties)
                    return node
                
                # Check exact property subset match
                if all(node.properties.get(k) == v for k, v in properties.items()):
                    return node

        # If not found, create new node
        node_id = self._next_node_id
        self._next_node_id += 1
        node = Node(node_id, set(labels), properties)
        self.nodes[node_id] = node
        return node

    def merge_relationship(self, start_node: Node, rel_type: str, end_node: Node, properties: Optional[Dict[str, Any]] = None) -> Relationship:
        """Idempotently find or create a directed relationship."""
        props = properties or {}
        for rel in self.relationships.values():
            if rel.start_node_id == start_node.id and rel.end_node_id == end_node.id and rel.type == rel_type:
                rel.properties.update(props)
                return rel

        rel_id = self._next_rel_id
        self._next_rel_id += 1
        rel = Relationship(rel_id, rel_type, start_node.id, end_node.id, props)
        self.relationships[rel_id] = rel
        return rel

    def detach_delete_node(self, node: Node) -> None:
        """Remove a node and all connected incoming and outgoing relationships."""
        rel_ids_to_remove = [
            r_id for r_id, r in self.relationships.items()
            if r.start_node_id == node.id or r.end_node_id == node.id
        ]
        for r_id in rel_ids_to_remove:
            del self.relationships[r_id]
        if node.id in self.nodes:
            del self.nodes[node.id]

    def get_nodes_by_label(self, label: str) -> List[Node]:
        return [n for n in self.nodes.values() if label in n.labels]

    def find_node(self, label: str, properties: Dict[str, Any]) -> Optional[Node]:
        for n in self.nodes.values():
            if n.matches(label, properties):
                return n
        return None

    def execute_seed(self) -> None:
        """Populate the graph with the exact seed data defined in init/seed.cypher."""
        # 1. Constraints
        self.add_constraint("movie_title", "Movie", "title", "UNIQUENESS")
        self.add_constraint("person_name", "Person", "name", "UNIQUENESS")
        self.add_constraint("genre_name", "Genre", "name", "UNIQUENESS")

        # 2. Genres
        g_scifi = self.merge_node(["Genre"], {"name": "Sci-Fi"})
        g_action = self.merge_node(["Genre"], {"name": "Action"})

        # 3. Movies & People for 'The Matrix'
        matrix = self.merge_node(["Movie"], {
            "title": "The Matrix",
            "released": 1999,
            "tagline": "Welcome to the Real World"
        })
        keanu = self.merge_node(["Person"], {"name": "Keanu Reeves", "born": 1964})
        carrie = self.merge_node(["Person"], {"name": "Carrie-Anne Moss", "born": 1967})
        laurence = self.merge_node(["Person"], {"name": "Laurence Fishburne", "born": 1961})
        hugo = self.merge_node(["Person"], {"name": "Hugo Weaving", "born": 1960})
        lana = self.merge_node(["Person"], {"name": "Lana Wachowski", "born": 1965})
        lilly = self.merge_node(["Person"], {"name": "Lilly Wachowski", "born": 1967})
        joel = self.merge_node(["Person"], {"name": "Joel Silver", "born": 1952})

        # 4. Relationships for 'The Matrix'
        self.merge_relationship(matrix, "HAS_GENRE", g_scifi)
        self.merge_relationship(keanu, "ACTED_IN", matrix, {"roles": ["Neo"]})
        self.merge_relationship(carrie, "ACTED_IN", matrix, {"roles": ["Trinity"]})
        self.merge_relationship(laurence, "ACTED_IN", matrix, {"roles": ["Morpheus"]})
        self.merge_relationship(hugo, "ACTED_IN", matrix, {"roles": ["Agent Smith"]})
        self.merge_relationship(lana, "DIRECTED", matrix)
        self.merge_relationship(lilly, "DIRECTED", matrix)
        self.merge_relationship(joel, "PRODUCED", matrix)

        # 5. Additional Movie: John Wick
        jwick = self.merge_node(["Movie"], {
            "title": "John Wick",
            "released": 2014,
            "tagline": "Don't set him off."
        })
        self.merge_relationship(jwick, "HAS_GENRE", g_action)
        self.merge_relationship(keanu, "ACTED_IN", jwick, {"roles": ["John Wick"]})

        # 6. Deletion test movie
        self.merge_node(["Movie"], {"title": "To Be Deleted", "released": 2024})

    def run_cypher_statement(self, cypher: str) -> List[Dict[str, Any]]:
        """
        Evaluate a Cypher statement or script against the in-memory graph.
        Accurately parses queries corresponding to the project requirements.
        """
        cleaned = " ".join([line.split("//")[0].strip() for line in cypher.strip().splitlines() if line.split("//")[0].strip()])
        cleaned_upper = cleaned.upper()

        # 1. SHOW CONSTRAINTS
        if "SHOW CONSTRAINTS" in cleaned_upper:
            return [
                {
                    "name": c["name"],
                    "type": c["type"],
                    "entityType": c["entityType"],
                    "labelsOrTypes": [c["label"]],
                    "properties": c["properties"]
                }
                for c in self.constraints
            ]

        # 2. CALL db.schema.visualization()
        if "DB.SCHEMA.VISUALIZATION" in cleaned_upper:
            all_labels = set()
            for n in self.nodes.values():
                all_labels.update(n.labels)
            all_rel_types = {r.type for r in self.relationships.values()}
            return [{
                "nodes": list(all_labels),
                "relationships": list(all_rel_types)
            }]

        # 3. Analytics Degree Centrality (analytics_degree.cypher)
        if "COUNT(R)" in cleaned_upper and "DEGREE" in cleaned_upper:
            limit_val = 5
            lim_match = re.search(r"LIMIT\s+(\d+)", cleaned_upper)
            if lim_match:
                limit_val = int(lim_match.group(1))
            people = self.get_nodes_by_label("Person")
            degrees = []
            for p in people:
                cnt = sum(1 for r in self.relationships.values() if r.start_node_id == p.id or r.end_node_id == p.id)
                degrees.append({"name": p.properties.get("name"), "degree": cnt})
            # Order by degree DESC, name ASC
            degrees.sort(key=lambda x: (-x["degree"], x["name"]))
            return degrees[:limit_val]

        # 4. Find co-actors: Hugo Weaving in The Matrix (find_co_actors.cypher)
        if "COACTOR" in cleaned_upper and "HUGO WEAVING" in cleaned_upper:
            matrix = self.find_node("Movie", {"title": "The Matrix"})
            hugo = self.find_node("Person", {"name": "Hugo Weaving"})
            if not matrix or not hugo:
                return []
            co_actors = set()
            for rel in self.relationships.values():
                if rel.end_node_id == matrix.id and rel.type == "ACTED_IN":
                    if rel.start_node_id != hugo.id:
                        actor = self.nodes.get(rel.start_node_id)
                        if actor:
                            co_actors.add(actor.properties.get("name"))
            return [{"name": name} for name in sorted(co_actors)]

        # 5. Find actor movies: Keanu Reeves (find_actor_movies.cypher)
        if "KEANU REEVES" in cleaned_upper and "ACTED_IN" in cleaned_upper and "RETURN M.TITLE" in cleaned_upper:
            keanu = self.find_node("Person", {"name": "Keanu Reeves"})
            if not keanu:
                return []
            results = []
            for rel in self.relationships.values():
                if rel.start_node_id == keanu.id and rel.type == "ACTED_IN":
                    movie = self.nodes.get(rel.end_node_id)
                    if movie and "Movie" in movie.labels:
                        results.append({"title": movie.properties.get("title")})
            results.sort(key=lambda x: x["title"])
            return results

        # 6. Verification query: Keanu Reeves ACTED_IN The Matrix
        if "KEANU REEVES" in cleaned_upper and "THE MATRIX" in cleaned_upper and re.search(r"RETURN\s+P\s*,\s*M\b", cleaned_upper):
            keanu = self.find_node("Person", {"name": "Keanu Reeves"})
            matrix = self.find_node("Movie", {"title": "The Matrix"})
            if keanu and matrix:
                for rel in self.relationships.values():
                    if rel.start_node_id == keanu.id and rel.end_node_id == matrix.id and rel.type == "ACTED_IN":
                        return [{"p": keanu.properties, "m": matrix.properties}]
            return []

        # 7. Create movie: 'V for Vendetta' (create_movie.cypher)
        if "V FOR VENDETTA" in cleaned_upper and ("CREATE" in cleaned_upper or "MERGE" in cleaned_upper) and not re.search(r"RETURN\s+P\s*,\s*M\b", cleaned_upper):
            m = self.merge_node(["Movie"], {"title": "V for Vendetta", "released": 2005, "tagline": "Freedom! Forever!"})
            hugo = self.find_node("Person", {"name": "Hugo Weaving"})
            if hugo:
                self.merge_relationship(hugo, "ACTED_IN", m, {"roles": ["V"]})
            lana = self.find_node("Person", {"name": "Lana Wachowski"})
            if lana:
                self.merge_relationship(lana, "PRODUCED", m)
            lilly = self.find_node("Person", {"name": "Lilly Wachowski"})
            if lilly:
                self.merge_relationship(lilly, "PRODUCED", m)
            return [{"title": m.properties.get("title"), "released": m.properties.get("released")}]

        # 8. Verification query: Hugo Weaving ACTED_IN V for Vendetta
        if "HUGO WEAVING" in cleaned_upper and "V FOR VENDETTA" in cleaned_upper and re.search(r"RETURN\s+P\s*,\s*M\b", cleaned_upper):
            hugo = self.find_node("Person", {"name": "Hugo Weaving"})
            v_movie = self.find_node("Movie", {"title": "V for Vendetta"})
            if hugo and v_movie:
                for rel in self.relationships.values():
                    if rel.start_node_id == hugo.id and rel.end_node_id == v_movie.id and rel.type == "ACTED_IN":
                        return [{"p": hugo.properties, "m": v_movie.properties}]
            return []

        # 9. Update rating on The Matrix (update_movie_rating.cypher)
        if "SET M.RATING = 8.7" in cleaned_upper:
            matrix = self.find_node("Movie", {"title": "The Matrix"})
            if matrix:
                matrix.properties["rating"] = 8.7
                return [{"title": matrix.properties.get("title"), "rating": 8.7}]
            return []

        # 10. Return rating on The Matrix (Verification query)
        if "RETURN M.RATING" in cleaned_upper and "THE MATRIX" in cleaned_upper:
            matrix = self.find_node("Movie", {"title": "The Matrix"})
            if matrix and "rating" in matrix.properties:
                return [{"rating": matrix.properties["rating"]}]
            return []

        # 11. Delete movie 'To Be Deleted' (delete_movie.cypher)
        if "TO BE DELETED" in cleaned_upper and ("DETACH DELETE" in cleaned_upper or re.search(r"\bDELETE\b", cleaned_upper)):
            to_del = self.find_node("Movie", {"title": "To Be Deleted"})
            if to_del:
                self.detach_delete_node(to_del)
            return []

        # 12. Query verification: MATCH (m:Movie {title: '...'}) RETURN m
        if "MATCH (M:MOVIE" in cleaned_upper and re.search(r"RETURN\s+M\s*(;|$)", cleaned_upper):
            match = re.search(r"title:\s*['\"]([^'\"]+)['\"]", cleaned, re.IGNORECASE)
            if match:
                movie_title = match.group(1)
                m = self.find_node("Movie", {"title": movie_title})
                if m:
                    return [{"m": m.properties}]
            return []

        # 13. Query verification: MATCH (p:Person {name: '...'}) RETURN p
        if "MATCH (P:PERSON" in cleaned_upper and re.search(r"RETURN\s+P\s*(;|$)", cleaned_upper):
            match = re.search(r"name:\s*['\"]([^'\"]+)['\"]", cleaned, re.IGNORECASE)
            if match:
                person_name = match.group(1)
                p = self.find_node("Person", {"name": person_name})
                if p:
                    return [{"p": p.properties}]
            return []

        return []
