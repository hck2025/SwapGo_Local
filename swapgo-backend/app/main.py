import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.envelope import envelope_ok, register_exception_handlers
from app.config import get_settings
from app.db.base import init_schema
from app.workers import candle_aggregator, merkle_snapshotter


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema()
    stop_event = asyncio.Event()
    workers = [
        asyncio.create_task(candle_aggregator.run_forever(stop_event)),
        asyncio.create_task(merkle_snapshotter.run_forever(stop_event)),
    ]
    try:
        yield
    finally:
        stop_event.set()
        for w in workers:
            try:
                await asyncio.wait_for(w, timeout=2)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                w.cancel()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="SwapGo Backend",
        description="Python AMM DEX (CPMM) — 학습 친화 모의투자 백엔드",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    # 라우터 등록은 Phase B/C에서 점진적으로 추가
    from app.api.v1 import (  # noqa: E402  (지연 임포트)
        admin,
        ai,
        auth,
        chart,
        explorer,
        glossary,
        liquidity,
        market,
        pools,
        swap,
        transactions,
        wallet,
    )
    from app.api import ws as ws_router

    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
    app.include_router(pools.router, prefix="/pools", tags=["pools"])
    app.include_router(swap.router, prefix="/swap", tags=["swap"])
    app.include_router(liquidity.router, prefix="/liquidity", tags=["liquidity"])
    app.include_router(market.router, prefix="/market", tags=["market"])
    app.include_router(chart.router, prefix="/chart", tags=["chart"])
    app.include_router(ai.router, prefix="/ai", tags=["ai"])
    app.include_router(transactions.router, prefix="/me", tags=["me"])
    app.include_router(explorer.router, prefix="/explorer", tags=["explorer"])
    app.include_router(glossary.router, prefix="/glossary", tags=["glossary"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(ws_router.router, tags=["ws"])

    @app.get("/health")
    async def _health():
        return envelope_ok({"status": "ok"})

    return app


app = create_app()
