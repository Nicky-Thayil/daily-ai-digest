# Flash (AI Digest Assistant)

An AI-powered content aggregation service that fetches articles from curated RSS feeds across 9 topics, deduplicates similar stories, and delivers a daily bullet-point digest — reducing 90 minutes of manual reading to under 5.

**Live frontend:** https://daily-ai-digest-sigma.vercel.app  
**Live API:** https://ai-digest-api-luqeb425fa-uc.a.run.app  
**Interactive docs:** https://ai-digest-api-luqeb425fa-uc.a.run.app/docs

---

## Overview

The platform has two independent services:

- **API service** — FastAPI on Cloud Run. Accepts digest generation requests, enqueues them as Celery tasks, and serves stored digests from PostgreSQL with clean REST semantics.
- **Worker service** — Celery worker on Cloud Run. Runs the full pipeline asynchronously: RSS fetch → deduplication → GPT-4o-mini summarisation → persist to DB.

---

## Architecture

```text
Browser (React + Vite)
        ↓ HTTP
Cloud Run Service — FastAPI
        ↓ enqueue          ↓ reads
    Redis (Upstash)    PostgreSQL (Supabase)
        ↓ consume          ↑ writes
Cloud Run Service — Celery Worker
        ↓ fetches from
    RSS Feeds (20+ sources)
        ↓ summarises via
    OpenAI API (GPT-4o-mini)
```

---

## Tech Stack

**Language:** Python 3.11  
**Framework:** FastAPI  
**Task Queue:** Celery + Redis  
**Database:** PostgreSQL · SQLAlchemy · asyncpg  
**AI:** OpenAI API (GPT-4o-mini)  
**Infrastructure:** Google Cloud Run · Artifact Registry · GitHub Actions  
**Managed Services:** Supabase · Upstash  
**Frontend:** React 18 · Vite · CSS Modules  
**Other:** Docker · Alembic

---

## Topics

AI · Programming · Space · Football · Cars · Food · Physics · Mathematics · Biology

Topics and RSS sources are configured via `app/config/topics.json`. Each topic can be individually enabled or disabled.

---

## Local Development

Copy `.env.example` to `.env` and fill in the values.

```bash
# Terminal 1 — API
uvicorn app.main:app --reload

# Terminal 2 — Celery worker
celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=solo

# Terminal 3 — Frontend
cd frontend && npm run dev
```

Or with Docker:

```bash
docker-compose up --build
cd frontend && npm run dev
```

---

## Deployment

Pushing to `main` triggers GitHub Actions, which builds the Docker image, pushes it to Artifact Registry, and deploys both Cloud Run services automatically.

GitHub Actions authenticates to GCP via Workload Identity Federation — no long-lived service account keys stored anywhere.

---

## Future Plans

- Topic management UI (add/remove/toggle topics without editing JSON)
- Per-topic article source health monitoring
