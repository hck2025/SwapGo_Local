"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import {
    Area,
    AreaChart,
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { api, type Candle } from "@/lib/api";
import { cn } from "@/lib/cn";

const INTERVALS: { key: string; label: string }[] = [
    { key: "1m", label: "1분" },
    { key: "5m", label: "5분" },
    { key: "1h", label: "1시간" },
    { key: "1d", label: "1일" },
];

export function PriceChart({ poolId, color }: { poolId: number; color?: string }) {
    const [interval, setInterval] = useState("1m");
    const [shape, setShape] = useState<"line" | "area">("area");
    const qc = useQueryClient(); // ★ 실시간 데이터 갱신을 위해 추가

    const { data, isLoading } = useQuery({
        queryKey: ["chart", poolId, interval],
        queryFn: () =>
            api<{ pool_id: number; interval: string; candles: Candle[] }>(
                `/chart/ohlc?pool_id=${poolId}&interval=${interval}`
            ),
        refetchInterval: 5000,
    });

    // ★ 웹소켓 실시간 리스너 추가
    useEffect(() => {
        // 백엔드 주소 기준 웹소켓 URL 생성 (개발환경 localhost:8000 기준)
        const ws = new WebSocket("ws://localhost:8000/ws");

        ws.onopen = () => {
            // pool 채널과 trades 채널 구독 요청
            ws.send(JSON.stringify({
                op: "subscribe",
                channels: [`pool:${poolId}`, `trades:${poolId}`]
            }));
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                // 사용자가 매매해서 풀이 업데이트되거나 새로운 체결 신호가 오면 관련 쿼리 즉시 갱신
                if (msg.channel === `pool:${poolId}` || msg.channel === `trades:${poolId}`) {
                    qc.invalidateQueries({ queryKey: ["chart", poolId] });
                }
            } catch (err) {
                console.error("WS 파싱 에러:", err);
            }
        };

        return () => {
            ws.close();
        };
    }, [poolId, qc]);

    const candles = data?.candles ?? [];
    const series = candles.map((c) => ({
        t: new Date(c.bucket_start).getTime(),
        label: new Date(c.bucket_start).toLocaleTimeString("ko-KR", {
            hour: "2-digit",
            minute: "2-digit",
        }),
        close: parseFloat(c.close),
    }));

    const last = series[series.length - 1]?.close ?? 0;
    const first = series[0]?.close ?? last;
    const isUp = last >= first;
    const change = first > 0 ? ((last - first) / first) * 100 : 0;
    const stroke = color || (isUp ? "#16a34a" : "#dc2626");

    return (
        // ... 하단 UI 부분은 기존과 완벽히 동일하므로 생략합니다 ...
        <div className="rounded-lg border border-slate-200 bg-white p-4">
            {/* 기존 JSX 코드 유지 */}
            <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-1">
                    {INTERVALS.map((i) => (
                        <button
                            key={i.key}
                            onClick={() => setInterval(i.key)}
                            className={cn(
                                "rounded px-2 py-1 text-xs",
                                interval === i.key
                                    ? "bg-blue-600 text-white"
                                    : "text-slate-600 hover:bg-slate-100"
                            )}
                        >
                            {i.label}
                        </button>
                    ))}
                </div>
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => setShape("line")}
                        className={cn(
                            "rounded-full px-3 py-1 text-xs",
                            shape === "line" ? "bg-blue-600 text-white" : "border border-slate-200 text-slate-600"
                        )}
                    >
                        라인
                    </button>
                    <button
                        onClick={() => setShape("area")}
                        className={cn(
                            "rounded-full px-3 py-1 text-xs",
                            shape === "area" ? "bg-blue-600 text-white" : "border border-slate-200 text-slate-600"
                        )}
                    >
                        영역
                    </button>
                </div>
            </div>

            <div>
                <div className="text-3xl font-bold tabular-nums">
                    ${last.toLocaleString("en-US", { maximumFractionDigits: 2 })}
                </div>
                <div className={cn("text-sm tabular-nums", isUp ? "text-emerald-600" : "text-red-600")}>
                    {isUp ? "+" : ""}
                    {(last - first).toLocaleString("en-US", { maximumFractionDigits: 2 })} ({change.toFixed(2)}%)
                </div>
            </div>

            <div className="mt-3 h-[260px]">
                {isLoading || series.length === 0 ? (
                    <div className="flex h-full items-center justify-center text-sm text-slate-400">
                        {isLoading ? "차트 불러오는 중…" : "거래가 시작되면 캔들이 그려져요."}
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height="100%">
                        {shape === "area" ? (
                            <AreaChart data={series}>
                                <defs>
                                    <linearGradient id="fillColor" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor={stroke} stopOpacity={0.3} />
                                        <stop offset="100%" stopColor={stroke} stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid stroke="#f1f5f9" strokeDasharray="3 3" />
                                <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                                <YAxis
                                    domain={["auto", "auto"]}
                                    tick={{ fontSize: 10, fill: "#94a3b8" }}
                                    width={70}
                                />
                                <Tooltip
                                    formatter={(v) => [
                                        `$${Number(v).toLocaleString("en-US", { maximumFractionDigits: 4 })}`,
                                        "가격",
                                    ]}
                                    labelStyle={{ fontSize: 11 }}
                                    contentStyle={{ fontSize: 11 }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="close"
                                    stroke={stroke}
                                    strokeWidth={2}
                                    fill="url(#fillColor)"
                                />
                            </AreaChart>
                        ) : (
                            <LineChart data={series}>
                                <CartesianGrid stroke="#f1f5f9" strokeDasharray="3 3" />
                                <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                                <YAxis
                                    domain={["auto", "auto"]}
                                    tick={{ fontSize: 10, fill: "#94a3b8" }}
                                    width={70}
                                />
                                <Tooltip
                                    formatter={(v) => [
                                        `$${Number(v).toLocaleString("en-US", { maximumFractionDigits: 4 })}`,
                                        "가격",
                                    ]}
                                    labelStyle={{ fontSize: 11 }}
                                    contentStyle={{ fontSize: 11 }}
                                />
                                <Line type="monotone" dataKey="close" stroke={stroke} strokeWidth={2} dot={false} />
                            </LineChart>
                        )}
                    </ResponsiveContainer>
                )}
            </div>
        </div>
    );
}