"use client";

import { useQuery } from "@tanstack/react-query";
import { api, type AiPrediction, type AiSentiment, type AiSignal, type Coin } from "@/lib/api";
import { cn } from "@/lib/cn";

export default function AiPage() {
  const { data: coins } = useQuery({
    queryKey: ["market-coins"],
    queryFn: () => api<{ coins: Coin[] }>("/market/coins"),
  });
  const symbols = coins?.coins.map((c) => c.symbol) ?? ["BTC", "ETH"];

  const { data: signals } = useQuery({
    queryKey: ["ai-signals-all"],
    queryFn: () => api<AiSignal[]>(`/ai/signals?limit=50`),
    refetchInterval: 10_000,
  });

  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-2xl font-bold">AI 시장 분석</h1>
        <p className="text-sm text-slate-500">인공지능이 실시간으로 시장을 분석하고 매매 신호를 제공합니다</p>
      </div>

      <Section title="실시간 AI 신호">
        {symbols.map((s) => {
          const last = signals?.find((x) => x.symbol === s);
          return <SignalRow key={s} symbol={s} signal={last} />;
        })}
        {(!signals || signals.length === 0) && (
          <Empty msg="AI 봇이 아직 신호를 올리지 않았어요. AI팀이 봇을 가동하면 여기에 표시돼요." />
        )}
      </Section>

      <Section title="가격 예측">
        {symbols.map((s) => (
          <PredictionRow key={s} symbol={s} />
        ))}
      </Section>

      <Section title="시장 심리 분석">
        {symbols.map((s) => (
          <SentimentRow key={s} symbol={s} />
        ))}
      </Section>

      <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
        ⚠️ 스왑고의 AI 분석은 참고 정보예요. 실제 투자 결정은 본인의 판단과 책임 하에 이루어져야
        합니다. 과거 데이터 기반 예측이므로 미래 가격을 보장하지 않습니다.
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-3 text-sm font-semibold">{title}</div>
      <div className="divide-y divide-slate-100">{children}</div>
    </div>
  );
}

function Empty({ msg }: { msg: string }) {
  return <div className="px-2 py-6 text-center text-sm text-slate-400">{msg}</div>;
}

function SignalRow({ symbol, signal }: { symbol: string; signal?: AiSignal }) {
  const side = signal?.side;
  return (
    <div className="flex items-center justify-between gap-3 py-3">
      <div className="flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-700">
          {symbol[0]}
        </span>
        <div>
          <div className="text-sm font-semibold">{symbol}</div>
          <div className="text-[11px] text-slate-400">
            {signal ? `${new Date(signal.created_at).toLocaleString("ko-KR")} · ${signal.source ?? "system"}` : "신호 없음"}
          </div>
        </div>
      </div>
      <div className="flex flex-1 flex-col items-end gap-1">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-semibold",
              !side && "bg-slate-100 text-slate-500",
              side === "buy" && "bg-emerald-100 text-emerald-700",
              side === "sell" && "bg-red-100 text-red-700",
              side === "hold" && "bg-amber-100 text-amber-700"
            )}
          >
            {side ? side.toUpperCase() : "—"}
          </span>
          {signal && (
            <span className="text-xs tabular-nums text-slate-500">
              신뢰도 {(signal.confidence * 100).toFixed(0)}%
            </span>
          )}
        </div>
        <div className="h-1 w-48 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full bg-blue-500"
            style={{ width: `${signal ? signal.confidence * 100 : 0}%` }}
          />
        </div>
        {signal?.reason && (
          <div className="text-right text-[11px] text-slate-500">{signal.reason}</div>
        )}
      </div>
    </div>
  );
}

function PredictionRow({ symbol }: { symbol: string }) {
  const { data } = useQuery({
    queryKey: ["ai-pred", symbol],
    queryFn: () => api<AiPrediction[]>(`/ai/predictions?symbol=${symbol}&limit=10`),
  });
  const by = (h: AiPrediction["horizon"]) => data?.find((x) => x.horizon === h);
  return (
    <div className="grid grid-cols-2 gap-2 py-3 sm:grid-cols-4">
      <div>
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-[10px] font-bold text-blue-700">
            {symbol[0]}
          </span>
          <span className="text-sm font-semibold">{symbol}</span>
        </div>
      </div>
      <PredCell label="1시간 후" pred={by("1h")} />
      <PredCell label="24시간 후" pred={by("24h")} />
      <PredCell label="7일 후" pred={by("7d")} />
    </div>
  );
}

function PredCell({ label, pred }: { label: string; pred?: AiPrediction }) {
  return (
    <div>
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="text-sm font-semibold tabular-nums">{pred?.predicted_price ?? "—"}</div>
      {pred && (
        <div className="text-[11px] text-slate-400">
          신뢰도 {(pred.confidence * 100).toFixed(0)}%
        </div>
      )}
    </div>
  );
}

function SentimentRow({ symbol }: { symbol: string }) {
  const { data } = useQuery<AiSentiment>({
    queryKey: ["ai-sentiment", symbol],
    queryFn: () => api<AiSentiment>(`/ai/sentiment?symbol=${symbol}`),
  });
  const score = data?.sentiment_score ?? null;
  const norm = score == null ? 50 : ((score + 100) / 200) * 100;
  return (
    <div className="py-3">
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="font-semibold">{symbol}</span>
        <span className="text-slate-500">
          {score == null ? "—" : score > 30 ? "강세" : score < -30 ? "약세" : "중립"}{" "}
          {score != null && `(${score})`}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-gradient-to-r from-red-200 via-amber-200 to-emerald-200">
        <div
          className="h-full bg-slate-700/30"
          style={{ width: `${100 - norm}%`, marginLeft: `${norm}%`, transform: "translateX(-100%)" }}
        />
      </div>
      {data && (
        <div className="mt-1 flex flex-wrap gap-3 text-[11px] text-slate-500">
          {data.rsi != null && <span>RSI {data.rsi.toFixed(1)}</span>}
          {data.macd != null && <span>MACD {data.macd.toFixed(2)}</span>}
          {data.ma7 && <span>MA7 {data.ma7}</span>}
          {data.ma25 && <span>MA25 {data.ma25}</span>}
        </div>
      )}
    </div>
  );
}
