from pydantic import BaseModel


class GlossaryItem(BaseModel):
    key: str
    term_ko: str
    term_en: str | None
    short_desc: str
    long_desc: str | None
    example: str | None
    related_keys: list[str]
    difficulty: int


class GlossaryListResp(BaseModel):
    items: list[GlossaryItem]
