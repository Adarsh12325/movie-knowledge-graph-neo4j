"""
Database connection manager for Neo4j.
Handles driver initialization, connectivity verification, session pooling, and safe cleanup.
"""

import logging
from typing import Optional
from contextlib import contextmanager

try:
    import neo4j
    from neo4j import GraphDatabase, Driver, Session
    from neo4j.exceptions import ServiceUnavailable, AuthError
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    Driver = None
    Session = None

from src.config import settings

logger = logging.getLogger(__name__)


class Neo4jConnectionManager:
    """Manages lifecycle and access to the Neo4j Bolt driver."""
    _instance: Optional["Neo4jConnectionManager"] = None
    _driver: Optional[Driver] = None

    def __new__(cls) -> "Neo4jConnectionManager":
        if cls._instance is None:
            cls._instance = super(Neo4jConnectionManager, cls).__new__(cls)
        return cls._instance

    def get_driver(self) -> Driver:
        """Lazily initialize and return the Neo4j driver."""
        if not NEO4J_AVAILABLE:
            raise RuntimeError(
                "The 'neo4j' Python package is not installed. "
                "Please run: pip install -r requirements.txt"
            )

        if self._driver is None:
            auth = (settings.neo4j_user, settings.neo4j_password)
            logger.info("Initializing Neo4j driver at %s (user: %s)", settings.neo4j_uri, settings.neo4j_user)
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=auth,
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=10.0
            )
        return self._driver

    def verify_connectivity(self) -> bool:
        """Check if Neo4j is reachable and authentication is valid."""
        if not NEO4J_AVAILABLE:
            return False
        
        # Fast TCP pre-check to prevent long driver connection timeouts when offline
        import socket
        try:
            # Parse host and port from URI (e.g. bolt://localhost:7687)
            uri = settings.neo4j_uri.replace("bolt://", "").replace("neo4j://", "")
            host, port_str = uri.split(":") if ":" in uri else (uri, "7687")
            if host.lower() == "localhost":
                host = "127.0.0.1"
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex((host, int(port_str)))
            sock.close()
            if result != 0:
                return False
        except Exception:
            return False

        try:
            driver = self.get_driver()
            driver.verify_connectivity()
            return True
        except Exception as exc:
            logger.debug("Connectivity check failed: %s", exc)
            return False

    @contextmanager
    def get_session(self, database: str = "neo4j") -> Session:
        """Context manager for acquiring and safely closing a Neo4j session."""
        driver = self.get_driver()
        session = driver.session(database=database)
        try:
            yield session
        finally:
            session.close()

    def close(self) -> None:
        """Close the active driver and connection pool."""
        if self._driver is not None:
            logger.info("Closing Neo4j driver connections")
            self._driver.close()
            self._driver = None


connection_manager = Neo4jConnectionManager()
