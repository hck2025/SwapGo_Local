"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, type AiSignal, type Pool, type Trade, type TxRow } from "@/lib/api";
import { useWallet } from "@/lib/wallet";
import { cn } from "@/lib/cn";
import { SlippagePill } from "@/components/slippage-pill";

type TabKey = "trades" | "my" | "ai" | "mock";

export function TradeTabs({ pool }: { pool: Pool }) {
  const [tab, setTab] = useState<TabKey>("trades");
  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <div className="flex border-b border-slate-200">
        {[
          { k: "trades", l: "체결 내역" },
          { k: "my", l: "내 거래" },
          { k: "ai", l: "AI 분석" },
          { k: "mock", l: "모의 투자" },
        ].map((t) => (
          <button
            key={t.k}
            onClick={() => setTab(t.k as TabKey)}
            className={cn(
              "px-4 py-2.5 text-sm",
              tab === t.k ? "border-b-2 border-blue-600 font-semibold text-blue-700" : "text-slate-500"
            )}
          >
            {t.l}
          </button>
        ))}
      </div>
      <div className="max-h-[320px] overflow-auto scrollbar-thin">
        {tab === "trades" && <TradesPanel pool={pool} />}
        {tab === "my" && <MyTradesPanel pool={pool} />}
        {tab === "ai" && <AiPanel symbol={pool.base_symbol} />}
        {tab === "mock" && <MockPanel pool={pool} />}
      </div>
    </div>
  );
}

function TradesPanel({ pool }: { pool: Pool }) {
  const { data } = useQuery({
    queryKey: ["trades", pool.id],
    queryFn: () => api<Trade[]>(`/market/trades?pool_id=${pool.id}&limit=30`),
    refetchInterval: 4000,
  });
  if (!data || data.length === 0) {
    return <Empty msg="아직 체결된 거래가 없어요." />;
  }
  return (
    <table className="w-full text-xs">
      <thead className="sticky top-0 bg-slate-50 text-left text-slate-500">
        <tr>
          <th className="px-4 py-2 font-medium">가격</th>
          <th className="px-4 py-2 font-medium">방향</th>
          <th className="px-4 py-2 font-medium">수량</th>
          <th className="px-4 py-2 text-right font-medium">시각</th>
        </tr>
      </thead>
      <tbody>
        {data.map((t) => (
          <tr key={t.tx_id} className="border-t border-slate-100">
            <td className="px-4 py-1.5 tabular-nums">
              <span className={t.side === "quote_to_base" ? "text-emerald-600" : "text-red-600"}>
                {parseFloat(t.price).toLocaleString("en-US", { maximumFractionDigits: 2 })}
              </span>
            </td>
            <td className="px-4 py-1.5">
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[10px]",
                  t.side === "quote_to_base"
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-red-100 text-red-700"
                )}
              >
                {t.side === "quote_to_base" ? "매수" : "매도"}
              </span>
            </td>
            <td className="px-4 py-1.5 tabular-nums">
              {parseFloat(t.amount_base_human || "0").toLocaleString("en-US", {
                maximumFractionDigits: 6,
              })}
              <span className="ml-1 text-[10px] text-slate-400">{t.base_symbol}</span>
            </td>
            <td className="px-4 py-1.5 text-right text-slate-400">
              {new Date(t.created_at).toLocaleTimeString("ko-KR")}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function MyTradesPanel({ pool }: { pool: Pool }) {
  const wallet = useWallet();
  const { data } = useQuery({
    queryKey: ["myTx", pool.id, wallet.token],
    queryFn: () =>
      api<{ items: TxRow[]; total: number; page: number; page_size: number }>(
        `/me/transactions?pool=${pool.id}&page_size=30`,
        { token: wallet.token }
      ),
    enabled: !!wallet.token,
  });
  if (!wallet.token) return <Empty msg="지갑을 연결하면 내 거래를 볼 수 있어요." />;
  if (!data || data.items.length === 0) return <Empty msg="아직 거래 내역이 없어요." />;
  return (
    <table className="w-full text-xs">
      <thead className="sticky top-0 bg-slate-50 text-left text-slate-500">
        <tr>
          <th className="px-4 py-2 font-medium">tx</th>
          <th className="px-4 py-2 font-medium">유형</th>
          <th className="px-4 py-2 font-medium">슬리피지</th>
          <th className="px-4 py-2 text-right font-medium">시각</th>
        </tr>
      </thead>
      <tbody>
        {data.items.map((t) => (
          <tr key={t.id} className="border-t border-slate-100">
            <td className="px-4 py-1.5 font-mono text-slate-600">#{t.id}</td>
            <td className="px-4 py-1.5">{t.tx_type}</td>
            <td className="px-4 py-1.5">
              {t.slippage_bps !== null ? (
                <SlippagePill
                  level={
                    t.slippage_bps < 50 ? "safe" : t.slippage_bps < 300 ? "warning" : "danger"
                  }
                  bps={t.slippage_bps}
                />
              ) : (
                "-"
              )}
            </td>
            <td className="px-4 py-1.5 text-right text-slate-400">
              {new Date(t.created_at).toLocaleString("ko-KR")}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function AiPanel({ symbol }: { symbol: string }) {
  const { data } = useQuery({
    queryKey: ["ai-signals", symbol],
    queryFn: () => api<AiSignal[]>(`/ai/signals?symbol=${symbol}&limit=10`),
    refetchInterval: 10_000,
  });
  if (!data || data.length === 0) {
    return (
      <Empty msg="AI 봇이 아직 신호를 올리지 않았어요. AI팀 봇이 가동되면 여기에 표시돼요." />
    );
  }
  return (
    <div className="divide-y divide-slate-100">
      {data.map((s) => (
        <div key={s.id} className="flex items-start gap-3 px-4 py-3">
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-semibold",
              s.side === "buy" && "bg-emerald-100 text-emerald-700",
              s.side === "sell" && "bg-red-100 text-red-700",
              s.side === "hold" && "bg-amber-100 text-amber-700"
            )}
          >
            {s.side.toUpperCase()}
          </span>
          <div className="flex-1">
            <div className="text-sm">{s.reason || `신뢰도 ${(s.confidence * 100).toFixed(0)}%`}</div>
            <div className="text-[11px] text-slate-400">
              {new Date(s.created_at).toLocaleString("ko-KR")} · {s.source ?? "system"}
            </div>
          </div>
          <div className="text-xs font-semibold tabular-nums text-slate-500">
            {(s.confidence * 100).toFixed(0)}%
          </div>
        </div>
      ))}
    </div>
  );
}

function MockPanel({ pool }: { pool: Pool }) {
  const wallet = useWallet();
  const { data } = useQuery({
    queryKey: ["stats", wallet.token],
    queryFn: () =>
      api<{
        trade_count: number;
        total_fees_paid_quote_human: string;
        total_volume_quote_human: string;
        win_rate_pct: number | null;
        note: string;
      }>("/me/stats", { token: wallet.token }),
    enabled: !!wallet.token,
  });
  if (!wallet.token) return <Empty msg="지갑을 연결하면 모의투자 통계를 볼 수 있어요." />;
  return (
    <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-4">
      <Stat label="총 거래" value={String(data?.trade_count ?? 0)} />
      <Stat label="총 수수료" value={`${data?.total_fees_paid_quote_human ?? 0}`} />
      <Stat label="총 거래액" value={`${data?.total_volume_quote_human ?? 0}`} />
      <Stat label="승률" value={data?.win_rate_pct == null ? "—" : `${data.win_rate_pct}%`} />
      <div className="col-span-2 text-[11px] text-slate-400 sm:col-span-4">
        {data?.note ?? `풀 ${pool.base_symbol}/${pool.quote_symbol} 기준입니다.`}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 p-3">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="text-sm font-bold tabular-nums">{value}</div>
    </div>
  );
}

function Empty({ msg }: { msg: string }) {
  return <div className="px-4 py-12 text-center text-sm text-slate-400">{msg}</div>;
}
