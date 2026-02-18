"""
Generates a bullet-point digest for each topic using GPT-4o-mini.
Takes deduplicated articles, trims to the 10 most recent per topic,
and returns a structured digest ready for display.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.services.fetcher import Article

logger = logging.getLogger(__name__)

MAX_ARTICLES_PER_TOPIC = 10
MAX_SUMMARY_CHARS = 300

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TopicDigest:
    topic_id: str
    topic_name: str
    article_count: int        # how many articles were summarized
    bullets: list[str]        # the generated bullet points
    generated_at: datetime

@dataclass
class Digest:
    topics: list[TopicDigest]
    generated_at: datetime
    total_articles_summarized: int

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _trim_articles(articles: list[Article]) -> list[Article]:
    """
    Sort by published date (most recent first) and take top MAX_ARTICLES_PER_TOPIC.
    Articles with no publish date are sorted to the end.
    """
    def sort_key(a: Article):
        if a.published is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        return a.published

    sorted_articles = sorted(articles, key=sort_key, reverse=True)
    return sorted_articles[:MAX_ARTICLES_PER_TOPIC]


def _build_prompt(topic_name: str, articles: list[Article]) -> str:
    """
    Build the user prompt sent to GPT-4o-mini for one topic.
    """
    article_lines = []
    for i, article in enumerate(articles, 1):
        summary = article.summary[:MAX_SUMMARY_CHARS] if article.summary else "No summary available."
        article_lines.append(
            f"{i}. [{article.source}] {article.title}\n   {summary}"
        )

    articles_text = "\n\n".join(article_lines)

    return f"""You are summarizing today's top {topic_name} news for a personal daily digest.

Here are the {len(articles)} most recent articles:

{articles_text}

Write 5 concise bullet points summarizing the most important and interesting developments.
Each bullet should:
- Be 1-2 sentences max
- Focus on what actually happened or what's new
- Be written in plain English, no jargon
- Include the source name in brackets at the end, e.g. [Hacker News]

Return only the bullet points, one per line, starting each with "•"."""

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
async def summarize(
    articles: list[Article],
    topics_data: dict,
    client: AsyncOpenAI | None = None,
) -> Digest:
    """
    Generate a bullet-point digest for each topic.

    Args:
        articles:     Deduplicated list of Article objects from the fetcher.
        topics_data:  The loaded topics.json dict (used for display names).
        client:       Optional AsyncOpenAI client (injected for testing).

    Returns:
        A Digest containing a TopicDigest for each topic that had articles.
    """
    if client is None:
        client = AsyncOpenAI()  # reads OPENAI_API_KEY from environment

    # Build a name lookup from topics_data
    topic_names: dict[str, str] = {
        t["id"]: t["name"]
        for t in topics_data.get("topics", [])
    }

    # Group articles by topic
    by_topic: dict[str, list[Article]] = {}
    for article in articles:
        by_topic.setdefault(article.topic, []).append(article)

    now = datetime.now(tz=timezone.utc)
    topic_digests: list[TopicDigest] = []
    total_summarized = 0

    for topic_id, topic_articles in by_topic.items():
        trimmed = _trim_articles(topic_articles)
        topic_name = topic_names.get(topic_id, topic_id.title())

        logger.info(
            "Summarizing topic '%s': %d articles (trimmed from %d)",
            topic_id, len(trimmed), len(topic_articles)
        )

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a concise news digest writer. "
                            "You write clear, factual bullet points for busy readers."
                        ),
                    },
                    {
                        "role": "user",
                        "content": _build_prompt(topic_name, trimmed),
                    },
                ],
                max_tokens=400,
                temperature=0.3,  
            )

            raw = response.choices[0].message.content or ""
            bullets = [
                line.strip()
                for line in raw.splitlines()
                if line.strip().startswith("•")
            ]

            if not bullets:
                # Fallback: treat every non-empty line as a bullet
                bullets = [f"• {line.strip()}" for line in raw.splitlines() if line.strip()]

            logger.info("Generated %d bullets for topic '%s'", len(bullets), topic_id)

        except Exception as e:
            logger.error("Failed to summarize topic '%s': %s", topic_id, e)
            bullets = [f"• Could not generate summary for {topic_name}: {e}"]

        topic_digests.append(
            TopicDigest(
                topic_id=topic_id,
                topic_name=topic_name,
                article_count=len(trimmed),
                bullets=bullets,
                generated_at=now,
            )
        )
        total_summarized += len(trimmed)

    return Digest(
        topics=topic_digests,
        generated_at=now,
        total_articles_summarized=total_summarized,
    )