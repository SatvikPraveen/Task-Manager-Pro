# Use an official Python runtime as the base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy only necessary files
COPY pyproject.toml README.md ./
COPY task_manager_pro ./task_manager_pro

# Install pip, build tools, and install project in editable mode
RUN pip install --upgrade pip setuptools \
    && pip install -e .

# Default command (entrypoint)
ENTRYPOINT ["task-manager"]