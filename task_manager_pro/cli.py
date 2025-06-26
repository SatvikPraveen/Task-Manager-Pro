import argparse
from services.task_manager import TaskManager
from storage.json_storage import JSONStorage

def main():
    parser = argparse.ArgumentParser(description="📝 Task Manager PRO CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add Task
    add_task_parser = subparsers.add_parser("add-task", help="Add a new task")
    add_task_parser.add_argument("--title", required=True)
    add_task_parser.add_argument("--desc", required=True)
    add_task_parser.add_argument("--due", required=True)

    # Update Task
    update_task_parser = subparsers.add_parser("update-task", help="Update task details")
    update_task_parser.add_argument("--id", required=True, help="Task ID to update")
    update_task_parser.add_argument("--title", help="New title (optional)")
    update_task_parser.add_argument("--desc", help="New description (optional)")
    update_task_parser.add_argument("--due", help="New due date (YYYY-MM-DD, optional)")

    # Complete Task
    complete_task_parser = subparsers.add_parser("complete-task", help="Mark task as completed")
    complete_task_parser.add_argument("--id", required=True)

    # List Tasks
    list_task_parser = subparsers.add_parser("list-tasks", help="List tasks")
    list_task_parser.add_argument("--filter", choices=["all", "completed", "pending"], default="all")
    list_task_parser.add_argument("--verbose", action="store_true", help="Show detailed task info")
    list_task_parser.add_argument("--summary", action="store_true", help="Show task summary (total/completed/pending)")

    # Delete Task
    delete_task_parser = subparsers.add_parser("delete-task", help="Delete task by ID")
    delete_task_parser.add_argument("--id", required=True)

    # Login (optional for future user features)
    login_parser = subparsers.add_parser("login", help="Login as user")
    login_parser.add_argument("--username", required=True)
    login_parser.add_argument("--email", help="Optional email for reminders")

    # Send Reminders Manually
    send_reminders_parser = subparsers.add_parser("send-reminders", help="Manually send email reminders (if enabled)")

    # Toggle Email Reminders
    toggle_email_parser = subparsers.add_parser("toggle-email-reminders", help="Toggle email reminder preference")


    # Logout
    logout_parser = subparsers.add_parser("logout", help="Log out current user")

    args = parser.parse_args()
    storage = JSONStorage()
    manager = TaskManager(storage)

    if args.command == "add-task":
        manager.add_task(args.title, args.desc, args.due)

    elif args.command == "complete-task":
        manager.mark_task_complete(args.id)

    elif args.command == "list-tasks":
        manager.list_tasks(args.filter, verbose=args.verbose, summary=args.summary)

    elif args.command == "delete-task":
        manager.delete_task(args.id)

    elif args.command == "login":
        manager.login(args.username, args.email)
    
    elif args.command == "logout":
        manager.logout()
    
    elif args.command == "update-task":
        manager.update_task(args.id, args.title, args.desc, args.due)
    
    elif args.command == "send-reminders":
        manager.send_due_reminders()
    
    elif args.command == "toggle-email-reminders":
        manager.toggle_email_reminders()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()