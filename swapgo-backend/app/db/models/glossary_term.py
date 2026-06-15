from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    term_ko: Mapped[str] = mapped_column(String(128), nullable=False)
    term_en: Mapped[str | None] = mapped_column(String(128))
    short_desc: Mapped[str] = mapped_column(Text, nullable=False)
    long_desc: Mapped[str | None] = mapped_column(Text)
    example: Mapped[str | None] = mapped_column(Text)
    related_keys: Mapped[str | None] = mapped_column(Text)  # JSON 문자열 ["a","b"]
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1~3
