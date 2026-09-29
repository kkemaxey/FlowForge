"""HTTP endpoints for orders, pick tasks and the supervisor's live board."""
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.errors import error_body
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schema import (LiveBoard, OrderCreate, OrderView, TaskStatusUpdate,
                                       TaskView)
from app.modules.orders.service import OrderService
from app.modules.orders.task_states import TaskStatus

router = APIRouter(prefix="/api")


def get_order_service(request: Request) -> Iterator[OrderService]:
    database = request.app.state.database
    for session in database.session():
        yield OrderService(OrderRepository(session))


def error_example(description: str, code: str, message: str) -> dict:
    return {"description": description,
            "content": {"application/json": {"example": error_body(code, message)}}}


def not_found(kind: str) -> dict:
    return {404: error_example(f"{kind} not found", "not_found", f"{kind} 42 does not exist.")}


UNPROCESSABLE = {422: error_example("Invalid input", "validation_failed",
                                    "due_at must be in the future.")}


@router.post("/orders", response_model=OrderView, status_code=status.HTTP_201_CREATED,
             tags=["orders"], summary="Take in an order", responses=UNPROCESSABLE)
def create_order(body: OrderCreate, service: OrderService = Depends(get_order_service)):
    """Saves the order and its lines, and generates one `open` pick task per line."""
    return service.create_order(body)


@router.get("/orders/{order_id}", response_model=OrderView, tags=["orders"],
            summary="Get an order and its tasks", responses=not_found("Order"))
def get_order(order_id: int, service: OrderService = Depends(get_order_service)):
    """`status` is `late` for any unfinished order past its due time."""
    return service.get_order(order_id)


@router.post("/orders/{order_id}/expedite", response_model=OrderView, tags=["orders"],
             summary="Expedite an order", responses={**not_found("Order"), **UNPROCESSABLE})
def expedite_order(order_id: int, service: OrderService = Depends(get_order_service)):
    """Raises the order to `expedite` so its tasks sort to the top of the board."""
    return service.expedite_order(order_id)


@router.get("/tasks", response_model=list[TaskView], tags=["tasks"], summary="List pick tasks")
def list_tasks(status_filter: TaskStatus | None = Query(default=None, alias="status"),
               service: OrderService = Depends(get_order_service)):
    return service.list_tasks(status_filter)


@router.get("/tasks/{task_id}", response_model=TaskView, tags=["tasks"],
            summary="Get one pick task", responses=not_found("Task"))
def get_task(task_id: int, service: OrderService = Depends(get_order_service)):
    return service.get_task(task_id)


@router.patch("/tasks/{task_id}/status", response_model=TaskView, tags=["tasks"],
              summary="Move a task to a new status",
              responses={**not_found("Task"), **UNPROCESSABLE,
                         409: error_example("Transition not allowed", "invalid_transition",
                                            "Cannot move a task from 'open' to 'picked'.")})
def change_task_status(task_id: int, body: TaskStatusUpdate,
                       service: OrderService = Depends(get_order_service)):
    """`assigned` needs a `worker_id` and records an assignment; `picked` completes it;
    `open` returns the task to the pool. The order's status follows its tasks."""
    return service.change_task_status(task_id, body)


@router.get("/board", response_model=LiveBoard, tags=["board"], summary="Live supervisor board")
def live_board(service: OrderService = Depends(get_order_service)):
    """Tasks in status columns (expedited orders first, then soonest due), orders counted by
    status, and WIP, exception, late-order and last-hour throughput counts."""
    return service.live_board()
