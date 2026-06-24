"""Tests for token resolution, expiry handling, and PKCE helpers.

No real network or browser is exercised; the token endpoint and cache are
monkeypatched.
"""

import base64
import hashlib
import json

import pytest

from euc_content_hub_mcp import auth


def _make_jwt(exp):
    """Build a fake JWT with the given exp claim (header/payload/sig)."""
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b'=').decode()
    return f"{b64({'alg': 'none'})}.{b64({'exp': exp})}.sig"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    # Never read a real cache or env token unless a test sets them.
    monkeypatch.setattr(auth, 'TOKEN_CACHE_PATH', tmp_path / 'token.json')
    monkeypatch.delenv('CONTENT_HUB_TOKEN', raising=False)
    monkeypatch.delenv('CONTENT_HUB_NONINTERACTIVE', raising=False)
    yield


def test_env_token_takes_priority(monkeypatch):
    monkeypatch.setenv('CONTENT_HUB_TOKEN', 'env-abc')
    assert auth.get_token() == 'env-abc'


def test_env_token_strips_bearer_prefix(monkeypatch):
    monkeypatch.setenv('CONTENT_HUB_TOKEN', 'Bearer env-xyz')
    assert auth.get_token() == 'env-xyz'


def test_valid_cached_token_used(monkeypatch):
    good = _make_jwt(2_000_000_000)  # far future
    auth._save_cache({'access_token': good})
    assert auth.get_token(interactive=False) == good


def test_expired_cache_no_refresh_noninteractive_raises(monkeypatch):
    expired = _make_jwt(1)  # 1970
    auth._save_cache({'access_token': expired})  # no refresh_token
    with pytest.raises(auth.AuthError):
        auth.get_token(interactive=False)


def test_expired_cache_refreshes(monkeypatch):
    expired = _make_jwt(1)
    fresh = _make_jwt(2_000_000_000)
    auth._save_cache({'access_token': expired, 'refresh_token': 'r1'})

    def fake_post(fields):
        assert fields['grant_type'] == 'refresh_token'
        assert fields['refresh_token'] == 'r1'
        return {'access_token': fresh}

    monkeypatch.setattr(auth, '_token_endpoint_post', fake_post)
    assert auth.get_token(interactive=False) == fresh
    # Refreshed token persisted, refresh_token preserved.
    cache = auth._load_cache()
    assert cache['access_token'] == fresh
    assert cache['refresh_token'] == 'r1'


def test_is_expired():
    assert auth._is_expired(_make_jwt(1)) is True
    assert auth._is_expired(_make_jwt(2_000_000_000)) is False
    assert auth._is_expired('not-a-jwt') is True  # exp=0 -> expired


def test_pkce_pair_is_valid_s256():
    verifier, challenge = auth._pkce_pair()
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b'=').decode()
    assert challenge == expected


def test_login_includes_identity_provider_hint(monkeypatch):
    """When IDENTITY_PROVIDER is set, the authorize URL deep-links to that IdP."""
    captured = {}

    monkeypatch.setattr(auth, 'IDENTITY_PROVIDER', 'AmazonFederate')

    class _FakeServer:
        def __init__(self, *a, **k):
            pass

        def serve_forever(self):
            pass

        def shutdown(self):
            pass

        def server_close(self):
            pass

    monkeypatch.setattr(auth.http.server, 'HTTPServer', _FakeServer)
    monkeypatch.setattr(auth.webbrowser, 'open', lambda url: captured.setdefault('url', url))
    monkeypatch.setattr(auth, '_exchange_code', lambda code, verifier: {'access_token': 'a'})
    monkeypatch.setattr(auth, '_persist', lambda tokens: None)

    # Simulate the browser hitting the callback immediately.
    def fake_sleep(_):
        auth._CallbackHandler.code = 'authcode'

    monkeypatch.setattr(auth.time, 'sleep', fake_sleep)

    auth.login(timeout=5)
    assert 'identity_provider=AmazonFederate' in captured['url']
    assert 'code_challenge_method=S256' in captured['url']
