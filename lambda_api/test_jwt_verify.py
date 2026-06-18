"""
Security tests for the stdlib-only RSA PKCS#1 v1.5 / RS256 JWT signature
verification used by validate_jwt_token (Issue 5).

These test the verification primitive (_rsa_pkcs1_v15_verify) and the JWT
plumbing in isolation, against REAL RSA signatures produced by the
`cryptography` library, so we know the hand-rolled verifier agrees with a
reference implementation and rejects forgeries/tampering.

The verifier is deliberately reimplemented here from the source so the test
needs no AWS env / boto3 import (the Lambda module binds config at import).
If you change _rsa_pkcs1_v15_verify in lambda_function.py, mirror it here.
"""

import base64
import hashlib
import hmac
import json

import pytest

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding


# --- Mirror of the production primitive (keep in sync with lambda_function.py) ---

_SHA256_DIGEST_INFO = bytes.fromhex('3031300d060960864801650304020105000420')


def _b64url_decode(segment):
    return base64.urlsafe_b64decode(segment + '=' * (-len(segment) % 4))


def _b64url_encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _rsa_pkcs1_v15_verify(n, e, message, signature):
    k = (n.bit_length() + 7) // 8
    if len(signature) != k:
        return False
    em = pow(int.from_bytes(signature, 'big'), e, n).to_bytes(k, 'big')
    digest = hashlib.sha256(message).digest()
    der = _SHA256_DIGEST_INFO + digest
    ps_len = k - len(der) - 3
    if ps_len < 8:
        return False
    expected = b'\x00\x01' + b'\xff' * ps_len + b'\x00' + der
    return hmac.compare_digest(em, expected)


# --- Test helpers ---

def _make_key(bits=2048):
    return rsa.generate_private_key(public_exponent=65537, key_size=bits)


def _pub_numbers(key):
    nums = key.public_key().public_numbers()
    return nums.n, nums.e


def _sign(key, message):
    return key.sign(message, padding.PKCS1v15(), hashes.SHA256())


def _make_jwt(key, payload, kid='test-kid', alg='RS256'):
    header = {'alg': alg, 'kid': kid, 'typ': 'JWT'}
    h = _b64url_encode(json.dumps(header, separators=(',', ':')).encode())
    p = _b64url_encode(json.dumps(payload, separators=(',', ':')).encode())
    signing_input = f'{h}.{p}'.encode('ascii')
    sig = _b64url_encode(_sign(key, signing_input))
    return f'{h}.{p}.{sig}', signing_input


# --- Tests: the verification primitive ---

def test_valid_signature_accepts():
    key = _make_key()
    n, e = _pub_numbers(key)
    msg = b'hello.world'
    assert _rsa_pkcs1_v15_verify(n, e, msg, _sign(key, msg)) is True


def test_tampered_message_rejects():
    key = _make_key()
    n, e = _pub_numbers(key)
    sig = _sign(key, b'hello.world')
    assert _rsa_pkcs1_v15_verify(n, e, b'hello.w0rld', sig) is False


def test_wrong_key_rejects():
    signer, attacker = _make_key(), _make_key()
    n, e = _pub_numbers(attacker)
    msg = b'hello.world'
    # signature made by `signer`, verified against `attacker`'s public key
    assert _rsa_pkcs1_v15_verify(n, e, msg, _sign(signer, msg)) is False


def test_bitflipped_signature_rejects():
    key = _make_key()
    n, e = _pub_numbers(key)
    msg = b'hello.world'
    sig = bytearray(_sign(key, msg))
    sig[-1] ^= 0x01
    assert _rsa_pkcs1_v15_verify(n, e, msg, bytes(sig)) is False


def test_wrong_length_signature_rejects():
    key = _make_key()
    n, e = _pub_numbers(key)
    assert _rsa_pkcs1_v15_verify(n, e, b'm', b'\x00' * 10) is False


def test_zero_signature_rejects():
    key = _make_key()
    n, e = _pub_numbers(key)
    k = (n.bit_length() + 7) // 8
    assert _rsa_pkcs1_v15_verify(n, e, b'm', b'\x00' * k) is False


def test_signature_of_one_rejects():
    # s = 1 => em = 1, which is not a valid PKCS#1 padded block.
    key = _make_key()
    n, e = _pub_numbers(key)
    k = (n.bit_length() + 7) // 8
    one = (1).to_bytes(k, 'big')
    assert _rsa_pkcs1_v15_verify(n, e, b'm', one) is False


def test_matches_reference_verifier():
    # Cross-check: cryptography's own verify agrees on a valid signature.
    key = _make_key()
    msg = b'consistency-check'
    sig = _sign(key, msg)
    key.public_key().verify(sig, msg, padding.PKCS1v15(), hashes.SHA256())  # raises if bad
    n, e = _pub_numbers(key)
    assert _rsa_pkcs1_v15_verify(n, e, msg, sig) is True


# --- Tests: JWT-level decisions (signature segment of validate_jwt_token) ---

def test_jwt_valid_token_verifies():
    key = _make_key()
    n, e = _pub_numbers(key)
    token, signing_input = _make_jwt(key, {'sub': 'u1', 'token_use': 'access'})
    h, p, s = token.split('.')
    assert _rsa_pkcs1_v15_verify(n, e, signing_input, _b64url_decode(s)) is True


def test_jwt_payload_swap_rejects():
    # Classic attack: keep header+signature, swap the payload.
    key = _make_key()
    n, e = _pub_numbers(key)
    token, _ = _make_jwt(key, {'sub': 'u1', 'admin': False})
    h, p, s = token.split('.')
    forged_payload = _b64url_encode(json.dumps({'sub': 'u1', 'admin': True}).encode())
    forged_input = f'{h}.{forged_payload}'.encode('ascii')
    assert _rsa_pkcs1_v15_verify(n, e, forged_input, _b64url_decode(s)) is False


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
