"""
Data access layer for the AI Digest Assistant.
"""

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Digest, DigestArticle, TopicDigest
from app.services.fetcher import Article
from app.services.summarizer import Digest as SummarizerDigest


# Writes
async def save_digest(
    session: AsyncSession,
    digest: SummarizerDigest,
    articles: list[Article],
) -> Digest:
    """Save a digest to the database."""
    # 1. Create parent Digest row
    db_digest = Digest(
        generated_at=digest.generated_at,
        total_articles_summarized=digest.total_articles_summarized,
    )
    session.add(db_digest)
    await session.flush()  # Flush to get db_digest.id without committing

    # 2. Create TopicDigest rows
    for topic in digest.topics:
        db_topic = TopicDigest(
            digest_id=db_digest.id,
            topic_id=topic.topic_id,
            topic_name=topic.topic_name,
            article_count=topic.article_count,
            bullets_text="\n".join(topic.bullets),
        )
        session.add(db_topic)

    # 3. Create DigestArticle rows (only articles that were summarized)
    summarized_topic_ids = {t.topic_id for t in digest.topics}
    for article in articles:
        if article.topic in summarized_topic_ids:
            db_article = DigestArticle(
                digest_id=db_digest.id,
                topic_id=article.topic,
                title=article.title,
                url=article.url,
                source=article.source,
            )
            session.add(db_article)

    return db_digest


# Reads
async def get_latest_digest(session: AsyncSession) -> Digest | None:
    """Get the most recent digest run."""
    result = await session.execute(
        select(Digest)
        .options(selectinload(Digest.topic_digests))
        .order_by(desc(Digest.generated_at))
        .limit(1)
    )
    return result.scalars().first()


async def get_digest_by_id(session: AsyncSession, digest_id: int) -> Digest | None:
    """Fetch a digest by ID with all topic_digests loaded."""
    result = await session.execute(
        select(Digest)
        .options(selectinload(Digest.topic_digests))
        .where(Digest.id == digest_id)
    )
    return result.scalars().first()


async def list_digests(session: AsyncSession, limit: int = 10) -> list[Digest]:
    """List the most recent digest runs (metadata)."""
    result = await session.execute(
        select(Digest)
        .order_by(desc(Digest.generated_at))
        .limit(limit)
    )
    return list(result.scalars().all())