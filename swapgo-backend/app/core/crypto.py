"""secp256k1 키 생성, EIP-191 서명/검증, EIP-55 주소 도출.

EIP-191 (`personal_sign`)을 채택해 추후 실제 MetaMask 연동 시 그대로 호환된다.
"""

from __future__ import annotations

import secrets

from coincurve import PrivateKey, PublicKey
from eth_utils import keccak, to_checksum_address


def generate_keypair() -> tuple[bytes, bytes, str]:
    """새 secp256k1 키쌍과 EIP-55 주소를 생성한다.

    Returns: (priv_bytes(32), pub_compressed(33), address("0x..."))
    """
    priv_bytes = secrets.token_bytes(32)
    pk = PrivateKey(priv_bytes)
    pub_compressed = pk.public_key.format(compressed=True)
    address = address_from_pubkey(pk.public_key)
    return priv_bytes, pub_compressed, address


def address_from_pubkey(pub: PublicKey) -> str:
    uncompressed = pub.format(compressed=False)  # 0x04 || X(32) || Y(32)
    addr_bytes = keccak(uncompressed[1:])[-20:]
    return to_checksum_address("0x" + addr_bytes.hex())


def address_from_compressed_pubkey(pub_compressed: bytes) -> str:
    return address_from_pubkey(PublicKey(pub_compressed))


def eip191_message_hash(message: str) -> bytes:
    msg_bytes = message.encode("utf-8")
    prefix = f"\x19Ethereum Signed Message:\n{len(msg_bytes)}".encode("utf-8")
    return keccak(prefix + msg_bytes)


def sign_message(priv_bytes: bytes, message: str) -> bytes:
    """클라이언트 측에서 사용할 EIP-191 서명. (테스트/봇 클라이언트용)

    반환: 65바이트 (r||s||v) — v는 27 또는 28
    """
    digest = eip191_message_hash(message)
    pk = PrivateKey(priv_bytes)
    sig_rec = pk.sign_recoverable(digest, hasher=None)  # 65 bytes, last byte = v(0 or 1)
    v = sig_rec[64] + 27
    return sig_rec[:64] + bytes([v])


def recover_address(message: str, signature_hex: str) -> str:
    sig_bytes = _decode_signature(signature_hex)
    if sig_bytes[64] in (27, 28):
        sig_for_lib = sig_bytes[:64] + bytes([sig_bytes[64] - 27])
    else:
        sig_for_lib = sig_bytes
    digest = eip191_message_hash(message)
    pub = PublicKey.from_signature_and_message(sig_for_lib, digest, hasher=None)
    return address_from_pubkey(pub)


def verify_signature(message: str, signature_hex: str, expected_address: str) -> bool:
    try:
        recovered = recover_address(message, signature_hex)
    except Exception:
        return False
    return recovered.lower() == expected_address.lower()


def _decode_signature(signature_hex: str) -> bytes:
    h = signature_hex[2:] if signature_hex.startswith("0x") else signature_hex
    sig = bytes.fromhex(h)
    if len(sig) != 65:
        raise ValueError("signature must be 65 bytes (r||s||v)")
    return sig
