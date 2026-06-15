"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useWallet } from "@/lib/wallet";
import { useWalletModal } from "@/components/wallet-modal";
import { cn } from "@/lib/cn";
import {
  BarChart3,
  TrendingUp,
  DollarSign,
  Wallet as WalletIcon,
  PieChart,
  Brain,
  ChevronDown,
} from "lucide-react";
import { useState } from "react";

const NAV = [
  { href: "/", label: "거래", icon: BarChart3 },
  { href: "/market", label: "마켓", icon: TrendingUp },
  { href: "/prices", label: "가격", icon: DollarSign },
  { href: "/holdings", label: "보유자산", icon: PieChart },
  { href: "/portfolio", label: "지갑 관리", icon: WalletIcon },
  { href: "/ai", label: "AI 분석", icon: Brain },
];

const MORE = [
  { href: "/history", label: "거래내역" },
  { href: "/explorer", label: "익스플로러" },
];

export function Topbar() {
  const pathname = usePathname();
  const { address, kind, logout } = useWallet();
  const { open } = useWalletModal();
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-[1200px] items-center justify-between px-4">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-white">
              <BarChart3 size={18} />
            </div>
            <div className="leading-tight">
              <div className="text-base font-bold">스왑고</div>
              <div className="text-[10px] text-blue-600">SwapGo</div>
            </div>
          </Link>
          <nav className="flex items-center gap-1">
            {NAV.map(({ href, label, icon: Icon }) => {
              const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm",
                    active
                      ? "border-b-2 border-blue-600 text-blue-700"
                      : "text-slate-600 hover:bg-slate-50"
                  )}
                >
                  <Icon size={14} /> {label}
                </Link>
              );
            })}
            <div className="relative">
              <button
                onClick={() => setMoreOpen((v) => !v)}
                onBlur={() => setTimeout(() => setMoreOpen(false), 200)}
                className="flex items-center gap-1 rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
              >
                더보기 <ChevronDown size={14} />
              </button>
              {moreOpen && (
                <div className="absolute right-0 top-9 w-40 rounded-md border border-slate-200 bg-white shadow-lg">
                  {MORE.map((m) => (
                    <Link
                      key={m.href}
                      href={m.href}
                      className="block px-3 py-2 text-sm hover:bg-slate-50"
                    >
                      {m.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </nav>
        </div>
        <div className="flex items-center gap-2">
          {address ? (
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-[10px]",
                  kind === "internal" ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-700"
                )}
              >
                {kind === "internal" ? "임시지갑" : "외부지갑"}
              </span>
              <span className="hidden font-mono text-xs text-slate-600 md:inline">
                {address.slice(0, 6)}…{address.slice(-4)}
              </span>
              <button
                onClick={logout}
                className="rounded-md border border-slate-200 px-3 py-1 text-xs text-slate-600 hover:bg-slate-50"
              >
                로그아웃
              </button>
            </div>
          ) : (
            <button
              onClick={open}
              className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-700"
            >
              지갑 연결
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
