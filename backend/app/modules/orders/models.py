"""Tables from the course data model: orders, order_lines, tasks, assignments.

`orders.priority` is the one addition, so a supervisor can expedite an order.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderRecord(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    due_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(16), default="new")
    priority: Mapped[str] = mapped_column(String(12), default="normal")

    lines: Mapped[list["OrderLineRecord"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderLineRecord.id")


class OrderLineRecord(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    sku_id: Mapped[str] = mapped_column(String(40))
    qty: Mapped[int] = mapped_column(Integer)

    order: Mapped[OrderRecord] = relationship(back_populates="lines")
    task: Mapped["TaskRecord"] = relationship(
        back_populates="order_line", cascade="all, delete-orphan", uselist=False)


class TaskRecord(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_line_id: Mapped[int] = mapped_column(ForeignKey("order_lines.id"), index=True)
    sku_id: Mapped[str] = mapped_column(String(40))
    location_id: Mapped[str] = mapped_column(String(20))
    qty: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), index=True, default="open")

    order_line: Mapped[OrderLineRecord] = relationship(back_populates="task")
    assignments: Mapped[list["AssignmentRecord"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="AssignmentRecord.id")

    @property
    def order(self) -> OrderRecord:
        return self.order_line.order

    @property
    def current_assignment(self) -> "AssignmentRecord | None":
        """The latest assignment, if the task has been handed to a worker."""
        return self.assignments[-1] if self.assignments else None


class AssignmentRecord(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    worker_id: Mapped[int] = mapped_column(Integer, index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    task: Mapped[TaskRecord] = relationship(back_populates="assignments")
