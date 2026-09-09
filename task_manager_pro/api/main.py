"""
api/main.py

Main FastAPI application file.
Initializes the API server with all routes, middleware, and configuration.
"""

from contextlib import asynccontextmanager
from importlib.metadata import version as _pkg_version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from task_manager_pro.api.routes import auth, tasks, users
from task_manager_pro.storage.database import init_db
import os

API_VERSION = _pkg_version("task-manager-pro")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on application startup."""
    init_db()
    print("✓ Database initialized")
    yield


# Create FastAPI app
app = FastAPI(
    title="Task Manager PRO API",
    description="Advanced task management API with authentication and database support",
    version=API_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Configure CORS (Cross-Origin Resource Sharing)
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "🎯 Task Manager PRO API",
        "version": API_VERSION,
        "docs": "/api/docs",
        "openapi_schema": "/api/openapi.json",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": API_VERSION,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "task_manager_pro.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
