"""The course-provided greedy assigner: each idle worker takes the nearest open task."""
from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class WorkerSnapshot:
    id: int
    x: int
    y: int
    status: str
    enabled: bool


@dataclass(frozen=True)
class OpenTask:
    id: int
    x: int
    y: int


@dataclass(frozen=True)
class Assignment:
    worker_id: int
    task_id: int


def manhattan(ax: int, ay: int, bx: int, by: int) -> int:
    return abs(ax - bx) + abs(ay - by)


def assign_greedy(
    workers: Sequence[WorkerSnapshot], open_tasks: Sequence[OpenTask]
) -> List[Assignment]:
    remaining_tasks = list(open_tasks)
    assignments: List[Assignment] = []

    for worker in workers:
        if worker.status != "idle" or not worker.enabled:
            continue
        if not remaining_tasks:
            break

        nearest_task = min(
            remaining_tasks,
            key=lambda task: manhattan(worker.x, worker.y, task.x, task.y),
        )
        assignments.append(Assignment(worker_id=worker.id, task_id=nearest_task.id))
        remaining_tasks.remove(nearest_task)

    return assignments
