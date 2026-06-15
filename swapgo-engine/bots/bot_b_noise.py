"""
bots/bot_b_noise.py — 시스템 B: 랜덤 노이즈 유동성 봇

[역할]
  AI 예측 없이 무작위 방향·금액으로 /swap/execute 를 반복 호출합니다.
  BotA_Trade 와 같은 풀에서 충돌하며 가상 시장 유동성을 조성합니다.

[설계 원칙]
  - 완전 무작위: 방향(BUY/SELL) 50/50, 금액 균등분포
  - ingest 호출 없음: swap/execute 만 사용
  - 슬리피지 상한 내에서만 거래: danger 수준이면 건너뜀
  - StaleQuote(409) 는 즉시 포기 (노이즈 봇은 타이밍보다 빈도가 중요)
"""

from __future__ import annotations

import asyncio
import logging
import random
import traceback
from typing import Callable, Optional

from config import settings
from core.swapgo_client import SwapGoClient, StaleQuoteError

logger = logging.getLogger(__name__)


class BotB_Noise:
    """
    랜덤 노이즈 유동성 봇.
    설정된 간격으로 무작위 매수/매도를 반복해 풀에 거래량을 공급합니다.
    """

    def __init__(
        self,
        client: SwapGoClient,
        trade_event_publisher: Optional[Callable[[dict], None]] = None,
        candle_cache=None,
    ):
        self._client = client
        self._trade_count = 0
        self._skip_count = 0
        self._publish = trade_event_publisher
        # 매수(quote→base) 시 수량을 quote(USDT)로 환산하기 위한 현재가 소스.
        # 없으면 base 단위를 그대로 사용(구버전 동작).
        self._cache = candle_cache

    # ── 메인 루프 ────────────────────────────────────────────
    async def run(self) -> None:
        logger.info(
            f"[BotB_Noise] 시작 | "
            f"interval=[{settings.noise_interval_min}, {settings.noise_interval_max}]s "
            f"amount=[{settings.noise_amount_min}, {settings.noise_amount_max}]"
        )
        while True:
            try:
                delay = random.uniform(
                    settings.noise_interval_min,
                    settings.noise_interval_max,
                )
                await asyncio.sleep(delay)
                await self._execute_random_swap()

            except Exception:
                logger.error(f"[BotB_Noise] 오류\n{traceback.format_exc()}")
                await asyncio.sleep(2.0)

    # ── 거래 대상 풀 목록 (BTC/ETH) ──────────────────────────
    def _pick_pool(self) -> tuple[int, float]:
        """매 사이클 BTC/ETH 풀을 무작위로 골라 (pool_id, 현재가) 반환.

        한 풀만 거래하면 다른 풀(ETH)이 평탄하게 멈춘다. 두 풀을 번갈아 거래해
        양쪽 차트 모두에 거래량을 공급한다. 가격은 매수 시 quote 환산에 사용.
        """
        pools: list[tuple[int, float]] = [
            (settings.pool_id, self._cache.latest_btc_close() if self._cache else 0.0),
        ]
        if settings.eth_pool_id:
            pools.append(
                (
                    settings.eth_pool_id,
                    self._cache.latest_eth_close() if self._cache else 0.0,
                )
            )
        return random.choice(pools)

    # ── 단일 랜덤 스왑 ───────────────────────────────────────
    async def _execute_random_swap(self) -> None:
        amount_min = float(settings.noise_amount_min)
        amount_max = float(settings.noise_amount_max)
        amount = round(random.uniform(amount_min, amount_max), 6)
        is_buy = random.choice([True, False])
        swap_side = "quote_to_base" if is_buy else "base_to_quote"
        direction = "BUY " if is_buy else "SELL"

        pool_id, price = self._pick_pool()
        if pool_id == 2:
            amount *= 10

        # 매도(base→quote)는 base(BTC/ETH) 단위, 매수(quote→base)는 quote(USDT) 단위.
        # 동일 수량을 양측에 쓰면 매수만 미미해져 풀이 한 방향(매도)으로만 쏠려
        # 가격이 계속 흘러내린다. 현재가로 환산해 양방향 거래량을 맞춘다.
        if is_buy and price and price > 0:
            amount_in_human = f"{amount * price:.6f}"
        else:
            amount_in_human = str(amount)

        quote_body = {
            "pool_id": pool_id,
            "side": swap_side,
            "amount_in_human": amount_in_human,
            "slippage_tolerance_bps": settings.noise_slippage_bps,
        }

        try:
            # 견적 (envelope 는 SwapGoClient._request 에서 이미 벗겨져 data 가 옴)
            quote = await self._client.quote_swap(quote_body)

            slippage_level = quote.get("slippage_level", "safe")

            if slippage_level == "danger":
                self._skip_count += 1
                logger.debug(
                    f"[BotB_Noise] slippage=danger → 건너뜀 (총 {self._skip_count}회)"
                )
                return

            # 실행
            exec_body = {
                "pool_id": pool_id,
                "side": swap_side,
                "amount_in_human": amount_in_human,
                "min_amount_out": quote["amount_out_min"],
                "slippage_tolerance_bps": quote.get(
                    "slippage_threshold_used_bps",
                    settings.noise_slippage_bps,
                ),
                "expected_revision": quote["pool_after"]["revision"],
            }
            result = await self._client.execute_swap(exec_body)
            self._trade_count += 1

            logger.debug(
                f"[BotB_Noise] {direction} #{self._trade_count} | "
                f"in={amount:.6f}  out={result.get('amount_out_human', '?')}  "
                f"slippage={slippage_level}"
            )

        except StaleQuoteError:
            # 노이즈 봇은 재시도 없이 즉시 포기 — 다음 사이클에 재시도
            logger.debug("[BotB_Noise] StaleQuote(409) → 포기 (다음 사이클에 재시도)")
            self._skip_count += 1

        except Exception as e:
            logger.warning(f"[BotB_Noise] 스왑 실패: {e}")

    # ── 상태 조회 ────────────────────────────────────────────
    def get_stats(self) -> dict:
        return {
            "trade_count": self._trade_count,
            "skip_count": self._skip_count,
        }
