"""
FastAPI application entrypoint.
"""

from contextlib import asynccontextmanager
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.loader import load_topics
from app.api.routes import router
from app.db.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in .env")
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set in .env")

    print("✅ Startup checks passed")
    yield

    await engine.dispose()
    print("🔌 Database engine disposed")


app = FastAPI(
    title="AI Digest Assistant",
    description="Automated content aggregation with AI-powered summaries",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS so the browser allows frontend (5173) to call backend (8000) across origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "AI Digest Assistant API", "status": "healthy"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/config/topics")
def get_topics():
    return load_topics()