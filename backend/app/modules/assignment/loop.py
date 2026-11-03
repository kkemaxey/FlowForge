"""Background assigner: runs one greedy pass every few seconds so new tasks get picked up with no
human action. Started by the app's lifespan when ASSIGNER_LOOP_ENABLED is true (on in Docker,
off in tests). Assumes a single backend instance; races with supervisor actions are safe
(compare-and-set + unique keys), but several instances would just waste passes on conflicts.
"""
import asyncio
import logging

from app.core.database import SessionLocal
from app.modules.assignment.service import run_pass

# Child of uvicorn's logger so passes show up in `docker compose logs backend`.
logger = logging.getLogger("uvicorn.error").getChild("assigner")

ALGORITHM = "greedy_v1"


def run_once() -> None:
    with SessionLocal() as session:
        result = run_pass(session, ALGORITHM)
    if result.assignments or result.conflicts:
        logger.info("assigned %d task(s), %d conflict(s)", len(result.assignments), result.conflicts)


async def assigner_loop(interval_seconds: float, stop: asyncio.Event) -> None:
    logger.info("assigner loop started (%s every %ss)", ALGORITHM, interval_seconds)
    while not stop.is_set():
        try:
            # Database work is blocking; keep it off the event loop that serves requests.
            await asyncio.to_thread(run_once)
        except Exception:
            logger.exception("assigner pass failed; retrying next interval")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except TimeoutError:
            pass
    logger.info("assigner loop stopped")
