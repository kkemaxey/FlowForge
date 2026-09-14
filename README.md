# FlowForge Server - Project Test

A FastAPI server for the FlowForge Warehouse Execution Control Tower project.

This server currently provides a GET endpoint that returns hard-coded warehouse worker and robot data.

## Prerequisites

- macOS
- Python 3.9 or newer
- Git
- Internet connection for installing Python packages

Verify you have what you need:

```bash
python3 --version
git --version
```

## Project Structure

```text
FlowForge/
├── app/
│   ├── __init__.py
│   └── main.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Setup

Clone the repository and move into it. The server lives on the `trentg`
branch, so check that branch out as part of the clone:

```bash
git clone -b trentg https://github.com/kkemaxey/FlowForge.git
cd FlowForge
```

Confirm you have the right files:

```bash
ls
# app  README.md  requirements.txt
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Your shell prompt should now start with `(.venv)`.

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Running the Server

With the virtual environment active, from the project root:

```bash
uvicorn app.main:app --reload
```

You should see output ending with:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Leave this running. The server reloads automatically when you edit files in `app/`.

## Getting a Response

In a **second** terminal window:

```bash
curl http://127.0.0.1:8000/api/workers
```

Expected response:

```json
[
  {"id":1,"name":"Work 1","type":"human","speed":1,"cur_x":0,"cur_y":0,"status":"idle","enabled":true},
  {"id":2,"name":"Romba 1","type":"robot","speed":5,"cur_x":1,"cur_y":1,"status":"idle","enabled":true},
  {"id":3,"name":"Romba 2","type":"human","speed":5,"cur_x":2,"cur_y":2,"status":"busy","enabled":true}
]
```

You can also open the endpoint in a browser at
<http://127.0.0.1:8000/api/workers>, or use the auto-generated interactive
docs at <http://127.0.0.1:8000/docs> to send the request from a web page.

## API Endpoints

| Method | Path           | Description                                  |
| ------ | -------------- | -------------------------------------------- |
| GET    | `/api/workers` | Returns the hard-coded list of workers/robots |

### Worker fields

| Field     | Type    | Description                            |
| --------- | ------- | -------------------------------------- |
| `id`      | int     | Unique identifier                      |
| `name`    | string  | Display name                           |
| `type`    | string  | `human` or `robot`                     |
| `speed`   | int     | Movement speed                         |
| `cur_x`   | int     | Current X position on the warehouse grid |
| `cur_y`   | int     | Current Y position on the warehouse grid |
| `status`  | string  | `idle` or `busy`                       |
| `enabled` | bool    | Whether the worker is active           |

## Stopping the Server

Press `CTRL+C` in the terminal running uvicorn, then deactivate the
virtual environment:

```bash
deactivate
```

## Troubleshooting

**`command not found: uvicorn`** — the virtual environment is not active. Run
`source .venv/bin/activate` from the project root and try again.

**`Error loading ASGI app. Could not import module "app.main".`** — you are not
in the project root. `cd` to the directory containing `requirements.txt`.

**`[Errno 48] Address already in use`** — port 8000 is taken. Start on a
different port and use it in your `curl`:

```bash
uvicorn app.main:app --reload --port 8001
```

**`{"detail":"Not Found"}`** — check the URL. The path is `/api/workers`, not `/workers`.
