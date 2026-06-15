import hashlib
import json
from typing import Any

GENESIS_PREV_HASH = "00" * 32


def canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_hex(*chunks: bytes) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c)
    return h.hexdigest()


def compute_tx_hash(prev_hash: str, meta: dict, payload: dict) -> str:
    return sha256_hex(
        prev_hash.encode("ascii"),
        b"|",
        canonical_json(meta),
        b"|",
        canonical_json(payload),
    )


def merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return GENESIS_PREV_HASH
    layer = [bytes.fromhex(h) for h in leaves]
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layer = [hashlib.sha256(layer[i] + layer[i + 1]).digest() for i in range(0, len(layer), 2)]
    return layer[0].hex()
