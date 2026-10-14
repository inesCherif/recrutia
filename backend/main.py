"""
Recrutia — FastAPI Backend Entry Point
==========================================
Run with: uvicorn backend.main:app --reload --port 8000
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env BEFORE anything else

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import auth, chat, recruiter, student, upload

app = FastAPI(
    title="Recrutia API",
    description="AI-powered recruitment platform — Multi-Agent backend",
    version="2.0.0",
)

# --- CORS (allow the React frontend) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mount Routers ---
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(recruiter.router)
app.include_router(student.router)
app.include_router(upload.router)


@app.get("/")
def root():
    return {
        "app": "Recrutia API",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "running"
    }
