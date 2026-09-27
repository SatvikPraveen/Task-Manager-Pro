#!/usr/bin/env python3
"""
scripts/seed_data.py

Populate a database with a *reproducible* synthetic workload.

Given the same ``--seed`` the script produces byte-identical users, tasks,
due dates, priorities and completion states, which makes benchmark runs and
demos comparable across machines and over time.

    SECRET_KEY=... DATABASE_URL=sqlite:///./tasks.db \
        python scripts/seed_data.py --users 5 --tasks-per-user 40 --seed 42

Users are named ``user01`` … and share the password ``password123`` (this is
a demo dataset; do not seed a production database).
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, datetime, timedelta, timezone

TITLES = [
    "Write literature review",
    "Run ablation study",
    "Refactor storage layer",
    "Prepare slides",
    "Reply to reviewer 2",
    "Update CI pipeline",
    "Fix flaky test",
    "Plan sprint",
    "Buy groceries",
    "Book flights",
    "Renew passport",
    "Read paper on scheduling",
    "Draft grant proposal",
    "Clean dataset",
    "Tune hyper-parameters",
    "Write unit tests",
    "Review pull request",
    "Back up laptop",
    "Call the dentist",
    "Submit expense report",
]
PRIORITIES = ["low", "medium", "high"]
PRIORITY_WEIGHTS = [0.3, 0.5, 0.2]


def seed(users: int, tasks_per_user: int, rng_seed: int, *, today: date | None = None) -> tuple[int, int]:
    from task_manager_pro.storage.sql_storage import SQLStorage

    rng = random.Random(rng_seed)
    today = today or date.today()
    storage = SQLStorage()
    created_users = created_tasks = 0

    for i in range(1, users + 1):
        username = f"user{i:02d}"
        try:
            user = storage.create_user(username, "password123", f"{username}@example.com")
            created_users += 1
        except ValueError:
            existing = storage.get_user_by_username(username)
            if existing is None:
                raise
            user = existing

        for _ in range(tasks_per_user):
            due = today + timedelta(days=rng.randint(-30, 60))
            priority = rng.choices(PRIORITIES, PRIORITY_WEIGHTS)[0]
            title = f"{rng.choice(TITLES)} #{rng.randint(1, 999)}"
            description = rng.choice([None, "See notes.", "Blocked on review.", "Quick win.", "Needs data."])
            task = storage.create_task(user.id, title, description, due, priority)
            created_tasks += 1
            # Tasks due in the past are more likely to be done already.
            p_done = 0.7 if due < today else 0.15
            if rng.random() < p_done:
                storage.update_task(task.id, completed=True)
                if due < today:
                    # Backdate completed_at deterministically for latency statistics.
                    finished = datetime.combine(due, datetime.min.time(), tzinfo=timezone.utc) + timedelta(
                        days=rng.randint(-2, 3), hours=rng.randint(0, 23)
                    )
                    storage.update_task(task.id, completed_at=finished)
    return created_users, created_tasks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--users", type=int, default=5)
    parser.add_argument("--tasks-per-user", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    users, tasks = seed(args.users, args.tasks_per_user, args.seed)
    print(f"Seeded {users} new user(s) and {tasks} task(s) with seed={args.seed}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
