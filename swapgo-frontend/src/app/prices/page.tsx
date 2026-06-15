"use client";

import { useQuery } from "@tanstack/react-query";
import { api, type Coin, type GlobalMarket } from "@/lib/api";
import { cn } from "@/lib/cn";

export default function PricesPage() {
  const { data: g } = useQuery({
    queryKey: ["market-global"],
    queryFn: () => api<GlobalMarket>("/market/global"),
    refetchInterval: 12000,
  });
  const { data: coins } = useQuery({
    queryKey: ["market-coins"],
    queryFn: () => api<{ coins: Coin[] }>("/market/coins"),
    refetchInterval: 8000,
  });

  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-2xl font-bold">가격 비교</h1>
        <p className="text-sm text-slate-500">
          모든 암호화폐의 가격과 변동률을 한눈에 확인하세요
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="전체 시가총액" value={`$${g?.total_market_cap_usdt_human ?? 0}`} accent="blue" />
        <Stat label="24h 거래량" value={`$${g?.total_volume_24h_usdt_human ?? 0}`} accent="emerald" />
        <Stat label="BTC 도미넌스" value={`${g?.btc_dominance_pct ?? 0}%`} accent="amber" />
        <Stat label="ETH 도미넌스" value={`${g?.eth_dominance_pct ?? 0}%`} accent="indigo" />
      </div>

      <div className="rounded-md border border-slate-200 bg-blue-50 p-3 text-xs text-blue-700">
        ℹ️ {g?.note ?? "시장 통계는 거래소 내부 풀 기반 학습용 추정치입니다."}
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">#</th>
              <th className="px-4 py-3 font-medium">코인</th>
              <th className="px-4 py-3 text-right font-medium">가격</th>
              <th className="px-4 py-3 text-right font-medium">24h</th>
              <th className="px-4 py-3 text-right font-medium">거래량</th>
            </tr>
          </thead>
          <tbody>
            {coins?.coins.map((c, i) => {
              const up = c.change_24h_pct >= 0;
              return (
                <tr key={c.symbol} className="border-t border-slate-100">
                  <td className="px-4 py-3 text-slate-500">{i + 1}</td>
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-2">
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                        {c.symbol[0]}
                      </span>
                      <span className="font-semibold">{c.symbol}</span>
                      <span className="text-xs text-slate-400">{c.name}</span>
                    </span>
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
                    {up ? "+" : ""}
                    {c.change_24h_pct.toFixed(2)}%
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-600">
                    {c.volume_24h_human}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: "blue" | "emerald" | "amber" | "indigo";
}) {
  const cls = {
    blue: "from-blue-50 to-white border-blue-100",
    emerald: "from-emerald-50 to-white border-emerald-100",
    amber: "from-amber-50 to-white border-amber-100",
    indigo: "from-indigo-50 to-white border-indigo-100",
  }[accent];
  return (
    <div className={cn("rounded-lg border bg-gradient-to-br p-4", cls)}>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-bold tabular-nums">{value}</div>
    </div>
  );
}
