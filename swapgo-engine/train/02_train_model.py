"""
train/02_train_model.py — GRU 모델 학습

[실행]
  python train/02_train_model.py --horizon trade
  python train/02_train_model.py --horizon scalper
  python train/02_train_model.py --horizon swing
  python train/02_train_model.py --horizon longterm

[모델 I/O]
  입력: (batch, seq_len, 10)  — Volat_eth, BB_Width_eth 추가 (기존 8 → 10)
  출력: (batch, 2)            — [BTC_log_ret, ETH_log_ret]

[ETH 변동폭 개선 포인트]
  ① input_size=10  : ETH 전용 피처(Volat_eth, BB_Width_eth) 추가
  ② 분리 헤드      : fc_btc / fc_eth 독립 레이어 (train_02_helpers.py)
  ③ ETH_WEIGHT=2.0 : ETH 손실 가중치 2배 → ETH 그래디언트 강제 증폭
  ④ DROPOUT=0.3    : 기존 dropout=3 버그 수정 (0~1 범위 필수)
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

# GRUModel 은 03_export_onnx.py 에서도 재사용 — helpers 에서 임포트
from train_02_helpers import GRUModel

# ── CLI ───────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument(
    "--horizon",
    choices=["trade", "scalper", "swing", "longterm"],
    required=True,
)
args = parser.parse_args()

# ── horizon 매핑 ─────────────────────────────────────────────
HORIZON_CFG: dict[str, dict] = {
    "trade":    {"seq_len": 30,  "model_name": "model_trade",    "data_tag": "trade"},
    "scalper":  {"seq_len": 10,  "model_name": "model_scalper",  "data_tag": "scalper"},
    "swing":    {"seq_len": 60,  "model_name": "model_swing",    "data_tag": "swing"},
    "longterm": {"seq_len": 120, "model_name": "model_longterm", "data_tag": "longterm"},
}
cfg      = HORIZON_CFG[args.horizon]
SEQ_LEN  = cfg["seq_len"]
NAME     = cfg["model_name"]
DATA_DIR = Path(f"data/{cfg['data_tag']}")

# ── 하이퍼파라미터 ────────────────────────────────────────────
HIDDEN_SIZE  = 128    # 표현력 확대 (기존 64)
NUM_LAYERS   = 3      # 레이어 수
DROPOUT      = 0.3    # ★ 버그 수정: dropout=3 → 0.3 (PyTorch 는 0~1 필수)
BATCH_SIZE   = 512
EPOCHS       = 100
LR           = 1e-3
PATIENCE     = 10
GRAD_CLIP    = 1.0
TRAIN_RATIO  = 0.7
VAL_RATIO    = 0.15

# ── ETH 손실 가중치 ★ ─────────────────────────────────────────
# BTC 손실이 ETH 헤드를 압도하는 것을 방지합니다.
# loss = L_btc * 1.0  +  L_eth * ETH_WEIGHT
ETH_WEIGHT = 2.0

# y_scale 파일이 있으면 BTC/ETH 타깃 분산 비율을 참고해 가중치를 보정합니다.
_scale_path = f"models/y_scale_{NAME}.json"
if Path(_scale_path).exists():
    with open(_scale_path) as _f:
        _ys = json.load(_f)
    _ratio = _ys["btc_std"] / max(_ys["eth_std"], 1e-8)
    # ETH std 가 BTC 보다 작을수록 ETH 가중치를 올림 (최소 ETH_WEIGHT 보장)
    ETH_WEIGHT = max(ETH_WEIGHT, _ratio)
    print(
        f"[y_scale] btc_std={_ys['btc_std']:.5f}  eth_std={_ys['eth_std']:.5f}"
        f"  → ETH_WEIGHT={ETH_WEIGHT:.2f} (자동 보정)"
    )
else:
    print(f"[y_scale] 파일 없음 → ETH_WEIGHT={ETH_WEIGHT} (기본값)")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"\n[{NAME}] device={DEVICE}  seq_len={SEQ_LEN}  ETH_WEIGHT={ETH_WEIGHT:.2f}")


# ════════════════════════════════════════════════════════════
# Step 1. 데이터 로드 및 시퀀스 윈도우 생성
# ════════════════════════════════════════════════════════════

print("[1/4] 데이터 로드 중...")
X_all = np.load(DATA_DIR / "features_scaled.npy")  # (T, 10)
y_btc = np.load(DATA_DIR / "targets_btc.npy")      # (T,)
y_eth = np.load(DATA_DIR / "targets_eth.npy")      # (T,)

T, n_feat = X_all.shape
assert T > SEQ_LEN, f"데이터({T}) < seq_len({SEQ_LEN})"
assert n_feat == 10, (
    f"피처 수={n_feat} ≠ 10\n"
    "  01_build_dataset.py 를 재실행하여 10피처 데이터셋을 다시 생성하세요."
)


def make_sequences(
    X: np.ndarray,
    y_b: np.ndarray,
    y_e: np.ndarray,
    seq_len: int,
) -> tuple[np.ndarray, np.ndarray]:
    """슬라이딩 윈도우 → (N, seq_len, 10) 입력 + (N, 2) 타깃"""
    N  = len(X) - seq_len
    Xs = np.zeros((N, seq_len, n_feat), dtype=np.float32)
    ys = np.zeros((N, 2),               dtype=np.float32)
    for i in range(N):
        Xs[i]    = X[i : i + seq_len]
        ys[i, 0] = y_b[i + seq_len - 1]
        ys[i, 1] = y_e[i + seq_len - 1]
    return Xs, ys


X_seq, y_seq = make_sequences(X_all, y_btc, y_eth, SEQ_LEN)
print(f"  시퀀스 — X: {X_seq.shape}  y: {y_seq.shape}")

n  = len(X_seq)
t1 = int(n * TRAIN_RATIO)
t2 = int(n * (TRAIN_RATIO + VAL_RATIO))

X_train, y_train = X_seq[:t1],   y_seq[:t1]
X_val,   y_val   = X_seq[t1:t2], y_seq[t1:t2]
X_test,  y_test  = X_seq[t2:],   y_seq[t2:]
print(f"  train={len(X_train):,}  val={len(X_val):,}  test={len(X_test):,}")


def to_loader(X: np.ndarray, y: np.ndarray, shuffle: bool = False) -> DataLoader:
    ds = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
    return DataLoader(
        ds, batch_size=BATCH_SIZE, shuffle=shuffle, pin_memory=(DEVICE == "cuda")
    )


train_loader = to_loader(X_train, y_train, shuffle=True)
val_loader   = to_loader(X_val,   y_val)
test_loader  = to_loader(X_test,  y_test)


# ════════════════════════════════════════════════════════════
# Step 2. 모델 초기화
# ════════════════════════════════════════════════════════════

print("[2/4] 모델 초기화...")
model = GRUModel(
    input_size=10,           # ★ 10피처
    hidden_size=HIDDEN_SIZE,
    num_layers=NUM_LAYERS,
    dropout=DROPOUT,         # ★ 0.3 (버그 수정)
).to(DEVICE)

print(f"  파라미터: {sum(p.numel() for p in model.parameters()):,}")
print(f"  구조: GRU({n_feat}→{HIDDEN_SIZE}×{NUM_LAYERS}) + dropout({DROPOUT})"
      f" + fc_btc + fc_eth")

optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer, patience=3, factor=0.5, min_lr=1e-5
)


# ════════════════════════════════════════════════════════════
# Step 3. 학습 루프 — ETH 가중 손실 적용
# ════════════════════════════════════════════════════════════

def run_epoch(loader: DataLoader, train: bool = True) -> tuple[float, float, float]:
    """
    반환: (total_loss, btc_loss, eth_loss)
    손실 = L_btc × 1.0  +  L_eth × ETH_WEIGHT
    """
    model.train(train)
    sum_total = sum_btc = sum_eth = 0.0
    n_samples = 0

    with torch.set_grad_enabled(train):
        for Xb, yb in loader:
            Xb, yb = Xb.to(DEVICE), yb.to(DEVICE)
            pred = model(Xb)                              # (B, 2)

            l_btc  = F.mse_loss(pred[:, 0], yb[:, 0])
            l_eth  = F.mse_loss(pred[:, 1], yb[:, 1])
            loss   = l_btc + ETH_WEIGHT * l_eth           # ★ ETH 가중 손실

            if train:
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
                optimizer.step()

            bs          = len(Xb)
            sum_total  += loss.item()  * bs
            sum_btc    += l_btc.item() * bs
            sum_eth    += l_eth.item() * bs
            n_samples  += bs

    return (
        sum_total / n_samples,
        sum_btc   / n_samples,
        sum_eth   / n_samples,
    )


print("[3/4] 학습 시작...")
best_val   = math.inf
no_improve = 0
Path("models").mkdir(exist_ok=True)
best_path  = f"models/{NAME}_best.pt"

for epoch in range(1, EPOCHS + 1):
    tr_loss, tr_btc, tr_eth = run_epoch(train_loader, train=True)
    va_loss, va_btc, va_eth = run_epoch(val_loader,   train=False)
    scheduler.step(va_loss)

    improved = va_loss < best_val
    if improved:
        best_val   = va_loss
        no_improve = 0
        torch.save(model.state_dict(), best_path)
    else:
        no_improve += 1

    if epoch % 10 == 0 or epoch <= 5 or improved:
        lr_now = optimizer.param_groups[0]["lr"]
        mark   = "✓" if improved else " "
        print(
            f"  [{mark}] epoch {epoch:03d}/{EPOCHS} | "
            f"val={va_loss:.6f}  (btc={va_btc:.6f} eth={va_eth:.6f})  "
            f"lr={lr_now:.2e}"
        )

    if no_improve >= PATIENCE:
        print(f"  Early stopping (epoch {epoch}, patience={PATIENCE})")
        break

model.load_state_dict(torch.load(best_path, map_location=DEVICE))


# ════════════════════════════════════════════════════════════
# Step 4. 테스트 평가 — 방향 정확도 + 예측 분산 비교
# ════════════════════════════════════════════════════════════

test_loss, test_btc, test_eth = run_epoch(test_loader, train=False)
print(f"\n  테스트 손실  total={test_loss:.6f}  btc={test_btc:.6f}  eth={test_eth:.6f}")

model.eval()
preds_list, trues_list = [], []
with torch.no_grad():
    for Xb, yb in test_loader:
        preds_list.append(model(Xb.to(DEVICE)).cpu().numpy())
        trues_list.append(yb.numpy())

all_pred = np.vstack(preds_list)
all_true = np.vstack(trues_list)

# 방향 정확도
dir_btc = np.mean(np.sign(all_pred[:, 0]) == np.sign(all_true[:, 0]))
dir_eth = np.mean(np.sign(all_pred[:, 1]) == np.sign(all_true[:, 1]))

# 예측 분산 (ETH 변동폭 개선 확인 지표)
std_pred_btc = all_pred[:, 0].std()
std_pred_eth = all_pred[:, 1].std()
std_true_btc = all_true[:, 0].std()
std_true_eth = all_true[:, 1].std()

print(f"\n  방향 정확도   BTC: {dir_btc*100:.1f}%   ETH: {dir_eth*100:.1f}%  (랜덤 기준선 50%)")
print(f"\n  예측 표준편차 (클수록 변동폭 큼)")
print(f"    BTC  pred_std={std_pred_btc:.6f}  true_std={std_true_btc:.6f}"
      f"  ratio={std_pred_btc/max(std_true_btc,1e-8):.2%}")
print(f"    ETH  pred_std={std_pred_eth:.6f}  true_std={std_true_eth:.6f}"
      f"  ratio={std_pred_eth/max(std_true_eth,1e-8):.2%}")
print(f"  ETH/BTC 분산 비율 (예측): {std_pred_eth/max(std_pred_btc,1e-8):.3f}"
      f"  (실제): {std_true_eth/max(std_true_btc,1e-8):.3f}")
print()
print(f"✅ 학습 완료: {best_path}")
print("  다음 단계: python train/03_export_onnx.py --horizon " + args.horizon)
