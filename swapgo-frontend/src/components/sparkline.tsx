"use client";

import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";

export function Sparkline({ values, isUp }: { values: number[]; isUp: boolean }) {
  const data = values.map((v, i) => ({ i, v }));
  if (data.length === 0) return <div className="h-[28px] w-[80px]" />;
  return (
    <div className="h-[28px] w-[80px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <YAxis hide domain={["auto", "auto"]} />
          <Line
            type="monotone"
            dataKey="v"
            stroke={isUp ? "#16a34a" : "#dc2626"}
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
