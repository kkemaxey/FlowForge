from fastapi import APIRouter

from app.modules.generator.schemas import GeneratorStatus, StartRequest
from app.modules.generator.service import generator

router = APIRouter(prefix="/api/v1/generator", tags=["generator"])


@router.get("", response_model=GeneratorStatus)
def generator_status() -> GeneratorStatus:
    return generator.status()


@router.post("/start", response_model=GeneratorStatus)
async def start_generator(payload: StartRequest | None = None) -> GeneratorStatus:
    """Start a new run: creates a sim_runs row and streams orders into intake until stopped."""
    payload = payload or StartRequest()
    await generator.start(payload.order_rate, payload.seed)
    return generator.status()


@router.post("/stop", response_model=GeneratorStatus)
async def stop_generator() -> GeneratorStatus:
    """Stop the current run (no-op if not running) and record its end time."""
    await generator.stop()
    return generator.status()
