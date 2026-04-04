#!/usr/bin/env python3
"""
Example usage of the workflow tracker
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from workflow_tracker import WorkflowTracker

def demo():
    """Demonstrate the workflow tracker functionality"""
    tracker = WorkflowTracker()
    
    # Add some team members
    tracker.add_member("commander", "strategic lead")
    tracker.add_member("maker", "tech lead") 
    tracker.add_member("vibe", "design lead")
    tracker.add_member("killjoy", "quality lead")
    
    # Add some tasks
    tracker.add_task("sq-001", "Setup project infrastructure", "maker", "todo", "high")
    tracker.add_task("sq-002", "Design user interface mockups", "vibe", "in_progress", "medium")
    tracker.add_task("sq-003", "Review API documentation", "killjoy", "todo", "medium")
    tracker.add_task("sq-004", "Define project roadmap", "commander", "done", "high")
    tracker.add_task("sq-005", "Test deployment pipeline", "maker", "blocked", "high")
    
    # Update some task statuses
    tracker.update_task_status("sq-003", "in_progress")
    
    # Show dashboard
    print("📊 DEMO DASHBOARD")
    tracker.show_dashboard()
    
    # Export summary
    tracker.export_summary("demo_summary.json")
    
    # Show workload breakdown
    print("\n👥 MEMBER WORKLOAD:")
    for member in tracker.data["members"]:
        member_tasks = tracker.get_member_tasks(member)
        print(f"  {member}: {len(member_tasks)} tasks")
    
    # Show tasks by status
    print("\n📋 TASKS BY STATUS:")
    for status in ["todo", "in_progress", "done", "blocked"]:
        tasks = tracker.get_tasks_by_status(status)
        if tasks:
            print(f"  {status.upper()}:")
            for task in tasks:
                print(f"    - {task['title']} (ID: {task['id']})")

if __name__ == "__main__":
    demo()