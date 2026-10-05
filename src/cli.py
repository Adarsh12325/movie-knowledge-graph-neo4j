import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configure standard output to handle UTF-8 cleanly if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

from src.config import settings
from src.graph_service import MovieKnowledgeGraphService


def format_table(data: List[Dict[str, Any]]) -> str:
    """Format a list of dicts as a clean ASCII table."""
    if not data:
        return "(No rows returned)"
    if TABULATE_AVAILABLE:
        headers = "keys"
        return tabulate(data, headers=headers, tablefmt="grid")
    else:
        # Simple ASCII fallback
        keys = list(data[0].keys())
        lines = [" | ".join(keys), "-" * 40]
        for row in data:
            lines.append(" | ".join(str(row.get(k, "")) for k in keys))
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Movie Knowledge Graph - Interactive Management and Analytics CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: seed
    subparsers.add_parser("seed", help="Execute init/seed.cypher to populate the graph")

    # Command: schema
    subparsers.add_parser("schema", help="Inspect graph schema, constraints, and counts")

    # Command: analytics
    analytics_parser = subparsers.add_parser("analytics", help="Run degree centrality analytics")
    analytics_parser.add_argument("--limit", type=int, default=5, help="Number of top people to display")

    # Command: query
    query_parser = subparsers.add_parser("query", help="Execute a specific query script or custom Cypher")
    query_parser.add_argument("name", help="Query script name (e.g. find_co_actors, analytics_degree) or Cypher text")

    # Command: run-all
    subparsers.add_parser("run-all", help="Sequentially run all 6 core query scripts")

    # Global flags
    parser.add_argument("--mock", action="store_true", help="Force using the offline in-memory graph engine")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    service = MovieKnowledgeGraphService(force_mock=args.mock)
    mode_str = "LIVE NEO4J" if service.is_live else "OFFLINE IN-MEMORY ENGINE"
    print(f"\n=======================================================")
    print(f"  Movie Knowledge Graph CLI [{mode_str}]")
    print(f"=======================================================\n")

    if args.command == "seed":
        print("[*] Seeding database from init/seed.cypher...")
        try:
            service.seed_database()
            print("[+] Seeding completed successfully.")
            summary = service.get_schema_summary()
            print(f"    Total Nodes: {summary['total_nodes']}, Total Relationships: {summary['total_relationships']}")
        except Exception as e:
            print(f"[-] Seeding failed: {e}")
            sys.exit(1)

    elif args.command == "schema":
        print("[*] Graph Schema Summary:")
        summary = service.get_schema_summary()
        print(f"    Labels: {', '.join(summary['labels'])}")
        print(f"    Relationship Types: {', '.join(summary['relationship_types'])}")
        print(f"    Nodes Count: {summary['total_nodes']}")
        print(f"    Relationships Count: {summary['total_relationships']}\n")

        print("[*] Registered Constraints:")
        constraints = service.get_constraints()
        if constraints:
            print(format_table(constraints))
        else:
            print("    (No constraints found)")

    elif args.command == "analytics":
        print(f"[*] Top {args.limit} People by Degree Centrality (Most Connected):")
        results = service.get_degree_centrality(limit=args.limit)
        print(format_table(results))

    elif args.command == "query":
        query_input = args.name
        # Check if it corresponds to a file in queries/
        potential_file = settings.get_query_path(query_input)
        if potential_file.exists():
            print(f"[*] Executing Cypher script: {potential_file.name}")
            results = service.execute_cypher_file(potential_file)
            print(format_table(results))
        else:
            print(f"[*] Executing custom Cypher statement...")
            results = service.execute_cypher(query_input)
            print(format_table(results))

    elif args.command == "run-all":
        query_files = [
            "create_movie.cypher",
            "find_actor_movies.cypher",
            "find_co_actors.cypher",
            "update_movie_rating.cypher",
            "delete_movie.cypher",
            "analytics_degree.cypher",
        ]
        for qf in query_files:
            p = settings.queries_dir / qf
            print(f"\n---> Executing {qf}:")
            if p.exists():
                results = service.execute_cypher_file(p)
                print(format_table(results))
            else:
                print(f"[-] File not found: {p}")
        print("\n[+] All core queries executed successfully.")


if __name__ == "__main__":
    main()
