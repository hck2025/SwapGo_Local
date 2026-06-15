"use client";

import { type SlippageLevel } from "@/lib/api";
import { cn } from "@/lib/cn";

const STYLES: Record<SlippageLevel, string> = {
  safe: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  danger: "bg-red-50 text-red-700 border-red-200",
};

const LABEL: Record<SlippageLevel, string> = {
  safe: "안전",
  warning: "주의",
  danger: "위험",
};

export function SlippagePill({
  level,
  bps,
  className,
}: {
  level: SlippageLevel;
  bps: number;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold tabular-nums",
        STYLES[level],
        className
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          level === "safe" && "bg-emerald-500",
          level === "warning" && "bg-amber-500",
          level === "danger" && "bg-red-500"
        )}
      />
      {LABEL[level]} · 슬리피지 {(bps / 100).toFixed(2)}%
    </span>
  );
}
