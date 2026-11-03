"""Command-line entry point for demo tooling. Run from backend/:

    python -m app.modules.simulation.cli seed [--reset] [--seed 480] [--grid 10x10] [--skus 25] ...
    python -m app.modules.simulation.cli run [--tick 1] [--worker-speed 1] [--p-jam 0.01] [--seed 7] ...
    python -m app.modules.simulation.cli orders [--rate 6] [--count 20] [--seed 7]
    python -m app.modules.simulation.cli trigger --task-id 42 --type stockout [--qty-found 0]
    python -m app.modules.simulation.cli demo [--orders 15] [--seed 7] [--db demo.db]

run/orders/trigger call the API and sign in as SIM_EMAIL (see client.py).
demo runs everything offline against its own SQLite file (see demo.py).

Each command is a cmd_* function. build_parser() wires each command name to its function and
flags; main() parses what you typed and calls the matching function.
"""
import argparse
import logging
import os
import sys
from dataclasses import fields
from pathlib import Path

# SessionLocal opens a session on the database in DATABASE_URL (used by `seed`).
from app.core.database import SessionLocal
from app.modules.simulation.client import ApiCallError, client_from_env
from app.modules.simulation.order_generator import OrderGenerator
from app.modules.simulation.seed import SeedConfig, SeedError, ensure_login_user, seed_database
from app.modules.simulation.simulator import Simulator, SimulatorConfig, trigger_exception


def _grid(value: str) -> tuple[int, int]:
    """Turn "--grid 10x10" into (10, 10); argparse shows our message if the format is wrong."""
    try:
        width, height = (int(part) for part in value.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError("grid must look like 10x10")
    return width, height


def cmd_seed(args: argparse.Namespace) -> int:
    """`seed`: build the synthetic warehouse, then (optionally) the Firebase logins."""
    # Start from the defaults/env vars, then apply any flags the user typed.
    config = SeedConfig()
    if args.seed is not None:
        config.seed = args.seed
    if args.grid is not None:
        config.width, config.height = args.grid
    for name in ("skus", "workers", "robots", "stations"):
        if getattr(args, name) is not None:
            setattr(config, name, getattr(args, name))

    with SessionLocal() as db:
        try:
            result = seed_database(db, config, reset_first=args.reset)
        except SeedError as exc:
            # A problem the user can fix: print it and exit with code 1.
            print(f"seed failed: {exc}", file=sys.stderr)
            return 1
        if result is None:
            print("Database already seeded; nothing changed. Use --reset to wipe and reseed.")
        else:
            print(
                f"Seeded run_id={result.run_id}: {result.locations} locations, {result.skus} SKUs, "
                f"{result.inventory_rows} inventory rows, {result.workers} workers/robots (seed {config.seed})."
            )

        if args.skip_firebase:
            return 0
        # Create each login whose email/password env vars are set; skip the others.
        for email_var, password_var, role in (
            ("SUPERVISOR_EMAIL", "SUPERVISOR_PASSWORD", "supervisor"),
            ("SIM_EMAIL", "SIM_PASSWORD", "service"),
        ):
            email, password = os.getenv(email_var), os.getenv(password_var)
            if not (email and password):
                print(f"Skipping {role} login: {email_var}/{password_var} not set.")
                continue
            ensure_login_user(db, email, password, role)
            print(f"Ensured {role} login {email}.")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """`run`: start the simulator against a live server until Ctrl+C (or --ticks)."""
    try:
        config = _simulator_config(args)
    except ValueError as exc:
        print(f"bad simulator config: {exc}", file=sys.stderr)
        return 2
    # `with` closes the HTTP connection when we're done.
    with client_from_env() as client:
        simulator = Simulator(client, config)
        run_id = simulator.start_run()
        print(f"Simulating run_id={run_id} with {config}. Ctrl+C to stop.")
        try:
            simulator.run(max_ticks=args.ticks)
        except KeyboardInterrupt:
            # Ctrl+C is the normal way to stop; exit quietly.
            pass
    return 0


def cmd_orders(args: argparse.Namespace) -> int:
    """`orders`: post synthetic orders at --rate per minute until Ctrl+C (or --count)."""
    with client_from_env() as client:
        generator = OrderGenerator(client, seed=args.seed)
        print(f"Posting {args.rate}/min orders for run_id={generator.run_id}. Ctrl+C to stop.")
        try:
            generator.run(per_minute=args.rate, count=args.count)
        except KeyboardInterrupt:
            pass
    return 0


def cmd_trigger(args: argparse.Namespace) -> int:
    """`trigger`: make a specific task fail right now (for live demos)."""
    with client_from_env() as client:
        try:
            result = trigger_exception(client, args.task_id, args.type, args.qty_found)
        except (ValueError, ApiCallError) as exc:
            print(f"trigger failed: {exc}", file=sys.stderr)
            return 1
    print(result)
    return 0


def _simulator_config(args: argparse.Namespace) -> SimulatorConfig:
    """Build a SimulatorConfig from defaults, overriding any field the user passed as a flag."""
    # For each SimulatorConfig field (tick_seconds, p_jam, ...), use the flag's value if one was given.
    overrides = {f.name: getattr(args, f.name) for f in fields(SimulatorConfig) if getattr(args, f.name, None) is not None}
    return SimulatorConfig(**overrides)


def cmd_demo(args: argparse.Namespace) -> int:
    """`demo`: run seed + orders + simulator offline on a local SQLite file and print a report."""
    # Imported here so the other commands don't load the demo's extra dependencies.
    from app.modules.simulation.demo import run_demo

    # Safety: the demo wipes its file every run, so only accept a .db file.
    if args.db.suffix != ".db":
        print("--db must be a .db file; it is wiped and reseeded on every run", file=sys.stderr)
        return 2
    try:
        sim_config = _simulator_config(args)
    except ValueError as exc:
        print(f"bad simulator config: {exc}", file=sys.stderr)
        return 2
    seed_config = SeedConfig()
    # --seed sets both the warehouse seed and the simulator's dice seed.
    if args.seed is not None:
        sim_config.seed = seed_config.seed = args.seed
    run_demo(args.db, orders=args.orders, seed_config=seed_config, sim_config=sim_config, max_seconds=args.max_seconds)
    return 0


def _add_simulator_flags(parser: argparse.ArgumentParser) -> None:
    """Flags shared by `run` and `demo`. Each dest= matches a SimulatorConfig field name."""
    parser.add_argument("--tick", dest="tick_seconds", type=float, help="seconds between ticks (default 1)")
    parser.add_argument("--worker-speed", dest="worker_speed", type=float, help="multiplier on each worker's speed")
    parser.add_argument("--pick-seconds", dest="pick_seconds", type=float, help="time to pick once at the bin (default 5)")
    parser.add_argument("--p-stockout", dest="p_stockout", type=float)
    parser.add_argument("--p-jam", dest="p_jam", type=float)
    parser.add_argument("--p-worker-down", dest="p_worker_down", type=float)
    parser.add_argument("--recovery-seconds", dest="recovery_seconds", type=float, help="downtime before a worker recovers (default 30)")
    parser.add_argument("--seed", type=int, help="random seed for reproducible runs")


def build_parser() -> argparse.ArgumentParser:
    """Define every command and its flags. set_defaults(handler=...) picks the function to run."""
    parser = argparse.ArgumentParser(prog="python -m app.modules.simulation.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    seed = commands.add_parser("seed", help="Seed synthetic warehouse data (env SEED_* sets defaults)")
    seed.add_argument("--reset", action="store_true", help="wipe all warehouse tables first (SQLite only unless FLOWFORGE_ALLOW_RESET=1)")
    seed.add_argument("--seed", type=int, help="random seed (default 480)")
    seed.add_argument("--grid", type=_grid, help="WIDTHxHEIGHT (default 10x10)")
    seed.add_argument("--skus", type=int)
    seed.add_argument("--workers", type=int, help="human pickers")
    seed.add_argument("--robots", type=int)
    seed.add_argument("--stations", type=int)
    seed.add_argument("--skip-firebase", action="store_true", help="don't create the supervisor/simulator logins")
    seed.set_defaults(handler=cmd_seed)

    run = commands.add_parser("run", help="Run the worker/robot simulator (env SIM_* sets defaults)")
    _add_simulator_flags(run)
    run.add_argument("--ticks", type=int, help="stop after this many ticks")
    run.set_defaults(handler=cmd_run)

    orders = commands.add_parser("orders", help="Post synthetic orders at a steady rate")
    orders.add_argument("--rate", type=float, default=float(os.getenv("SIM_ORDERS_PER_MIN", 6)), help="orders per minute")
    orders.add_argument("--count", type=int, help="stop after this many orders")
    orders.add_argument("--seed", type=int, default=int(os.environ["SIM_SEED"]) if os.getenv("SIM_SEED") else None)
    orders.set_defaults(handler=cmd_orders)

    trigger = commands.add_parser("trigger", help="Raise an exception on a task's active assignment now")
    trigger.add_argument("--task-id", type=int, required=True)
    trigger.add_argument("--type", choices=["stockout", "jam", "worker_down"], required=True)
    trigger.add_argument("--qty-found", type=int, help="units found in the bin (stockout; default 0)")
    trigger.set_defaults(handler=cmd_trigger)

    demo = commands.add_parser("demo", help="Offline end-to-end demo on a local SQLite file (no server, no Firebase)")
    demo.add_argument("--orders", type=int, default=15)
    demo.add_argument("--db", type=Path, default=Path("demo.db"), help="SQLite file, wiped each run (default demo.db)")
    demo.add_argument("--max-seconds", type=float, default=900, help="stop after this much simulated time")
    _add_simulator_flags(demo)
    demo.set_defaults(handler=cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse the command line, run the chosen command, and return its exit code (0 = success)."""
    # Print log lines as "time logger-name message".
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    # Hide httpx's line-per-request logging.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if sys.argv[1:2] == ["demo"] or (argv or [])[:1] == ["demo"]:
        # The demo prints its own summary; per-task log lines would bury it.
        logging.getLogger("flowforge").setLevel(logging.WARNING)
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except RuntimeError as exc:
        # e.g. missing SIM_EMAIL: show the message, not a traceback.
        print(exc, file=sys.stderr)
        return 1


# Runs only when started as `python -m app.modules.simulation.cli`, not when imported.
if __name__ == "__main__":
    sys.exit(main())
