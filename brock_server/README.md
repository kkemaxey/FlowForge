# Morehouse Ultimate Roster API

A small server, written in Python with Flask, that answers one real request:
it returns the team roster as JSON. This is a read operation (the **R** in CRUD).

> **Author:** Brock Caston Jr.

---

## How to start it (fresh clone → response)

These steps take you from a clean clone to a live response. All commands are run
from **inside this folder** (`brock_server/`).

### Prerequisites

- **Python 3.9 or newer** (developed and tested on Python 3.11).
  Check what you have:
  ```
  python --version
  ```
  If `python` is not found, try `python3 --version`. On some systems the
  command is `python3`; use whichever one reports 3.9+ and use it consistently
  below.
- No database, no other tools to install — everything else comes from the
  install step.

### Install

From the repository root, move into this folder and install the one dependency:

```
cd brock_server
python -m pip install -r requirements.txt
```

(Optional but recommended — install into a virtual environment so nothing is
added to your system Python:)

```
cd brock_server
python -m venv venv

# macOS / Linux:
source venv/bin/activate
# Windows (PowerShell):
venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
```

### Run

```
python app.py
```

The server starts and listens on **port 5000**. You should see a line like:

```
 * Running on http://127.0.0.1:5000
```

Leave it running and open a second terminal for the request below.

### Example request

Ask the server for the roster:

```
curl http://localhost:5000/api/players
```

Response (`200 OK`, `application/json`):

```json
{
  "count": 8,
  "players": [
    {
      "id": 1,
      "name": "Brock Caston Jr.",
      "number": 7,
      "position": "handler",
      "class_year": "Junior",
      "captain": true
    },
    {
      "id": 2,
      "name": "Marcus Ellison",
      "number": 3,
      "position": "cutter",
      "class_year": "Senior",
      "captain": true
    }
  ]
}
```

(The response above is trimmed — the live endpoint returns all 8 players.)

---

## All endpoints

| Method & path            | What it returns                                  |
|--------------------------|--------------------------------------------------|
| `GET /`                  | A small index describing the API                 |
| `GET /api/players`       | The full roster (the main read endpoint)         |
| `GET /api/players/<id>`  | One player by id, or `404` if no such player     |

Try a single player:

```
curl http://localhost:5000/api/players/1
```

---

## Notes

- The roster is hard-coded in `app.py` for now. That is intentional for this
  assignment — it is the data that a database would hold in a later week.
- The server binds to `0.0.0.0`, so it starts and answers the same way on a
  machine other than the one it was written on.
