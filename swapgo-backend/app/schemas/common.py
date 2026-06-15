from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorPayload(BaseModel):
    code: str
    message: str
    suggestion: str = ""
    glossary_keys: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class Envelope(BaseModel, Generic[T]):
    ok: bool = True
    data: T | None = None
    error: ErrorPayload | None = None
    server_time: str
