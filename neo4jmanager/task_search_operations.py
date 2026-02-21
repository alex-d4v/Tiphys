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
    
    def __init__(self, db_manager: Neo4jManager, embeddings_func=None):
        self.db = db_manager
        self.embeddings_func = embeddings_func

    def get_available_tools(self) -> List[Dict[str, str]]:
        """Returns a list of tools with their signatures and documentation."""
        tools = []
        import inspect
        for method_name in dir(self):
            if method_name.startswith("get_") and callable(getattr(self, method_name)) and method_name != "get_available_tools":
                method = getattr(self, method_name)
                signature = str(inspect.signature(method))
                # Remove self from signature if present
                signature = signature.replace("(self, ", "(").replace("(self)", "()")
                
                tools.append({
                    "name": method_name,
                    "signature": f"{method_name}{signature}",
                    "description": (method.__doc__ or "No description.").strip()
                })
        return tools
    
    def get_tasks_by_time_range(self, start_date: str, end_date: str, start_time: str = None, end_time: str = None, limit: int = 10) -> pd.DataFrame:
        """
        Get tasks within a given date/time range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            start_time: Optional start time (HH:MM). If None, searches from start of day.
            end_time: Optional end time (HH:MM). If None, searches until end of day.
            limit: Maximum number of results
        
        Returns:
            DataFrame of tasks in the time range
        """
        s_time = start_time or "00:00"
        e_time = end_time or "23:59"
        
        with self.db.driver.session() as session:
            query = """
                MATCH (t:Task)
                WHERE (t.date > $start_date OR (t.date = $start_date AND (t.time >= $start_time OR t.time IS NULL)))
                  AND (t.date < $end_date OR (t.date = $end_date AND (t.time <= $end_time OR t.time IS NULL)))
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
            result = session.run(query, start_date=start_date, start_time=s_time, end_date=end_date, end_time=e_time, limit=limit)
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
    
    def get_relevant_tasks_by_query(self, query: str, top_k: int = 5) -> pd.DataFrame:
        """
        Find tasks similar to a query using vector similarity search.
        
        Args:
            query: Search query string , it will be converted to embedding using the provided embeddings function
            top_k: Number of most similar tasks to return
        
        Returns:
            DataFrame of similar tasks with similarity scores
        
        Note: Requires Neo4j 5.11+ with vector index support
        """
        if not self.embeddings_func:
            raise ValueError("Embeddings function not provided for vector search.")
        
        query_embedding = self.embeddings_func(query)
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
