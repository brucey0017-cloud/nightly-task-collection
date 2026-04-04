#!/usr/bin/env python3
"""
Simple workflow tracker for teams
Author: commander (sidequest)
Date: 2026-04-04
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

class WorkflowTracker:
    def __init__(self, data_file=None):
        self.data_file = data_file or "/tmp/workflow_data.json"
        self.data = self._load_data()
    
    def _load_data(self):
        """Load existing data or create new structure"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "created_at": datetime.now().isoformat(),
            "tasks": [],
            "members": {}
        }
    
    def _save_data(self):
        """Save data to file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def add_task(self, task_id, title, assigned_to=None, status="todo", priority="medium"):
        """Add a new task"""
        task = {
            "id": task_id,
            "title": title,
            "assigned_to": assigned_to,
            "status": status,
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.data["tasks"].append(task)
        self._save_data()
    
    def update_task_status(self, task_id, new_status):
        """Update task status"""
        for task in self.data["tasks"]:
            if task["id"] == task_id:
                task["status"] = new_status
                task["updated_at"] = datetime.now().isoformat()
                self._save_data()
                return True
        return False
    
    def add_member(self, name, role="member"):
        """Add a team member"""
        self.data["members"][name] = {
            "name": name,
            "role": role,
            "joined_at": datetime.now().isoformat()
        }
        self._save_data()
    
    def get_member_tasks(self, member_name):
        """Get all tasks for a specific member"""
        return [task for task in self.data["tasks"] if task["assigned_to"] == member_name]
    
    def get_tasks_by_status(self, status):
        """Get tasks by status"""
        return [task for task in self.data["tasks"] if task["status"] == status]
    
    def show_dashboard(self):
        """Display a simple dashboard"""
        print("\n" + "="*50)
        print("WORKFLOW TRACKER DASHBOARD")
        print("="*50)
        print(f"Total tasks: {len(self.data['tasks'])}")
        print(f"Team members: {len(self.data['members'])}")
        
        # Show tasks by status
        status_counts = {}
        for task in self.data["tasks"]:
            status = task["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\nTask Status:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        # Show recent tasks
        print("\nRecent Tasks:")
        recent_tasks = sorted(self.data["tasks"], 
                            key=lambda x: x["updated_at"], 
                            reverse=True)[:5]
        for task in recent_tasks:
            status_icon = {"todo": "⏳", "in_progress": "🔄", "done": "✅", "blocked": "🚫"}
            icon = status_icon.get(task["status"], "❓")
            print(f"  {icon} {task['title']} ({task['status']}) - {task['assigned_to'] or 'unassigned'}")
        
        print("="*50 + "\n")
    
    def export_summary(self, output_file):
        """Export summary to file"""
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_tasks": len(self.data["tasks"]),
            "task_status_breakdown": {},
            "member_workload": {}
        }
        
        # Task status breakdown
        for task in self.data["tasks"]:
            status = task["status"]
            summary["task_status_breakdown"][status] = summary["task_status_breakdown"].get(status, 0) + 1
        
        # Member workload
        for member in self.data["members"]:
            member_tasks = self.get_member_tasks(member)
            summary["member_workload"][member] = len(member_tasks)
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Summary exported to: {output_file}")

def main():
    tracker = WorkflowTracker()
    
    # Example usage
    if len(sys.argv) > 1:
        if sys.argv[1] == "dashboard":
            tracker.show_dashboard()
        elif sys.argv[1] == "add-member":
            if len(sys.argv) > 2:
                tracker.add_member(sys.argv[2])
                print(f"Added member: {sys.argv[2]}")
        elif sys.argv[1] == "add-task":
            if len(sys.argv) > 4:
                tracker.add_task(sys.argv[2], sys.argv[3], sys.argv[4])
                print(f"Added task: {sys.argv[3]}")
        elif sys.argv[1] == "export":
            if len(sys.argv) > 2:
                tracker.export_summary(sys.argv[2])
    else:
        # Interactive mode
        while True:
            print("\nWorkflow Tracker - Commands:")
            print("  1. Show dashboard")
            print("  2. Add task")
            print("  3. Add member")
            print("  4. Export summary")
            print("  5. Exit")
            
            choice = input("Choose option: ")
            
            if choice == "1":
                tracker.show_dashboard()
            elif choice == "2":
                task_id = input("Task ID: ")
                title = input("Task title: ")
                assigned = input("Assigned to (leave blank if none): ")
                priority = input("Priority (low/medium/high): ")
                tracker.add_task(task_id, title, assigned, "todo", priority)
            elif choice == "3":
                name = input("Member name: ")
                role = input("Role (default: member): ") or "member"
                tracker.add_member(name, role)
            elif choice == "4":
                output = input("Output file: ")
                tracker.export_summary(output)
            elif choice == "5":
                break

if __name__ == "__main__":
    main()