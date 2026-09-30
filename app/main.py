from fastapi import FastAPI

app = FastAPI(title="FlowForge Server")

workers = [
    {
        "id": 1,
        "name": "Worker 1",
        "type": "human",
        "speed": 2,
        "cur_x": 3,
        "cur_y": 2,
        "status": "idle",
        "enabled": True,
    },
    {
        "id": 2,
        "name": "Robot 1",
        "type": "robot",
        "speed": 4,
        "cur_x": 15,
        "cur_y": 9,
        "status": "idle",
        "enabled": True,
    },
    {
        "id": 3,
        "name": "Worker 2",
        "type": "human",
        "speed": 3,
        "cur_x": 7,
        "cur_y": 5,
        "status": "busy",
        "enabled": True,
    },
]


@app.get("/api/workers")
def get_workers():
    return workers