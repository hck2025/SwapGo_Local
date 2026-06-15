/**
 * 백엔드 API 클라이언트.
 * 모든 응답은 {ok, data, error, server_time} 봉투. error.code/message/suggestion/glossary_keys 를
 * 그대로 활용해 친절한 에러 모달/토스트를 만들 수 있다.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type ApiError = {
  code: string;
  message: string;
  suggestion?: string;
  glossary_keys?: string[];
  details?: Record<string, unknown>;
};

export class ApiException extends Error {
  status: number;
  error: ApiError;
  constructor(status: number, error: ApiError) {
    super(error.message);
    this.status = status;
    this.error = error;
  }
}

type Envelope<T> = {
  ok: boolean;
  data: T | null;
  error: ApiError | null;
  server_time: string;
};

function authHeader(token?: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function api<T>(
  path: string,
  opts: {
    method?: "GET" | "POST" | "PATCH" | "DELETE";
    body?: unknown;
    token?: string | null;
    headers?: Record<string, string>;
    signal?: AbortSignal;
  } = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: opts.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...authHeader(opts.token),
      ...(opts.headers || {}),
    },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
    cache: "no-store",
  });

  let payload: Envelope<T> | null = null;
  try {
    payload = (await res.json()) as Envelope<T>;
  } catch {
    throw new ApiException(res.status, {
      code: "BAD_RESPONSE",
      message: "서버 응답을 읽지 못했어요.",
    });
  }

  if (!res.ok || !payload.ok) {
    throw new ApiException(
      res.status,
      payload.error || {
        code: "UNKNOWN",
        message: "알 수 없는 오류가 발생했어요.",
      }
    );
  }
  return payload.data as T;
}

// ---------- 도메인 타입 ----------

export type SignupResp = {
  address: string;
  public_key_hex: string;
  private_key_ONCE: string;
  mnemonic_ONCE: string;
  warning: string;
};

export type ChallengeResp = {
  nonce: string;
  message: string;
  expires_at: string;
};

export type LoginResp = {
  access_token: string;
  token_type: string;
  expires_in: number;
  address: string;
};

export type Pool = {
  id: number;
  base_symbol: string;
  quote_symbol: string;
  reserve_base: string;
  reserve_quote: string;
  reserve_base_human: string;
  reserve_quote_human: string;
  price: string;
  raw_price: string;
  fee_bps: number;
  is_active: boolean;
  revision: number;
  tvl_quote_human: string;
};

export type SlippageLevel = "safe" | "warning" | "danger";

export type SwapQuote = {
  pool_id: number;
  side: "base_to_quote" | "quote_to_base";
  amount_in: string;
  amount_in_human: string;
  amount_out: string;
  amount_out_human: string;
  amount_out_min: string;
  fee_amount: string;
  fee_bps: number;
  execution_price: string;
  mid_price_before: string;
  mid_price_after: string;
  price_impact_bps: number;
  slippage_bps: number;
  slippage_level: SlippageLevel;
  slippage_threshold_used_bps: number;
  pool_after: { reserve_base: string; reserve_quote: string; price: string; revision: number };
  friendly_message: string;
  glossary_keys: string[];
  quote_id: string;
  expires_at: string;
};

export type SwapResult = {
  tx_id: number;
  tx_hash: string;
  quote: SwapQuote;
  explorer_url: string;
};

export type Balance = {
  symbol: string;
  amount: string;
  amount_human: string;
  decimals: number;
};

export type HoldingItem = {
  symbol: string;
  amount_human: string;
  current_price_human: string;
  value_quote_human: string;
  avg_cost_human: string | null;
  invested_quote_human: string | null;
  pnl_value_human: string | null;
  pnl_pct: number | null;
};

export type Holdings = {
  address: string;
  total_value_quote_human: string;
  total_invested_quote_human: string | null;
  total_pnl_value_human: string | null;
  total_pnl_pct: number | null;
  items: HoldingItem[];
};

export type GlossaryItem = {
  key: string;
  term_ko: string;
  term_en: string | null;
  short_desc: string;
  long_desc: string | null;
  example: string | null;
  related_keys: string[];
  difficulty: number;
};

export type Coin = {
  symbol: string;
  name: string;
  price_human: string;
  change_24h_pct: number;
  volume_24h_human: string;
  sparkline: number[];
  pool_id: number | null;
};

export type Orderbook = {
  pool_id: number;
  mid: string;
  bids: { price: string; size: string; cum_size: string }[];
  asks: { price: string; size: string; cum_size: string }[];
  revision: number;
};

export type Candle = {
  bucket_start: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume_base: string;
  volume_quote: string;
  trades_count: number;
};

export type Trade = {
  tx_id: number;
  side: string;
  amount_in: string;
  amount_out: string;
  amount_in_human: string;
  amount_out_human: string;
  amount_base_human: string;
  base_symbol: string;
  price: string;
  slippage_level: SlippageLevel | null;
  created_at: string;
};

export type AiSignal = {
  id: number;
  symbol: string;
  side: "buy" | "sell" | "hold";
  confidence: number;
  reason: string | null;
  source: string | null;
  created_at: string;
  expires_at: string | null;
};

export type AiPrediction = {
  id: number;
  symbol: string;
  horizon: "1h" | "24h" | "7d";
  predicted_price: string;
  lower_bound: string | null;
  upper_bound: string | null;
  confidence: number;
  model_tag: string | null;
  created_at: string;
};

export type AiSentiment = {
  id: number;
  symbol: string;
  sentiment_score: number;
  rsi: number | null;
  macd: number | null;
  ma7: string | null;
  ma25: string | null;
  created_at: string;
} | null;

export type GlobalMarket = {
  total_market_cap_usdt_human: string;
  total_volume_24h_usdt_human: string;
  btc_dominance_pct: number;
  eth_dominance_pct: number;
  note: string;
};

export type ExplorerTx = {
  id: number;
  tx_type: string;
  pool_id: number | null;
  actor_wallet_id: number | null;
  actor_address: string | null;
  amount_in: string | null;
  amount_out: string | null;
  fee_amount: string | null;
  slippage_bps: number | null;
  price_after: string | null;
  prev_hash: string;
  tx_hash: string;
  payload: Record<string, unknown>;
  created_at: string;
  friendly_message?: string;
};

export type VerifyResp = {
  ok: boolean;
  count: number;
  start_id: number;
  end_id: number | null;
  first_invalid_id: number | null;
  recomputed_root: string | null;
  friendly_message?: string;
};

export type StatsResp = {
  trade_count: number;
  total_fees_paid_quote_human: string;
  total_volume_quote_human: string;
  win_rate_pct: number | null;
  note: string;
};

export type TxRow = ExplorerTx;
