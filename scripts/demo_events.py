"""Posts a burst of warehouse events so /api/metrics has something to show.

Usage: python scripts/demo_events.py [--base-url http://127.0.0.1:8000] [--tasks 12] [--first-task-id 1]
Uses only the standard library, so it runs outside the venv too.
"""
import argparse
import json
import random
import urllib.request


def post_json(base_url: str, path: str, body: dict) -> dict:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def get_json(base_url: str, path: str) -> dict:
    with urllib.request.urlopen(f"{base_url}{path}") as response:
        return json.loads(response.read())


def main() -> None:
    parser = argparse.ArgumentParser(description="Post demo pick events to FlowForge.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--tasks", type=int, default=12)
    parser.add_argument("--first-task-id", type=int, default=1)
    args = parser.parse_args()

    task_ids = range(args.first_task_id, args.first_task_id + args.tasks)
    for task_id in task_ids:
        post_json(args.base_url, "/api/events", {"type": "task_assigned", "task_id": task_id})

    for task_id in task_ids:
        roll = random.random()
        if roll < 0.7:
            post_json(args.base_url, "/api/events",
                      {"type": "task_picked", "task_id": task_id, "qty": random.randint(1, 5)})
        elif roll < 0.85:
            post_json(args.base_url, "/api/events",
                      {"type": "task_exception", "task_id": task_id, "payload": {"reason": "stockout"}})
        # otherwise the task stays in progress and shows up in WIP

    print(json.dumps(get_json(args.base_url, "/api/metrics"), indent=2))


if __name__ == "__main__":
    main()
