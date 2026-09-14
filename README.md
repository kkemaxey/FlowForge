# FlowForge

FlowForge is a small FastAPI server that provides a worker directory. The
`GET /api/workers` endpoint is a read operation that returns worker records as
JSON.

## Prerequisites

Install these before starting:

- Python 3.10 or newer
- Git
- `curl` for the example request (usually preinstalled on Linux and macOS)

## Install

Clone the repository and change into its directory:

```bash
git clone https://github.com/kkemaxey/FlowForge.git
cd FlowForge
```

Create a virtual environment and activate it:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies from the repository root:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

Start the server from the repository root:

```bash
python server.py
```

The server listens on `http://127.0.0.1:8000`. Keep this terminal running
while making requests. The interactive API documentation is available at
`http://127.0.0.1:8000/docs`.

## Example Request

In a second terminal, from any directory, run:

```bash
curl http://127.0.0.1:8000/api/workers
```

The server returns:

```json
{
	"workers": [
		{
			"id": "worker-001",
			"name": "Ada",
			"role": "Data Engineer",
			"status": "available"
		},
		{
			"id": "worker-002",
			"name": "Grace",
			"role": "Backend Engineer",
			"status": "busy"
		},
		{
			"id": "worker-003",
			"name": "Linus",
			"role": "Platform Engineer",
			"status": "available"
		}
	]
}
```

## Fresh Clone Check

Before submitting, verify the instructions in a new directory:

```bash
git clone https://github.com/kkemaxey/FlowForge.git flowforge-test
cd flowforge-test
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python server.py
```

Then, in a second terminal, run the example request above and confirm that it
returns the three worker records shown above.