"""
Test script for Neo4j task operations
Run this to verify your Neo4j setup and operations
"""
import pandas as pd
from db import Neo4jManager, TaskOperations


def test_connection():
    """Test Neo4j connection."""
    print("=" * 60)
    print("TEST 1: Connection & Schema")
    print("=" * 60)
    
    with Neo4jManager() as db:
        db.initialize_schema()
        stats = db.get_database_stats()
        print(f"Current stats: {stats['tasks']} tasks, {stats['dependencies']} dependencies\n")


def test_store_and_retrieve():
    """Test storing and retrieving tasks."""
    print("=" * 60)
    print("TEST 2: Store & Retrieve Tasks")
    print("=" * 60)
    
    # Create sample tasks
    tasks_data = [
        {
            "id": "task-001",
            "description": "Write project proposal",
            "date": "2026-02-21",
            "time": "09:00",
            "priority": "high",
            "status": "pending",
            "dependencies": [],
            "started_at": None,
            "ended_at": None
        },
        {
            "id": "task-002",
            "description": "Review budget requirements",
            "date": "2026-02-21",
            "time": "14:00",
            "priority": "medium",
            "status": "pending",
            "dependencies": ["task-001"],
            "started_at": None,
            "ended_at": None
        },
        {
            "id": "task-003",
            "description": "Submit final proposal",
            "date": "2026-02-22",
            "time": "10:00",
            "priority": "high",
            "status": "pending",
            "dependencies": ["task-001", "task-002"],
            "started_at": None,
            "ended_at": None
        }
    ]
    
    tasks_df = pd.DataFrame(tasks_data)
    
    with Neo4jManager() as db:
        ops = TaskOperations(db)
        
        # Store tasks
        count = ops.store_tasks(tasks_df)
        print(f"Stored {count} tasks")
        
        # Retrieve all tasks
        retrieved = ops.get_tasks()
        print(f"Retrieved {len(retrieved)} tasks")
        print(retrieved[["id", "description", "status", "dependencies"]].to_string(index=False))
        print()


def test_related_tasks():
    """Test finding related tasks."""
    print("=" * 60)
    print("TEST 3: Related Tasks")
    print("=" * 60)
    
    with Neo4jManager() as db:
        ops = TaskOperations(db)
        
        # Get tasks related to task-001
        related = ops.get_relevant_tasks_by_task("task-001", max_depth=2)
        print(f"Found {len(related)} tasks related to task-001:")
        print(related[["id", "description"]].to_string(index=False))
        print()


def test_task_path():
    """Test showing task dependency paths."""
    print("=" * 60)
    print("TEST 4: Task Dependency Paths")
    print("=" * 60)
    
    with Neo4jManager() as db:
        ops = TaskOperations(db)
        
        # Show path from task-001 to task-003
        paths = ops.show_task_path("task-001", "task-003")
        print(f"Found {len(paths)} path(s) from task-001 to task-003:")
        for i, path in enumerate(paths, 1):
            print(f"\n  Path {i}:")
            for task in path:
                print(f"    → {task['id']}: {task['description']} [{task['status']}]")
        print()


def test_update_and_delete():
    """Test updating and deleting tasks."""
    print("=" * 60)
    print("TEST 5: Update & Delete")
    print("=" * 60)
    
    with Neo4jManager() as db:
        ops = TaskOperations(db)
        
        # Update task status
        success = ops.update_task_status("task-001", "completed")
        print(f"Updated task-001 status: {success}")
        
        # Verify update
        task = ops.get_task_by_id("task-001")
        print(f"  New status: {task['status']}")
        
        # Delete a task
        deleted = ops.delete_tasks(["task-002"])
        print(f"Deleted {deleted} task(s)")
        
        # Verify deletion
        remaining = ops.get_tasks()
        print(f"  Remaining tasks: {len(remaining)}")
        print()


def cleanup():
    """Clean up test data."""
    print("=" * 60)
    print("CLEANUP: Removing Test Data")
    print("=" * 60)
    
    with Neo4jManager() as db:
        ops = TaskOperations(db)
        deleted = ops.delete_tasks(["task-001", "task-002", "task-003"])
        print(f"Deleted {deleted} test task(s)\n")


if __name__ == "__main__":
    try:
        test_connection()
        test_store_and_retrieve()
        test_related_tasks()
        test_task_path()
        test_update_and_delete()
        
        # Ask before cleanup
        response = input("\nRemove test data? (y/n): ").strip().lower()
        if response == 'y':
            cleanup()
        
        print("=" * 60)
        print("All tests passed!")
        print("=" * 60)
    
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()