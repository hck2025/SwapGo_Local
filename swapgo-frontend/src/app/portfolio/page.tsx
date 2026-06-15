"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiException, type Balance, type TxRow } from "@/lib/api";
import { useWallet } from "@/lib/wallet";
import { useWalletModal } from "@/components/wallet-modal";
import { useToast } from "@/components/toast";
import { cn } from "@/lib/cn";
import { Copy, ArrowDownLeft, ArrowUpRight } from "lucide-react";

export default function PortfolioPage() {
  const wallet = useWallet();
  const { open } = useWalletModal();
  const [tab, setTab] = useState<"deposit" | "withdraw">("deposit");

  if (!wallet.address) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-12 text-center">
        <div className="text-sm text-slate-500">지갑을 연결하면 입출금을 할 수 있어요.</div>
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
      <div>
        <h1 className="text-2xl font-bold">지갑 관리</h1>
        <p className="text-sm text-slate-500">자산을 입금하고 출금하세요</p>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_360px]">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 flex rounded-md bg-slate-100 p-1">
            <button
              onClick={() => setTab("deposit")}
              className={cn(
                "flex flex-1 items-center justify-center gap-1 rounded-md py-2 text-sm font-semibold",
                tab === "deposit" ? "bg-blue-600 text-white" : "text-slate-600"
              )}
            >
              <ArrowDownLeft size={14} /> 입금
            </button>
            <button
              onClick={() => setTab("withdraw")}
              className={cn(
                "flex flex-1 items-center justify-center gap-1 rounded-md py-2 text-sm font-semibold",
                tab === "withdraw" ? "bg-blue-600 text-white" : "text-slate-600"
              )}
            >
              <ArrowUpRight size={14} /> 출금
            </button>
          </div>
          {tab === "deposit" ? <DepositForm /> : <WithdrawForm />}
        </div>

        <div className="space-y-3">
          <BalancesCard />
          <RecentTxCard />
        </div>
      </div>
    </div>
  );
}

function BalancesCard() {
  const wallet = useWallet();
  const { data } = useQuery({
    queryKey: ["wallet", wallet.token],
    queryFn: () =>
      api<{ address: string; balances: Balance[] }>("/wallet/me", { token: wallet.token }),
    enabled: !!wallet.token,
    refetchInterval: 6000,
  });
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-2 text-sm font-semibold">내 자산</div>
      <div className="divide-y divide-slate-100">
        {(data?.balances ?? []).map((b) => (
          <div key={b.symbol} className="flex items-center justify-between py-2">
            <span className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                {b.symbol[0]}
              </span>
              <span className="text-sm font-semibold">{b.symbol}</span>
            </span>
            <span className="text-sm tabular-nums">{b.amount_human}</span>
          </div>
        ))}
        {(data?.balances ?? []).length === 0 && (
          <div className="py-6 text-center text-xs text-slate-400">
            아직 자산이 없어요. 입금 탭에서 모의 입금을 해보세요.
          </div>
        )}
      </div>
    </div>
  );
}

function RecentTxCard() {
  const wallet = useWallet();
  const { data } = useQuery({
    queryKey: ["myTx-portfolio", wallet.token],
    queryFn: () =>
      api<{ items: TxRow[] }>(`/me/transactions?page_size=5`, { token: wallet.token }),
    enabled: !!wallet.token,
    refetchInterval: 6000,
  });
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-2 text-sm font-semibold">최근 거래</div>
      {(data?.items ?? []).length === 0 ? (
        <div className="py-6 text-center text-xs text-slate-400">거래 내역이 없습니다</div>
      ) : (
        <ul className="divide-y divide-slate-100 text-xs">
          {data!.items.slice(0, 5).map((t) => (
            <li key={t.id} className="py-1.5">
              <span className="mr-2 font-mono text-slate-600">#{t.id}</span>
              <span>{t.tx_type}</span>
              <span className="float-right text-slate-400">
                {new Date(t.created_at).toLocaleTimeString("ko-KR")}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function DepositForm() {
  const wallet = useWallet();
  const toast = useToast();
  const qc = useQueryClient();
  const [symbol, setSymbol] = useState("USDT");
  const [amount, setAmount] = useState("1000");
  const [busy, setBusy] = useState(false);

  const handle = async () => {
    setBusy(true);
    try {
      await api<unknown>("/wallet/deposit/mock", {
        method: "POST",
        body: { symbol, amount },
        token: wallet.token,
      });
      toast.push({ kind: "success", title: "입금 완료", message: `${amount} ${symbol}` });
      qc.invalidateQueries({ queryKey: ["wallet"] });
      qc.invalidateQueries({ queryKey: ["myTx-portfolio"] });
    } catch (e) {
      if (e instanceof ApiException)
        toast.push({
          kind: "error",
          title: e.error.code,
          message: e.error.message,
          suggestion: e.error.suggestion,
        });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <Field label="자산 선택">
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="USDT">USDT</option>
          <option value="BTC">BTC</option>
          <option value="ETH">ETH</option>
        </select>
      </Field>
      <Field label="모의 입금 주소">
        <div className="flex items-center justify-between rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs">
          <span className="font-mono">{wallet.address}</span>
          <button
            onClick={() => wallet.address && navigator.clipboard.writeText(wallet.address)}
            className="text-slate-500 hover:text-slate-700"
          >
            <Copy size={14} />
          </button>
        </div>
      </Field>
      <Field label="수량">
        <input
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          inputMode="decimal"
          className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm tabular-nums"
        />
      </Field>
      <button
        onClick={handle}
        disabled={busy || !amount}
        className={cn(
          "w-full rounded-md py-2.5 text-sm font-semibold text-white",
          busy ? "bg-slate-300" : "bg-blue-600 hover:bg-blue-700"
        )}
      >
        {busy ? "처리 중..." : "모의 입금하기"}
      </button>
      <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
        ⚠️ 스왑고는 학습용 모의 환경이에요. 실제 자산은 받지 않으며, 테스트 가능한 가상의 입금이 즉시
        반영됩니다.
      </div>
    </div>
  );
}

function WithdrawForm() {
  const wallet = useWallet();
  const toast = useToast();
  const qc = useQueryClient();
  const [symbol, setSymbol] = useState("USDT");
  const [amount, setAmount] = useState("");
  const [to, setTo] = useState("0x");
  const [busy, setBusy] = useState(false);

  const handle = async () => {
    setBusy(true);
    try {
      await api<unknown>("/wallet/withdraw/mock", {
        method: "POST",
        body: { symbol, amount, to_address: to },
        token: wallet.token,
      });
      toast.push({ kind: "success", title: "출금 완료", message: `${amount} ${symbol} → ${to.slice(0,8)}…` });
      qc.invalidateQueries({ queryKey: ["wallet"] });
    } catch (e) {
      if (e instanceof ApiException)
        toast.push({
          kind: "error",
          title: e.error.code,
          message: e.error.message,
          suggestion: e.error.suggestion,
        });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <Field label="자산 선택">
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="USDT">USDT</option>
          <option value="BTC">BTC</option>
          <option value="ETH">ETH</option>
        </select>
      </Field>
      <Field label="출금 주소">
        <input
          value={to}
          onChange={(e) => setTo(e.target.value)}
          className="w-full rounded-md border border-slate-200 px-3 py-2 font-mono text-xs"
        />
      </Field>
      <Field label="출금 수량">
        <input
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          inputMode="decimal"
          className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm tabular-nums"
        />
      </Field>
      <button
        onClick={handle}
        disabled={busy || !amount}
        className={cn(
          "w-full rounded-md py-2.5 text-sm font-semibold text-white",
          busy ? "bg-slate-300" : "bg-blue-600 hover:bg-blue-700"
        )}
      >
        {busy ? "처리 중..." : "출금하기"}
      </button>
      <div className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700">
        ⚠️ 출금 주소를 정확히 확인하세요. 잘못된 주소로 출금 시 복구가 불가능합니다.
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-slate-600">{label}</span>
      {children}
    </label>
  );
}
