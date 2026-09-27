# Phase 4: Testing & CI/CD Pipeline

## Overview

Phase 4 establishes a production-grade testing framework and automated CI/CD pipeline using GitHub Actions.

### Key Components

- ✅ **Comprehensive Test Suite** - Unit and integration tests for all modules
- ✅ **GitHub Actions Workflow** - Automated testing on push and PR
- ✅ **Coverage Reporting** - Codecov integration for coverage tracking
- ✅ **Multi-Version Testing** - Python 3.10, 3.11, 3.12 support
- ✅ **Security Scanning** - Bandit security analysis
- ✅ **Docker Build** - Automated Docker image building
- ✅ **Distribution Packaging** - Build wheel and sdist packages

## Test Structure

```
tests/
├── conftest.py               # Pins env (in-memory DB, bcrypt cost 4, no rate limit) before app import
├── helpers.py                # register/login/create_task helpers for API tests
├── test_api.py               # Original REST API integration tests
├── test_api_tasks_query.py   # Filtering, sorting, paging metadata, isolation, refresh
├── test_api_analytics.py     # /api/tasks/stats and /api/tasks/next (incl. calibration)
├── test_analytics.py         # Hypothesis property tests for the urgency model & statistics
├── test_calibration.py       # Property tests for per-user calibration
├── test_storage.py           # SQLStorage against a private in-memory engine
├── test_middleware.py        # Rate limiter (fake clock), request ID, security headers, metrics
├── test_token_revocation.py  # Denylist, Redis limiter (when REDIS_URL set), logout/rotation
├── test_cli_service.py       # JSON-backed CLI service, session, decorators, LoggerContext
├── test_email.py             # SMTP helper with a fake transport
├── test_tasks.py             # Task domain model
└── test_users.py             # User domain model
```

The CI matrix runs Python 3.10–3.13 on SQLite and 3.12 on PostgreSQL 16 +
Redis 7, enforces an 80 % coverage floor, and gates on Ruff, mypy, Bandit,
pip-audit, `alembic check` and a Docker smoke test.

## Running Tests Locally

### All Tests

```bash
# Run all tests with coverage
pytest --cov=task_manager_pro

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::test_create_task_authenticated -v
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=task_manager_pro --cov-report=html
# Open htmlcov/index.html in browser

# Terminal coverage report
pytest --cov=task_manager_pro --cov-report=term-missing
```

### Test Database

Tests use SQLite test database that's automatically cleaned up:

```python
@pytest.fixture
def storage():
    """Provides clean test database."""
    os.environ["DATABASE_URL"] = "sqlite:///./test_tasks.db"
    # ...
    # Cleanup after test
    if os.path.exists("test_tasks.db"):
        os.remove("test_tasks.db")
```

## GitHub Actions Workflow

### Trigger Events

- **Push to main/develop** - Full test suite runs
- **Pull Requests** - All checks required before merge
- **On demand** - Manual trigger via Actions tab

### Workflow Jobs

#### 1. Test Job

Runs on Ubuntu with Python 3.10, 3.11, 3.12:

```yaml
- Install dependencies
- Run mypy type checking
- Run pytest test suite
- Generate coverage reports
- Upload to Codecov
```

**Status Badges:**

```markdown
![Tests](https://github.com/YOUR_USER/Task-Manager-Pro/workflows/CI%2FCD%20Pipeline/badge.svg)
```

#### 2. Build Job

Triggered after tests pass on main branch:

```yaml
- Build wheel and source distributions
- Run twine check for distribution validity
- Upload build artifacts
```

#### 3. Security Scan

Bandit security analysis on every push:

```yaml
- Scan for common security issues
- Report high/critical findings
```

#### 4. Docker Build

Build Docker image after successful tests:

```yaml
- Set up Docker Buildx
- Build multi-arch image
- Tag as latest
```

## Test Coverage

### Current Coverage

Target: >80% coverage

```
task_manager_pro/
  models/        - 95% (Task, User models)
  storage/       - 90% (SQLStorage implementation)
  utils/         - 88% (Security functions)
  api/           - 85% (FastAPI endpoints)
  services/      - 92% (TaskManager)
  schemas/       - 98% (Pydantic models)
```

### Improving Coverage

1. **Run coverage report:**

   ```bash
   pytest --cov=task_manager_pro --cov-report=term-missing
   ```

2. **Identify uncovered lines:**

   ```bash
   # Lines not covered marked with "!"
   # Branch coverage shown separately
   ```

3. **Add tests for gaps:**
   ```python
   # tests/test_module.py
   def test_edge_case():
       """Test specific scenario not covered."""
   ```

## Test Examples

### Authentication Tests

```python
@pytest.mark.asyncio
async def test_login_valid_credentials(client):
    """Test login with valid credentials."""
    # Register
    await client.post("/api/auth/register", json={...})

    # Login
    response = await client.post("/api/auth/login", json={...})
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Task CRUD Tests

```python
@pytest.mark.asyncio
async def test_create_task_authenticated(client):
    """Test creating a task as authenticated user."""
    # Setup with auth
    token = get_token(client)

    # Create task
    response = await client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={...}
    )
    assert response.status_code == 201
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_workflow(client):
    """Test complete user workflow."""
    # 1. Register
    # 2. Login
    # 3. Create tasks
    # 4. Update tasks
    # 5. Delete tasks
    # 6. Verify state
```

## Continuous Integration Features

### Branch Protection

Configure in GitHub Settings → Branches:

```
✓ Require status checks to pass before merging
✓ Require code reviews
✓ Require branches to be up to date
✓ Require conversation resolution
```

### Status Checks Required

- `test` - Python 3.10, 3.11, 3.12 must all pass
- `security-scan` - No critical issues
- Code review from maintainer

### Workflow Badge

Add to README.md:

```markdown
![CI/CD](https://github.com/SatvikPraveen/Task-Manager-Pro/workflows/CI%2FCD%20Pipeline/badge.svg)
[![codecov](https://codecov.io/gh/SatvikPraveen/Task-Manager-Pro/branch/main/graph/badge.svg)](https://codecov.io/gh/SatvikPraveen/Task-Manager-Pro)
```

## Performance Benchmarks

### Test Execution Time

```
Total: ~45 seconds (on GitHub Actions)
  - Test setup: 5s
  - Unit tests: 15s
  - Integration tests: 20s
  - Coverage report: 5s
```

### Coverage Goals

- **Unit Tests**: >90%
- **Integration Tests**: >85%
- **Overall**: >85%

## Debugging Failed Tests

### Local Reproduction

```bash
# Get exact test name from CI failure
pytest -k "test_create_task_authenticated" -vvs

# Add breakpoint
def test_something():
    import pdb; pdb.set_trace()
    # ... code
```

### Common Failures

**ImportError**: Missing dependency

```bash
pip install -r requirements.txt
```

**Database locked**: SQLite concurrency

```bash
# Already handled in tests with cleanup
```

**Async errors**: Event loop issues

```bash
# Mark async tests correctly
@pytest.mark.asyncio
async def test_something():
    pass
```

## Deployment Integration

### After Tests Pass

1. **On Pull Request**: Checks must pass
2. **On Merge to Main**:
   - Build packages
   - Build Docker image
   - Deploy to staging (manual)
3. **On Release Tag**:
   - Publish to PyPI
   - Push to Docker Hub

## Environment Variables for CI

Add to GitHub Secrets (Settings → Secrets):

```
SECRET_KEY          - JWT signing key
DATABASE_URL        - Test database (optional)
CODECOV_TOKEN       - For codecov.io integration
DOCKER_USERNAME     - Docker Hub username
DOCKER_PASSWORD     - Docker Hub password
PYPI_API_TOKEN      - PyPI publishing token
```

## Monitoring & Alerts

### GitHub Notifications

- Workflow failures email you immediately
- PR checks prevent merge on failure
- Discussion option in workflow runs

### Codecov Integration

- Coverage reports in PR comments
- Coverage badges in README
- Trend tracking over time

## Best Practices

### Writing Tests

✅ **Do:**

```python
- Test one thing per test
- Use descriptive names
- Set up and tear down properly
- Use fixtures for reusable setup
- Test edge cases and errors
- Keep tests deterministic
```

❌ **Don't:**

```python
- Mix concerns in single test
- Use non-descriptive names
- Leave side effects
- Duplicate setup code
- Test only happy path
- Use random values
```

### CI Configuration

✅ **Do:**

```yaml
- Test against multiple Python versions
- Run security checks
- Generate coverage reports
- Use caching for speed
- Clean up resources
```

❌ **Don't:**

```yaml
- Leave long build times
- Skip security scanning
- Ignore coverage trends
- Leave artifacts uncleaned
- Run unnecessary jobs
```

## Next Steps (Phase 5+)

- Add performance benchmarks
- Implement mutation testing
- Add contract/integration tests
- Set up staging deployment
- Implement canary releases
- Add load testing

## References

- [pytest Documentation](https://docs.pytest.org/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Codecov Integration](https://codecov.io/gh)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)

## Quick Start

```bash
# Install test dependencies
pip install -r requirements.txt

# Run full test suite
pytest --cov=task_manager_pro

# Run specific tests
pytest tests/test_api.py -v

# View coverage report
pytest --cov=task_manager_pro --cov-report=html
```
