from app.services.assigner import (
    Assignment,
    OpenTask,
    WorkerSnapshot,
    assign_greedy,
    manhattan,
)


def idle_worker(worker_id, x, y):
    return WorkerSnapshot(id=worker_id, x=x, y=y, status="idle", enabled=True)


def test_manhattan_distance():
    assert manhattan(0, 0, 3, 4) == 7
    assert manhattan(5, 5, 2, 9) == 7
    assert manhattan(1, 1, 1, 1) == 0


def test_worker_gets_nearest_task():
    workers = [idle_worker(1, 0, 0)]
    tasks = [OpenTask(id=10, x=9, y=9), OpenTask(id=11, x=1, y=2)]

    assert assign_greedy(workers, tasks) == [Assignment(worker_id=1, task_id=11)]


def test_tie_goes_to_first_task_in_list():
    workers = [idle_worker(1, 5, 5)]
    tasks = [OpenTask(id=20, x=5, y=7), OpenTask(id=21, x=7, y=5)]

    assert assign_greedy(workers, tasks) == [Assignment(worker_id=1, task_id=20)]


def test_assigned_task_is_not_given_to_a_second_worker():
    workers = [idle_worker(1, 0, 0), idle_worker(2, 0, 1)]
    tasks = [OpenTask(id=30, x=0, y=0), OpenTask(id=31, x=8, y=8)]

    assert assign_greedy(workers, tasks) == [
        Assignment(worker_id=1, task_id=30),
        Assignment(worker_id=2, task_id=31),
    ]


def test_more_workers_than_tasks_leaves_extra_workers_unassigned():
    workers = [idle_worker(1, 0, 0), idle_worker(2, 5, 5), idle_worker(3, 9, 9)]
    tasks = [OpenTask(id=40, x=9, y=9)]

    assert assign_greedy(workers, tasks) == [Assignment(worker_id=1, task_id=40)]


def test_more_tasks_than_workers_assigns_one_task_per_worker():
    workers = [idle_worker(1, 0, 0)]
    tasks = [OpenTask(id=50, x=1, y=0), OpenTask(id=51, x=2, y=0)]

    assert assign_greedy(workers, tasks) == [Assignment(worker_id=1, task_id=50)]


def test_busy_and_disabled_workers_are_skipped():
    workers = [
        WorkerSnapshot(id=1, x=0, y=0, status="busy", enabled=True),
        WorkerSnapshot(id=2, x=0, y=0, status="idle", enabled=False),
        idle_worker(3, 9, 9),
    ]
    tasks = [OpenTask(id=60, x=0, y=0)]

    assert assign_greedy(workers, tasks) == [Assignment(worker_id=3, task_id=60)]


def test_empty_inputs_return_no_assignments():
    assert assign_greedy([], [OpenTask(id=1, x=0, y=0)]) == []
    assert assign_greedy([idle_worker(1, 0, 0)], []) == []


def test_input_task_list_is_not_mutated():
    tasks = [OpenTask(id=70, x=0, y=0)]

    assign_greedy([idle_worker(1, 0, 0)], tasks)

    assert tasks == [OpenTask(id=70, x=0, y=0)]
