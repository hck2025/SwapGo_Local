"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiException, type Balance, type Pool, type SwapQuote, type SwapResult } from "@/lib/api";
import { useWallet } from "@/lib/wallet";
import { useWalletModal } from "@/components/wallet-modal";
import { useToast } from "@/components/toast";
import { SlippagePill } from "@/components/slippage-pill";
import { InfoTooltip } from "@/components/info-tooltip";
import { ArrowDownUp, Settings2 } from "lucide-react";
import { cn } from "@/lib/cn";

const PRESETS = [25, 50, 75, 100];
const SLIPPAGES: (number | "auto")[] = ["auto", 50, 100];

export function SwapPanel({ pool }: { pool: Pool }) {
  const wallet = useWallet();
  const { open } = useWalletModal();
  const toast = useToast();
  const qc = useQueryClient();

  const [side, setSide] = useState<"base_to_quote" | "quote_to_base">("quote_to_base");
  const [amount, setAmount] = useState<string>("");
  const [slip, setSlip] = useState<number | "auto">("auto");
  const [submitting, setSubmitting] = useState(false);
  const [advanced, setAdvanced] = useState(false);

  const inSym = side === "base_to_quote" ? pool.base_symbol : pool.quote_symbol;
  const outSym = side === "base_to_quote" ? pool.quote_symbol : pool.base_symbol;

  // 잔고
  const { data: walletData } = useQuery({
    queryKey: ["wallet", wallet.token],
    queryFn: () =>
      api<{ address: string; balances: Balance[] }>("/wallet/me", { token: wallet.token }),
    enabled: !!wallet.token,
    refetchInterval: 8000,
  });
  const balanceMap = useMemo(() => {
    const m: Record<string, Balance> = {};
    walletData?.balances.forEach((b) => (m[b.symbol] = b));
    return m;
  }, [walletData]);
  const inBalance = balanceMap[inSym]?.amount_human ?? "0";
  const outBalance = balanceMap[outSym]?.amount_human ?? "0";

  // 견적 (debounced)
  const [quote, setQuote] = useState<SwapQuote | null>(null);
  const [quoting, setQuoting] = useState(false);
  const [quoteErr, setQuoteErr] = useState<string | null>(null);

  useEffect(() => {
    setQuote(null);
    setQuoteErr(null);
    if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) return;
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      setQuoting(true);
      try {
        const q = await api<SwapQuote>(`/swap/quote`, {
          method: "POST",
          body: {
            pool_id: pool.id,
            side,
            amount_in_human: amount,
            slippage_tolerance_bps: slip === "auto" ? null : slip,
          },
          signal: ctrl.signal,
        });
        setQuote(q);
      } catch (e) {
        if (e instanceof ApiException) {
          setQuoteErr(e.error.message);
        }
      } finally {
        setQuoting(false);
      }
    }, 350);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [amount, side, slip, pool.id]);

  const setPercent = (p: number) => {
    const bal = parseFloat(inBalance);
    if (!isFinite(bal) || bal <= 0) return;
    const v = (bal * p) / 100;
    setAmount(p === 100 ? String(bal) : v.toFixed(6).replace(/\.?0+$/, ""));
  };

  const flip = () => setSide((s) => (s === "base_to_quote" ? "quote_to_base" : "base_to_quote"));

  const handleSwap = async () => {
    if (!wallet.token || !quote) return;
    setSubmitting(true);
    try {
      const res = await api<SwapResult>("/swap/execute", {
        method: "POST",
        body: {
          pool_id: pool.id,
          side,
          amount_in_human: amount,
          min_amount_out: quote.amount_out_min,
          slippage_tolerance_bps: quote.slippage_threshold_used_bps,
          expected_revision: quote.pool_after.revision,
        },
        token: wallet.token,
      });
      toast.push({
        kind: "success",
        title: "스왑 완료",
        message: `${quote.amount_in_human} ${inSym} → ${quote.amount_out_human} ${outSym}`,
        suggestion: `tx#${res.tx_id} · 익스플로러에서 무결성 검증 가능`,
        glossary_keys: ["integrity"],
      });
      setAmount("");
      setQuote(null);
      qc.invalidateQueries({ queryKey: ["wallet"] });
      qc.invalidateQueries({ queryKey: ["pools"] });
      qc.invalidateQueries({ queryKey: ["chart", pool.id] });
      qc.invalidateQueries({ queryKey: ["orderbook", pool.id] });
      qc.invalidateQueries({ queryKey: ["trades", pool.id] });
      qc.invalidateQueries({ queryKey: ["myTx"] });
    } catch (e) {
      if (e instanceof ApiException) {
        toast.push({
          kind: "error",
          title: e.error.code,
          message: e.error.message,
          suggestion: e.error.suggestion,
          glossary_keys: e.error.glossary_keys,
        });
      } else {
        toast.push({ kind: "error", title: "오류", message: (e as Error).message });
      }
    } finally {
      setSubmitting(false);
    }
  };

  const dangerLevel = quote?.slippage_level === "danger";
  const overTolerance = quote && quote.slippage_bps > quote.slippage_threshold_used_bps;
  const noBalance = parseFloat(amount || "0") > parseFloat(inBalance || "0");

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-base font-bold">
          <InfoTooltip termKey="swap">
            <span>스왑</span>
          </InfoTooltip>
        </div>
        <button
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700"
          onClick={() => setAdvanced((v) => !v)}
        >
          <Settings2 size={12} /> 고급 설정
        </button>
      </div>

      <Field
        title="보낼 코인"
        symbol={inSym}
        value={amount}
        onChange={setAmount}
        balance={inBalance}
      />
      <div className="my-1 flex justify-center">
        <button
          onClick={flip}
          className="rounded-full border border-slate-200 bg-white p-1.5 hover:bg-slate-50"
        >
          <ArrowDownUp size={14} />
        </button>
      </div>
      <Field
        title="받을 코인"
        symbol={outSym}
        value={quote?.amount_out_human ?? "0.00"}
        balance={outBalance}
        readOnly
        sub={pool.price ? `1 ${pool.base_symbol} = ${pool.price} ${pool.quote_symbol}` : ""}
      />

      <div className="mt-3 flex flex-wrap gap-2">
        {PRESETS.map((p) => (
          <button
            key={p}
            onClick={() => setPercent(p)}
            disabled={!wallet.token}
            className="flex-1 rounded-md border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50 disabled:opacity-40"
          >
            {p === 100 ? "전액" : `${p}%`}
          </button>
        ))}
      </div>

      <div className="mt-3 flex items-center gap-2">
        <span className="text-xs text-slate-500">
          <InfoTooltip termKey="slippage">
            <span>슬리피지</span>
          </InfoTooltip>{" "}
          허용치
        </span>
        <div className="flex flex-1 items-center justify-end gap-1">
          {SLIPPAGES.map((s) => (
            <button
              key={String(s)}
              onClick={() => setSlip(s)}
              className={cn(
                "rounded-full border px-2 py-0.5 text-[11px]",
                slip === s
                  ? "border-blue-300 bg-blue-50 text-blue-700"
                  : "border-slate-200 text-slate-600 hover:bg-slate-50"
              )}
            >
              {s === "auto" ? "자동" : `${s / 100}%`}
            </button>
          ))}
        </div>
      </div>

      {advanced && (
        <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600 space-y-1">
          <div>
            풀 ID #{pool.id} ({pool.base_symbol}/{pool.quote_symbol})
          </div>
          <div>수수료: {pool.fee_bps / 100}%</div>
          <div>풀 revision: {pool.revision}</div>
        </div>
      )}

      {quote && (
        <div className="mt-3 space-y-1 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs">
          <div className="flex justify-between">
            <span className="text-slate-500">예상 수령</span>
            <span className="tabular-nums">
              {quote.amount_out_human} {outSym}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">최소 수령 (min)</span>
            <span className="tabular-nums">{quote.amount_out_min}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">
              <InfoTooltip termKey="price_impact">
                <span>가격 영향</span>
              </InfoTooltip>
            </span>
            <span className="tabular-nums">{(quote.price_impact_bps / 100).toFixed(2)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">수수료</span>
            <span className="tabular-nums">
              {quote.amount_in_human === "0" ? "0" : `${(quote.fee_bps / 100).toFixed(2)}%`}
            </span>
          </div>
          <div className="pt-1">
            <SlippagePill level={quote.slippage_level} bps={quote.slippage_bps} />
          </div>
          <div
            className={cn(
              "rounded-md p-2 text-[11px]",
              dangerLevel
                ? "bg-red-50 text-red-700"
                : quote.slippage_level === "warning"
                ? "bg-amber-50 text-amber-700"
                : "bg-emerald-50 text-emerald-700"
            )}
          >
            {quote.friendly_message}
          </div>
        </div>
      )}

      {quoteErr && (
        <div className="mt-2 rounded-md border border-red-300 bg-red-50 p-2 text-xs text-red-700">
          {quoteErr}
        </div>
      )}

      <button
        onClick={wallet.token ? handleSwap : open}
        disabled={
          wallet.token
            ? !quote || submitting || quoting || noBalance || !!overTolerance
            : false
        }
        className={cn(
          "mt-3 w-full rounded-md py-2.5 text-sm font-semibold text-white transition",
          !wallet.token
            ? "bg-blue-600 hover:bg-blue-700"
            : !quote || submitting || quoting || noBalance || overTolerance
            ? "cursor-not-allowed bg-slate-300"
            : dangerLevel
            ? "bg-red-600 hover:bg-red-700"
            : "bg-blue-600 hover:bg-blue-700"
        )}
      >
        {!wallet.token
          ? "지갑 연결"
          : !amount
          ? "수량을 입력하세요"
          : noBalance
          ? "잔고 부족"
          : overTolerance
          ? "허용치 초과 — 수량 줄이거나 허용치 ↑"
          : quoting
          ? "견적 계산 중…"
          : submitting
          ? "스왑 처리 중…"
          : dangerLevel
          ? "위험 — 그래도 스왑"
          : "스왑하기"}
      </button>
    </div>
  );
}

function Field({
  title,
  symbol,
  value,
  onChange,
  balance,
  readOnly,
  sub,
}: {
  title: string;
  symbol: string;
  value: string;
  onChange?: (v: string) => void;
  balance: string;
  readOnly?: boolean;
  sub?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="mb-1 flex justify-between text-[11px] text-slate-500">
        <span>{title}</span>
        <span className="max-w-[55%] truncate">잔고: {balance}</span>
      </div>
      <div className="flex min-w-0 items-center gap-2">
        <div className="flex h-9 shrink-0 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-[10px] font-bold text-blue-700">
            {symbol[0]}
          </span>
          {symbol}
        </div>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          readOnly={readOnly}
          inputMode="decimal"
          placeholder="0.00"
          title={value}
          className={cn(
            "w-0 min-w-0 flex-1 rounded-md bg-transparent text-right font-semibold tabular-nums outline-none",
            // 입력 길이에 따라 자동으로 폰트 축소 → 컨테이너를 넘어가지 않게
            value.length > 18
              ? "text-sm"
              : value.length > 14
              ? "text-base"
              : value.length > 10
              ? "text-lg"
              : "text-2xl",
            readOnly && "text-slate-400"
          )}
        />
      </div>
      {sub && <div className="mt-1 truncate text-right text-[11px] text-slate-400">{sub}</div>}
    </div>
  );
}
