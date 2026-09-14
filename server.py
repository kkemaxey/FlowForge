from fastapi import FastAPI


app = FastAPI(title="FlowForge API")


@app.get("/")
def get_api_info() -> dict[str, str]:
	return {
		"message": "FlowForge API is running",
		"workers_endpoint": "/api/workers",
		"docs": "/docs",
	}

workers = [
	{
		"id": "worker-001",
		"name": "Ada",
		"role": "Data Engineer",
		"status": "available",
	},
	{
		"id": "worker-002",
		"name": "Grace",
		"role": "Backend Engineer",
		"status": "busy",
	},
	{
		"id": "worker-003",
		"name": "Linus",
		"role": "Platform Engineer",
		"status": "available",
	},
]

@app.get("/api/workers")
def get_workers() -> dict[str, list[dict[str, str]]]:
    return {"workers": workers}


if __name__ == "__main__":
	import uvicorn

	uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
