"""HTTP endpoints for pick tasks and the supervisor's live board."""
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.errors import error_body
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.schema import LiveBoard, TaskCreate, TaskRead, TaskStatusUpdate
from app.modules.tasks.service import TaskService
from app.modules.tasks.task_states import TaskStatus

router = APIRouter(prefix="/api", tags=["tasks"])


def get_task_service(request: Request) -> Iterator[TaskService]:
    database = request.app.state.database
    for session in database.session():
        yield TaskService(TaskRepository(session))


def error_example(description: str, code: str, message: str) -> dict:
    return {"description": description,
            "content": {"application/json": {"example": error_body(code, message)}}}


NOT_FOUND = {404: error_example("Task not found", "not_found", "Task 42 does not exist.")}
UNPROCESSABLE = {422: error_example("Invalid input", "validation_failed",
                                    "due_at must be in the future.")}


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED,
             summary="Create a pick task", responses=UNPROCESSABLE)
def create_task(body: TaskCreate, service: TaskService = Depends(get_task_service)):
    """Creates an `open` pick task for one order line. `due_at` must be in the future."""
    return service.create_task(body)


@router.get("/tasks", response_model=list[TaskRead], summary="List pick tasks")
def list_tasks(status_filter: TaskStatus | None = Query(default=None, alias="status"),
               service: TaskService = Depends(get_task_service)):
    """Lists tasks ordered by due time, optionally filtered by `status`."""
    return service.list_tasks(status_filter)


@router.get("/tasks/{task_id}", response_model=TaskRead, summary="Get one pick task",
            responses=NOT_FOUND)
def get_task(task_id: int, service: TaskService = Depends(get_task_service)):
    return service.get_task(task_id)


@router.patch("/tasks/{task_id}/status", response_model=TaskRead,
              summary="Move a task to a new status",
              responses={**NOT_FOUND, **UNPROCESSABLE,
                         409: error_example("Transition not allowed", "invalid_transition",
                                            "Cannot move a task from 'open' to 'picked'.")})
def change_task_status(task_id: int, body: TaskStatusUpdate,
                       service: TaskService = Depends(get_task_service)):
    """Advances a task through its lifecycle. `assigned` needs `worker_id`;
    `exception` needs `reason`; moving back to `open` clears both."""
    return service.change_status(task_id, body)


@router.post("/tasks/{task_id}/expedite", response_model=TaskRead,
             summary="Expedite a task", responses={**NOT_FOUND, **UNPROCESSABLE})
def expedite_task(task_id: int, service: TaskService = Depends(get_task_service)):
    """Raises a task to `expedite` priority so it sorts to the top of its board column."""
    return service.expedite(task_id)


@router.get("/board", response_model=LiveBoard, summary="Live supervisor board")
def live_board(service: TaskService = Depends(get_task_service)):
    """Tasks grouped into status columns (expedited first, then soonest due),
    with WIP, late-task, exception and last-hour throughput counts."""
    return service.live_board()
