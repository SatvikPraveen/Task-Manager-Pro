# 🤝 Contributing Guidelines for Task Manager PRO

Thank you for considering contributing to **Task Manager PRO**!

This project is a Python-based CLI task manager aimed at helping developers stay organized and productive. Your contributions—whether code, ideas, or documentation—are welcome!

---

## 🚀 How to Contribute

1. **Fork** the repository.
2. **Create a new branch**  
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. Make your changes with **clear and descriptive commits**.
4. **Test** your changes thoroughly to ensure functionality.
5. **Submit a pull request** that includes:

   * A summary of your changes
   * Why the change is necessary or beneficial

---

## 🧪 Local checks

Everything CI runs is a `make` target:

```bash
make install       # editable install with dev extras + pre-commit hooks
make lint          # ruff check + ruff format --check
make typecheck     # mypy
make security      # bandit
make test          # pytest with the 80 % coverage gate
make migrate-check # alembic upgrade head && alembic check
```

If you change `task_manager_pro/storage/models.py`, generate a migration with
`alembic revision --autogenerate -m "..."` and commit it; CI fails on drift.
Record non-obvious design decisions as an ADR in `docs/adr/` and add a line to
`CHANGELOG.md` under *Unreleased*.

## 🧑‍💻 Code Style

* `ruff format` is the formatter; `ruff check` the linter (config in `pyproject.toml`).
* Follow **PEP8** guidelines for Python code.
* Keep functions **modular** and **readable**.
* Add **comments** where logic isn’t obvious.
* **Update documentation** if your change affects usage or behavior.

---

## 🐞 Reporting Bugs

If you find a bug, please open a GitHub [Issue](https://github.com/your-username/Task-Manager-PRO/issues) with:

* **Clear and concise title**
* **Steps to reproduce the issue**
* **Expected vs. actual behavior**
* Relevant **screenshots or logs**, if available

---

## 💡 Feature Suggestions

Have an idea to improve Task Manager PRO? Open an issue describing:

* **What problem it solves**
* **How it benefits users**
* **Any potential implementation details** (if you have suggestions)

---

Thanks again for your interest in contributing — your input helps improve the tool for everyone! 🙌
