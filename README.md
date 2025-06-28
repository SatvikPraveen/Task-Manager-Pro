# 📝 Task Manager PRO — Modular Python CLI for Tasks  
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Issues](https://img.shields.io/github/issues/SatvikPraveen/task-manager-pro)](https://github.com/SatvikPraveen/task-manager-pro/issues)


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
├── __init__.py
├── cli.py                   # 🎯 CLI entrypoint (registered as `task-manager`)
├── send_reminders.py        # 🔔 Standalone script for daily reminder emails
├── models/                  # 📦 Task and User data models
│   ├── __init__.py
│   ├── task.py
│   └── user.py
├── services/                # 🧠 Core logic — TaskManager class
│   ├── __init__.py
│   └── task_manager.py
├── storage/                 # 💾 JSON-based persistent storage
│   ├── __init__.py
│   ├── interface.py
│   └── json_storage.py
├── utils/                   # 🛠️ Utilities for decorators, email, session, etc.
│   ├── __init__.py
│   ├── decorators.py
│   ├── emailer.py
│   ├── logger_context.py
│   └── session.py
tests/
├── test_email.py
├── test_tasks.py
└── test_users.py
requirements.txt
pyproject.toml
README.md
.env.template
```

🧱 The project uses a modular, package-based layout to support clean imports, scalability, and production readiness.

- **models/**: Data classes for `Task` and `User`
- **services/**: Core logic with `TaskManager`
- **storage/**: Persistence layer (JSON implementation)
- **utils/**: Decorators and Context Managers
- **tests/**: Pytest unit tests
- **main.py**: CLI entrypoint using `argparse`

---

## 💻 CLI Usage (via task-manager)

Once installed with:

```bash
pip install -e .
```

You can access the app using the command:

```bash
task-manager
```

### ▶ Login

```bash
task-manager login --username <user-name>
```

### ➕ Add a Task

```bash
task-manager add-task --title <task-title> --desc <task-description> --due <due-date(yyyy-mm-dd)>
```

After adding a task, the system displays unique ID:

```bash
✅ Task <task-title> added.
🆔 Task ID: 7e0a3457d1ba4d57a3c9c58e12e6e7a4
```

### ✅ Complete a Task

```bash
task-manager complete-task --id <task_id>
```

### 🔄 Toggle Email Reminders

```bash
task-manager toggle-email-reminders
```

Use this to enable or disable email-based due-date reminders anytime.

### 📋 List Tasks

```bash
task-manager list-tasks --filter all --verbose --pending
```

- `--filter` options: `all`, `completed`, `pending`
- `--verbose`: show task descriptions
- `--summary`: show task count statistics
- Displays real-time due-date reminders for logged-in user (console + optional email)

### 🗑️ Delete a Task

```bash
task-manager delete-task --id <task_id>
```

### 🚪 Logout

```bash
task-manager logout
```

Ends the current session and clears the saved login.
Use this when switching users or exiting securely.

### 🔔 Optional: Send All Due Reminders

```bash
task-manager send-due-reminders
```

Sends email reminders (if enabled) to all users who have tasks due today or earlier.

---

## 🧪 Running Tests

```bash
pytest
```

Make sure you’re in the virtual environment and inside the root project directory.

---

## 🔐 Enabling Email Reminders (Gmail Setup)

To use **email-based reminders**, you'll need to:

1. **Enable App Passwords** in your Google Account:

   - Visit: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - Select `Mail` as the app and `Other` → enter `TaskManagerPRO`
   - Copy the 16-character app password.

2. **Create a `.env` file** in your project root:

   ```env
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASS=your_app_password_here
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=465
   ```

   Optionally, you can start by copying the provided `.env.template`:

   ```bash
   cp .env.template .env
   ```

   > ✅ `EMAIL_PASS` should be your **App Password**, _not_ your actual Gmail password.

3. The app automatically loads `.env` values and uses them when sending reminders.

4. Confirm `.gitignore` already contains:

   ```bash
   .env
   ```

5. You can toggle email reminders at any time using:

```bash
python main.py toggle-email-reminders
```

---

## ⏰ Scheduled Email Reminders (CRON)

You can automate daily due-date email reminders using `cron`.

### ✅ Step 1: Environment Setup

Ensure your `.env` file in the project root is properly configured:

```env
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password  # App password, not your Gmail login
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

Confirm all dependencies are installed:

```bash
pip install -r requirements.txt
```

---

### 🛠 Step 2: Add CRON Job (macOS/Linux)

1. Open the crontab editor:

   ```bash
   crontab -e
   ```

2. Add this line to run the reminder script daily at 9:00 AM:

   ```cron
   0 9 * * * /bin/bash -c 'source /path/to/venv/bin/activate && python /path/to/project/task_manager_pro/send_reminders.py >> /path/to/project/logs/cron.log 2>&1'
   ```

   > 🔁 Replace the paths with your actual project and virtual environment location.

   Make sure your `.env` is set up and `.gitignore` excludes it.

3. Save and exit (press `ESC`, then type `:wq` and hit `Enter`).

---

### 📁 Notes

- **Logs** are saved to: `logs/cron.log`
- **Script used**: `task_manager_pro/send_reminders.py`
- The cron job respects the `.env` config and only sends reminders if due tasks exist.

---

### 🧹 Disable CRON Job

To stop or edit the job:

```bash
crontab -e
```

Delete or update the corresponding task.

---

## 🧰 Developer Notes

- All methods include **type hints**
- Decorators are used for action logging
- Custom context manager for session logging
- Clean OOP desgin with modular components
- Fully modular and extensible codebase
- Abstraction via `StorageInterface` allows for future storage backends

---

## 🐳 Docker Usage

### 🧱 Build the Docker Image

```bash
docker build -t task-manager-pro .
```

### ▶ Run a Task Command

```bash
docker run -it task-manager-pro login --username satvik
docker run -it task-manager-pro add-task --title "Read book" --desc "30 pages" --due 2025-06-26
```

> 📝 `tasks.json` is internal to the container and intentionally not volume-mounted.
> For persistence outside Docker, consider extending this with bind mounts.

---

## 🙋 Contributing

Feel free to fork, enhance, and submit a pull request.
To suggest features or report bugs, open an issue.

---

## 📜 License

This project is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

---

## 🧠 Author

Built with ❤️ by [Satvik Praveen](https://github.com/SatvikPraveen)

---

## ⭐️ Star this repo if you found it helpful
