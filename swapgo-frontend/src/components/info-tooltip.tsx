"use client";

/**
 * 용어 툴팁: 마우스 호버 시 백엔드 /glossary/{key} 호출 → 말풍선으로 한국어 설명.
 * 처음 보는 단어 위에 마우스를 가져가면 설명이 나오는 학습 장치.
 */

import { useEffect, useRef, useState } from "react";
import { HelpCircle } from "lucide-react";
import { api, type GlossaryItem } from "@/lib/api";
import { cn } from "@/lib/cn";

const cache = new Map<string, GlossaryItem>();

export function InfoTooltip({
  termKey,
  children,
  className,
}: {
  termKey: string;
  children?: React.ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<GlossaryItem | null>(cache.get(termKey) ?? null);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open || data) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const item = await api<GlossaryItem>(`/glossary/${encodeURIComponent(termKey)}`);
        if (!cancelled) {
          cache.set(termKey, item);
          setData(item);
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, data, termKey]);

  return (
    <span
      ref={ref}
      className={cn("relative inline-flex items-center gap-1", className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      tabIndex={0}
    >
      {children ?? <span className="underline decoration-dotted">{termKey}</span>}
      <HelpCircle size={12} className="text-slate-400" />
      {open && (
        <span className="pointer-events-none absolute left-0 top-full z-40 mt-1 w-64 rounded-md border border-slate-200 bg-white p-3 text-left text-xs shadow-xl">
          {loading || !data ? (
            <span className="text-slate-500">불러오는 중…</span>
          ) : (
            <>
              <span className="block text-sm font-semibold text-slate-900">
                {data.term_ko}
                {data.term_en && (
                  <span className="ml-1 text-[10px] text-slate-400">{data.term_en}</span>
                )}
              </span>
              <span className="mt-1 block text-slate-700">{data.short_desc}</span>
              {data.example && (
                <span className="mt-1 block text-slate-500">예) {data.example}</span>
              )}
            </>
          )}
        </span>
      )}
    </span>
  );
}
