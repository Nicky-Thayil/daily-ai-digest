"""
API endpoints for digest generation and retrieval.
"""

from dataclasses import asdict
from typing import Annotated

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.loader import load_topics
from app.db.database import get_db
from app.db.repository import (
    get_digest_by_id,
    get_latest_digest,
    list_digests,
    save_digest,
)
from app.services.deduplicator import deduplicate
from app.services.fetcher import fetch_all_feeds
from app.services.summarizer import summarize
from app.workers.tasks import generate_digest

router = APIRouter()

DBSession = Annotated[AsyncSession, Depends(get_db)]

# Test / pipeline endpoints
@router.get("/test/fetch")
async def test_fetch(topic_id: str | None = None):
    """Raw RSS fetch — no deduplication, no DB."""
    topics_data = load_topics()
    if topic_id:
        matched = [t for t in topics_data["topics"] if t["id"] == topic_id]
        if not matched:
            raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")
        topics_data = {"topics": matched}

    articles = await fetch_all_feeds(topics_data)
    return {"count": len(articles), "articles": [asdict(a) for a in articles]}


@router.get("/test/dedupe")
async def test_dedupe(topic_id: str | None = None):
    """Fetch + deduplicate. Shows before/after counts per topic."""
    topics_data = load_topics()
    if topic_id:
        matched = [t for t in topics_data["topics"] if t["id"] == topic_id]
        if not matched:
            raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")
        topics_data = {"topics": matched}

    articles = await fetch_all_feeds(topics_data)
    deduped = deduplicate(articles)

    before_by_topic: dict[str, int] = {}
    for a in articles:
        before_by_topic[a.topic] = before_by_topic.get(a.topic, 0) + 1

    after_by_topic: dict[str, int] = {}
    for a in deduped:
        after_by_topic[a.topic] = after_by_topic.get(a.topic, 0) + 1

    topic_summary = [
        {
            "topic": topic,
            "before": before_by_topic.get(topic, 0),
            "after": after_by_topic.get(topic, 0),
            "removed": before_by_topic.get(topic, 0) - after_by_topic.get(topic, 0),
        }
        for topic in before_by_topic
    ]

    return {
        "total_before": len(articles),
        "total_after": len(deduped),
        "total_removed": len(articles) - len(deduped),
        "by_topic": topic_summary,
        "articles": [asdict(a) for a in deduped],
    }


@router.get("/test/summarize")
async def test_summarize(db: DBSession, topic_id: str | None = None):
    """Run the full digest pipeline inline (fetch → dedupe → summarize → persist)."""
    topics_data = load_topics()
    if topic_id:
        matched = [t for t in topics_data["topics"] if t["id"] == topic_id]
        if not matched:
            raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")
        topics_data = {"topics": matched}

    articles = await fetch_all_feeds(topics_data)
    deduped = deduplicate(articles)
    digest = await summarize(deduped, topics_data)
    db_digest = await save_digest(db, digest, deduped)

    return {
        "digest_id": db_digest.id,
        "generated_at": digest.generated_at.isoformat(),
        "total_articles_summarized": digest.total_articles_summarized,
        "topics": [
            {
                "topic_id": t.topic_id,
                "topic_name": t.topic_name,
                "article_count": t.article_count,
                "bullets": t.bullets,
            }
            for t in digest.topics
        ],
    }


# Async digest generation (Celery)
@router.post("/digest/generate", status_code=202)
async def trigger_digest(topic_id: str | None = None):
    """Enqueue a digest generation task and return a task_id immediately."""
    task = generate_digest.delay(topic_id=topic_id)
    return {
        "task_id": task.id,
        "status": "queued",
        "message": "Digest generation started. Poll /digest/status/{task_id} for updates.",
    }


@router.get("/digest/status/{task_id}")
async def get_task_status(task_id: str):
    """Return the current status of a digest task (pending/started/progress/success/failure)."""
    result = AsyncResult(task_id, app=generate_digest.app)
    state = result.state

    if state == "PENDING":
        return {"task_id": task_id, "status": "pending", "detail": "Task queued, waiting for worker"}

    if state == "STARTED":
        return {"task_id": task_id, "status": "started", "detail": "Worker has picked up the task"}

    if state == "PROGRESS":
        return {"task_id": task_id, "status": "progress", "detail": result.info.get("status", "")}

    if state == "SUCCESS":
        return {
            "task_id": task_id,
            "status": "success",
            "result": result.result,
        }

    if state == "FAILURE":
        return {
            "task_id": task_id,
            "status": "failed",
            "error": str(result.result),
        }

    return {"task_id": task_id, "status": state.lower()}


# Digest retrieval endpoints
@router.get("/digest/latest")
async def get_latest(db: DBSession):
    """Return the most recently generated digest from the database."""
    digest = await get_latest_digest(db)
    if not digest:
        raise HTTPException(
            status_code=404,
            detail="No digest found. Run POST /digest/generate to create one."
        )
    return _format_digest(digest)


@router.get("/digest/{digest_id}")
async def get_digest(digest_id: int, db: DBSession):
    """Return a specific digest by ID."""
    digest = await get_digest_by_id(db, digest_id)
    if not digest:
        raise HTTPException(
            status_code=404,
            detail=f"No digest found with id={digest_id}."
        )
    return _format_digest(digest)


@router.get("/digests")
async def list_all_digests(db: DBSession, limit: int = 10):
    """List the most recent digest runs (metadata)."""
    digests = await list_digests(db, limit=limit)
    if not digests:
        raise HTTPException(
            status_code=404,
            detail="No digests found. Run POST /digest/generate to create one."
        )
    return [
        {
            "digest_id": d.id,
            "generated_at": d.generated_at.isoformat(),
            "total_articles_summarized": d.total_articles_summarized,
        }
        for d in digests
    ]


# Internal helpers
def _format_digest(digest) -> dict:
    return {
        "digest_id": digest.id,
        "generated_at": digest.generated_at.isoformat(),
        "total_articles_summarized": digest.total_articles_summarized,
        "topics": [
            {
                "topic_id": t.topic_id,
                "topic_name": t.topic_name,
                "article_count": t.article_count,
                "bullets": t.bullets,
            }
            for t in digest.topic_digests
        ],
    }