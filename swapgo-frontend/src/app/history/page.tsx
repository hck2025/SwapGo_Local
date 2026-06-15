"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, API_BASE, type StatsResp, type TxRow } from "@/lib/api";
import { useWallet } from "@/lib/wallet";
import { useWalletModal } from "@/components/wallet-modal";
import { Download, Filter } from "lucide-react";
import { cn } from "@/lib/cn";

const TYPES = [
  { k: "", l: "전체" },
  { k: "swap", l: "스왑" },
  { k: "deposit", l: "입금" },
  { k: "withdraw", l: "출금" },
  { k: "add_liq", l: "유동성 공급" },
  { k: "remove_liq", l: "유동성 회수" },
];

export default function HistoryPage() {
  const wallet = useWallet();
  const { open } = useWalletModal();
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);

  const { data: stats } = useQuery({
    queryKey: ["stats", wallet.token],
    queryFn: () => api<StatsResp>("/me/stats", { token: wallet.token }),
    enabled: !!wallet.token,
  });
  const { data: txs } = useQuery({
    queryKey: ["myTx-history", wallet.token, type, page],
    queryFn: () =>
      api<{ items: TxRow[]; total: number; page: number; page_size: number }>(
        `/me/transactions?page=${page}&page_size=20${type ? `&type=${type}` : ""}`,
        { token: wallet.token }
      ),
    enabled: !!wallet.token,
  });

  if (!wallet.address) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-12 text-center">
        <div className="text-sm text-slate-500">지갑을 연결하면 거래내역을 볼 수 있어요.</div>
        <button
          onClick={open}
          className="mt-3 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          지갑 연결
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">거래 내역</h1>
          <p className="text-sm text-slate-500">모든 거래 기록을 확인하고 분석하세요</p>
        </div>
        <a
          href={`${API_BASE}/me/transactions.csv`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-3 py-2 text-xs hover:bg-slate-50"
        >
          <Download size={14} /> CSV 다운로드
        </a>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="총 거래" value={String(stats?.trade_count ?? 0)} />
        <Stat label="총 수수료" value={`$${stats?.total_fees_paid_quote_human ?? "0"}`} />
        <Stat label="총 거래액" value={`$${stats?.total_volume_quote_human ?? "0"}`} />
        <Stat label="승률" value={stats?.win_rate_pct == null ? "—" : `${stats.win_rate_pct}%`} />
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center gap-2 text-xs text-slate-500">
          <Filter size={14} />
          {TYPES.map((t) => (
            <button
              key={t.k}
              onClick={() => {
                setType(t.k);
                setPage(1);
              }}
              className={cn(
                "rounded-full px-2 py-0.5",
                type === t.k ? "bg-blue-600 text-white" : "border border-slate-200 hover:bg-slate-50"
              )}
            >
              {t.l}
            </button>
          ))}
        </div>

        <div className="overflow-auto">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-3 py-2 font-medium">시각</th>
                <th className="px-3 py-2 font-medium">tx</th>
                <th className="px-3 py-2 font-medium">유형</th>
                <th className="px-3 py-2 text-right font-medium">in</th>
                <th className="px-3 py-2 text-right font-medium">out</th>
                <th className="px-3 py-2 text-right font-medium">slip</th>
                <th className="px-3 py-2 text-center font-medium">검증</th>
              </tr>
            </thead>
            <tbody>
              {(txs?.items ?? []).map((t) => (
                <tr key={t.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 whitespace-nowrap text-slate-500">
                    {new Date(t.created_at).toLocaleString("ko-KR")}
                  </td>
                  <td className="px-3 py-2 font-mono">#{t.id}</td>
                  <td className="px-3 py-2">{t.tx_type}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{t.amount_in ?? "-"}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{t.amount_out ?? "-"}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {t.slippage_bps != null ? `${(t.slippage_bps / 100).toFixed(2)}%` : "-"}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <Link
                      href={`/explorer?tx=${t.id}`}
                      className="text-blue-600 hover:underline"
                    >
                      익스플로러
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {txs && txs.total > txs.page_size && (
          <div className="mt-3 flex items-center justify-end gap-2 text-xs">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-md border border-slate-200 px-2 py-1 disabled:opacity-40"
            >
              이전
            </button>
            <span>
              {page} / {Math.ceil(txs.total / txs.page_size)}
            </span>
            <button
              disabled={page * txs.page_size >= txs.total}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-md border border-slate-200 px-2 py-1 disabled:opacity-40"
            >
              다음
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-bold tabular-nums">{value}</div>
    </div>
  );
}
