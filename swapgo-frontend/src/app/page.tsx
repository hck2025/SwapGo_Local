"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, type Pool } from "@/lib/api";
import { PriceChart } from "@/components/price-chart";
import { OrderbookCard } from "@/components/orderbook-card";
import { SwapPanel } from "@/components/swap-panel";
import { TradeTabs } from "@/components/trade-tabs";
import { cn } from "@/lib/cn";

export default function Page() {
  const [poolId, setPoolId] = useState<number | null>(null);

  const { data: pools } = useQuery({
    queryKey: ["pools"],
    queryFn: () => api<Pool[]>("/pools"),
    refetchInterval: 5000,
  });
  const pool = pools?.find((p) => p.id === poolId) ?? pools?.[0];

  if (!pool) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-12 text-center text-slate-500">
        풀이 아직 시드되지 않았어요. 백엔드에서{" "}
        <code className="rounded bg-slate-100 px-1.5 py-0.5">POST /admin/seed</code> 를 호출해주세요.
      </div>
    );
  }

  const ticker = (
    <div className="flex items-center gap-3 text-sm">
      <select
        value={pool.id}
        onChange={(e) => setPoolId(parseInt(e.target.value))}
        className="rounded-md border border-slate-200 bg-blue-50 px-2 py-1 text-blue-700"
      >
        {pools!.map((p) => (
          <option key={p.id} value={p.id}>
            {p.base_symbol} / {p.quote_symbol}
          </option>
        ))}
      </select>
      <span className="font-bold tabular-nums">
        {parseFloat(pool.price).toLocaleString("en-US", { maximumFractionDigits: 2 })}
      </span>
      <Pulse symbol={pool.base_symbol} />
    </div>
  );

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">{ticker}</div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_220px_360px]">
        <div className="space-y-3">
          <PriceChart poolId={pool.id} />
          <TickerStats pool={pool} />
        </div>
        <OrderbookCard poolId={pool.id} quoteSymbol={pool.quote_symbol} />
        <SwapPanel pool={pool} />
      </div>

      <TradeTabs pool={pool} />
    </div>
  );
}

function Pulse({ symbol }: { symbol: string }) {
  return (
    <span className="ml-2 inline-flex items-center gap-1 text-[11px] text-slate-400">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" /> 실시간 {symbol}
    </span>
  );
}

function TickerStats({ pool }: { pool: Pool }) {
  const { data } = useQuery({
    queryKey: ["ticker", pool.id],
    queryFn: () =>
      api<{
        last_price: string;
        high_24h: string;
        low_24h: string;
        change_24h_pct: number;
        volume_24h_base: string;
        volume_24h_quote: string;
      }>(`/chart/ticker?pool_id=${pool.id}`),
    refetchInterval: 8000,
  });
  const isUp = (data?.change_24h_pct ?? 0) >= 0;
  return (
    <div className="grid grid-cols-2 gap-2 rounded-lg border border-slate-200 bg-white p-3 text-xs sm:grid-cols-4">
      <Cell label="24h 거래량" value={`${data?.volume_24h_base ?? 0}`} />
      <Cell
        label="TVL (quote)"
        value={`${(parseFloat(pool.tvl_quote_human) || 0).toLocaleString("en-US", {
          maximumFractionDigits: 0,
        })}`}
      />
      <Cell
        label="24h 변동"
        value={`${isUp ? "+" : ""}${(data?.change_24h_pct ?? 0).toFixed(2)}%`}
        cls={cn(isUp ? "text-emerald-600" : "text-red-600")}
      />
      <Cell label="풀 revision" value={`#${pool.revision}`} />
    </div>
  );
}

function Cell({ label, value, cls }: { label: string; value: string; cls?: string }) {
  return (
    <div>
      <div className="text-slate-500">{label}</div>
      <div className={cn("font-semibold tabular-nums", cls)}>{value}</div>
    </div>
  );
}
