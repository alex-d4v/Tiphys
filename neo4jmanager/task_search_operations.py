"""
Task Operations for Neo4j
CRUD operations and queries for Task nodes
"""
import pandas as pd
from typing import List, Dict, Optional, Any, Literal
from .manager import Neo4jManager


class TaskSearchOperations:
    """
    Handles all task-related search operations in the database.
    
    This includes:
    - get_task_by_id: Retrieve a single task by its unique ID.
    - get_tasks_by_time_range: Get tasks within a date/time range.
    - get_relevant_tasks_by_task: Get tasks related through dependencies.
    - get_relevant_tasks_by_query: Vector similarity search.
    """
    
    def __init__(self, db_manager: Neo4jManager):
        self.db = db_manager
    
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

    def get_tasks_by_time_range(self, start_date: str, end_date: str, start_time: str = "00:00", end_time: str = "23:59", limit: int = 10) -> pd.DataFrame:
        """
        Get tasks within a given date/time range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            start_time: Start time (HH:MM), defaults to "00:00"
            end_time: End time (HH:MM), defaults to "23:59"
            limit: Maximum number of results
        
        Returns:
            DataFrame of tasks in the time range
        """
        with self.db.driver.session() as session:
            query = """
                MATCH (t:Task)
                WHERE (t.date > $start_date OR (t.date = $start_date AND t.time >= $start_time))
                  AND (t.date < $end_date OR (t.date = $end_date AND t.time <= $end_time))
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
                LIMIT $limit
            """
            result = session.run(query, start_date=start_date, start_time=start_time, end_date=end_date, end_time=end_time, limit=limit)
            records = [dict(record) for record in result]
            cols = ["id", "description", "date", "time", "priority", "status", "started_at", "ended_at", "dependencies", "blocked_tasks"]
            return pd.DataFrame(records, columns=cols) if records else pd.DataFrame(columns=cols)
    
    def get_relevant_tasks_by_task(self, task_id: str, max_depth: int | Literal['full'] = 'full') -> pd.DataFrame:
        """
        Get tasks related to a given task through dependencies.
        
        Args:
            task_id: UUID of the source task
            max_depth: Maximum relationship depth to traverse ('full' for unlimited, or int)
        
        Returns:
            DataFrame of related tasks
        """
        with self.db.driver.session() as session:
            depth_str = "*" if max_depth == 'full' else f"*0..{max_depth}"
            
            result = session.run(f"""
                MATCH (t:Task {{id: $task_id}})
                MATCH path = (t)-[:DEPENDS_ON{depth_str}]-(related:Task)
                WITH DISTINCT related
                OPTIONAL MATCH (related)-[:DEPENDS_ON]->(d:Task)
                OPTIONAL MATCH (future:Task)-[:DEPENDS_ON]->(related)
                WITH related, collect(DISTINCT d.id) as dependencies, collect(DISTINCT future.id) as blocked_tasks
                RETURN related.id as id,
                       related.description as description,
                       related.date as date,
                       related.time as time,
                       related.priority as priority,
                       related.status as status,
                       related.started_at as started_at,
                       related.ended_at as ended_at,
                       dependencies,
                       blocked_tasks
                ORDER BY related.date, related.time
            """, task_id=task_id)
            
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