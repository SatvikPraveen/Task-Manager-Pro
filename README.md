# 📝 Task Manager PRO — Modular Python CLI for Tasks

**Task Manager PRO** is a fully modular, object-oriented, command-line task management tool built with Python.  
It serves as a production-grade reference project for mastering Python fundamentals and professional development best practices.

---

## 🚀 Features

- ✅ User Login System (username-based)
- 🆕 Add Tasks with Title, Description, and Due Date
- ✏️ Update Task Title/Description/Due Date
- ✔️ Mark Tasks as Completed
- 📋 List Tasks (All / Completed / Pending)
- 🔍 View Task Details with `--verbose`
- 📊 Task Summary Report with `--summary`
- 🗑️ Delete Tasks by ID
- 📧 **Hybrid Due-Date Reminders** (terminal + optional email)
- 🔄 **Toggle Email Reminders** anytime
- 🚪 Logout functionality
- 🧱 JSON-based Persistent Storage
- 🧰 Modular Architecture with Composition & Decorators
- 🧪 Unit Tested with `pytest`
- 🐍 Type Hinted and `mypy` Validated
- 🐳 Docker-Ready Structure

---

## 🛠️ Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/SatvikPraveen/task-manager-pro.git
   cd task-manager-pro

   ```

2. **Create a Virtual Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`

   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Setup `.env` for Email Reminders (Optional)**
   Create a `.env` file in the project root:

```bash
EMAIL_USER=your_email@example.com
EMAIL_PASS=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

## 📦 Project Structure

```bash
task_manager_pro/
├── main.py                    # 🎯 CLI entrypoint using argparse
├── models/                   # 📦 Data models (domain objects)
│   ├── task.py               # 📝 Task class with properties and methods
│   └── user.py               # 👤 User class (basic login representation)
├── services/                 # 🧠 Core business logic layer
│   └── task_manager.py       # 🔧 TaskManager class for handling task/user actions
├── storage/                  # 💾 Persistence layer
│   ├── interface.py          # 🧩 Abstract Base Class for storage backends
│   └── json_storage.py       # 📂 JSON-based implementation of StorageInterface
├── utils/                    # 🛠️ Utility functions and reusable components
│   ├── decorators.py         # 🌀 Logging decorator for function calls
│   ├── logger_context.py     # 📋 Context manager for logging sessions to console
│   ├── emailer.py            # 📬 Utility class for sending email reminders using SMTP
│   └── session.py            # 🔒 Session management for tracking logged-in user
├── tests/                    # 🧪 Unit tests
│   ├── test_email.py         # ✅ Tests for Sending Email Reminders
│   ├── test_tasks.py         # ✅ Tests for Task creation and behavior
│   └── test_users.py         # ✅ Tests for User login and edge cases
└── requirements.txt          # 📜 List of project dependencies
```

- **models/**: Data classes for `Task` and `User`
- **services/**: Core logic with `TaskManager`
- **storage/**: Persistence layer (JSON implementation)
- **utils/**: Decorators and Context Managers
- **tests/**: Pytest unit tests
- **main.py**: CLI entrypoint using `argparse`

---

## 💻 Usage

### ▶ Login

```bash
python main.py login --username <user-name>
```

### ➕ Add a Task

```bash
python main.py add-task --title <task-title> --desc <task-description> --due <due-date(yyyy-mm-dd)>
```

After adding a task, the system displays unique ID:

```bash
✅ Task <task-title> added.
🆔 Task ID: 7e0a3457d1ba4d57a3c9c58e12e6e7a4
```

### ✅ Complete a Task

```bash
python main.py complete-task --id <task_id>
```

### 🔄 Toggle Email Reminders

```bash
python main.py toggle-email-reminders
```

Use this to enable or disable email-based due-date reminders anytime.

### 📋 List Tasks

```bash
python main.py list-tasks --filter all --verbose --pending
```

- `--filter` options: `all`, `completed`, `pending`
- `--verbose`: show task descriptions
- `--summary`: show task count statistics
- Displays real-time due-date reminders for logged-in user (console + optional email)

### 🗑️ Delete a Task

```bash
python main.py delete-task --id <task_id>
```

### 🚪 Logout

```bash
python main.py logout
```

Ends the current session and clears the saved login.
Use this when switching users or exiting securely.

### 🔔 Optional: Send All Due Reminders

```bash
python main.py send-due-reminders
```

Sends email reminders (if enabled) to all users who have tasks due today or earlier.

---

## 🧪 Running Tests

```bash
pytest
```

Make sure you’re in the virtual environment and inside the root project directory.

---

## 🧰 Developer Notes

- All methods include **type hints**
- Decorators are used for action logging
- Custom context manager for session logging
- Clean OOP desgin with modular components
- Fully modular and extensible codebase
- Abstraction via `StorageInterface` allows for future storage backends

---

## 🐳 Docker (Optional)

To build and run the app using Docker:

```bash
docker build -t task-manager-pro .
docker run -it --rm -v "$(pwd):/app" task-manager-pro
```

---

## 🙋 Contributing

Feel free to fork, enhance, and submit a pull request.
To suggest features or report bugs, open an issue.

---

## 📜 License

This project is licensed under the MIT License.

---

## ⭐️ Star this repo if you found it helpful
