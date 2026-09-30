# FlowForge

Warehouse execution control tower: orders become pick tasks, a greedy assigner
hands them to workers and robots, a simulator executes them, and a supervisor
watches and steers it all from a live console.

| Part | Stack | Hosting |
|---|---|---|
| `frontend/` | Next.js (App Router), TypeScript, Tailwind | Vercel |
| `backend/` | FastAPI, SQLAlchemy, Alembic | Cloud Run |
| Database | MySQL (SQLite locally by default) | Cloud SQL |
| Auth | Firebase (supervisor role) | |

## Backend

Requires Python 3.11+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # defaults work locally
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

- Health check: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs
- Tests: `pytest` (from `backend/`)

## Frontend

Requires Node 20+.

```bash
cd frontend
npm install
cp .env.example .env.local         # add the Firebase web config
npm run dev
```

Open http://localhost:3000. The home page shows whether it can reach the backend.

## Layout

Code is organized by feature so each person works in their own folder
(owners are in [`.github/CODEOWNERS`](.github/CODEOWNERS)).

- `backend/app/core/`: config, database session, Firebase token check (shared)
- `backend/app/modules/<feature>/`: `router.py`, `models.py`, `schemas.py`, `service.py`
- `frontend/app/console/<feature>/`: console panels
- `frontend/lib/`: API client and Firebase setup

To add a backend feature, work inside its module. Its router is already
registered in `backend/app/main.py`.
