"""Worker/robot simulator. Drives the system only through the HTTP API.

Each tick it reads the active assignments. The first time it sees one, it plans it:
  duration = manhattan(worker, bin) / (worker.speed * worker_speed) + pick_seconds
  outcome  = pick, or stockout / jam / worker_down with the configured probabilities
and once the duration has passed (on the simulator's own clock) it carries the outcome out by
calling POST /tasks/{id}/pick or POST /tasks/{id}/exceptions. A bin that turns out to hold less
than the task needs becomes a stockout, which is how low-stock SKUs fail naturally. Workers it sends
'down' are brought back with POST /simulation/workers/{id}/recover after recovery_seconds.

Assigning open tasks to idle workers is the assigner's job, not the simulator's.
"""
import logging
import os
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

# checked(): raises ApiCallError if a response is an error.
from app.modules.simulation.client import ApiCallError, checked

# Log lines show up as "flowforge.simulator task 12: pick".
log = logging.getLogger("flowforge.simulator")

# Every endpoint lives under this prefix.
API = "/api/v1"


def _env_float(name: str, default: float) -> float:
    """Read a decimal environment variable, or use the default if it isn't set."""
    return float(os.getenv(name, default))


@dataclass
class SimulatorConfig:
    """All simulator settings. Defaults come from SIM_* env vars; CLI flags override them."""

    # How often tick() runs, in real seconds.
    tick_seconds: float = field(default_factory=lambda: _env_float("SIM_TICK_SECONDS", 1.0))
    # Multiplies every worker's own speed (grid cells per second).
    worker_speed: float = field(default_factory=lambda: _env_float("SIM_WORKER_SPEED", 1.0))
    # Time spent picking once the worker reaches the bin.
    pick_seconds: float = field(default_factory=lambda: _env_float("SIM_PICK_SECONDS", 5.0))
    # Chance (0-1) that an assignment ends in each kind of exception instead of a pick.
    p_stockout: float = field(default_factory=lambda: _env_float("SIM_P_STOCKOUT", 0.02))
    p_jam: float = field(default_factory=lambda: _env_float("SIM_P_JAM", 0.01))
    p_worker_down: float = field(default_factory=lambda: _env_float("SIM_P_WORKER_DOWN", 0.005))
    # How long a downed worker stays down before the simulator recovers them.
    recovery_seconds: float = field(default_factory=lambda: _env_float("SIM_WORKER_RECOVERY_SECONDS", 30.0))
    # Random seed. Same seed + same assignments = same outcomes. None = different every run.
    seed: int | None = field(default_factory=lambda: int(os.environ["SIM_SEED"]) if os.getenv("SIM_SEED") else None)

    def __post_init__(self) -> None:
        """Reject nonsense settings as soon as the config is created."""
        if self.tick_seconds <= 0 or self.worker_speed <= 0 or self.pick_seconds < 0 or self.recovery_seconds < 0:
            raise ValueError("tick_seconds and worker_speed must be > 0; pick_seconds and recovery_seconds >= 0")
        # The three probabilities share one roll of the dice, so together they can't exceed 100%.
        if min(self.p_stockout, self.p_jam, self.p_worker_down) < 0 or self.p_stockout + self.p_jam + self.p_worker_down > 1:
            raise ValueError("exception probabilities must be >= 0 and sum to at most 1")


@dataclass
class Plan:
    """What the simulator decided for one assignment, and when it happens."""

    # Simulator-clock time at which the worker finishes walking + picking.
    due_at: float
    outcome: str  # "pick", "stockout", "jam" or "worker_down"


@dataclass
class Action:
    """One thing the simulator did during a tick (returned for logging and tests)."""

    task_id: int
    assignment_id: int
    outcome: str
    # False if the API said the state had already moved on (409) and the action was skipped.
    ok: bool
    detail: str = ""


class Simulator:
    def __init__(self, client: httpx.Client, config: SimulatorConfig, clock: Callable[[], float] = time.monotonic) -> None:
        # The HTTP client used to call the API (a real one, or TestClient in tests and the demo).
        self.client = client
        self.config = config
        # Where "now" comes from. Real runs use the system clock; tests pass a fake clock.
        self.clock = clock
        # Our own random generator, so the seed controls every dice roll.
        self.rng = random.Random(config.seed)
        # assignment_id -> its plan, made the first time we see the assignment.
        self.plans: dict[int, Plan] = {}
        # task_id -> exception type to raise instead of the planned outcome (manual demo trigger).
        self.forced: dict[int, str] = {}
        # worker_id -> simulator time at which a worker this simulator sent 'down' gets back up.
        self.down_until: dict[int, float] = {}

    def force(self, task_id: int, outcome: str) -> None:
        """Make the task's current (or next) assignment end in this exception when it comes due."""
        self.forced[task_id] = outcome

    def _plan(self, assignment: dict, now: float) -> Plan:
        """Decide how long this assignment takes and how it ends."""
        # Manhattan distance: cells across + cells up/down (workers can't walk diagonally).
        distance = abs(assignment["worker_x"] - assignment["location_x"]) + abs(assignment["worker_y"] - assignment["location_y"])
        # Walking time = distance / speed (the worker's own speed times the global multiplier).
        travel = distance / (assignment["worker_speed"] * self.config.worker_speed)
        # One random number between 0 and 1 decides the outcome.
        roll = self.rng.random()
        c = self.config
        # The probabilities are stacked: [0, p_stockout) = stockout, then the next p_jam = jam, etc.
        if roll < c.p_stockout:
            outcome = "stockout"
        elif roll < c.p_stockout + c.p_jam:
            outcome = "jam"
        elif roll < c.p_stockout + c.p_jam + c.p_worker_down:
            outcome = "worker_down"
        else:
            outcome = "pick"
        # Due once the walk and the pick are both done.
        return Plan(due_at=now + travel + c.pick_seconds, outcome=outcome)

    def _recover_workers(self, now: float) -> None:
        """Bring back every downed worker whose downtime is over."""
        # list(...) copies the items so we can delete from the dict while looping.
        for worker_id, due in list(self.down_until.items()):
            if now < due:
                continue  # still down
            del self.down_until[worker_id]
            try:
                checked(self.client.post(f"{API}/simulation/workers/{worker_id}/recover"))
                log.info("worker %s recovered", worker_id)
            except ApiCallError as exc:
                if exc.status_code != 409:  # 409: someone already brought them back
                    raise

    def tick(self) -> list[Action]:
        """One step of the simulation. Returns what was done this step."""
        now = self.clock()
        # 1. Bring back any workers whose downtime is over.
        self._recover_workers(now)
        # 2. Ask the API what everyone is working on.
        active = checked(self.client.get(f"{API}/simulation/assignments/active")).json()["items"]
        active_ids = {a["assignment_id"] for a in active}
        # Forget plans for assignments that are no longer active (finished, reassigned, ...).
        self.plans = {aid: plan for aid, plan in self.plans.items() if aid in active_ids}

        actions = []
        # Lowest assignment id first, so runs with the same seed always process in the same order.
        for assignment in sorted(active, key=lambda a: a["assignment_id"]):
            plan = self.plans.get(assignment["assignment_id"])
            # 3. First time we see this assignment: plan it (and remember the plan).
            if plan is None:
                plan = self.plans[assignment["assignment_id"]] = self._plan(assignment, now)
            # 4. Not done walking/picking yet: check again next tick.
            if now < plan.due_at:
                continue
            # 5. Time's up. A forced exception (demo trigger) overrides the planned outcome.
            outcome = self.forced.pop(assignment["task_id"], plan.outcome)
            actions.append(self._finish(assignment, outcome, now))
            del self.plans[assignment["assignment_id"]]
        return actions

    def _finish(self, assignment: dict, outcome: str, now: float) -> Action:
        """Carry out an outcome by calling the pick or exceptions endpoint."""
        task_id, assignment_id, qty = assignment["task_id"], assignment["assignment_id"], assignment["qty"]
        on_hand = assignment["bin_on_hand"]
        # Natural stockout: the bin doesn't really hold enough, whatever the dice said.
        if outcome == "pick" and on_hand < qty:
            outcome = "stockout"
        body: dict = {"type": outcome, "assignment_id": assignment_id}
        if outcome == "stockout":
            # Found whatever the bin really holds, which is less than the task needs.
            # (For a random stockout on a full bin, pretend we found a random shortfall.)
            body["qty_found"] = min(on_hand, qty - 1) if on_hand < qty else self.rng.randint(0, qty - 1)

        try:
            if outcome == "pick":
                checked(self.client.post(f"{API}/tasks/{task_id}/pick", json={"assignment_id": assignment_id}))
                detail = ""
            else:
                result = checked(self.client.post(f"{API}/tasks/{task_id}/exceptions", json=body)).json()
                # Remember when this worker should get back up.
                if outcome == "worker_down":
                    self.down_until[assignment["worker_id"]] = now + self.config.recovery_seconds
                detail = f"task {result['task_status']}, rerouted to {result['rerouted_to_location_id']}"
        except ApiCallError as exc:
            # 409: the state moved on (another tick, the supervisor, the assigner). Skip and move on.
            if exc.status_code != 409:
                raise  # anything else is a real error
            log.info("task %s: %s skipped (%s)", task_id, outcome, exc.code)
            return Action(task_id, assignment_id, outcome, ok=False, detail=exc.code or "conflict")
        log.info("task %s: %s %s", task_id, outcome, detail)
        return Action(task_id, assignment_id, outcome, ok=True, detail=detail)

    def run(self, max_ticks: int | None = None) -> None:
        """Tick forever (or max_ticks times), once every tick_seconds of real time."""
        ticks = 0
        while max_ticks is None or ticks < max_ticks:
            started = time.monotonic()
            try:
                self.tick()
            except (httpx.HTTPError, ApiCallError) as exc:
                # The API hiccupped (e.g. the dev server reloading). Keep the demo going; retry next tick.
                log.warning("tick failed, retrying: %s", exc)
            ticks += 1
            # Sleep for the rest of the tick interval (minus however long the tick took).
            time.sleep(max(0.0, self.config.tick_seconds - (time.monotonic() - started)))


def trigger_exception(client: httpx.Client, task_id: int, type: str, qty_found: int | None = None) -> dict:
    """Raise an exception on a task's active assignment right now (demo control)."""
    # Find the task's active assignment.
    active = checked(client.get(f"{API}/simulation/assignments/active")).json()["items"]
    assignment = next((a for a in active if a["task_id"] == task_id), None)
    if assignment is None:
        raise ValueError(f"Task {task_id} has no active assignment")
    body: dict = {"type": type, "assignment_id": assignment["assignment_id"]}
    if type == "stockout":
        # A stockout needs qty_found; default to "found nothing".
        body["qty_found"] = qty_found if qty_found is not None else 0
    elif qty_found is not None:
        body["qty_found"] = qty_found
    return checked(client.post(f"{API}/tasks/{task_id}/exceptions", json=body)).json()
