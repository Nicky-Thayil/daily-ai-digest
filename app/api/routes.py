"""
app/api/routes.py

API routes for the AI Digest Assistant.
"""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query

from app.config.loader import load_topics
from app.services.fetcher import fetch_all_feeds
from app.services.deduplicator import deduplicate
from app.services.summarizer import summarize

router = APIRouter()


@router.get("/test/fetch")
async def test_fetch(
    topic_id: str = Query(default=None, description="Filter to a single topic id, e.g. 'ai'")
):
    """
    Trigger a live RSS fetch and return raw results (no deduplication).
    Useful for checking feed health.
    """
    topics_data = load_topics()

    if topic_id:
        matched = [t for t in topics_data["topics"] if t["id"] == topic_id]
        if not matched:
            raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")
        topics_data = {"topics": matched}

    articles = await fetch_all_feeds(topics_data)

    return {
        "count": len(articles),
        "articles": [asdict(a) for a in articles],
    }


@router.get("/test/dedupe")
async def test_dedupe(
    topic_id: str = Query(default=None, description="Filter to a single topic id, e.g. 'ai'")
):
    """
    Fetch and deduplicate articles. Shows before/after counts per topic.
    """
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
async def test_summarize(
    topic_id: str = Query(default=None, description="Filter to a single topic id, e.g. 'ai'")
):
    """
    Fetch, deduplicate, and summarize articles using GPT-4o-mini.
    Returns the full digest with bullet points per topic.

    Tip: test with a single topic first to avoid burning tokens on all 9.
    e.g. GET /test/summarize?topic_id=ai
    """
    topics_data = load_topics()

    if topic_id:
        matched = [t for t in topics_data["topics"] if t["id"] == topic_id]
        if not matched:
            raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")
        topics_data = {"topics": matched}

    articles = await fetch_all_feeds(topics_data)
    deduped = deduplicate(articles)
    digest = await summarize(deduped, topics_data)

    return {
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