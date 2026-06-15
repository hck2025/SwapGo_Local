"""인-프로세스 WebSocket 브로커. 채널 단위 pub/sub.

Phase A에서는 단일 프로세스 가정. PG/Redis 마이그레이션 시 redis pubsub 으로 자연 교체.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class _Hub:
    def __init__(self) -> None:
        self._subs: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, ws: WebSocket, channels: list[str]) -> None:
        async with self._lock:
            for ch in channels:
                self._subs[ch].add(ws)

    async def unsubscribe(self, ws: WebSocket, channels: list[str] | None = None) -> None:
        async with self._lock:
            if channels is None:
                for s in self._subs.values():
                    s.discard(ws)
            else:
                for ch in channels:
                    self._subs[ch].discard(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        await self.unsubscribe(ws, channels=None)

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        message = json.dumps({"channel": channel, **payload}, ensure_ascii=False)
        async with self._lock:
            targets = list(self._subs.get(channel, set()))
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                # 끊긴 소켓은 다음 라운드에 정리
                await self.disconnect(ws)


hub = _Hub()


def publish_sync(channel: str, payload: dict[str, Any]) -> None:
    """동기 컨텍스트(서비스 레이어)에서 호출 가능. 이벤트 루프가 없으면 무시."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return
    if loop.is_running():
        loop.create_task(hub.publish(channel, payload))
