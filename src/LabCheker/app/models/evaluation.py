
from datetime import datetime

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        index=True
    )

    criteria_markdown: Mapped[str] = mapped_column(Text)
    source_code: Mapped[str] = mapped_column(Text)

    result_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    feedback_markdown: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
