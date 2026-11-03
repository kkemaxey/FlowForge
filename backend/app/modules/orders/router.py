from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.orders import service
from app.modules.orders.schemas import OrderCreate, OrderOut

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "Replay: external_ref already exists; the existing order is returned"}},
)
def create_order(payload: OrderCreate, response: Response, db: Session = Depends(get_db)) -> OrderOut:
    order, created = service.create_order(db, payload)
    if not created:
        response.status_code = status.HTTP_200_OK
    return service.order_out(db, order)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)) -> OrderOut:
    return service.order_out(db, service.get_order(db, order_id))


@router.post("/{order_id}/expedite", response_model=OrderOut)
def expedite_order(order_id: int, db: Session = Depends(get_db)) -> OrderOut:
    """Mark the order expedited and move its unfinished tasks to the front of the work queue."""
    return service.order_out(db, service.expedite_order(db, order_id))
