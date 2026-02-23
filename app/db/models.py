"""
Database models for the AI Digest Assistant.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    total_articles_summarized: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    topic_digests: Mapped[list["TopicDigest"]] = relationship(
        "TopicDigest", back_populates="digest", cascade="all, delete-orphan"
    )
    articles: Mapped[list["DigestArticle"]] = relationship(
        "DigestArticle", back_populates="digest", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Digest id={self.id} generated_at={self.generated_at}>"


class TopicDigest(Base):
    __tablename__ = "topic_digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    digest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("digests.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[str] = mapped_column(String(100), nullable=False)
    topic_name: Mapped[str] = mapped_column(String(100), nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False)
    bullets_text: Mapped[str] = mapped_column(Text, nullable=False)
    # bullets stored as newline-separated string for simplicity

    digest: Mapped["Digest"] = relationship("Digest", back_populates="topic_digests")

    @property
    def bullets(self) -> list[str]:
        return [b for b in self.bullets_text.split("\n") if b.strip()]

    def __repr__(self) -> str:
        return f"<TopicDigest topic={self.topic_id} digest_id={self.digest_id}>"


class DigestArticle(Base):
    __tablename__ = "digest_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    digest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("digests.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)

    # Relationship
    digest: Mapped["Digest"] = relationship("Digest", back_populates="articles")

    def __repr__(self) -> str:
        return f"<DigestArticle title={self.title[:40]!r}>"