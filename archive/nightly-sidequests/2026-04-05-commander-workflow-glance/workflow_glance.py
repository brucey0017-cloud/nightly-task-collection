#!/usr/bin/env python3
"""
Quick Workflow Status Tool - Simple self-contained workflow visibility
"""

import json
import os
import sys
from datetime import datetime, timezone

def check_openclaw_processes():
    """Check for running OpenClaw-related processes"""
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        processes = result.stdout
        
        openclaw_processes = []
        for line in processes.split('\n'):
            if 'openclaw' in line.lower() and 'python' in line.lower():
                openclaw_processes.append(line.strip())
        
        return openclaw_processes
    except Exception as e:
        return [f"Error checking processes: {str(e)}"]

def check_workspace_files():
    """Check key workspace files for recent activity"""
    workspace_path = "/root/.openclaw/workspace-commander"
    if not os.path.exists(workspace_path):
        return []
    
    recent_files = []
    try:
        for root, dirs, files in os.walk(workspace_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    mod_time = os.path.getmtime(file_path)
                    # Files modified in last hour
                    if mod_time > datetime.now(timezone.utc).timestamp() - 3600:
                        relative_path = os.path.relpath(file_path, workspace_path)
                        recent_files.append(relative_path)
                except:
                    continue
    except Exception as e:
        recent_files.append(f"Error scanning workspace: {str(e)}")
    
    return recent_files[:10]  # Limit to 10 most recent files

def generate_report():
    """Generate workflow status report"""
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"📊 Workflow Status Report - {timestamp}")
    print("=" * 60)
    
    # Check running processes
    processes = check_openclaw_processes()
    print("\n🔥 Active Processes:")
    print("-" * 30)
    if processes:
        for proc in processes[:3]:  # Show max 3 processes
            print(f"  • {proc[:80]}...")
    else:
        print("  • No active OpenClaw processes detected")
    
    # Check workspace activity
    recent_files = check_workspace_files()
    print("\n📁 Recent Workspace Activity (last hour):")
    print("-" * 30)
    if recent_files:
        for file in recent_files[:5]:  # Show max 5 files
            print(f"  • {file}")
    else:
        print("  • No recent file activity detected")
    
    print("\n📋 Status Summary:")
    print("-" * 30)
    print("  ✅ Zero-dependency Python script")
    print("  ✅ Self-contained workflow monitoring")
    print("  ✅ Quick team coordination aid")
    print("  ✅ No external API calls required")
    
    print("\n🔧 Tool Information:")
    print("-" * 30)
    print("  Name: Workflow Status Tool")
    print("  Purpose: Quick visibility into current development activity")
    print("  Location: /root/.openclaw/workspace/nightly-sidequests/2026-04-05-commander-workflow-glance/")
    print("  Dependencies: None (uses built-in Python modules)")

if __name__ == "__main__":
    import subprocess
    generate_report()