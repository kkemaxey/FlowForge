from fastapi import FastAPI
app = FastAPI(title="FlowForge CSC460 Server")

workers = [
    {
        "id": 1,
        "name": "Work 1",
        "type": "human",
        "speed": 1,
        "cur_x": 0,
        "cur_y": 0,
        "status": "idle",
        "enabled": True
    },
    {
        "id": 2,
        "name": "Romba 1",
        "type": "robot",
        "speed": 5,
        "cur_x": 1,
        "cur_y": 1,
        "status": "idle",
        "enabled": True
    },
    {
        "id": 3,
        "name": "Romba 2",
        "type": "human",
        "speed": 5,
        "cur_x": 2,
        "cur_y": 2,
        "status": "busy",
        "enabled": True
    }
]

@app.get("/api/workers")
def get_workers():
    return workers