"""모든 응답을 {ok, data, error, server_time} 봉투로 감싸는 헬퍼 + 글로벌 에러 핸들러."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError
from app.core.time import iso_now


def envelope_ok(data: Any) -> dict:
    return {"ok": True, "data": data, "error": None, "server_time": iso_now()}


def envelope_err(
    code: str,
    message: str,
    *,
    suggestion: str = "",
    glossary_keys: list[str] | None = None,
    details: dict[str, Any] | None = None,
    status_code: int = 400,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "data": None,
            "error": {
                "code": code,
                "message": message,
                "suggestion": suggestion,
                "glossary_keys": glossary_keys or [],
                "details": details or {},
            },
            "server_time": iso_now(),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return envelope_err(
            exc.code,
            exc.message,
            suggestion=exc.suggestion,
            glossary_keys=list(exc.glossary_keys),
            details=exc.details,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return envelope_err(
            "VALIDATION_ERROR",
            "요청 형식이 올바르지 않아요.",
            suggestion="입력값과 타입을 확인해주세요.",
            details={"errors": exc.errors()[:5]},
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        return envelope_err(
            "HTTP_ERROR",
            str(exc.detail) if exc.detail else "요청을 처리할 수 없어요.",
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        return envelope_err(
            "INTERNAL_ERROR",
            "서버 내부 오류가 발생했어요.",
            details={"type": type(exc).__name__},
            status_code=500,
        )
