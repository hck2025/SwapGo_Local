"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api, type Holdings } from "@/lib/api";
import { useWallet } from "@/lib/wallet";
import { useWalletModal } from "@/components/wallet-modal";
import { cn } from "@/lib/cn";
import { ArrowDownLeft, BarChart3, RefreshCw, TrendingUp, TrendingDown } from "lucide-react";

export default function HoldingsPage() {
  const wallet = useWallet();
  const { open } = useWalletModal();

  const { data, isFetching } = useQuery({
    queryKey: ["holdings", wallet.token],
    queryFn: () => api<Holdings>("/wallet/holdings", { token: wallet.token }),
    enabled: !!wallet.token,
    refetchInterval: 6000,
  });

  if (!wallet.address) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-12 text-center">
        <div className="text-sm text-slate-500">
          지갑을 연결하면 보유 코인과 수익률을 볼 수 있어요.
        </div>
        <button
          onClick={open}
          className="mt-3 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          지갑 연결
        </button>
      </div>
    );
  }

  const items = data?.items ?? [];
  const num = (s: string | null | undefined) => parseFloat(s ?? "0") || 0;
  const usd = (n: number) =>
    n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const signed = (n: number) => `${n >= 0 ? "+" : ""}${usd(n)}`;

  const totalValue = num(data?.total_value_quote_human);
  const totalPnl = data?.total_pnl_value_human != null ? num(data.total_pnl_value_human) : null;
  const totalPnlPct = data?.total_pnl_pct ?? null;
  const up = (totalPnl ?? 0) >= 0;

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold">보유자산</h1>
          <p className="text-sm text-slate-500">
            보유 코인과 매수가 대비 수익률을 한눈에 확인하세요
          </p>
        </div>
        <Link
          href="/portfolio"
          className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          <ArrowDownLeft size={14} /> 입금하기
        </Link>
      </div>

      {/* 총 평가액 + 총 손익 */}
      <div className="rounded-lg border border-slate-200 bg-gradient-to-br from-blue-600 to-blue-500 p-5 text-white">
        <div className="flex items-center gap-1.5 text-xs text-blue-100">
          총 평가액 (USDT 기준)
          {isFetching && <RefreshCw size={11} className="animate-spin" />}
        </div>
        <div className="mt-1 text-3xl font-bold tabular-nums">${usd(totalValue)}</div>
        {totalPnl !== null ? (
          <div className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-white/15 px-2.5 py-1 text-sm font-semibold tabular-nums">
            {up ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            평가손익 ${signed(totalPnl)} ({totalPnlPct! >= 0 ? "+" : ""}
            {totalPnlPct!.toFixed(2)}%)
          </div>
        ) : (
          <div className="mt-2 text-xs text-blue-100">
            매수(스왑) 기록이 쌓이면 수익률이 표시돼요.
          </div>
        )}
        <div className="mt-2 text-xs text-blue-100">
          {items.length}개 자산 · 투자원금 $
          {usd(num(data?.total_invested_quote_human))} · 주소 {wallet.address.slice(0, 6)}…
          {wallet.address.slice(-4)}
        </div>
      </div>

      {/* 자산 목록 */}
      <div className="rounded-lg border border-slate-200 bg-white">
        <div className="grid grid-cols-[1.2fr_1fr_1fr_1fr_1.1fr] gap-2 border-b border-slate-100 px-4 py-2.5 text-xs font-semibold text-slate-500">
          <div>자산</div>
          <div className="text-right">보유 수량</div>
          <div className="text-right">평균 매수가</div>
          <div className="text-right">현재가</div>
          <div className="text-right">평가액 · 수익률</div>
        </div>

        {items.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm text-slate-400">
            아직 보유한 자산이 없어요.{" "}
            <Link href="/portfolio" className="text-blue-600 underline">
              입금 탭
            </Link>
            에서 모의 입금을 하거나{" "}
            <Link href="/" className="text-blue-600 underline">
              거래
            </Link>
            를 시작해보세요.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {items.map((it) => {
              const value = num(it.value_quote_human);
              const pnl = it.pnl_value_human != null ? num(it.pnl_value_human) : null;
              const pnlPct = it.pnl_pct;
              const isUp = (pnl ?? 0) >= 0;
              return (
                <div
                  key={it.symbol}
                  className="grid grid-cols-[1.2fr_1fr_1fr_1fr_1.1fr] items-center gap-2 px-4 py-3"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-700">
                      {it.symbol[0]}
                    </span>
                    <span className="text-sm font-semibold">{it.symbol}</span>
                  </div>
                  <div className="text-right text-sm tabular-nums">{it.amount_human}</div>
                  <div className="text-right text-sm tabular-nums text-slate-500">
                    {it.avg_cost_human ? `$${usd(num(it.avg_cost_human))}` : "—"}
                  </div>
                  <div className="text-right text-sm tabular-nums text-slate-600">
                    {num(it.current_price_human) > 0 ? `$${usd(num(it.current_price_human))}` : "—"}
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold tabular-nums">${usd(value)}</div>
                    {pnl !== null && pnlPct !== null ? (
                      <div
                        className={cn(
                          "text-[11px] font-medium tabular-nums",
                          isUp ? "text-emerald-600" : "text-red-600"
                        )}
                      >
                        {isUp ? "▲" : "▼"} ${signed(pnl)} ({pnlPct >= 0 ? "+" : ""}
                        {pnlPct.toFixed(2)}%)
                      </div>
                    ) : (
                      <div className="text-[11px] text-slate-400">현금성</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="flex items-start gap-2 text-xs text-slate-400">
        <BarChart3 size={13} className="mt-0.5 shrink-0" />
        <span>
          수익률은 거래 내역을 재생해 구한 평균 매수가(이동평균) 대비 현재가로 계산해요.
          USDT 는 기준통화라 손익 계산에서 제외되고, 입금받은 코인은 입금 시점 시장가를
          매수가로 봅니다. (학습용 모의 평가)
        </span>
      </div>
    </div>
  );
}
