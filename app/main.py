from fastapi import FastAPI
from app.config.loader import load_topics

app = FastAPI(
    title="AI Digest Assistant",
    description="Automated content aggregation with AI-powered summaries",
    version="0.1.0"
)

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