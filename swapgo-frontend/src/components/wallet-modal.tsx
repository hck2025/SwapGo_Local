"use client";

/**
 * 시안의 지갑 연결 모달 + 임시지갑 발급 흐름.
 *
 * 시안 옵션: MetaMask / WalletConnect / Coinbase Wallet.
 * 추가: "스왑고 임시지갑 새로 만들기" (이 모의 환경의 기본값) + "기존 개인키로 로그인" + "저장된 키로 다시 로그인".
 *
 * 임시지갑은 secp256k1/EIP-191 기반이라 ethers.js 의 personal_sign 으로 그대로 동작 ⇒
 * 추후 실제 web3 연동 시 동일 인증 흐름을 외부 지갑 어댑터(window.ethereum)로 자연스럽게 이전 가능.
 */

import { createContext, useCallback, useContext, useState } from "react";
import { Copy, ShieldCheck, Plus, KeyRound, RefreshCw, X } from "lucide-react";
import { useWallet } from "@/lib/wallet";
import { useToast } from "@/components/toast";
import { ApiException } from "@/lib/api";
import { cn } from "@/lib/cn";

type Ctx = { open: () => void; close: () => void };
const C = createContext<Ctx | null>(null);

export function WalletModalProvider({ children }: { children: React.ReactNode }) {
  const [shown, setShown] = useState(false);
  const open = useCallback(() => setShown(true), []);
  const close = useCallback(() => setShown(false), []);
  return (
    <C.Provider value={{ open, close }}>
      {children}
      {shown && <WalletModal onClose={close} />}
    </C.Provider>
  );
}

export function useWalletModal() {
  const v = useContext(C);
  if (!v) throw new Error("WalletModalProvider 안에서 사용해주세요.");
  return v;
}

type Step = "select" | "creating" | "show-keys" | "import";

function WalletModal({ onClose }: { onClose: () => void }) {
  const wallet = useWallet();
  const toast = useToast();
  const [step, setStep] = useState<Step>("select");
  const [keys, setKeys] = useState<{ priv: string; mnemonic: string; address: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [importValue, setImportValue] = useState("");
  const [agreed, setAgreed] = useState(false);

  const handleCreate = useCallback(async () => {
    setStep("creating");
    setError(null);
    try {
      const out = await wallet.signupAndLogin();
      setKeys({ priv: out.private_key_ONCE, mnemonic: out.mnemonic_ONCE, address: out.address });
      setStep("show-keys");
    } catch (e) {
      setError(e instanceof Error ? e.message : "지갑 생성에 실패했어요.");
      setStep("select");
    }
  }, [wallet]);

  const handleImport = useCallback(async () => {
    setError(null);
    try {
      await wallet.importPrivateKey(importValue.trim());
      toast.push({ kind: "success", title: "지갑 연결 완료", message: "로그인되었어요." });
      onClose();
    } catch (e) {
      const msg = e instanceof ApiException ? e.error.message : (e as Error).message;
      setError(msg || "개인키가 올바르지 않아요.");
    }
  }, [importValue, wallet, toast, onClose]);

  const handleStored = useCallback(async () => {
    setError(null);
    try {
      await wallet.loginWithStoredKey();
      toast.push({ kind: "success", title: "다시 로그인했어요" });
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장된 지갑이 없어요.");
    }
  }, [wallet, toast, onClose]);

  const handleExternal = useCallback(async () => {
    setError(null);
    try {
      await wallet.connectExternal();
      toast.push({ kind: "success", title: "외부 지갑 연결됨" });
      onClose();
    } catch (e) {
      const msg = e instanceof ApiException ? e.error.message : (e as Error).message;
      setError(
        (msg || "") +
          " (외부 지갑은 백엔드에 사전 등록된 주소만 로그인할 수 있어요. 처음이라면 먼저 임시지갑을 만들어주세요.)"
      );
    }
  }, [wallet, toast, onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-[420px] max-w-[95vw] rounded-xl border border-slate-200 bg-white p-5 shadow-2xl">
        <div className="flex items-center justify-between">
          <div className="text-base font-bold">
            {step === "show-keys" ? "지갑이 생성되었어요" : "지갑을 연결하세요"}
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <X size={18} />
          </button>
        </div>

        {step === "select" && (
          <div className="mt-4 space-y-2">
            <p className="text-sm text-slate-500">
              스왑고에서 지갑 연결 없이도 차트는 볼 수 있어요. 거래하려면 연결이 필요해요.
            </p>

            <ProviderRow
              icon={<Plus className="text-emerald-700" />}
              title="스왑고 임시지갑 새로 만들기"
              subtitle="모의투자 권장 · 1회 표시되는 개인키/니모닉을 안전한 곳에 보관하세요"
              onClick={handleCreate}
              accent
            />
            <ProviderRow
              icon={<RefreshCw className="text-slate-700" />}
              title="이 기기에 저장된 임시지갑으로 로그인"
              subtitle="새로고침 후 빠르게 다시 로그인"
              onClick={handleStored}
            />
            <ProviderRow
              icon={<KeyRound className="text-slate-700" />}
              title="개인키로 로그인"
              subtitle="0x 로 시작하는 64자 hex"
              onClick={() => setStep("import")}
            />

            <div className="mt-4 mb-1 text-xs font-semibold uppercase text-slate-400">외부 지갑</div>
            <ProviderRow
              icon={<MetaMaskIcon />}
              title="MetaMask"
              subtitle="브라우저 확장 지갑으로 서명"
              onClick={handleExternal}
            />
            <ProviderRow
              icon={<DotIcon color="#3b99fc" />}
              title="WalletConnect"
              subtitle="QR 코드로 모바일 연결"
              onClick={() =>
                toast.push({
                  kind: "info",
                  title: "준비 중",
                  message: "WalletConnect는 다음 마일스톤에서 지원됩니다.",
                })
              }
            />
            <ProviderRow
              icon={<DotIcon color="#0052ff" />}
              title="Coinbase Wallet"
              subtitle="초보자에게 추천"
              onClick={() =>
                toast.push({
                  kind: "info",
                  title: "준비 중",
                  message: "Coinbase Wallet은 다음 마일스톤에서 지원됩니다.",
                })
              }
            />

            {error && (
              <div className="mt-2 rounded-md border border-red-300 bg-red-50 p-2 text-xs text-red-700">
                {error}
              </div>
            )}
          </div>
        )}

        {step === "creating" && (
          <div className="mt-6 text-center text-sm text-slate-500">지갑 생성 중…</div>
        )}

        {step === "show-keys" && keys && (
          <div className="mt-3 space-y-3">
            <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-800">
              ⚠️ 이 화면을 벗어나면 개인키와 니모닉은 다시 표시되지 않아요. 안전한 곳에 보관하지 않으면
              계정 복구가 불가능합니다 (실제 DEX 동일 경험).
            </div>
            <Field label="주소" value={keys.address} mono />
            <Field label="개인키 (1회 표시)" value={keys.priv} mono secret />
            <Field label="니모닉 (1회 표시)" value={keys.mnemonic} />
            <label className="flex items-start gap-2 text-xs text-slate-600">
              <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                className="mt-1"
              />
              안전한 곳에 보관했고, 분실 시 복구가 불가능함을 이해했어요.
            </label>
            <button
              onClick={onClose}
              disabled={!agreed}
              className={cn(
                "w-full rounded-md py-2 text-sm font-semibold text-white",
                agreed ? "bg-blue-600 hover:bg-blue-700" : "cursor-not-allowed bg-slate-300"
              )}
            >
              계속하기
            </button>
          </div>
        )}

        {step === "import" && (
          <div className="mt-3 space-y-3">
            <div className="text-xs text-slate-500">개인키는 0x 로 시작하는 64자 hex 형식이에요.</div>
            <input
              autoFocus
              value={importValue}
              onChange={(e) => setImportValue(e.target.value)}
              placeholder="0x..."
              className="w-full rounded-md border border-slate-300 p-2 font-mono text-xs"
            />
            {error && <div className="text-xs text-red-600">{error}</div>}
            <div className="flex gap-2">
              <button
                onClick={() => setStep("select")}
                className="flex-1 rounded-md border border-slate-300 py-2 text-sm"
              >
                뒤로
              </button>
              <button
                onClick={handleImport}
                disabled={!importValue.trim()}
                className={cn(
                  "flex-1 rounded-md py-2 text-sm font-semibold text-white",
                  importValue.trim() ? "bg-blue-600 hover:bg-blue-700" : "bg-slate-300"
                )}
              >
                로그인
              </button>
            </div>
          </div>
        )}

        <div className="mt-4 flex items-center gap-1 text-[11px] text-slate-400">
          <ShieldCheck size={12} /> 개인키는 서버에 저장되지 않으며 로그인은 EIP-191 서명으로만 검증돼요.
        </div>
      </div>
    </div>
  );
}

function ProviderRow({
  icon,
  title,
  subtitle,
  onClick,
  accent,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  onClick: () => void;
  accent?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-3 rounded-md border p-3 text-left transition hover:bg-slate-50",
        accent ? "border-emerald-200 bg-emerald-50/50" : "border-slate-200"
      )}
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100">
        {icon}
      </div>
      <div className="flex-1">
        <div className="text-sm font-semibold">{title}</div>
        <div className="text-xs text-slate-500">{subtitle}</div>
      </div>
    </button>
  );
}

function Field({
  label,
  value,
  mono,
  secret,
}: {
  label: string;
  value: string;
  mono?: boolean;
  secret?: boolean;
}) {
  const [reveal, setReveal] = useState(!secret);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px] text-slate-500">
        <span>{label}</span>
        <div className="flex items-center gap-2">
          {secret && (
            <button onClick={() => setReveal((v) => !v)} className="hover:text-slate-700">
              {reveal ? "숨기기" : "보기"}
            </button>
          )}
          <button
            onClick={() => navigator.clipboard.writeText(value)}
            className="flex items-center gap-1 hover:text-slate-700"
          >
            <Copy size={12} /> 복사
          </button>
        </div>
      </div>
      <div
        className={cn(
          "break-all rounded-md border border-slate-200 bg-slate-50 p-2 text-xs",
          mono && "font-mono"
        )}
      >
        {reveal ? value : "•".repeat(Math.min(48, value.length))}
      </div>
    </div>
  );
}

function MetaMaskIcon() {
  return (
    <div className="flex h-5 w-5 items-center justify-center rounded-full bg-orange-500 text-[10px] font-bold text-white">
      M
    </div>
  );
}

function DotIcon({ color }: { color: string }) {
  return <div className="h-3 w-3 rounded-full" style={{ background: color }} />;
}
