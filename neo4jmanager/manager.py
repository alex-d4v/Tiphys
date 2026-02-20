"""
Neo4j Database Manager for Task Manager
Handles connection, schema, and basic operations
"""
import os
from typing import Optional
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

class Neo4jManager:
    """Manages Neo4j connection and schema operations."""
    
    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j bolt URI (default: from .env or bolt://localhost:7687)
            user: Neo4j username (default: from .env or neo4j)
            password: Neo4j password (default: from .env)
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        
        # Extract password from NEO4J_AUTH if present (format: neo4j/password)
        neo4j_auth = os.getenv("NEO4J_AUTH", "")
        if "/" in neo4j_auth:
            self.password = password or neo4j_auth.split("/", 1)[1]
        else:
            self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print(f"✓ Connected to Neo4j at {self.uri}")
        except Exception as e:
            print(f"✗ Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            print("✓ Neo4j connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def initialize_schema(self):
        """
        Create indexes and constraints for the Task graph schema.
        
        Schema:
        - Node: Task
          - Properties: id (UUID), description, date, time, priority, status, 
                       started_at, ended_at, embedding (vector)
          - Relationships: DEPENDS_ON (Task -> Task)
        """
        with self.driver.session() as session:
            # Create unique constraint on Task.id (automatically creates index)
            session.run("""
                CREATE CONSTRAINT task_id_unique IF NOT EXISTS
                FOR (t:Task) REQUIRE t.id IS UNIQUE
            """)
            
            # Create index on status for filtering
            session.run("""
                CREATE INDEX task_status_idx IF NOT EXISTS
                FOR (t:Task) ON (t.status)
            """)
            
            # Create index on date for temporal queries
            session.run("""
                CREATE INDEX task_date_idx IF NOT EXISTS
                FOR (t:Task) ON (t.date)
            """)
            
            # Create vector index for embeddings (for similarity search)
            # Note: Requires Neo4j 5.11+ with vector support
            try:
                session.run("""
                    CREATE VECTOR INDEX task_embedding_idx IF NOT EXISTS
                    FOR (t:Task) ON (t.embedding)
                    OPTIONS {indexConfig: {
                        `vector.dimensions`: 1024,
                        `vector.similarity_function`: 'cosine'
                    }}
                """)
                print("✓ Vector index created (Neo4j 5.11+ with vector support)")
            except Exception as e:
                print(f"⚠ Vector index creation skipped: {e}")
                print("  (This is fine if you're using Neo4j < 5.11 or without vector plugin)")
            
            print("✓ Schema initialized successfully")
    
    def clear_database(self, confirm: bool = False):
        """
        Delete all nodes and relationships. USE WITH CAUTION.
        
        Args:
            confirm: Must be True to actually clear the database
        """
        if not confirm:
            print("⚠ clear_database() called without confirmation. No action taken.")
            return
        
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✓ Database cleared")
    
    def get_database_stats(self) -> dict:
        """Get basic statistics about the database."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (t:Task)
                OPTIONAL MATCH (t)-[r:DEPENDS_ON]->()
                RETURN 
                    count(DISTINCT t) as task_count,
                    count(r) as dependency_count
            """)
            record = result.single()
            return {
                "tasks": record["task_count"],
                "dependencies": record["dependency_count"]
            }


if __name__ == "__main__":
    # Test connection and schema initialization
    with Neo4jManager() as db:
        db.initialize_schema()
        stats = db.get_database_stats()
        print(f"\nDatabase stats: {stats['tasks']} tasks, {stats['dependencies']} dependencies")