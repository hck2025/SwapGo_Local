"""WebSocket 멀티 채널: pool / trades / ohlc / orderbook / ai:* / me:<address>."""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.notifier import hub

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        await ws.send_text(
            json.dumps(
                {
                    "type": "hello",
                    "message": "SwapGo WS 연결됨. {op:'subscribe', channels:[...]} 메시지를 보내세요.",
                    "available_channels": [
                        "pool:{id}",
                        "trades:{id}",
                        "ohlc:{id}:{interval}",
                        "orderbook:{id}",
                        "ai:signals",
                        "ai:predictions",
                        "ai:sentiment",
                        "me:{address}",
                    ],
                }
            )
        )
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"type": "error", "message": "JSON 형식이 아니에요."}))
                continue
            op = msg.get("op")
            channels = msg.get("channels") or []
            if op == "subscribe":
                await hub.subscribe(ws, list(channels))
                await ws.send_text(
                    json.dumps({"type": "subscribed", "channels": list(channels)})
                )
            elif op == "unsubscribe":
                await hub.unsubscribe(ws, list(channels) if channels else None)
                await ws.send_text(
                    json.dumps({"type": "unsubscribed", "channels": list(channels)})
                )
            elif op == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
            else:
                await ws.send_text(
                    json.dumps({"type": "error", "message": f"알 수 없는 op: {op}"})
                )
    except WebSocketDisconnect:
        await hub.disconnect(ws)
    except Exception:
        await hub.disconnect(ws)
