# FlowForge Server - Project Test

A FastAPI server for the FlowForge Warehouse Execution Control Tower project.

This server currently provides a GET endpoint that returns hard-coded warehouse worker and robot data.

## Prerequisites

- macOS, or Windows 10/11
- Python 3.9 or newer
  - **Windows:** install from <https://www.python.org/downloads/> and check
    **"Add python.exe to PATH"** on the first installer screen.
- Git
- Internet connection for installing Python packages

Commands below are given for both platforms. On macOS use **Terminal**; on
Windows use **PowerShell**.

Verify you have what you need:

**macOS**

```bash
python3 --version
git --version
```

**Windows (PowerShell)**

```powershell
python --version
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

Confirm you have the right files. You should see `app`, `README.md`, and
`requirements.txt`:

```bash
ls
```

Create and activate a virtual environment:

**macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

The `Set-ExecutionPolicy` line only affects the current PowerShell window; it
allows the activation script to run.

Your prompt should now start with `(.venv)`.

Install the dependencies (same command on both platforms):

```bash
pip install -r requirements.txt
```

## Running the Server

With the virtual environment active, from the project root (same command on
both platforms):

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

**macOS**

```bash
curl http://127.0.0.1:8000/api/workers
```

**Windows (PowerShell)**

```powershell
curl.exe http://127.0.0.1:8000/api/workers
```

Type `curl.exe`, not `curl` — in PowerShell, plain `curl` is a different command
that prints a formatted object instead of the raw JSON.

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

**`command not found: uvicorn`** (macOS) or **`uvicorn : The term 'uvicorn' is not
recognized`** (Windows) — the virtual environment is not active. From the project
root, run `source .venv/bin/activate` (macOS) or
`.venv\Scripts\Activate.ps1` (Windows) and try again.

**`running scripts is disabled on this system`** (Windows) — run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that same
PowerShell window, then activate again.

**`Python was not found; run without arguments to install from the Microsoft
Store`** (Windows) — Python is not on your PATH. Re-run the python.org installer,
choose **Modify**, and enable **"Add Python to environment variables"**, then
open a new PowerShell window.

**`Error loading ASGI app. Could not import module "app.main".`** — you are not
in the project root. `cd` to the directory containing `requirements.txt`.

**`[Errno 48] Address already in use`** (macOS) or **`[WinError 10048]`**
(Windows) — port 8000 is taken. Start on a
different port and use it in your `curl`:

```bash
uvicorn app.main:app --reload --port 8001
```

**`{"detail":"Not Found"}`** — check the URL. The path is `/api/workers`, not `/workers`.
