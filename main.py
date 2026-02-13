# main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.leads import router as leads_router

from routers.projects import router as projects_router
from routers.chat_router import router as chat_router

load_dotenv()

app = FastAPI(title="Real Estate Agent API")

# ---- CORS (Render/Vercel friendly) ----
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routes ----
app.include_router(projects_router)
app.include_router(chat_router)

@app.get("/")
def root():
    return {"status": "ok", "service": "realestate_agent_v1"}

@app.get("/health")
def health():
    return {"status": "ok"}
