"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { api, type ExplorerTx, type VerifyResp } from "@/lib/api";
import { InfoTooltip } from "@/components/info-tooltip";
import { ShieldCheck, Hash, Search } from "lucide-react";
import { cn } from "@/lib/cn";

export const dynamic = "force-dynamic";

export default function ExplorerPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-slate-400">로딩 중…</div>}>
      <ExplorerInner />
    </Suspense>
  );
}

function ExplorerInner() {
  const sp = useSearchParams();
  const txParam = sp.get("tx");
  const [searchAddr, setSearchAddr] = useState("");

  const { data: blocks } = useQuery({
    queryKey: ["explorer-blocks"],
    queryFn: () => api<ExplorerTx[]>(`/explorer/blocks?from=1&limit=50`),
    refetchInterval: 8000,
  });
  const { data: latestMerkle } = useQuery({
    queryKey: ["merkle-latest"],
    queryFn: () =>
      api<{
        id: number;
        from_tx_id: number;
        to_tx_id: number;
        merkle_root: string;
        tx_count: number;
        created_at: string;
      } | null>(`/explorer/merkle/latest`),
    refetchInterval: 30000,
  });

  return (
    <div className="space-y-3">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <ShieldCheck size={24} className="text-blue-600" /> 익스플로러
        </h1>
        <p className="text-sm text-slate-500">
          모든 거래는{" "}
          <InfoTooltip termKey="integrity">
            <span>해시 체인</span>
          </InfoTooltip>
          으로 연결되어 있어요. 누구나 무결성을 검증할 수 있습니다.
        </p>
      </div>

      {txParam && <TxDetail txId={parseInt(txParam)} />}

      <VerifyCard latestMerkle={latestMerkle ?? null} />

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center gap-2">
          <Search size={14} className="text-slate-400" />
          <input
            value={searchAddr}
            onChange={(e) => setSearchAddr(e.target.value)}
            placeholder="지갑 주소로 거래 검색 (0x...)"
            className="flex-1 rounded-md border border-slate-200 px-3 py-2 text-sm font-mono"
          />
          {searchAddr && (
            <button
              onClick={() => setSearchAddr("")}
              className="rounded-md border border-slate-200 px-2 py-1 text-xs"
            >
              초기화
            </button>
          )}
        </div>
        {searchAddr ? (
          <WalletTxs address={searchAddr} />
        ) : (
          <BlocksTable blocks={blocks ?? []} />
        )}
      </div>
    </div>
  );
}

function VerifyCard({
  latestMerkle,
}: {
  latestMerkle:
    | {
        id: number;
        from_tx_id: number;
        to_tx_id: number;
        merkle_root: string;
        tx_count: number;
      }
    | null;
}) {
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState<VerifyResp | null>(null);

  const run = async () => {
    setVerifying(true);
    try {
      const r = await api<VerifyResp>(`/explorer/verify?from=1`);
      setResult(r);
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50/40 p-4">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-blue-800">
        <ShieldCheck size={16} /> 무결성 검증
      </div>
      <p className="text-xs text-slate-600">
        체인의 모든 거래에 대해{" "}
        <code className="rounded bg-white px-1">sha256(prev_hash + meta + payload)</code> 로 다시
        해시를 계산해 위·변조 여부를 확인합니다. 다른 사용자나 익명 사용자도 동일하게 검증할 수
        있어요.
      </p>
      {latestMerkle && (
        <div className="mt-2 rounded-md border border-slate-200 bg-white p-2 text-[11px]">
          <div className="text-slate-500">최신 머클루트 스냅샷</div>
          <div className="font-mono break-all">{latestMerkle.merkle_root}</div>
          <div className="text-slate-400">
            tx#{latestMerkle.from_tx_id}–{latestMerkle.to_tx_id} ({latestMerkle.tx_count}건)
          </div>
        </div>
      )}
      <button
        onClick={run}
        disabled={verifying}
        className="mt-3 inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
      >
        {verifying ? "검증 중..." : "전체 체인 검증 실행"}
      </button>
      {result && (
        <div
          className={cn(
            "mt-3 rounded-md border p-3 text-xs",
            result.ok ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-700"
          )}
        >
          <div className="font-semibold">
            {result.ok ? "✅ 무결성 검증 통과" : "❌ 무결성 위반"} ({result.count}건)
          </div>
          {result.first_invalid_id != null && (
            <div>위변조 추정 위치: tx#{result.first_invalid_id}</div>
          )}
          {result.recomputed_root && (
            <div className="break-all font-mono">머클루트: {result.recomputed_root}</div>
          )}
          {result.friendly_message && (
            <div className="mt-1 text-slate-600">{result.friendly_message}</div>
          )}
        </div>
      )}
    </div>
  );
}

function TxDetail({ txId }: { txId: number }) {
  const { data } = useQuery({
    queryKey: ["tx", txId],
    queryFn: () => api<ExplorerTx>(`/explorer/tx/${txId}`),
  });
  if (!data) {
    return <div className="rounded-lg border border-slate-200 bg-white p-4">로딩 중…</div>;
  }
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
        <Hash size={14} /> 트랜잭션 #{data.id} · {data.tx_type}
      </div>
      <Row k="prev_hash" v={data.prev_hash} mono />
      <Row k="tx_hash" v={data.tx_hash} mono accent />
      <Row k="actor" v={data.actor_address || "system"} mono />
      <Row k="created_at" v={new Date(data.created_at).toLocaleString("ko-KR")} />
      <details className="mt-2 rounded-md border border-slate-200 p-2 text-xs">
        <summary className="cursor-pointer text-slate-600">payload</summary>
        <pre className="mt-2 overflow-auto bg-slate-50 p-2">{JSON.stringify(data.payload, null, 2)}</pre>
      </details>
      {data.friendly_message && (
        <div className="mt-2 rounded-md border border-blue-200 bg-blue-50 p-2 text-xs text-blue-700">
          {data.friendly_message}
        </div>
      )}
    </div>
  );
}

function Row({ k, v, mono, accent }: { k: string; v: string; mono?: boolean; accent?: boolean }) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-2 py-1 text-xs">
      <div className="text-slate-500">{k}</div>
      <div
        className={cn(
          "break-all",
          mono && "font-mono",
          accent && "font-semibold text-blue-700"
        )}
      >
        {v}
      </div>
    </div>
  );
}

function WalletTxs({ address }: { address: string }) {
  const { data } = useQuery({
    queryKey: ["wallet-explorer", address],
    queryFn: () => api<{ address: string; items: ExplorerTx[] }>(`/explorer/wallet/${address}`),
  });
  if (!data) return <div className="text-center text-sm text-slate-400">로딩 중…</div>;
  if (data.items.length === 0)
    return (
      <div className="py-8 text-center text-sm text-slate-400">해당 주소의 거래가 없어요.</div>
    );
  return <BlocksTable blocks={data.items} />;
}

function BlocksTable({ blocks }: { blocks: ExplorerTx[] }) {
  return (
    <div className="overflow-auto">
      <table className="w-full text-xs">
        <thead className="bg-slate-50 text-left text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">tx</th>
            <th className="px-3 py-2 font-medium">유형</th>
            <th className="px-3 py-2 font-medium">주소</th>
            <th className="px-3 py-2 font-medium">tx_hash</th>
            <th className="px-3 py-2 text-right font-medium">시각</th>
          </tr>
        </thead>
        <tbody>
          {blocks.map((b) => (
            <tr key={b.id} className="border-t border-slate-100 hover:bg-slate-50">
              <td className="px-3 py-2 font-mono">
                <Link href={`/explorer?tx=${b.id}`} className="text-blue-600 hover:underline">
                  #{b.id}
                </Link>
              </td>
              <td className="px-3 py-2">{b.tx_type}</td>
              <td className="px-3 py-2 font-mono text-slate-500">
                {b.actor_address ? `${b.actor_address.slice(0, 8)}…${b.actor_address.slice(-4)}` : "system"}
              </td>
              <td className="px-3 py-2 font-mono text-slate-400">
                {b.tx_hash.slice(0, 12)}…
              </td>
              <td className="px-3 py-2 text-right text-slate-400">
                {new Date(b.created_at).toLocaleString("ko-KR")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
