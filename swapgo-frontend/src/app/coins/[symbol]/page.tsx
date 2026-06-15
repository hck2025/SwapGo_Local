"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, type Coin, type Pool } from "@/lib/api";
import { PriceChart } from "@/components/price-chart";
import { ArrowLeft, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/cn";

export default function CoinDetailPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const router = useRouter();
  const { data: coins } = useQuery({
    queryKey: ["market-coins"],
    queryFn: () => api<{ coins: Coin[] }>("/market/coins"),
  });
  const { data: pools } = useQuery({
    queryKey: ["pools"],
    queryFn: () => api<Pool[]>("/pools"),
  });

  const coin = coins?.coins.find((c) => c.symbol.toLowerCase() === symbol?.toLowerCase());
  const pool = pools?.find(
    (p) => p.base_symbol.toLowerCase() === symbol?.toLowerCase()
  );
  const up = (coin?.change_24h_pct ?? 0) >= 0;

  return (
    <div className="space-y-3">
      <Link
        href="/market"
        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
      >
        <ArrowLeft size={14} /> 마켓으로 돌아가기
      </Link>
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-base font-bold text-blue-700">
          {symbol?.[0]?.toUpperCase()}
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{coin?.name ?? symbol}</h1>
            <span className="text-sm text-slate-500">{symbol?.toUpperCase()}</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-2xl font-bold tabular-nums">
              ${(parseFloat(coin?.price_human ?? "0") || 0).toLocaleString("en-US", {
                maximumFractionDigits: 4,
              })}
            </div>
            <div
              className={cn(
                "flex items-center gap-1 text-sm tabular-nums",
                up ? "text-emerald-600" : "text-red-600"
              )}
            >
              {up ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {up ? "+" : ""}
              {(coin?.change_24h_pct ?? 0).toFixed(2)}%
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Cell label="24h 거래량" value={coin?.volume_24h_human ?? "0"} />
        <Cell label="풀 ID" value={pool ? `#${pool.id}` : "—"} />
        <Cell label="유동성(quote)" value={pool?.tvl_quote_human ?? "—"} />
        <Cell label="수수료" value={pool ? `${pool.fee_bps / 100}%` : "—"} />
      </div>

      {pool && <PriceChart poolId={pool.id} />}

      {pool && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-2 text-sm font-semibold">빠른 거래</div>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => router.push(`/?pool=${pool.id}&side=quote_to_base`)}
              className="flex h-20 flex-col items-center justify-center rounded-lg border-2 border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
            >
              <TrendingUp />
              <span className="mt-1 text-sm font-semibold">매수하기</span>
            </button>
            <button
              onClick={() => router.push(`/?pool=${pool.id}&side=base_to_quote`)}
              className="flex h-20 flex-col items-center justify-center rounded-lg border-2 border-red-200 bg-red-50 text-red-700 hover:bg-red-100"
            >
              <TrendingDown />
              <span className="mt-1 text-sm font-semibold">매도하기</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="text-sm font-semibold tabular-nums">{value}</div>
    </div>
  );
}
