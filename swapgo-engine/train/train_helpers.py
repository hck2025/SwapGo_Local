"""
train/train_02_helpers.py — GRUModel 공유 클래스

변경 사항:
  - input_size 기본값 8 → 10 (ETH 피처 2개 추가: Volat_eth, BB_Width_eth)
  - fc 단일 헤드 → fc_btc / fc_eth 분리
    BTC 그래디언트가 ETH 헤드를 압도하는 문제를 해결합니다.
  - dropout 기본값 0.2 유지 (호출부에서 0.3 주입)
"""

import torch
import torch.nn as nn


class GRUModel(nn.Module):
    """
    ai_engine.py 의 ONNX 스펙과 일치:
      입력  : (batch, seq_len, 10)   ← 8 → 10 (Volat_eth, BB_Width_eth 추가)
      출력  : (batch, 2)             — [BTC_log_ret, ETH_log_ret]

    BTC / ETH 출력 헤드를 분리하여 각 출력이 독립적인 그래디언트를
    받을 수 있도록 합니다. ETH 예측 변동폭 개선의 핵심입니다.
    """

    def __init__(
        self,
        input_size: int = 10,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)

        # 분리된 출력 헤드 — BTC / ETH 각각 독립 fc 레이어
        self.fc_btc = nn.Linear(hidden_size, 1)
        self.fc_eth = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _  = self.gru(x)           # (batch, seq_len, hidden)
        last    = self.dropout(out[:, -1, :])   # (batch, hidden)
        btc_out = self.fc_btc(last)     # (batch, 1)
        eth_out = self.fc_eth(last)     # (batch, 1)
        return torch.cat([btc_out, eth_out], dim=1)  # (batch, 2)
