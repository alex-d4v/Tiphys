"""
Task Operations for Neo4j
CRUD operations and queries for Task nodes
"""
import pandas as pd
from typing import List, Dict, Optional, Any
from .manager import Neo4jManager


class TaskOperations:
    """Handles all task-related database operations."""
    
    def __init__(self, db_manager: Neo4jManager):
        self.db = db_manager
    
    # ── CREATE ────────────────────────────────────────────────────────────────
    
    def store_tasks(self, tasks: pd.DataFrame, embeddings_func=None) -> int:
        """
        Store tasks in Neo4j with their dependencies.
        
        Args:
            tasks: DataFrame with columns: id, description, date, time, priority, 
                   status, dependencies (list of UUIDs), started_at, ended_at
            embeddings_func: Optional function to generate embeddings for tasks
        
        Returns:
            Number of tasks created
        """
        with self.db.driver.session() as session:
            created_count = 0
            
            for _, task in tasks.iterrows():
                # Generate embedding if function provided
                embedding = None
                if embeddings_func:
                    task_text = self._task_to_text(task)
                    embedding = embeddings_func(task_text)
                
                # Create task node
                result = session.run("""
                    MERGE (t:Task {id: $id})
                    SET t.description = $description,
                        t.date = $date,
                        t.time = $time,
                        t.priority = $priority,
                        t.status = $status,
                        t.started_at = $started_at,
                        t.ended_at = $ended_at,
                        t.embedding = $embedding,
                        t.updated_at = datetime()
                    RETURN t
                """, 
                    id=str(task["id"]),
                    description=str(task["description"]),
                    date=str(task["date"]),
                    time=str(task["time"]),
                    priority=str(task.get("priority", "medium")),
                    status=str(task.get("status", "pending")),
                    started_at=task.get("started_at"),
                    ended_at=task.get("ended_at"),
                    embedding=embedding
                )
                
                if result.single():
                    created_count += 1
                
                # Create dependency relationships
                dependencies = task.get("dependencies", [])
                if isinstance(dependencies, list) and dependencies:
                    for dep_id in dependencies:
                        session.run("""
                            MATCH (t:Task {id: $task_id})
                            MATCH (d:Task {id: $dep_id})
                            MERGE (t)-[:DEPENDS_ON]->(d)
                        """,
                            task_id=str(task["id"]),
                            dep_id=str(dep_id)
                        )
            
            return created_count
    
    # ── READ ──────────────────────────────────────────────────────────────────
    def get_tasks(self, status: Optional[str] = None, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Retrieve all tasks, optionally filtered by status.
        
        Args:
            status: Filter by status (pending, in_progress, completed, etc.)
            limit: Maximum number of tasks to return
        
        Returns:
            DataFrame of tasks with dependencies as lists
        """
        with self.db.driver.session() as session:
            query = """
                MATCH (t:Task)
                WHERE $status IS NULL OR t.status = $status
                OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:Task)
                OPTIONAL MATCH (future:Task)-[:DEPENDS_ON]->(t)
                WITH t, collect(DISTINCT d.id) as dependencies, collect(DISTINCT future.id) as blocked_tasks
                RETURN t.id as id,
                       t.description as description,
                       t.date as date,
                       t.time as time,
                       t.priority as priority,
                       t.status as status,
                       t.started_at as started_at,
                       t.ended_at as ended_at,
                       dependencies,
                       blocked_tasks
                ORDER BY t.date, t.time
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            result = session.run(query, status=status)
            records = [dict(record) for record in result]
            
            # Ensure we return a DataFrame with expected columns even if empty
            cols = ["id", "description", "date", "time", "priority", "status", "started_at", "ended_at", "dependencies", "blocked_tasks"]
            return pd.DataFrame(records, columns=cols) if records else pd.DataFrame(columns=cols)
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a single task by ID."""
        with self.db.driver.session() as session:
            result = session.run("""
                MATCH (t:Task {id: $task_id})
                OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:Task)
                OPTIONAL MATCH (future:Task)-[:DEPENDS_ON]->(t)
                WITH t, collect(DISTINCT d.id) as dependencies, collect(DISTINCT future.id) as blocked_tasks
                RETURN t.id as id,
                       t.description as description,
                       t.date as date,
                       t.time as time,
                       t.priority as priority,
                       t.status as status,
                       t.started_at as started_at,
                       t.ended_at as ended_at,
                       dependencies,
                       blocked_tasks
            """, task_id=task_id)
            
            record = result.single()
            return dict(record) if record else None
            
    def get_today_tasks(self) -> pd.DataFrame:
        """Get all tasks for today (or with today's date)."""
        import datetime
        today = datetime.date.today().isoformat()
        with self.db.driver.session() as session:
            
            result = session.run("""
                MATCH (t:Task {date: $today})
                OPTIONAL MATCH (t)-[:DEPENDS_ON]->(past:Task)
                OPTIONAL MATCH (future:Task)-[:DEPENDS_ON]->(t)
                WITH t, 
                    collect(DISTINCT past.id) as dependencies,
                    collect(DISTINCT future.id) as blocked_tasks
                RETURN t.id as id,
                    t.description as description,
                    t.date as date,
                    t.time as time,
                    t.priority as priority,
                    t.status as status,
                    t.started_at as started_at,
                    t.ended_at as ended_at,
                    dependencies,
                    blocked_tasks
                ORDER BY t.time
            """, today=today)
            
            records = [dict(record) for record in result]
            cols = ["id", "description", "date", "time", "priority", "status", "started_at", "ended_at", "dependencies", "blocked_tasks"]
            return pd.DataFrame(records, columns=cols) if records else pd.DataFrame(columns=cols)
    
    def get_relevant_tasks_by_task(self, task_id: str, max_depth: int = 2) -> pd.DataFrame:
        """
        Get tasks related to a given task through dependencies.
        
        Args:
            task_id: UUID of the source task
            max_depth: Maximum relationship depth to traverse
        
        Returns:
            DataFrame of related tasks
        """
        with self.db.driver.session() as session:
            result = session.run("""
                MATCH (t:Task {id: $task_id})
                MATCH path = (t)-[:DEPENDS_ON*0..%d]-(related:Task)
                WITH DISTINCT related
                OPTIONAL MATCH (related)-[:DEPENDS_ON]->(d:Task)
                OPTIONAL MATCH (future:Task)-[:DEPENDS_ON]->(related)
                WITH related, collect(d.id) as dependencies, collect(future.id) as blocked_tasks
                RETURN related.id as id,
                       related.description as description,
                       related.date as date,
                       related.time as time,
                       related.priority as priority,
                       related.status as status,
                       related.started_at as started_at,
                       related.ended_at as ended_at,
                       dependencies,
                       blocked_tasks  -- Tasks waiting on this one
                ORDER BY related.date, related.time
            """ % max_depth, task_id=task_id)
            
            records = [dict(record) for record in result]
            cols = ["id", "description", "date", "time", "priority", "status", "started_at", "ended_at", "dependencies", "blocked_tasks"]
            return pd.DataFrame(records, columns=cols) if records else pd.DataFrame(columns=cols)
    
    def get_relevant_tasks_by_query(self, query_embedding: List[float], top_k: int = 5) -> pd.DataFrame:
        """
        Find tasks similar to a query using vector similarity search.
        
        Args:
            query_embedding: Embedding vector for the search query
            top_k: Number of most similar tasks to return
        
        Returns:
            DataFrame of similar tasks with similarity scores
        
        Note: Requires Neo4j 5.11+ with vector index support
        """
        with self.db.driver.session() as session:
            try:
                result = session.run("""
                    CALL db.index.vector.queryNodes('task_embedding_idx', $top_k, $query_embedding)
                    YIELD node, score
                    OPTIONAL MATCH (node)-[:DEPENDS_ON]->(d:Task)
                    OPTIONAL MATCH (future:Task)-[:DEPENDS_ON]->(node)
                    WITH node, score, collect(DISTINCT d.id) as dependencies, collect(DISTINCT future.id) as blocked_tasks
                    RETURN node.id as id,
                        node.description as description,
                        node.date as date,
                        node.time as time,
                        node.priority as priority,
                        node.status as status,
                        node.started_at as started_at,
                        node.ended_at as ended_at,
                        dependencies,
                        blocked_tasks,
                        score
                    ORDER BY score DESC
                """, query_embedding=query_embedding, top_k=top_k)
                
                records = [dict(record) for record in result]
                cols = ["id", "description", "date", "time", "priority", "status", "started_at", "ended_at", "dependencies", "blocked_tasks", "score"]
                return pd.DataFrame(records, columns=cols) if records else pd.DataFrame(columns=cols)
            
            except Exception as e:
                print(f"Vector search failed: {e}")
                print("Falling back to text-based search...")
                cols = ["id", "description", "date", "time", "priority", "status", "started_at", "ended_at", "dependencies", "blocked_tasks", "score"]
                return pd.DataFrame(columns=cols)
    
    def show_task_path(self, start_task_id: str, end_task_id: Optional[str] = None) -> List[Dict]:
        """
        Find the dependency path between two tasks or show all paths from a task.
        
        Args:
            start_task_id: Starting task UUID
            end_task_id: Optional ending task UUID
        
        Returns:
            List of paths, where each path is a list of task dicts
        """
        with self.db.driver.session() as session:
            if end_task_id:
                # Find shortest path between two specific tasks
                result = session.run("""
                    MATCH path = shortestPath((start:Task {id: $start_id})-[:DEPENDS_ON*]->(end:Task {id: $end_id}))
                    RETURN [node in nodes(path) | {
                        id: node.id,
                        description: node.description,
                        status: node.status
                    }] as path
                """, start_id=start_task_id, end_id=end_task_id)
                
                record = result.single()
                return [record["path"]] if record else []
            else:
                # Show all downstream dependencies
                result = session.run("""
                    MATCH path = (start:Task {id: $start_id})-[:DEPENDS_ON*]->(dep:Task)
                    WITH path
                    RETURN [node in nodes(path) | {
                        id: node.id,
                        description: node.description,
                        status: node.status
                    }] as path
                    ORDER BY length(path)
                """, start_id=start_task_id)
                
                return [record["path"] for record in result]
    
    # ── UPDATE ────────────────────────────────────────────────────────────────
    def update_task_status(self, task_id: str, new_status: str) -> bool:
        """Update the status of a task."""
        with self.db.driver.session() as session:
            result = session.run("""
                MATCH (t:Task {id: $task_id})
                SET t.status = $new_status,
                    t.updated_at = datetime()
                RETURN t
            """, task_id=task_id, new_status=new_status)
            
            return result.single() is not None
            
    def update_task(self, task_id: str, update_dict: Dict[str, Any]) -> bool:
        """Generic update for any task properties."""
        if not update_dict:
            return False
            
        # Don't allow updating id
        update_dict.pop("id", None)
        
        # Format set string
        set_clauses = []
        for key in update_dict.keys():
            set_clauses.append(f"t.{key} = ${key}")
        
        set_clauses.append("t.updated_at = datetime()")
        set_query = "SET " + ", ".join(set_clauses)
        
        with self.db.driver.session() as session:
            result = session.run(f"""
                MATCH (t:Task {{id: $task_id}})
                {set_query}
                RETURN t
            """, task_id=task_id, **update_dict)
            
            return result.single() is not None
    
    # ── DELETE ────────────────────────────────────────────────────────────────
    
    def delete_tasks(self, task_ids: List[str]) -> int:
        """
        Delete tasks by their IDs.
        
        Args:
            task_ids: List of task UUIDs to delete
        
        Returns:
            Number of tasks deleted
        """
        with self.db.driver.session() as session:
            result = session.run("""
                MATCH (t:Task)
                WHERE t.id IN $task_ids
                DETACH DELETE t
                RETURN count(t) as deleted_count
            """, task_ids=task_ids)
            
            record = result.single()
            return record["deleted_count"] if record else 0
    
    def delete_all_tasks(self) -> int:
        """Delete all tasks from the database."""
        with self.db.driver.session() as session:
            result = session.run("""
                MATCH (t:Task)
                DETACH DELETE t
                RETURN count(t) as deleted_count
            """)
            record = result.single()
            return record["deleted_count"] if record else 0
    
    # ── UTILITIES ─────────────────────────────────────────────────────────────
    
    @staticmethod
    def _task_to_text(task: pd.Series) -> str:
        """Convert a task to a text representation for embedding."""
        parts = [
            f"Description: {task['description']}",
            f"Date: {task['date']}",
            f"Priority: {task.get('priority', 'medium')}",
            f"Status: {task.get('status', 'pending')}",
            f"Dependencies: {task.get('dependencies', [])}",
            f"Blocked Tasks: {task.get('blocked_tasks', [])}"
        ]
        return " | ".join(parts)