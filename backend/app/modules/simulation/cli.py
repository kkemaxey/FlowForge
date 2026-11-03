"""Command-line demo tools. Run them inside the backend container, in their own terminal:

    docker compose exec backend python -m app.modules.simulation.cli run [--tick 1] [--seed 7] ...
    docker compose exec backend python -m app.modules.simulation.cli trigger --task-id 42 --type stockout

Orders come from POST /api/v1/generator/start, and the warehouse from `python -m app.seed`.
"""
import argparse
import logging
import sys
from dataclasses import fields

import httpx

from app.modules.simulation.client import ApiCallError, client_from_env
from app.modules.simulation.simulator import Simulator, SimulatorConfig, trigger_exception


def cmd_run(args: argparse.Namespace) -> int:
    """`run`: start the simulator against a live server until Ctrl+C (or --ticks)."""
    try:
        config = _simulator_config(args)
    except ValueError as exc:
        print(f"bad simulator config: {exc}", file=sys.stderr)
        return 2
    # `with` closes the HTTP connection when we're done.
    with client_from_env() as client:
        print(f"Simulating with {config}. Ctrl+C to stop.")
        try:
            Simulator(client, config).run(max_ticks=args.ticks)
        except KeyboardInterrupt:
            # Ctrl+C is the normal way to stop; exit quietly.
            pass
    return 0


def cmd_trigger(args: argparse.Namespace) -> int:
    """`trigger`: make a specific task fail right now (for live demos)."""
    with client_from_env() as client:
        try:
            result = trigger_exception(client, args.task_id, args.type, args.qty_found)
        except (ValueError, ApiCallError, httpx.HTTPError) as exc:
            print(f"trigger failed: {exc}", file=sys.stderr)
            return 1
    print(result)
    return 0


def _simulator_config(args: argparse.Namespace) -> SimulatorConfig:
    """Build a SimulatorConfig from defaults, overriding any field the user passed as a flag."""
    overrides = {f.name: getattr(args, f.name) for f in fields(SimulatorConfig) if getattr(args, f.name, None) is not None}
    return SimulatorConfig(**overrides)


def build_parser() -> argparse.ArgumentParser:
    """Define every command and its flags. set_defaults(handler=...) picks the function to run."""
    parser = argparse.ArgumentParser(prog="python -m app.modules.simulation.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    # Each dest= matches a SimulatorConfig field name. Env vars (SIM_*) set the defaults.
    run = commands.add_parser("run", help="Run the worker/robot simulator")
    run.add_argument("--tick", dest="tick_seconds", type=float, help="seconds between ticks (default 1)")
    run.add_argument("--worker-speed", dest="worker_speed", type=float, help="multiplier on each worker's speed")
    run.add_argument("--pick-seconds", dest="pick_seconds", type=float, help="time to pick once at the bin (default 5)")
    run.add_argument("--p-stockout", dest="p_stockout", type=float)
    run.add_argument("--p-jam", dest="p_jam", type=float)
    run.add_argument("--p-worker-down", dest="p_worker_down", type=float)
    run.add_argument("--recovery-seconds", dest="recovery_seconds", type=float, help="downtime before a worker recovers (default 30)")
    run.add_argument("--seed", type=int, help="random seed for reproducible runs")
    run.add_argument("--ticks", type=int, help="stop after this many ticks")
    run.set_defaults(handler=cmd_run)

    trigger = commands.add_parser("trigger", help="Raise an exception on a task's active assignment now")
    trigger.add_argument("--task-id", type=int, required=True)
    trigger.add_argument("--type", choices=["stockout", "jam", "worker_down"], required=True)
    trigger.add_argument("--qty-found", type=int, help="units found in the bin (stockout; default 0)")
    trigger.set_defaults(handler=cmd_trigger)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse the command line, run the chosen command, and return its exit code (0 = success)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    # Hide httpx's line-per-request logging.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args = build_parser().parse_args(argv)
    return args.handler(args)


# Runs only when started as `python -m app.modules.simulation.cli`, not when imported.
if __name__ == "__main__":
    sys.exit(main())
