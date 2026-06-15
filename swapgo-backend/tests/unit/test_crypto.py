from app.core.crypto import (
    address_from_compressed_pubkey,
    generate_keypair,
    sign_message,
    verify_signature,
)


def test_keypair_roundtrip():
    priv, pub_compressed, addr = generate_keypair()
    assert len(priv) == 32
    assert len(pub_compressed) == 33
    assert addr.startswith("0x") and len(addr) == 42
    assert address_from_compressed_pubkey(pub_compressed) == addr


def test_signature_valid():
    priv, _, addr = generate_keypair()
    msg = "SwapGo Login: deadbeefcafe at 2026-04-30T00:00:00+00:00"
    sig = sign_message(priv, msg)
    assert verify_signature(msg, "0x" + sig.hex(), addr) is True


def test_signature_wrong_address():
    priv, _, addr_a = generate_keypair()
    _, _, addr_b = generate_keypair()
    msg = "x"
    sig = sign_message(priv, msg)
    assert verify_signature(msg, "0x" + sig.hex(), addr_b) is False
    assert addr_a != addr_b


def test_signature_tampered_message():
    priv, _, addr = generate_keypair()
    sig = sign_message(priv, "original")
    assert verify_signature("tampered", "0x" + sig.hex(), addr) is False
