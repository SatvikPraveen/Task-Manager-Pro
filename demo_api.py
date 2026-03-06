#!/usr/bin/env python3
"""
🚀 Task Manager PRO - API Demo Script
Demonstrates all major API features with live testing
"""

import requests
import json
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import time

console = Console()
BASE_URL = "http://localhost:8000"

def print_response(title, response):
    """Pretty print API response"""
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print(f"Status: [green]{response.status_code}[/green]")
    try:
        console.print(Panel(json.dumps(response.json(), indent=2), title="Response"))
    except:
        console.print(response.text)

def main():
    console.print(Panel.fit(
        "🎯 Task Manager PRO - API Demo\n"
        "Testing all major features...",
        border_style="bold green"
    ))
    
    # 1. Health Check
    console.print("\n[bold yellow]═══ 1. Health Check ═══[/bold yellow]")
    response = requests.get(f"{BASE_URL}/health")
    print_response("Health Check", response)
    time.sleep(1)
    
    # 2. Register User
    console.print("\n[bold yellow]═══ 2. Register New User ═══[/bold yellow]")
    user_data = {
        "username": "demo_user",
        "email": "demo@taskmanager.com",
        "password": "SecurePass123!"
    }
    response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
    print_response("User Registration", response)
    time.sleep(1)
    
    # 3. Login
    console.print("\n[bold yellow]═══ 3. Login & Get Token ═══[/bold yellow]")
    login_data = {
        "username": "demo_user",
        "password": "SecurePass123!"
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    print_response("User Login", response)
    
    if response.status_code != 200:
        console.print("[red]Login failed! Stopping demo.[/red]")
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    console.print(f"\n[green]✓ Token acquired: {token[:30]}...[/green]")
    time.sleep(1)
    
    # 4. Create Multiple Tasks
    console.print("\n[bold yellow]═══ 4. Create Tasks ═══[/bold yellow]")
    tasks = [
        {
            "title": "Complete API Documentation",
            "description": "Write comprehensive API docs with examples",
            "due_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "priority": "high"
        },
        {
            "title": "Code Review",
            "description": "Review pull requests from team",
            "due_date": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
            "priority": "medium"
        },
        {
            "title": "Deploy to Production",
            "description": "Deploy Task Manager PRO v0.3.0",
            "due_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "priority": "high"
        }
    ]
    
    task_ids = []
    for task in tasks:
        response = requests.post(f"{BASE_URL}/api/tasks", json=task, headers=headers)
        if response.status_code == 201:
            task_id = response.json()["id"]
            task_ids.append(task_id)
            console.print(f"[green]✓ Created task: {task['title']} (ID: {task_id})[/green]")
        else:
            console.print(f"[red]✗ Failed to create task: {task['title']}[/red]")
        time.sleep(0.5)
    
    # 5. List All Tasks
    console.print("\n[bold yellow]═══ 5. List All Tasks ═══[/bold yellow]")
    response = requests.get(f"{BASE_URL}/api/tasks", headers=headers)
    
    if response.status_code == 200:
        tasks_list = response.json()
        
        table = Table(title="📋 Your Tasks")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Priority", style="yellow")
        table.add_column("Due Date", style="magenta")
        table.add_column("Status", style="blue")
        
        for task in tasks_list:
            status = "✅ Done" if task["completed"] else "⏳ Pending"
            table.add_row(
                str(task["id"]),
                task["title"],
                task.get("priority", "N/A"),
                task["due_date"],
                status
            )
        
        console.print(table)
    time.sleep(1)
    
    # 6. Get Single Task
    if task_ids:
        console.print("\n[bold yellow]═══ 6. Get Task Details ═══[/bold yellow]")
        response = requests.get(f"{BASE_URL}/api/tasks/{task_ids[0]}", headers=headers)
        print_response(f"Task Details (ID: {task_ids[0]})", response)
        time.sleep(1)
    
    # 7. Update Task
    if task_ids:
        console.print("\n[bold yellow]═══ 7. Update Task ═══[/bold yellow]")
        update_data = {
            "title": "Complete API Documentation (UPDATED)",
            "completed": True
        }
        response = requests.put(
            f"{BASE_URL}/api/tasks/{task_ids[0]}", 
            json=update_data, 
            headers=headers
        )
        print_response("Task Update", response)
        time.sleep(1)
    
    # 8. Get Current User
    console.print("\n[bold yellow]═══ 8. Get Current User Info ═══[/bold yellow]")
    response = requests.get(f"{BASE_URL}/api/users/me", headers=headers)
    print_response("Current User", response)
    time.sleep(1)
    
    # 9. Toggle Email Reminders
    console.print("\n[bold yellow]═══ 9. Toggle Email Reminders ═══[/bold yellow]")
    response = requests.post(f"{BASE_URL}/api/users/me/toggle-reminders", headers=headers)
    print_response("Toggle Email Reminders", response)
    time.sleep(1)
    
    # 10. Pagination Test
    console.print("\n[bold yellow]═══ 10. Test Pagination ═══[/bold yellow]")
    response = requests.get(f"{BASE_URL}/api/tasks?skip=0&limit=2", headers=headers)
    print_response("Paginated Tasks (limit=2)", response)
    time.sleep(1)
    
    # 11. Delete Task
    if len(task_ids) > 1:
        console.print("\n[bold yellow]═══ 11. Delete Task ═══[/bold yellow]")
        delete_id = task_ids[-1]
        response = requests.delete(f"{BASE_URL}/api/tasks/{delete_id}", headers=headers)
        print_response(f"Delete Task (ID: {delete_id})", response)
        time.sleep(1)
    
    # 12. Try Unauthorized Access
    console.print("\n[bold yellow]═══ 12. Test Unauthorized Access ═══[/bold yellow]")
    response = requests.get(f"{BASE_URL}/api/tasks")  # No token
    print_response("Unauthorized Access (no token)", response)
    time.sleep(1)
    
    # Summary
    console.print("\n")
    console.print(Panel.fit(
        "✅ Demo Complete!\n\n"
        "📚 Next Steps:\n"
        "  • Visit http://localhost:8000/api/docs for interactive docs\n"
        "  • Visit http://localhost:8000/api/redoc for alternative docs\n"
        "  • Check out the test suite: pytest tests/ -v\n"
        "  • Review README.md for more examples",
        border_style="bold green",
        title="🎉 Success"
    ))

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        console.print("\n[bold red]❌ Error: Could not connect to API server![/bold red]")
        console.print("\n[yellow]Make sure the server is running:[/yellow]")
        console.print("  uvicorn task_manager_pro.api.main:app --reload\n")
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
