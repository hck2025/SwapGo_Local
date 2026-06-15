"""SwapGo 백엔드 서버 실행 스크립트.

사용법:
  python run.py                # 기본: 0.0.0.0:8000, reload, 부팅 시 자동 시드
  python run.py --port 8080
  python run.py --no-seed      # 자동 시드 끄기
  python run.py --no-reload    # 핫리로드 끄기 (운영 모드 시)
"""

from __future__ import annotations

import argparse
import os
import sys

import uvicorn


def _seed_if_empty(database_url: str) -> None:
    """assets/pools/glossary가 비어있으면 한 번 시드한다. 봇 키는 콘솔에 1회 출력."""
    os.environ.setdefault("DATABASE_URL", database_url)
    from app.db.base import SessionLocal, init_schema
    from app.db.models.asset import Asset
    from app.seeders import seed_bot, seed_glossary, seed_pools

    init_schema()
    db = SessionLocal()
    try:
        if db.query(Asset).count() > 0:
            return
        print("[seed] 자산/풀/용어사전/봇을 시드합니다...")
        seed_pools.run(db)
        seed_glossary.run(db)
        bot_info = seed_bot.run(db)
        if bot_info.get("api_key_ONCE"):
            print("=" * 60)
            print("[bot] 기본 봇 API 키 (이 메시지는 한 번만 표시됩니다):")
            print(f"      X-Bot-Key: {bot_info['api_key_ONCE']}")
            print(f"      scopes:    {bot_info['scopes']}")
            print("=" * 60)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="SwapGo backend runner")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-reload", action="store_true")
    parser.add_argument("--no-seed", action="store_true")
    parser.add_argument("--db", default=os.environ.get("DATABASE_URL", "sqlite:///./swapgo.db"))
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    os.environ["DATABASE_URL"] = args.db

    if not args.no_seed:
        _seed_if_empty(args.db)

    print(f"[server] http://{args.host}:{args.port}  docs: /docs  ws: /ws")
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        workers=args.workers if args.no_reload else 1,
    )


if __name__ == "__main__":
    sys.exit(main())
