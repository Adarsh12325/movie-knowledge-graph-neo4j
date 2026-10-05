"""
Configuration module for the Movie Knowledge Graph application.
Loads and validates environment settings from .env file and environment variables.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
    # Load .env from project root if it exists
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
except ImportError:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    """Application configuration parameters."""
    project_root: Path = PROJECT_ROOT
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_auth_raw: str = os.getenv("NEO4J_AUTH", "neo4j/neo4j")
    
    @property
    def neo4j_user(self) -> str:
        """Extract username from NEO4J_USER or NEO4J_AUTH."""
        if os.getenv("NEO4J_USER"):
            return os.environ["NEO4J_USER"]
        if "/" in self.neo4j_auth_raw:
            return self.neo4j_auth_raw.split("/", 1)[0]
        return "neo4j"

    @property
    def neo4j_password(self) -> str:
        """Extract password from NEO4J_PASSWORD or NEO4J_AUTH."""
        if os.getenv("NEO4J_PASSWORD"):
            return os.environ["NEO4J_PASSWORD"]
        if "/" in self.neo4j_auth_raw:
            return self.neo4j_auth_raw.split("/", 1)[1]
        return self.neo4j_auth_raw

    @property
    def init_dir(self) -> Path:
        return self.project_root / "init"

    @property
    def seed_file(self) -> Path:
        return self.init_dir / "seed.cypher"

    @property
    def queries_dir(self) -> Path:
        return self.project_root / "queries"

    def get_query_path(self, filename: str) -> Path:
        if not filename.endswith(".cypher"):
            filename += ".cypher"
        return self.queries_dir / filename


settings = Settings()
