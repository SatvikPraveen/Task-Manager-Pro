# 📝 Task Manager PRO — Production-Grade Task Management System

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.10%2B-darkgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red.svg)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/Tests-20%2F20%20Passing-brightgreen.svg)](./tests/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF.svg)](https://github.com/features/actions)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-blueviolet.svg)](https://www.docker.com/)
[![Security](https://img.shields.io/badge/Security-Hardened-critical.svg)](#-security-features)
[![Type Hints](https://img.shields.io/badge/Type%20Hints-Mypy-informational.svg)](http://mypy-lang.org/)

**Task Manager PRO** is a **production-grade distributed task management system** combining a Python CLI tool with a modern REST API.  
It demonstrates mastery of full-stack development: SQLAlchemy ORM, FastAPI REST endpoints, JWT authentication, comprehensive testing, and CI/CD automation.

---

## 🚀 Major Features

### 🌐 REST API (Phase 3)

- **17 Production-Ready Endpoints** across 3 resource types
- JWT Bearer Token Authentication
- Full pagination support (skip/limit)
- Automatic OpenAPI/Swagger documentation
- CORS middleware enabled

### 🔐 Security & Authentication (Phase 2)

- bcrypt password hashing (12-round salting)
- JWT token generation and validation
- User isolation (tasks scoped by user)
- Pydantic v2 input validation
- Environment variable credential management

### 📊 Database Layer (Phase 2)

- SQLAlchemy ORM with SQLite/PostgreSQL support
- User and Task models with relationships
- Automatic timestamp tracking
- Query optimization with indexes
- Migration utilities for data portability

### ✅ Testing & Quality (Phase 4)

- 15 comprehensive API integration tests
- 4+ unit tests for core functionality
- Full test isolation with database cleanup
- 100% passing test suite (20/20 ✅)
- GitHub Actions CI/CD pipeline

### 💻 CLI Tool (Original)

- User login system
- Add/Update/Delete/List tasks
- Mark tasks completed
- Task filtering and summaries
- JSON-based storage
- Email reminders via SMTP
- CRON automation support

---

## 🛠️ Technology Stack

| Layer             | Technology                         |
| ----------------- | ---------------------------------- |
| **API Framework** | FastAPI 0.100+, Uvicorn            |
| **Database**      | SQLAlchemy 2.0+, SQLite/PostgreSQL |
| **Security**      | bcrypt, PyJWT, Pydantic v2         |
| **Testing**       | pytest, pytest-cov                 |
| **DevOps**        | GitHub Actions, Docker             |
| **CLI**           | argparse, python-dotenv            |
| **Python**        | 3.10, 3.11, 3.12                   |

---

## 🚀 Quick Start

### Via REST API (Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Start the development server
uvicorn task_manager_pro.api.main:app --reload

# Access documentation
# - Interactive Docs: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
```

### Via CLI

```bash
pip install -e .
task-manager login --username <username>
task-manager add-task --title "My Task" --due 2025-12-31
```

---

## 📚 Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - Get started with the API in 5 minutes
- **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** - Complete project overview
- **[docs/PHASE2_DATABASE_SECURITY.md](./docs/PHASE2_DATABASE_SECURITY.md)** - Database architecture
- **[docs/PHASE3_REST_API.md](./docs/PHASE3_REST_API.md)** - API reference with examples
- **[docs/PHASE4_TESTING_CI_CD.md](./docs/PHASE4_TESTING_CI_CD.md)** - Testing infrastructure

---

## 📦 Project Architecture

```
task_manager_pro/
├── api/                     # REST API Layer (Phase 3)
│   ├── main.py             # FastAPI app with 17 endpoints
│   ├── dependencies.py     # JWT auth & dependency injection
│   └── routes/
│       ├── auth.py         # Authentication endpoints
│       ├── tasks.py        # Task CRUD operations
│       └── users.py        # User management
├── storage/                # Data Persistence (Phase 2)
│   ├── database.py         # SQLAlchemy setup
│   ├── models.py           # ORM entities (User, Task)
│   ├── sql_storage.py      # SQL implementation
│   ├── json_storage.py     # Original JSON storage
│   ├── interface.py        # Storage abstraction
│   └── migration.py        # Data migration utilities
├── schemas/                # Validation (Phase 2)
│   ├── user.py            # User request/response schemas
│   └── task.py            # Task request/response schemas
├── services/               # Business Logic
│   └── task_manager.py    # Core task operations
├── models/                 # Domain Models
│   ├── task.py
│   └── user.py
├── utils/                  # Utilities
│   ├── security.py        # bcrypt, JWT, password hashing
│   ├── decorators.py
│   ├── emailer.py         # SMTP integration
│   ├── logger_context.py
│   └── session.py
├── cli.py                  # CLI entrypoint (argparse)
└── send_reminders.py       # Reminder automation

tests/                      # Test Suite (Phase 4)
├── test_api.py            # 15 API integration tests ✅
├── test_tasks.py          # Task unit tests
├── test_users.py          # User model tests
└── test_email.py          # Email utility tests

.github/workflows/          # CI/CD Pipeline (Phase 4)
└── ci-cd.yml              # GitHub Actions workflow

docs/                       # Documentation
├── PHASE2_DATABASE_SECURITY.md
├── PHASE3_REST_API.md
└── PHASE4_TESTING_CI_CD.md

.env.template              # Environment variables template
dockerfile                 # Container image
requirements.txt           # Dependencies
requirements_dev.txt       # Dev dependencies
pyproject.toml            # Project config & CLI registration
```

**Key Design Patterns:**

- **Layered Architecture:** Routes → Validation → Services → Storage → Database
- **Dependency Injection:** FastAPI dependencies for auth and storage
- **Abstract Interfaces:** StorageInterface supports multiple backends
- **Security-First:** JWT tokens, bcrypt hashing, Pydantic validation

---

## 🌐 REST API Usage

### Start the Server

```bash
uvicorn task_manager_pro.api.main:app --reload
```

Access interactive docs: http://localhost:8000/docs

### Register & Login

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password_123"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "secure_password_123"
  }'
```

### Create & Manage Tasks

```bash
TOKEN="your_jwt_token"

# Create task
curl -X POST http://localhost:8000/api/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Buy groceries",
    "description": "Milk, bread, eggs",
    "due_date": "2025-12-31",
    "priority": "high"
  }'

# List tasks (paginated)
curl -X GET "http://localhost:8000/api/tasks?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Update task
curl -X PUT http://localhost:8000/api/tasks/{task_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'

# Delete task
curl -X DELETE http://localhost:8000/api/tasks/{task_id} \
  -H "Authorization: Bearer $TOKEN"
```

For complete API examples, see [QUICKSTART.md](./QUICKSTART.md)

---

## 💻 CLI Tool Usage

### Installation

```bash
pip install -e .
```

### Commands

```bash
# Login
task-manager login --username <username>

# Add task
task-manager add-task --title <title> --desc <description> --due <yyyy-mm-dd>

# List tasks
task-manager list-tasks --filter all --verbose

# Mark completed
task-manager complete-task --id <task_id>

# Delete task
task-manager delete-task --id <task_id>

# Toggle email reminders
task-manager toggle-email-reminders

# Logout
task-manager logout
```

---

## 🧪 Testing

Install test/dev tooling (not part of the runtime dependencies):

```bash
pip install -r requirements_dev.txt
# or: pip install -e ".[test]"
```

Run the comprehensive test suite:

```bash
# All tests (20/20 passing)
pytest tests/ -v

# With coverage report
pytest tests/ --cov=task_manager_pro

# Specific test file
pytest tests/test_api.py -v

# Specific test
pytest tests/test_api.py::test_create_task_authenticated -v
```

**Test Coverage:**

- 15 API integration tests (authentication, CRUD, pagination)
- 4+ unit tests (task models, user models)
- 100% test isolation with fresh database per test
- Full authentication flow testing
- Error case and edge case coverage

---

## 🔐 Security Features

### Authentication

- JWT Bearer tokens with HS256 encryption
- 30-minute token expiration (configurable)
- Secure token refresh endpoint
- User isolation on all operations

### Password Security

- bcrypt hashing with 12-round salting
- Never stored in plain text
- Secure comparison to prevent timing attacks

### Input Validation

- Pydantic v2 schema validation on all endpoints
- Email format validation
- Username and password constraints
- Type checking and automatic coercion

### Credential Management

- All secrets use environment variables
- `.env.template` for safe configuration
- `.env` excluded from git via `.gitignore`
- Database passwords in connection strings

### Deployment Security

- Hardened `.gitignore` (databases, keys, secrets excluded)
- No sensitive data in git history
- Docker image security best practices
- GitHub Actions secrets for CI/CD

For detailed security audit, see git commit: `7f49c77`

---

## 📧 Email Reminders Setup (Optional)

### Gmail Configuration

1. Enable App Passwords: https://myaccount.google.com/apppasswords
2. Create `.env` file:

```env
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password_here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

3. Toggle reminders:

```bash
task-manager toggle-email-reminders
```

### CRON Automation (macOS/Linux)

```bash
crontab -e

# Add this line to run daily at 9:00 AM:
0 9 * * * /bin/bash -c 'source /path/to/venv/bin/activate && python /path/to/task_manager_pro/send_reminders.py'
```

---

## 🐳 Docker Usage

### Build Image

```bash
docker build -t task-manager-pro:latest .
```

### Run Container

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL="sqlite:///./tasks.db" \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  task-manager-pro:latest
```

### With PostgreSQL

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:password@postgres:5432/taskdb" \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  task-manager-pro:latest
```

---

## 📈 Development Roadmap

### Completed ✅

- **Phase 1:** Branch consolidation and analysis
- **Phase 2:** Database (SQLAlchemy) & Security (JWT, bcrypt)
- **Phase 3:** REST API with FastAPI (17 endpoints)
- **Phase 4:** Testing (20 tests) & CI/CD (GitHub Actions)

### Upcoming 🚀

- **Phase 5:** Advanced features (tags, categories, subtasks, time tracking)
- **Phase 6:** Web UI (React/Vue) & monitoring (logging, APM)

---

## 💡 Skills Demonstrated

### Backend Development

- **FastAPI & REST APIs** - 17 production endpoints
- **SQLAlchemy ORM** - Relational database modeling
- **JWT Authentication** - Secure token-based auth
- **Pydantic Validation** - Type-safe input/output
- **Python CLI** - argparse command-line tools

### Security & DevOps

- **Password Hashing** - bcrypt with salting
- **Credential Management** - Environment variables
- **Git Security** - Sensitive data exclusion
- **Docker** - Container orchestration
- **GitHub Actions** - CI/CD automation

### Testing & Quality

- **pytest Framework** - Unit and integration tests
- **Test Fixtures** - Database cleanup and isolation
- **API Testing** - Full endpoint coverage
- **Coverage Reports** - Code quality metrics

### Software Engineering

- **Layered Architecture** - Clean separation of concerns
- **Design Patterns** - Dependency injection, factories
- **SOLID Principles** - Single responsibility, interfaces
- **Code Organization** - Modular, scalable structure

---

## 🚀 Deployment

### Environment Variables Required

```env
DATABASE_URL=postgresql://user:password@localhost/taskdb
SECRET_KEY=$(openssl rand -hex 32)   # REQUIRED — app refuses to start without a real value
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=0.5
DEBUG=False
```

> ⚠️ `SECRET_KEY` has no insecure fallback. If it's missing or left as a
> placeholder, the app raises `RuntimeError` at import time instead of
> starting with a public signing key.

### Production Deployment

1. Set environment variables in hosting platform
2. Use PostgreSQL for production database
3. Set `DEBUG=False` in production
4. Enable HTTPS only
5. Use GitHub Secrets for CI/CD credentials

---

## 🧰 Development Notes

- All code includes type hints for IDE support
- Modular architecture enables easy testing and maintenance
- Abstraction via `StorageInterface` supports multiple backends
- Clean OOP design with composition and proper encapsulation
- Fully documented with docstrings and comments

## 🙋 Contributing

Feel free to fork, enhance, and submit a pull request.
To suggest features or report bugs, open an issue.

---

## 📜 License

This project is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0). See the [LICENSE](./LICENSE) file for more details.

---

## 🧠 Author

Built with ❤️ by [Satvik Praveen](https://github.com/SatvikPraveen)

---

## ⭐️ Star this repo if you found it helpful
