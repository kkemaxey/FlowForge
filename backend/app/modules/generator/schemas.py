"""Request and response bodies for /api/v1/generator."""
from pydantic import BaseModel, Field

from app.core.schemas import UtcDatetime


class StartRequest(BaseModel):
    order_rate: float = Field(default=6.0, gt=0, le=600, description="Average orders per minute")
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1, description="Omit for a random (recorded) seed")


class OutOfStockOut(BaseModel):
    sku_code: str
    # Generated orders rejected because of this shoe since it ran out.
    rejected_orders: int


class GeneratorStatus(BaseModel):
    running: bool
    # The current run, or the last one after a stop; null if the generator never ran.
    run_id: int | None
    order_rate: float | None
    seed: int | None
    started_at: UtcDatetime | None
    created: int
    # Orders intake refused with insufficient_stock (nothing was written for them).
    rejected: int
    # Unexpected failures, logged to the backend log; the generator keeps going.
    errors: int
    # Shoes with 0 unreserved pairs left. Re-checked every few seconds; a restocked shoe drops off.
    out_of_stock: list[OutOfStockOut]
