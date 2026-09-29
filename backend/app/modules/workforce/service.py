"""Workforce management rules: creating, editing, and removing workers and robots."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from typing_extensions import Protocol

from app.core.exceptions import ConflictError, NotFoundError, RuleViolationError

EDITABLE_FIELDS = frozenset({"name", "type", "speed", "cur_x", "cur_y", "enabled"})


@dataclass
class Worker:
    id: int
    name: str
    type: str
    speed: float
    cur_x: int
    cur_y: int
    status: str
    enabled: bool


@dataclass(frozen=True)
class GridBounds:
    width: int
    height: int


class WorkerRepository(Protocol):
    def list_workers(self, status: Optional[str] = None, worker_type: Optional[str] = None) -> List[Worker]: ...

    def get(self, worker_id: int) -> Optional[Worker]: ...

    def add(self, name: str, worker_type: str, speed: float, cur_x: int, cur_y: int,
            status: str, enabled: bool) -> Worker: ...

    def update(self, worker_id: int, changes: Dict[str, Any]) -> Worker: ...

    def delete(self, worker_id: int) -> None: ...


class WorkforceService:
    def __init__(self, repo: WorkerRepository, grid: GridBounds):
        self._repo = repo
        self._grid = grid

    def list_workers(self, status: Optional[str] = None, worker_type: Optional[str] = None) -> List[Worker]:
        return self._repo.list_workers(status=status, worker_type=worker_type)

    def get_worker(self, worker_id: int) -> Worker:
        worker = self._repo.get(worker_id)
        if worker is None:
            raise NotFoundError("worker_not_found", f"Worker {worker_id} does not exist")
        return worker

    def create_worker(self, name: str, worker_type: str, speed: float, cur_x: int, cur_y: int,
                      enabled: bool = True) -> Worker:
        self._check_position(cur_x, cur_y)
        return self._repo.add(name=name, worker_type=worker_type, speed=speed,
                              cur_x=cur_x, cur_y=cur_y, status="idle", enabled=enabled)

    def update_worker(self, worker_id: int, changes: Dict[str, Any]) -> Worker:
        read_only_fields = set(changes) - EDITABLE_FIELDS
        if read_only_fields:
            raise RuleViolationError(
                "field_not_editable",
                f"These fields cannot be edited: {', '.join(sorted(read_only_fields))}",
            )

        current = self.get_worker(worker_id)
        if not changes:
            return current

        self._check_position(changes.get("cur_x", current.cur_x), changes.get("cur_y", current.cur_y))
        return self._repo.update(worker_id, changes)

    def delete_worker(self, worker_id: int) -> None:
        worker = self.get_worker(worker_id)
        if worker.status == "busy":
            raise ConflictError("worker_busy", f"Worker {worker_id} is busy and cannot be deleted")
        self._repo.delete(worker_id)

    def _check_position(self, cur_x: int, cur_y: int) -> None:
        if not (0 <= cur_x < self._grid.width and 0 <= cur_y < self._grid.height):
            raise RuleViolationError(
                "position_off_grid",
                f"Position ({cur_x}, {cur_y}) is outside the "
                f"{self._grid.width}x{self._grid.height} warehouse grid",
            )
