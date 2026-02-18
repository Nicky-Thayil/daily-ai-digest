"""
Async RSS feed fetcher using httpx + feedparser.
Fetches all configured feeds concurrently and returns
a normalized list of Article objects.
"""

import asyncio
import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from time import struct_time

import feedparser
import httpx

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(10.0, connect=5.0)
MAX_CONCURRENT = 10  # semaphore: max simultaneous open connections

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Article:
    title: str
    url: str
    summary: str
    published: datetime | None
    source: str   # e.g. "OpenAI Blog"
    topic: str    # e.g. "ai"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities from a string."""
    text = re.sub(r"<[^>]+>", " ", text)   # strip tags
    text = html.unescape(text)              # &amp; → &, etc.
    text = re.sub(r"\s+", " ", text)        # collapse whitespace
    return text.strip()

def _parse_date(entry: feedparser.FeedParserDict) -> datetime | None:
    """
    Convert feedparser's struct_time to a timezone-aware datetime.
    Tries published_parsed first, then updated_parsed.
    Returns None if neither is available.
    """
    raw: struct_time | None = entry.get("published_parsed") or entry.get("updated_parsed")
    if raw is None:
        return None
    try:
        # struct_time from feedparser is always in UTC
        return datetime(*raw[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _parse_entries(
    feed: feedparser.FeedParserDict,
    source_name: str,
    topic_id: str,
) -> list[Article]:
    """
    Normalize raw feedparser entries into Article objects.
    Skips entries that are missing a title or URL.
    """
    articles: list[Article] = []

    for entry in feed.entries:
        title: str = _strip_html(entry.get("title", "")).strip()
        url: str = entry.get("link", "").strip()

        # Skip unusable entries
        if not title or not url:
            continue

        # Try summary, then content (Atom feeds), then fall back to empty string
        raw_summary = (
            entry.get("summary")
            or (entry.get("content") or [{}])[0].get("value")
            or ""
        )
        summary = _strip_html(raw_summary)

        articles.append(
            Article(
                title=title,
                url=url,
                summary=summary,
                published=_parse_date(entry),
                source=source_name,
                topic=topic_id,
            )
        )

    return articles


# ---------------------------------------------------------------------------
# Core fetch logic
# ---------------------------------------------------------------------------

async def _fetch_feed(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    source_name: str,
    url: str,
    topic_id: str,
) -> list[Article]:
    """
    Fetch a single RSS feed and return parsed articles.
    Returns an empty list on any network or parse error so one
    bad feed never takes down the whole batch.
    """
    async with sem:
        try:
            response = await client.get(url, timeout=TIMEOUT)
            response.raise_for_status()
        except httpx.TimeoutException:
            logger.warning("Timeout fetching %s (%s)", source_name, url)
            return []
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP %s from %s (%s)", e.response.status_code, source_name, url)
            return []
        except httpx.HTTPError as e:
            logger.warning("Network error fetching %s: %s", source_name, e)
            return []

    # feedparser.parse() is synchronous and CPU-bound on large feeds.
    # run_in_executor offloads it to a thread so the event loop stays free.
    loop = asyncio.get_event_loop()
    feed: feedparser.FeedParserDict = await loop.run_in_executor(
        None, feedparser.parse, response.text
    )

    if feed.bozo and not feed.entries:
        logger.warning("Malformed feed from %s, skipping", source_name)
        return []

    articles = _parse_entries(feed, source_name, topic_id)
    logger.info("Fetched %d articles from %s", len(articles), source_name)
    return articles


async def fetch_all_feeds(topics_data: dict) -> list[Article]:
    """
    Fetch every feed across all topics concurrently.

    Expects the shape from your topics.json:
        {
          "topics": [
            {
              "id": "ai",
              "name": "AI",
              "enabled": true,
              "sources": [
                {"name": "OpenAI Blog", "url": "https://..."}
              ]
            }
          ]
        }

    Only fetches topics where "enabled" is true.
    Returns a flat, URL-deduplicated list of Articles.
    """
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    enabled_topics = [t for t in topics_data.get("topics", []) if t.get("enabled", True)]

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "daily-ai-digest/1.0 (RSS Reader)"},
    ) as client:
        tasks = [
            _fetch_feed(client, sem, source["name"], source["url"], topic["id"])
            for topic in enabled_topics
            for source in topic.get("sources", [])
        ]
        results: list[list[Article]] = await asyncio.gather(*tasks)

    # Flatten and deduplicate by URL
    seen_urls: set[str] = set()
    articles: list[Article] = []
    for feed_articles in results:
        for article in feed_articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                articles.append(article)

    logger.info("Total unique articles fetched: %d", len(articles))
    return articles