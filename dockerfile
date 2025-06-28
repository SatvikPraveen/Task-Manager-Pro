# 🐍 Use official lightweight Python 3.11 image as the base
FROM python:3.11-slim

# 🚫 Prevent Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1

# 🧼 Ensure stdout/stderr are unbuffered for real-time logs
ENV PYTHONUNBUFFERED=1

# 📁 Set working directory inside the container
WORKDIR /app

# 📦 Copy dependency metadata and documentation
COPY pyproject.toml README.md ./

# 📂 Copy main application source code
COPY task_manager_pro ./task_manager_pro

# 🔧 Upgrade pip & setuptools, then install app in editable mode
RUN pip install --upgrade pip setuptools \
    && pip install -e .

# 🚀 Define default command to run the CLI when container starts
ENTRYPOINT ["task-manager"]