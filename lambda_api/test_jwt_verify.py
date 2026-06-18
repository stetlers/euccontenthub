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


# --- Tests: JWKS forced-refresh throttle (DoS hardening) ---
#
# Mirror of _get_jwks/_find_jwk's refresh logic (keep in sync with
# lambda_function.py). The module binds boto3 at import, so we reimplement the
# throttle here and drive it with a fake clock + fetch counter. The property
# under test: a flood of unknown-kid lookups cannot force more than one
# outbound JWKS fetch per throttle window.

_JWKS_TTL_SECONDS = 3600
_JWKS_MIN_FORCED_REFRESH_SECONDS = 60


class _FakeJwks:
    def __init__(self, keys):
        self.keys = list(keys)
        self.fetches = 0
        self.cache = {'keys': None, 'fetched_at': 0, 'last_forced': 0}
        self.now = 1000.0

    def _get(self, force_refresh=False):
        now = self.now
        c = self.cache
        forced = force_refresh and now - c['last_forced'] >= _JWKS_MIN_FORCED_REFRESH_SECONDS
        if forced or c['keys'] is None or now - c['fetched_at'] > _JWKS_TTL_SECONDS:
            if force_refresh:
                c['last_forced'] = now
            self.fetches += 1  # stands in for the urlopen call
            c['keys'] = self.keys
            c['fetched_at'] = now
        return c['keys']

    def find(self, kid):
        for jwk in self._get():
            if jwk.get('kid') == kid:
                return jwk
        for jwk in self._get(force_refresh=True):
            if jwk.get('kid') == kid:
                return jwk
        return None


def test_unknown_kid_flood_is_throttled():
    j = _FakeJwks([{'kid': 'real'}])
    # 500 lookups for a kid that does not exist, all within one window.
    for _ in range(500):
        assert j.find('bogus') is None
    # First lookup primes the cache (1) + one forced refresh (1); every
    # subsequent forced refresh is throttled away.
    assert j.fetches == 2, j.fetches


def test_forced_refresh_allowed_after_window():
    j = _FakeJwks([{'kid': 'real'}])
    assert j.find('bogus') is None
    fetches_after_first = j.fetches
    j.now += _JWKS_MIN_FORCED_REFRESH_SECONDS + 1
    assert j.find('bogus') is None
    # A new window elapsed, so exactly one more forced fetch is permitted.
    assert j.fetches == fetches_after_first + 1, j.fetches


def test_known_kid_after_rotation_still_resolves():
    # Key rotation: 'new' kid is absent, then a forced refresh brings it in.
    j = _FakeJwks([{'kid': 'old'}])
    j.find('old')  # prime cache
    j.keys = [{'kid': 'old'}, {'kid': 'new'}]  # Cognito rotated in a new key
    j.now += _JWKS_MIN_FORCED_REFRESH_SECONDS + 1  # past the throttle window
    assert j.find('new') == {'kid': 'new'}


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
