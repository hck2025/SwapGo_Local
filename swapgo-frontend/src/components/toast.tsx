"use client";

import { createContext, useCallback, useContext, useState } from "react";
import { cn } from "@/lib/cn";

type ToastKind = "info" | "success" | "warning" | "error";

type ToastItem = {
  id: number;
  kind: ToastKind;
  title: string;
  message?: string;
  suggestion?: string;
  glossary_keys?: string[];
};

type ToastCtx = {
  push: (t: Omit<ToastItem, "id">) => void;
};

const Ctx = createContext<ToastCtx | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const push = useCallback((t: Omit<ToastItem, "id">) => {
    const id = Date.now() + Math.random();
    setItems((arr) => [...arr, { ...t, id }]);
    setTimeout(() => setItems((arr) => arr.filter((x) => x.id !== id)), 6000);
  }, []);

  return (
    <Ctx.Provider value={{ push }}>
      {children}
      <div className="pointer-events-none fixed top-3 right-3 z-50 flex w-[360px] flex-col gap-2">
        {items.map((t) => (
          <div
            key={t.id}
            className={cn(
              "pointer-events-auto rounded-md border bg-white p-3 shadow-md",
              t.kind === "error" && "border-red-300",
              t.kind === "warning" && "border-amber-300",
              t.kind === "success" && "border-emerald-300",
              t.kind === "info" && "border-slate-300"
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm font-semibold">{t.title}</div>
              <button
                className="text-slate-400 hover:text-slate-700"
                onClick={() => setItems((arr) => arr.filter((x) => x.id !== t.id))}
              >
                ×
              </button>
            </div>
            {t.message && <div className="mt-1 text-sm text-slate-700">{t.message}</div>}
            {t.suggestion && (
              <div className="mt-1 text-xs text-slate-500">💡 {t.suggestion}</div>
            )}
            {t.glossary_keys && t.glossary_keys.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1">
                {t.glossary_keys.map((k) => (
                  <a
                    key={k}
                    href={`/explorer?term=${k}`}
                    className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 hover:bg-slate-200"
                  >
                    #{k}
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast() {
  const c = useContext(Ctx);
  if (!c) throw new Error("ToastProvider 안에서 사용해주세요.");
  return c;
}
