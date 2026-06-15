"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, type Coin, type GlobalMarket } from "@/lib/api";
import { Sparkline } from "@/components/sparkline";
import { cn } from "@/lib/cn";
import { TrendingUp, TrendingDown } from "lucide-react";

export default function MarketPage() {
  const { data: coins } = useQuery({
    queryKey: ["market-coins"],
    queryFn: () => api<{ coins: Coin[] }>("/market/coins"),
    refetchInterval: 8000,
  });
  const { data: g } = useQuery({
    queryKey: ["market-global"],
    queryFn: () => api<GlobalMarket>("/market/global"),
    refetchInterval: 12000,
  });

  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-2xl font-bold">암호화폐 마켓</h1>
        <p className="text-sm text-slate-500">
          스왑고에서 실시간 가격과 시장 정보를 확인하세요
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat
          label="상승 코인"
          value={(coins?.coins.filter((c) => c.change_24h_pct > 0).length ?? 0).toString()}
          subtext={`${coins ? Math.round((coins.coins.filter((c) => c.change_24h_pct > 0).length / Math.max(1, coins.coins.length)) * 100) : 0}%`}
        />
        <Stat
          label="하락 코인"
          value={(coins?.coins.filter((c) => c.change_24h_pct < 0).length ?? 0).toString()}
          subtext={`${coins ? Math.round((coins.coins.filter((c) => c.change_24h_pct < 0).length / Math.max(1, coins.coins.length)) * 100) : 0}%`}
          accent="red"
        />
        <Stat
          label="평균 변동률"
          value={`${
            coins
              ? (
                  coins.coins.reduce((s, c) => s + c.change_24h_pct, 0) /
                  Math.max(1, coins.coins.length)
                ).toFixed(2)
              : "0"
          }%`}
        />
        <Stat label="BTC 도미넌스" value={`${g?.btc_dominance_pct ?? 0}%`} />
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">코인</th>
              <th className="px-4 py-3 text-right font-medium">가격</th>
              <th className="px-4 py-3 text-right font-medium">24h 변동</th>
              <th className="px-4 py-3 text-right font-medium">거래량</th>
              <th className="px-4 py-3 text-center font-medium">차트</th>
            </tr>
          </thead>
          <tbody>
            {coins?.coins.map((c) => {
              const up = c.change_24h_pct >= 0;
              return (
                <tr key={c.symbol} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/coins/${c.symbol}`}
                      className="flex items-center gap-2 font-semibold"
                    >
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                        {c.symbol[0]}
                      </span>
                      <span>
                        {c.symbol}
                        <span className="ml-2 text-xs font-normal text-slate-400">{c.name}</span>
                      </span>
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    ${(parseFloat(c.price_human) || 0).toLocaleString("en-US", {
                      maximumFractionDigits: 4,
                    })}
                  </td>
                  <td
                    className={cn(
                      "px-4 py-3 text-right tabular-nums",
                      up ? "text-emerald-600" : "text-red-600"
                    )}
                  >
                    <span className="inline-flex items-center gap-1">
                      {up ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                      {up ? "+" : ""}
                      {c.change_24h_pct.toFixed(2)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-600">
                    {c.volume_24h_human}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-center">
                      <Sparkline values={c.sparkline} isUp={up} />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {(coins?.coins.length ?? 0) === 0 && (
          <div className="p-12 text-center text-sm text-slate-400">
            지원 페어가 아직 없어요. 백엔드 시드를 실행해주세요.
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  subtext,
  accent,
}: {
  label: string;
  value: string;
  subtext?: string;
  accent?: "red";
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <div
          className={cn(
            "text-xl font-bold tabular-nums",
            accent === "red" ? "text-red-600" : "text-slate-900"
          )}
        >
          {value}
        </div>
        {subtext && <div className="text-xs text-slate-400">{subtext}</div>}
      </div>
    </div>
  );
}
