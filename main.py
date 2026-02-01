# main.py
from fastapi import FastAPI

from routers.projects import router as projects_router
from routers.chat_router import router as chat_router

app = FastAPI(title="Real Estate Agent API")

app.include_router(projects_router)
app.include_router(chat_router)

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "realestate_agent_v1"
    }
