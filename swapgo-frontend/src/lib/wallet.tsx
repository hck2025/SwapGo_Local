"use client";

/**
 * 지갑 컨텍스트.
 * - 임시지갑: 백엔드가 발급한 secp256k1 개인키를 ethers v6 Wallet 으로 로드
 * - 챌린지-서명 로그인: ethers Wallet.signMessage 가 EIP-191 personal_sign 을 만들어 백엔드와 호환
 * - 외부 메타마스크 연결도 지원: window.ethereum 로 personal_sign 후 동일 백엔드 사용
 *
 * 개인키와 토큰은 localStorage 에만 저장. 새로고침 후에도 유지되도록.
 */

import { Wallet, BrowserProvider } from "ethers";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api, type ChallengeResp, type LoginResp, type SignupResp } from "@/lib/api";

const KEY_PRIV = "swapgo.priv";
const KEY_ADDR = "swapgo.address";
const KEY_TOKEN = "swapgo.token";
const KEY_MNEMONIC_ONCE = "swapgo.mnemonic_once";

type WalletKind = "internal" | "external" | null;

type WalletState = {
  address: string | null;
  token: string | null;
  kind: WalletKind;
};

type WalletCtx = WalletState & {
  ready: boolean;
  signupAndLogin: (displayName?: string) => Promise<SignupResp>;
  loginWithStoredKey: () => Promise<void>;
  importPrivateKey: (privHex: string) => Promise<void>;
  connectExternal: () => Promise<void>;
  logout: () => void;
};

const Ctx = createContext<WalletCtx | null>(null);

declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
      isMetaMask?: boolean;
    };
  }
}

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<WalletState>({ address: null, token: null, kind: null });
  const [ready, setReady] = useState(false);

  // 새로고침 시 localStorage 복원
  useEffect(() => {
    const addr = typeof window !== "undefined" ? localStorage.getItem(KEY_ADDR) : null;
    const tok = typeof window !== "undefined" ? localStorage.getItem(KEY_TOKEN) : null;
    const priv = typeof window !== "undefined" ? localStorage.getItem(KEY_PRIV) : null;
    if (addr && tok) {
      setState({
        address: addr,
        token: tok,
        kind: priv ? "internal" : "external",
      });
    }
    setReady(true);
  }, []);

  const persist = useCallback((next: WalletState, priv?: string) => {
    setState(next);
    if (next.address) localStorage.setItem(KEY_ADDR, next.address);
    if (next.token) localStorage.setItem(KEY_TOKEN, next.token);
    if (priv) localStorage.setItem(KEY_PRIV, priv);
  }, []);

  const challengeAndLogin = useCallback(
    async (address: string, signMessage: (msg: string) => Promise<string>) => {
      const ch = await api<ChallengeResp>("/auth/challenge", {
        method: "POST",
        body: { address },
      });
      const sig = await signMessage(ch.message);
      const out = await api<LoginResp>("/auth/login", {
        method: "POST",
        body: { address, signature: sig, nonce: ch.nonce },
      });
      return out;
    },
    []
  );

  const signupAndLogin = useCallback(
    async (displayName?: string): Promise<SignupResp> => {
      const signup = await api<SignupResp>("/auth/signup", {
        method: "POST",
        body: { display_name: displayName },
      });
      // 개인키로 챌린지 서명
      const wallet = new Wallet(signup.private_key_ONCE);
      const login = await challengeAndLogin(signup.address, async (msg) =>
        wallet.signMessage(msg)
      );
      // 1회 표시 후 사용자 확인했다고 가정하고 localStorage 보관
      // (실 DEX와 다르지만 모의투자라서 새로고침 편의 우선)
      localStorage.setItem(KEY_MNEMONIC_ONCE, signup.mnemonic_ONCE);
      persist(
        { address: signup.address, token: login.access_token, kind: "internal" },
        signup.private_key_ONCE
      );
      return signup;
    },
    [challengeAndLogin, persist]
  );

  const loginWithStoredKey = useCallback(async () => {
    const priv = localStorage.getItem(KEY_PRIV);
    if (!priv) throw new Error("저장된 개인키가 없어요.");
    const wallet = new Wallet(priv);
    const login = await challengeAndLogin(wallet.address, async (msg) =>
      wallet.signMessage(msg)
    );
    persist({ address: wallet.address, token: login.access_token, kind: "internal" });
  }, [challengeAndLogin, persist]);

  const importPrivateKey = useCallback(
    async (privHex: string) => {
      const wallet = new Wallet(privHex);
      const login = await challengeAndLogin(wallet.address, async (msg) =>
        wallet.signMessage(msg)
      );
      persist(
        { address: wallet.address, token: login.access_token, kind: "internal" },
        privHex
      );
    },
    [challengeAndLogin, persist]
  );

  const connectExternal = useCallback(async () => {
    if (typeof window === "undefined" || !window.ethereum) {
      throw new Error("이 브라우저에는 MetaMask 같은 지갑이 설치되어 있지 않아요.");
    }
    const provider = new BrowserProvider(window.ethereum);
    const accounts = (await window.ethereum.request({ method: "eth_requestAccounts" })) as string[];
    const address = accounts[0];
    if (!address) throw new Error("지갑 주소를 가져오지 못했어요.");
    // 외부 지갑 주소도 백엔드에 등록되어야 챌린지 발급이 가능. 미가입이면 회원가입 시도.
    try {
      const signer = await provider.getSigner(address);
      const login = await challengeAndLogin(address, async (msg) => signer.signMessage(msg));
      persist({ address, token: login.access_token, kind: "external" });
    } catch (e) {
      // 신규 외부 지갑은 백엔드가 모르므로 실패. 임시지갑 생성을 권장.
      throw e;
    }
  }, [challengeAndLogin, persist]);

  const logout = useCallback(() => {
    setState({ address: null, token: null, kind: null });
    localStorage.removeItem(KEY_ADDR);
    localStorage.removeItem(KEY_TOKEN);
    localStorage.removeItem(KEY_PRIV);
    localStorage.removeItem(KEY_MNEMONIC_ONCE);
  }, []);

  const value = useMemo<WalletCtx>(
    () => ({
      ...state,
      ready,
      signupAndLogin,
      loginWithStoredKey,
      importPrivateKey,
      connectExternal,
      logout,
    }),
    [state, ready, signupAndLogin, loginWithStoredKey, importPrivateKey, connectExternal, logout]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useWallet() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("WalletProvider 안에서만 사용할 수 있어요.");
  return ctx;
}
