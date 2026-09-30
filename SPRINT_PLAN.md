# FlowForge Sprint Plan

Sep 30, 2026 · @Kanayo Egwuekwe-Maxey

This is the FlowForge team's sprint-by-sprint plan from foundation to the Dec 1, 2026 code freeze. It turns the roadmap in the project context into concrete goals and to-dos for each two-week sprint, so all six team members know what "done" looks like each sprint and who owns each piece.

How to use it:

- **Sprint planning:** at the start of each sprint, review that sprint's section and turn its checklist into GitHub issues.
- **Progress tracking:** tick checklist items as PRs merge. Anything unticked at sprint end carries over or is cut as a team decision.
- **Scope guard:** baseline (MVP) work always comes before growth, and growth before stretch. Stretch work does not start until Sprint 2's MVP checkpoint passes.
- **Ownership:** names in parentheses match CODEOWNERS. Cross-module work goes through a PR the owning module's person reviews.

Each sprint lists its main goal, a description, the frontend and backend features involved, and a checklist.

## Sprint 0: Foundation (Sept 17–24)

**Main goal:** Get a working skeleton deployed, with all six people able to contribute.

**Description:** Set up the repo, tooling, infrastructure and auth. No product features yet. At the end, a logged-in supervisor can open a deployed frontend that talks to a deployed backend and database, and CI runs on every PR.

**Front end features involved**

- Next.js App Router scaffold in the feature-folder layout (`console/grid-map`, `controls`, `live-board`, `workforce`, `(auth)/login`)
- Shared `components/ui`, `lib/api-client.ts`, `lib/firebase.ts`, `types/`
- Login page wired to Firebase

**Back end features involved**

- FastAPI app factory (`main.py`) with an empty router for each module
- `core/config.py`, `core/database.py`, `core/security.py` (Firebase token check)
- Cloud SQL MySQL connection with Alembic set up
- CORS configured for the Vercel domain

**Checklist**

- [X] Create the repo, give all 6 members access, and turn on branch protection for `main`
- [X] Add the `CODEOWNERS` file that encodes the ownership table
- [X] Scaffold the monorepo (`backend/`, `frontend/`)
- [X] Scaffold every backend module folder with `router.py`, `models.py`, `schemas.py`, `service.py`
- [X] Scaffold the frontend feature folders
- [ ] Provision Cloud SQL (MySQL) and run the first Alembic migration
- [ ] Set up env vars and secrets (local `.env`, Cloud Run secrets, Vercel env)
- [ ] Wire Firebase auth end to end: login page → token → backend `security.py` check
- [ ] Configure CORS between frontend and backend
- [ ] Add a GitHub Actions workflow that runs pytest on PRs
- [ ] Add a Dockerfile for the backend (Trent)
- [ ] Deploy the skeleton to Vercel and Cloud Run
- [X] Add a `/health` endpoint and have the frontend call it

## Sprint 1: Thin Vertical Slice (Sept 24–Oct 8)

**Main goal:** Follow one order on screen from "placed" to "complete."

**Description:** Build the smallest end-to-end version of the core loop. Each stage only needs a happy path: order intake, task generation, greedy assignment, simulated execution, and a read-only console behind login. No exceptions, no supervisor controls and no polish yet.

**Front end features involved**

- Read-only console page, gated by auth
- Basic live board: list of orders and tasks with their status
- Basic grid map or worker list showing each worker's status (idle or busy)
- Shared TS types for Order, Task and Worker

**Back end features involved**

- **orders:** `POST /orders` (order plus order lines), `GET /orders`; models and migration
- **tasks:** turn each order into pick tasks; state machine `open → assigned → picked → complete`
- **assignment:** greedy loop that gives open tasks to idle workers
- **simulation:** worker simulator that moves tasks through their states over time (happy path only)
- **workforce:** seeded workers/robots (the minimum the assigner needs)
- **events:** basic event log of state changes
- **auth:** every console endpoint protected

**Checklist**

- [ ] Order and OrderLine models, migration, intake endpoint (Kanayo)
- [ ] Task model and state machine; generate tasks when an order arrives (Kanayo)
- [ ] Greedy assigner that runs on a loop or tick (Kanayo)
- [ ] Worker simulator for the happy path: assigned → picked → complete (Kendyn)
- [ ] Basic event logging on each transition (Kendyn)
- [ ] Worker model and seed data (Trent)
- [ ] Auth dependency applied to all console routes (Brock)
- [ ] Console layout and grid map/worker status view (Aalan)
- [ ] Live board showing order and task statuses with polling (Jayden)
- [ ] pytest for the task state machine and the greedy assignment basics (Trent)
- [ ] Order generator script or endpoint for demos
- [ ] **Checkpoint:** place one order and watch it complete on the deployed console

## Sprint 2: Finish MVP Baseline (Oct 8–22)

**Main goal:** Meet the Definition of Done for the entire MVP.

**Description:** Fill in every baseline requirement: workforce CRUD, supervisor reassign and expedite controls, a polished live board with throughput and WIP, one full exception flow (stockout or worker-down) with automatic reassignment, and solid test coverage. The sprint ends with a full demo against the Definition of Done. This is the gate before any growth work starts.

**Front end features involved**

- Workforce CRUD forms with validation
- Reassign and expedite controls
- Live board with throughput and WIP metrics
- Console highlights the exception or bottleneck when one fires

**Back end features involved**

- **workforce:** full CRUD endpoints with validation
- **tasks/assignment:** reassign and expedite endpoints; expedited tasks get priority
- **simulation:** one exception type end to end (stockout or worker-down), with automatic reassignment when it fires
- **events:** metrics (throughput, WIP, task counts per state)

**Checklist**

- [ ] Team decision: stockout or worker-down for the MVP exception (Kendyn)
- [ ] Workforce CRUD API with validation (Trent)
- [ ] Workforce CRUD frontend forms (Trent)
- [ ] Reassign and expedite endpoints; greedy assigner respects priority (Kanayo)
- [ ] Reassign and expedite UI controls (Aalan)
- [ ] Exception trigger, detection and automatic reassignment of the affected task (Kendyn, with Kanayo)
- [ ] Metrics/events endpoint for throughput and WIP (Kendyn)
- [ ] Throughput and WIP views on the live board (Jayden)
- [ ] Console flags the exception visually (Aalan/Jayden)
- [ ] Auth hardening: supervisor role check, handling of expired tokens (Brock)
- [ ] pytest coverage of the assignment loop, state transitions and exception flow (Trent)
- [ ] **Checkpoint:** full MVP demo against the Definition of Done

## Sprint 3: Harden and Start Growth Goals (Oct 22–Nov 5)

**Main goal:** Make the MVP solid, then start 1–2 growth goals.

**Description:** Start with a bug bash on everything built so far: edge cases, race conditions in the assigner and simulator, and UI rough spots. Once the MVP is stable, the team picks 1–2 growth goals and starts on them.

**Front end features involved (depending on the growth goals picked)**

- SLA and due-time indicators on orders
- Bottleneck highlighting by zone or aisle on the grid map
- Wave view on the live board

**Back end features involved (depending on the growth goals picked)**

- Wave/batch planning in tasks/assignment
- A second exception type in simulation
- SLA tracking (order due times, at-risk detection)
- Bottleneck metrics by zone or aisle in events

**Checklist**

- [ ] Team-wide bug bash; file and triage issues
- [ ] Fix every MVP-critical bug before starting growth work
- [ ] Check deploy stability (Cloud Run cold starts, DB connection pooling)
- [ ] Team meeting to pick 1–2 growth goals
- [ ] Break the chosen goals into issues with owners
- [ ] Start building the growth goals
- [ ] Extend pytest to cover the new code

## Sprint 4: Growth Wrap-up and Stretch if Ahead (Nov 5–19)

**Main goal:** Finish the growth goals and run a full mock demo.

**Description:** Complete and polish the growth features, then run a full mock demo dry run to find problems early. Stretch work only happens if there is real slack and the MVP plus growth goals are solid.

**Front end features involved**

- Polish on the growth-goal UI
- Stretch, only if ahead: throughput comparison view (greedy vs. improved), map upload screen

**Back end features involved**

- Finish the growth-goal logic
- Stretch, only if ahead: BFS/Dijkstra pathfinding over the aisle graph; "beat the greedy" with batch/zone picking or nearest-neighbor; variable worker speeds

**Checklist**

- [ ] Finish and merge the growth-goal features
- [ ] Full mock demo dry run following the Definition of Done script
- [ ] File and fix issues found in the dry run
- [ ] Go/no-go call on stretch goals as a team
- [ ] Stretch work (Kanayo: pathfinding, beat the greedy), only with a clear yes
- [ ] Test coverage for the growth features

## Sprint 5: Freeze Prep (Nov 19–Dec 1)

**Main goal:** Ship a stable, demo-ready build by the Dec 1 code freeze.

**Description:** A hard feature freeze lands a few days into the sprint. After that, only bug fixes, deploy stability and demo rehearsal. No new scope.

**Front end features involved**

- Bug fixes and visual polish only

**Back end features involved**

- Bug fixes and stability only

**Checklist**

- [ ] Announce the hard feature freeze date (about Nov 22)
- [ ] Fix remaining bugs by priority
- [ ] Verify the production deploy: env vars, DB migrations, auth domains
- [ ] Seed realistic demo data and build a reliable demo order generator
- [ ] Write the demo script: orders → tasks → assignment → exception → auto-reassign → supervisor expedite
- [ ] At least 2 full demo rehearsals
- [ ] Update the README and setup docs
- [ ] Final green CI run on `main` and tag the release
- [ ] **Dec 1: code freeze**
