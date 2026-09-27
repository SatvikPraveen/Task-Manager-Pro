# Phase 3: REST API Implementation

## Overview

Phase 3 adds a complete REST API layer built with FastAPI, enabling web and mobile client integration while maintaining the existing CLI functionality.

### Key Features

- ✅ **FastAPI Framework** - Modern, fast, auto-documented API
- ✅ **JWT Authentication** - Secure token-based auth for all endpoints
- ✅ **Full CRUD Operations** - Complete task and user management
- ✅ **Automatic OpenAPI Documentation** - Swagger UI at `/api/docs`
- ✅ **Input Validation** - Pydantic-based request/response validation
- ✅ **Error Handling** - Comprehensive error responses
- ✅ **Pagination** - Efficient data fetching with limits
- ✅ **CORS Support** - Cross-origin requests for web clients

## Architecture

```
FastAPI Application
├── Authentication Routes (/api/auth)
│   ├── POST /register       - User registration
│   ├── POST /login          - User login (returns JWT)
│   ├── POST /refresh-token  - Token rotation
│   └── POST /logout         - Token revocation
├── Tasks Routes (/api/tasks)
│   ├── POST /              - Create task
│   ├── GET /               - List tasks (paginated)
│   ├── GET /{id}           - Get task details
│   ├── PUT /{id}           - Update task
│   └── DELETE /{id}        - Delete task
├── Users Routes (/api/users)
│   ├── GET /me             - Get user profile
│   ├── PUT /me             - Update profile
│   └── POST /me/toggle-reminders - Toggle reminders
└── Health & Info
    ├── GET /              - API info
    └── GET /health        - Health check
```

## Starting the API Server

```bash
# Development mode (with auto-reload)
python -m uvicorn task_manager_pro.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
python -m uvicorn task_manager_pro.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# View documentation
# Swagger UI: http://localhost:8000/api/docs
# ReDoc:      http://localhost:8000/api/redoc
```

## API Endpoints Reference

### Authentication

#### Register User

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "satvik",
    "password": "securepass123",
    "email": "satvik@example.com"
  }'
```

Response (201):

```json
{
  "id": "user-uuid",
  "username": "satvik",
  "email": "satvik@example.com",
  "email_reminders_enabled": true,
  "created_at": "2025-11-23T12:00:00",
  "updated_at": "2025-11-23T12:00:00"
}
```

#### Login

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "satvik",
    "password": "securepass123"
  }'
```

Response (200):

```json
{
  "user": {...},
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

#### Refresh (rotate) Token

Since 0.4.0 the token is read from the `Authorization` header (never the
query string or body, so it does not end up in access logs); since 0.5.0 the
presented token is revoked when the new one is issued.

```bash
curl -X POST "http://localhost:8000/api/auth/refresh-token" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Logout

Revokes the presented token immediately (other sessions are unaffected).

```bash
curl -X POST "http://localhost:8000/api/auth/logout" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Tasks

#### Create Task

```bash
curl -X POST "http://localhost:8000/api/tasks" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learn FastAPI",
    "description": "Read the official docs",
    "due_date": "2025-12-31",
    "priority": "high"
  }'
```

#### List Tasks

```bash
# All tasks
curl -X GET "http://localhost:8000/api/tasks" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Pending tasks only
curl -X GET "http://localhost:8000/api/tasks?completed=false" \
  -H "Authorization: Bearer YOUR_TOKEN"

# With pagination
curl -X GET "http://localhost:8000/api/tasks?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response (200):

```json
{
  "total": 5,
  "tasks": [
    {
      "id": "task-uuid",
      "title": "Learn FastAPI",
      "description": "Read docs",
      "due_date": "2025-12-31",
      "priority": "high",
      "completed": false,
      "created_at": "2025-11-23T12:00:00",
      "updated_at": "2025-11-23T12:00:00",
      "completed_at": null
    }
  ],
  "page": 1,
  "page_size": 10
}
```

#### Get Task Details

```bash
curl -X GET "http://localhost:8000/api/tasks/task-uuid" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Update Task

```bash
curl -X PUT "http://localhost:8000/api/tasks/task-uuid" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "completed": true,
    "priority": "medium"
  }'
```

#### Delete Task

```bash
curl -X DELETE "http://localhost:8000/api/tasks/task-uuid" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Users

#### Get Current User

```bash
curl -X GET "http://localhost:8000/api/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Update Profile

```bash
curl -X PUT "http://localhost:8000/api/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newemail@example.com",
    "email_reminders_enabled": false
  }'
```

#### Toggle Email Reminders

```bash
curl -X POST "http://localhost:8000/api/users/me/toggle-reminders" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## File Structure

```
task_manager_pro/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization
│   ├── dependencies.py      # JWT auth dependencies
│   └── routes/
│       ├── __init__.py
│       ├── auth.py          # Authentication endpoints
│       ├── tasks.py         # Task CRUD endpoints
│       └── users.py         # User management endpoints
├── schemas/                 # Pydantic models (Phase 2)
├── storage/                 # Database layer (Phase 2)
└── utils/
    ├── security.py          # JWT and bcrypt (Phase 2)
    └── ...
```

## Security Features

### JWT Authentication

- **Token Type**: HS256 (symmetric)
- **Expiration**: 30 minutes (configurable)
- **Issuer**: Configured via `SECRET_KEY` env var
- **Bearer Token Format**: `Authorization: Bearer <token>`

### Password Security

- Hashed with bcrypt (12 rounds)
- Never stored or transmitted in plain text
- Validated on login

### CORS

- Configurable origins via `CORS_ORIGINS` env var
- Credentials allowed
- All methods and headers allowed

## Error Handling

All errors return proper HTTP status codes:

```json
{
  "detail": "Invalid username or password"
}
```

### Common Status Codes

- `200` - Success
- `201` - Created
- `204` - No Content (deleted)
- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid credentials/token)
- `404` - Not Found
- `500` - Server Error

## Testing the API

### Using httpx (Python)

```python
import httpx

async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
    # Register
    resp = await client.post("/api/auth/register", json={
        "username": "test",
        "password": "pass123",
        "email": "test@example.com"
    })
    print(resp.json())

    # Login
    resp = await client.post("/api/auth/login", json={
        "username": "test",
        "password": "pass123"
    })
    token = resp.json()["access_token"]

    # Create task
    resp = await client.post("/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test",
            "description": "Test task",
            "due_date": "2025-12-31"
        }
    )
    print(resp.json())
```

### Using Pytest

See `tests/test_api.py` for comprehensive test examples.

## Performance Considerations

- **Pagination**: Limited to 100 items per request
- **Database Indexes**: On user_id, due_date, completed
- **Connection Pooling**: Automatic via SQLAlchemy
- **Async Support**: FastAPI handles async naturally

## Configuration

### Environment Variables

```bash
# API
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Security (from Phase 2)
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database (from Phase 2)
DATABASE_URL=sqlite:///./tasks.db
SQL_ECHO=false
```

## Next Steps (Phase 4)

- Add GitHub Actions CI/CD pipeline
- Create comprehensive integration tests
- Add coverage reporting
- Load testing and performance optimization
- Database connection pooling configuration

## Troubleshooting

### Port Already in Use?

```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use different port
uvicorn task_manager_pro.api.main:app --port 8001
```

### Token Expired?

Call `/api/auth/refresh-token` with the current token in the `Authorization` header to get a new one (the old one is revoked).

### CORS Errors?

Check `CORS_ORIGINS` env var includes your frontend URL.

### Database Locked?

SQLite doesn't support concurrent writes. For production, switch to PostgreSQL.
