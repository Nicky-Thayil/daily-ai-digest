"""
app/main.py

Main FastAPI application entry point.
"""

from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from app.config.loader import load_topics
from app.api.routes import router

app = FastAPI(
    title="AI Digest Assistant",
    description="Automated content aggregation with AI-powered summaries",
    version="0.1.0"
)

app.include_router(router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup checks
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in .env")
    yield
    
@app.get("/")
def root():
    return {
        "message": "AI Digest Assistant API",
        "status": "healthy"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/config/topics")
def get_topics():
    return load_topics()