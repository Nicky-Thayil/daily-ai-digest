"""
Celery task definitions.
"""

import asyncio
import logging
import os

from celery import states

from app.workers.celery_app import celery_app
from app.config.loader import load_topics
from app.db.database import AsyncSessionLocal
from app.db.repository import save_digest
from app.services.deduplicator import deduplicate
from app.services.fetcher import fetch_all_feeds
from app.services.summarizer import summarize

logger = logging.getLogger(__name__)


async def _run_pipeline(topic_id: str | None) -> dict:
    """Run the full digest generation pipeline."""
    topics_data = load_topics()

    if topic_id:
        matched = [t for t in topics_data["topics"] if t["id"] == topic_id]
        if not matched:
            raise ValueError(f"Topic '{topic_id}' not found")
        topics_data = {"topics": matched}

    articles = await fetch_all_feeds(topics_data)
    deduped = deduplicate(articles)
    digest = await summarize(deduped, topics_data)

    # DB session managed manually
    async with AsyncSessionLocal() as session:
        try:
            db_digest = await save_digest(session, digest, deduped)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    return {
        "digest_id": db_digest.id,
        "generated_at": digest.generated_at.isoformat(),
        "total_articles_summarized": digest.total_articles_summarized,
        "topic_count": len(digest.topics),
    }


@celery_app.task(
    bind=True,
    name="app.workers.tasks.generate_digest",
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=10,
)
def generate_digest(self, topic_id: str | None = None) -> dict:
    """Runs the full digest pipeline asynchronously."""
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Fetching RSS feeds..."}
        )
        logger.info("Starting digest generation (topic_id=%s)", topic_id)

        result = asyncio.run(_run_pipeline(topic_id))

        logger.info("Digest generation complete: digest_id=%s", result["digest_id"])
        return result

    except ValueError as e:
        # No retry on invalid input
        self.update_state(state=states.FAILURE, meta={"error": str(e)})
        raise
    except Exception as e:
        logger.error("Digest generation failed: %s", e)
        raise