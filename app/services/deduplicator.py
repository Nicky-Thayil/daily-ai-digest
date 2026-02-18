"""
Deduplicates articles within each topic using:
  1. Exact URL matching (already handled by fetcher, but re-checked here for safety)
  2. Jaccard title similarity — catches the same story from multiple outlets

Only compares articles within the same topic, not across topics.
"""

import logging
import re
import string

from app.services.fetcher import Article

logger = logging.getLogger(__name__)

# Articles with title similarity >= this threshold are considered duplicates.
SIMILARITY_THRESHOLD = 0.6

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "was", "were", "be", "been", "has", "have",
    "had", "it", "its", "this", "that", "by", "from", "as", "new", "how",
    "why", "what", "who", "will", "can", "just", "more", "up", "about",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalize(title: str) -> set[str]:
    """
    Lowercase, strip punctuation, remove stopwords.
    Returns a set of meaningful words for Jaccard comparison.
    """
    title = title.lower()
    title = title.translate(str.maketrans("", "", string.punctuation))
    words = title.split()
    return {w for w in words if w not in STOPWORDS and len(w) > 1}

def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    """
    Jaccard similarity = |intersection| / |union|
    Returns 0.0 if both sets are empty.
    """
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def deduplicate(articles: list[Article]) -> list[Article]:
    """
    Remove duplicate articles using URL deduplication and Jaccard title
    similarity. Runs independently within each topic group.

    Strategy:
    - Iterate through articles in order (fetcher order = source order)
    - For each article, compare its normalized title against all already-kept
      articles in the same topic
    - If similarity >= SIMILARITY_THRESHOLD with any kept article, discard it
    - Otherwise keep it

    The first-seen article wins (earlier sources in topics.json are preferred),
    so put your highest-quality sources first in topics.json.
    """
    # Group by topic
    by_topic: dict[str, list[Article]] = {}
    for article in articles:
        by_topic.setdefault(article.topic, []).append(article)

    result: list[Article] = []
    total_removed = 0

    for topic, topic_articles in by_topic.items():
        kept: list[Article] = []
        kept_urls: set[str] = set()
        kept_title_sets: list[set[str]] = []

        for article in topic_articles:
            # 1. URL deduplication
            if article.url in kept_urls:
                total_removed += 1
                continue

            # 2. Title similarity
            normalized = _normalize(article.title)
            is_duplicate = False

            for kept_title_set in kept_title_sets:
                score = _jaccard(normalized, kept_title_set)
                if score >= SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break

            if is_duplicate:
                total_removed += 1
                continue

            kept.append(article)
            kept_urls.add(article.url)
            kept_title_sets.append(normalized)

        logger.info(
            "Topic '%s': %d → %d articles after deduplication",
            topic, len(topic_articles), len(kept)
        )
        result.extend(kept)

    logger.info(
        "Deduplication complete: %d removed, %d remaining",
        total_removed, len(result)
    )
    return result