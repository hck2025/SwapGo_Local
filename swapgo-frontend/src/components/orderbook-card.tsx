"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query"; // ★ useQueryClient 추가
import { useEffect } from "react"; // ★ useEffect 추가
import { api, type Orderbook } from "@/lib/api";
import { InfoTooltip } from "@/components/info-tooltip";

export function OrderbookCard({ poolId, quoteSymbol }: { poolId: number; quoteSymbol: string }) {
    const qc = useQueryClient(); // ★ 추가

    const { data } = useQuery({
        queryKey: ["orderbook", poolId],
        queryFn: () =>
            api<Orderbook>(`/market/orderbook?pool_id=${poolId}&levels=4&step_pct=0.001`),
        refetchInterval: 3000,
    });

    // ★ 웹소켓 실시간 리스너 추가
    useEffect(() => {
        const ws = new WebSocket("ws://localhost:8000/ws");

        ws.onopen = () => {
            ws.send(JSON.stringify({
                op: "subscribe",
                channels: [`pool:${poolId}`] // 풀 상태(가격 변동) 채널 구독
            }));
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.channel === `pool:${poolId}`) {
                    // 매매가 발생하여 풀 정보가 바뀌면 호가창 데이터 즉시 강제 리프레시
                    qc.invalidateQueries({ queryKey: ["orderbook", poolId] });
                }
            } catch (err) {
                console.error("WS 파싱 에러:", err);
            }
        };

        return () => {
            ws.close();
        };
    }, [poolId, qc]);

    const asks = (data?.asks ?? []).slice().reverse();
    const bids = data?.bids ?? [];
    const mid = data?.mid ?? "0";

    const maxCum = Math.max(
        ...[...(data?.asks ?? []), ...(data?.bids ?? [])].map((l) => parseFloat(l.cum_size) || 0),
        1
    );

    return (
        <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="mb-2 flex items-center justify-between">
                <div className="text-sm font-semibold">
                    <InfoTooltip termKey="amm">
                        <span>호가창</span>
                    </InfoTooltip>
                </div>
            </div>
            <div className="grid grid-cols-[1fr_1fr] text-[11px] text-slate-400">
                <div>가격({quoteSymbol})</div>
                <div className="text-right">수량</div>
            </div>
            <div className="mt-1 space-y-0.5">
                {asks.map((l, i) => (
                    <Row key={`a${i}`} side="ask" l={l} maxCum={maxCum} />
                ))}
            </div>
            <div className="my-2 rounded bg-blue-50 py-1 text-center text-sm font-bold text-blue-700 tabular-nums">
                {fmtPrice(mid)} {quoteSymbol}
            </div>
            <div className="space-y-0.5">
                {bids.map((l, i) => (
                    <Row key={`b${i}`} side="bid" l={l} maxCum={maxCum} />
                ))}
            </div>
        </div>
    );
}

// ... 하단 Row 및 포맷팅 함수는 기존과 동일함 ...
function Row({
    side,
    l,
    maxCum,
}: {
    side: "ask" | "bid";
    l: { price: string; size: string; cum_size: string };
    maxCum: number;
}) {
    const cum = parseFloat(l.cum_size) || 0;
    const w = Math.min(100, (cum / maxCum) * 100);
    return (
        <div className="relative grid grid-cols-[1fr_1fr] py-0.5 text-[11px] tabular-nums">
            <div
                className={
                    side === "ask"
                        ? "absolute inset-y-0 right-0 bg-red-50"
                        : "absolute inset-y-0 right-0 bg-emerald-50"
                }
                style={{ width: `${w}%` }}
            />
            <div className={`relative ${side === "ask" ? "text-red-600" : "text-emerald-600"}`}>
                {fmtPrice(l.price)}
            </div>
            <div className="relative text-right">{fmtSize(l.size)}</div>
        </div>
    );
}

function fmtPrice(s: string) {
    const n = parseFloat(s);
    if (!isFinite(n) || n === 0) return "-";
    return n.toLocaleString("en-US", { maximumFractionDigits: 2 });
}
function fmtSize(s: string) {
    const n = parseFloat(s);
    if (!isFinite(n)) return "-";
    if (n > 1) return n.toLocaleString("en-US", { maximumFractionDigits: 3 });
    return n.toFixed(6);
}