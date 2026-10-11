"""
docs/PHASE2_DATABASE_SECURITY.md

Documentation for Phase 2: Database & Security Layer Implementation
"""

# Phase 2: Database & Security Layer

## Overview

Phase 2 implements a production-grade database layer and security hardening:

- **SQLAlchemy ORM** with SQLite (PostgreSQL ready)
- **Password hashing** with bcrypt
- **JWT authentication** for API integration
- **Pydantic validation** for all inputs
- **Migration tool** for JSON → SQL conversion

## New Dependencies

```
sqlalchemy==2.0+       # SQL toolkit and ORM
alembic==1.13+         # Database migrations
bcrypt==4.1+           # Password hashing
pyjwt==2.8+            # JWT tokens
pydantic==2.0+         # Data validation
pydantic-settings==2.0+# Settings management
```

## Architecture Changes

### Before (Phase 1)

```
CLI → JSON Storage (tasks.json)
     └─ Plain text passwords (if any)
     └─ No validation
     └─ Single file, not scalable
```

### After (Phase 2)

```
CLI ──┐
      ├─→ TaskManager Service
      │
REST API (Phase 3)  ──→ Pydantic Schemas (Validation)
      │                 │
      └─────────────────┴→ SQLStorage
                         ├─ SQLAlchemy Models
                         ├─ bcrypt Hashing
                         └─ tasks.db (SQLite)
```

## File Structure

### New Files Created

```
task_manager_pro/
├── storage/
│   ├── database.py      # SQLAlchemy engine, session, Base
│   ├── models.py        # UserModel, TaskModel (ORM)
│   └── sql_storage.py   # SQLStorage implementation
├── schemas/
│   ├── __init__.py
│   ├── user.py          # UserRegister, UserLogin, UserResponse
│   └── task.py          # TaskCreate, TaskUpdate, TaskResponse
└── utils/
    ├── security.py      # hash_password, create_access_token
    └── migration.py     # JSON → SQL migration tool
```

## Usage Guide

### 1. Setup Environment

```bash
# Copy .env template
cp .env.template .env

# Edit .env with your settings (optional - defaults work)
```

### 2. Migrate Existing Data (Optional)

If you have existing data in `tasks.json`:

```bash
# Dry run (preview what would migrate)
python -m task_manager_pro.utils.migration tasks.json --dry-run

# Actual migration
python -m task_manager_pro.utils.migration tasks.json
```

Migration creates:

- A user account per JSON user, each with a random one-time password that is
  printed once at the end of the run; hand it over and have the user set a new
  one with `PUT /api/users/me/password`
- Those users' tasks, keeping `created_at`

Usernames that already exist in the database are skipped together with their
JSON tasks, so tasks never attach to someone else's account and re-running the
migration does not duplicate anything.
- Database: `tasks.db`

### 3. Use Updated CLI

The CLI now works with the database instead of JSON:

```bash
task-manager login --username satvik
task-manager add-task --title "Learn SQLAlchemy" --desc "..." --due 2025-12-31
task-manager list-tasks --filter pending --verbose
```

## Security Features

### Password Hashing

```python
from task_manager_pro.utils.security import hash_password, verify_password

# Hashing (one-way)
hashed = hash_password("my_password")

# Verification
is_valid = verify_password("my_password", hashed)  # True
is_valid = verify_password("wrong_password", hashed)  # False
```

Uses **bcrypt** with 12 salt rounds:

- ✅ Slow by design (resists brute force)
- ✅ Salted (prevents rainbow tables)
- ✅ Production-ready

### JWT Tokens

```python
from task_manager_pro.utils.security import create_access_token, decode_token

# Create token (Phase 3 REST API)
token = create_access_token({"sub": "user_id"})

# Verify token
payload = decode_token(token)
if payload:
    user_id = payload.get("sub")
```

### Input Validation

All inputs validated via Pydantic:

```python
from task_manager_pro.schemas import TaskCreate

# Valid
task = TaskCreate(
    title="Learn Pydantic",
    description="Read docs",
    due_date="2025-12-31",
    priority="high"
)

# Invalid - raises ValidationError
task = TaskCreate(title="")  # Too short
task = TaskCreate(due_date="31-12-2025")  # Wrong format
```

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    email_reminders_enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME,
    updated_at DATETIME,
    INDEX idx_username (username),
    INDEX idx_email (email)
);
```

### Tasks Table

```sql
CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    due_date DATETIME NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    priority VARCHAR(20) DEFAULT 'medium',
    created_at DATETIME,
    updated_at DATETIME,
    completed_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_due_date (due_date),
    INDEX idx_completed (completed)
);
```

## Transitioning to SQL Storage

### Update TaskManager (Coming in Phase 3)

Currently, `TaskManager` still uses JSON storage. To fully transition:

```python
# Phase 2 (NOW): Both available
from task_manager_pro.storage.json_storage import JSONStorage
from task_manager_pro.storage.sql_storage import SQLStorage

# Phase 3: Update CLI to use SQLStorage
manager = TaskManager(SQLStorage())  # Instead of JSONStorage()
```

### Why Two Implementations?

- **JSONStorage**: Backwards compatible, used by existing CLI
- **SQLStorage**: New, for REST API and advanced features
- Transition happens gradually in Phase 3

## Database Operations

### User Operations

```python
from task_manager_pro.storage.sql_storage import SQLStorage

storage = SQLStorage()

# Create user
user = storage.create_user("satvik", "password123", email="satvik@example.com")

# Get user
user = storage.get_user_by_username("satvik")

# Verify password
is_valid = storage.verify_user_password("satvik", "password123")

# Update user
storage.update_user(user.id, email="newemail@example.com")
```

### Task Operations

```python
# Create task
task = storage.create_task(
    user_id=user.id,
    title="Learn SQLAlchemy",
    description="Complete tutorial",
    due_date="2025-12-31",
    priority="high"
)

# Get user tasks
tasks = storage.get_user_tasks(user.id, completed=False)

# Update task
storage.update_task(task.id, completed=True)

# Get due tasks
due_tasks = storage.get_due_tasks()  # Today and earlier

# Delete task
storage.delete_task(task.id)
```

## Configuration

### Environment Variables

```bash
# Database (default: SQLite in current directory)
DATABASE_URL=sqlite:///./tasks.db

# Enable query logging (for debugging)
SQL_ECHO=false

# JWT Security
SECRET_KEY=your-secret-key  # Generate: openssl rand -hex 32
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email (existing)
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
```

## Next Steps (Phase 3)

- Create FastAPI REST API endpoints
- Implement JWT authentication middleware
- Update CLI to use SQLStorage
- Add API documentation (Swagger/OpenAPI)
- Support for PostgreSQL, MySQL

## Troubleshooting

### Import Errors?

Install dependencies:

```bash
pip install -r requirements.txt
```

### Database Locked?

SQLite locks on concurrent writes. For production, switch to PostgreSQL:

```bash
# Install
pip install psycopg2-binary

# Update .env
DATABASE_URL=postgresql://user:password@localhost/taskmanager
```

### Password Verification Fails?

Ensure password was hashed with `hash_password()`:

```python
# ❌ Wrong
user.password_hash = "my_password"  # Plain text!

# ✅ Correct
from task_manager_pro.utils.security import hash_password
user.password_hash = hash_password("my_password")
```

## Testing

Tests for Phase 2:

```bash
# Run all tests with coverage
pytest --cov=task_manager_pro

# Test specific module
pytest tests/test_security.py -v
pytest tests/test_storage.py -v
```

See `tests/` for examples.
