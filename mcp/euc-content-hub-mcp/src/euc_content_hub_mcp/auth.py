"""
Authentication for the EUC Content Hub MCP server.

The ``/search-analytics/gaps`` endpoint (behind ``list_content_gaps``) requires a
Cognito-issued JWT in the ``Authorization`` header; the other tools hit public
endpoints. This module resolves a usable bearer token from, in priority order:

    1. ``CONTENT_HUB_TOKEN`` env var — a JWT pasted in by the user. Simplest;
       works with zero backend changes. Tokens expire (~1h), so this is best for
       quick/manual use and testing.

    2. A cached token from a prior interactive login, refreshed via the Cognito
       token endpoint when expired (see ``login()``).

    3. An on-demand loopback **PKCE** login: opens the Cognito Hosted UI in the
       browser, captures the authorization code on ``http://localhost:<port>/callback``,
       and exchanges it for tokens. The default port (3000) is already registered on
       the Cognito app client, so this works with no backend change; a non-default
       port must have its callback URL registered too (see the README).

Only the Python standard library is used. Token validation is intentionally not
performed here; we only check expiry to decide whether to refresh. The backend
validates ``exp``/``aud``/``token_use``.
"""

import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

# Cognito configuration for the EUC Content Hub user pool (public client values;
# see cognito_config.json in the repo root). Overridable via env for staging.
COGNITO_DOMAIN = os.environ.get(
    'CONTENT_HUB_COGNITO_DOMAIN',
    'euc-content-hub.auth.us-east-1.amazoncognito.com',
)
COGNITO_CLIENT_ID = os.environ.get(
    'CONTENT_HUB_COGNITO_CLIENT_ID',
    '3pv5jf235vj14gu148b9vjt3od',
)
COGNITO_SCOPES = os.environ.get('CONTENT_HUB_COGNITO_SCOPES', 'email openid profile')

# Optional identity-provider hint. When set, the Hosted UI skips its chooser and
# goes straight to that provider (e.g. the Amazon Federate employee-SSO provider,
# whatever it's named on the app client). Leave empty to show all login options
# (Google, Amazon, …). Override with CONTENT_HUB_IDENTITY_PROVIDER.
IDENTITY_PROVIDER = os.environ.get('CONTENT_HUB_IDENTITY_PROVIDER', '').strip()

# Loopback redirect. The port must be registered on the app client as
# http://localhost:<port>/callback. Port 3000 is already registered on the EUC
# Content Hub app client, so the default works with no backend change.
LOOPBACK_PORT = int(os.environ.get('CONTENT_HUB_LOOPBACK_PORT', '3000'))
REDIRECT_URI = f'http://localhost:{LOOPBACK_PORT}/callback'

TOKEN_CACHE_PATH = Path(
    os.environ.get(
        'CONTENT_HUB_TOKEN_CACHE',
        str(Path.home() / '.euc-content-hub' / 'token.json'),
    )
)

# Refresh a little before actual expiry to avoid edge-of-expiry 401s.
_EXPIRY_SKEW_SECONDS = 60


class AuthError(Exception):
    """Raised when no usable token can be obtained."""


# --------------------------------------------------------------------------- #
# Token cache helpers
# --------------------------------------------------------------------------- #

def _load_cache():
    try:
        return json.loads(TOKEN_CACHE_PATH.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError, OSError):
        return {}


def _save_cache(data):
    try:
        TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE_PATH.write_text(json.dumps(data), encoding='utf-8')
        # Best-effort tighten permissions (no-op on platforms without chmod).
        try:
            os.chmod(TOKEN_CACHE_PATH, 0o600)
        except OSError:
            pass
    except OSError:
        pass  # caching is best-effort; failure just means we re-login next time


def _jwt_exp(token):
    """Return the ``exp`` claim of a JWT, or 0 if it can't be parsed."""
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return int(claims.get('exp', 0))
    except (ValueError, IndexError, TypeError):
        return 0


def _is_expired(token):
    return _jwt_exp(token) <= time.time() + _EXPIRY_SKEW_SECONDS


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

def get_token(interactive=None):
    """Return a usable bearer token (no ``Bearer `` prefix), or raise AuthError.

    Resolution order: ``CONTENT_HUB_TOKEN`` env var, then a cached/refreshed
    token, then (if allowed) an interactive PKCE login.

    Args:
        interactive: If True, fall back to a browser login when no token is
            cached. If False, never open a browser. If None (default), infer
            from the ``CONTENT_HUB_NONINTERACTIVE`` env var (defaults to
            interactive).
    """
    env_token = os.environ.get('CONTENT_HUB_TOKEN', '').strip()
    if env_token:
        return env_token[7:].strip() if env_token.startswith('Bearer ') else env_token

    cache = _load_cache()
    access = cache.get('access_token')
    if access and not _is_expired(access):
        return access

    # Try a refresh if we have a refresh token.
    refresh = cache.get('refresh_token')
    if refresh:
        refreshed = _refresh(refresh)
        if refreshed:
            return refreshed['access_token']

    if interactive is None:
        interactive = os.environ.get('CONTENT_HUB_NONINTERACTIVE', '').lower() not in ('1', 'true', 'yes')
    if not interactive:
        raise AuthError(
            'No valid Content Hub token. Set CONTENT_HUB_TOKEN to a Cognito JWT, '
            'or run an interactive login.'
        )

    tokens = login()
    return tokens['access_token']


# --------------------------------------------------------------------------- #
# PKCE loopback login
# --------------------------------------------------------------------------- #

def _pkce_pair():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b'=').decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b'=').decode()
    return verifier, challenge


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    code = None
    error = None
    error_description = None
    expected_state = None

    def do_GET(self):  # noqa: N802 - http.server API
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != '/callback':
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        _CallbackHandler.error = (params.get('error') or [None])[0]
        _CallbackHandler.error_description = (params.get('error_description') or [None])[0]
        state = (params.get('state') or [None])[0]
        if state != _CallbackHandler.expected_state:
            _CallbackHandler.error = _CallbackHandler.error or 'state_mismatch'
        else:
            _CallbackHandler.code = (params.get('code') or [None])[0]

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        err = _CallbackHandler.error
        if _CallbackHandler.error_description:
            err = f'{err}: {_CallbackHandler.error_description}'
        msg = ('Login complete — you can close this tab and return to your agent.'
               if _CallbackHandler.code else
               f'Login failed: {err}')
        body = f'<html><head><meta charset="utf-8"></head><body><p>{msg}</p></body></html>'
        self.wfile.write(body.encode('utf-8'))

    def log_message(self, *a):  # silence the default stderr logging
        pass


def login(timeout=180):
    """Run the loopback PKCE login flow and return + cache the token set.

    Opens the Cognito Hosted UI in the browser, captures the auth code on the
    loopback redirect, exchanges it for tokens, and persists them. Raises
    AuthError on failure.
    """
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)
    _CallbackHandler.code = None
    _CallbackHandler.error = None
    _CallbackHandler.error_description = None
    _CallbackHandler.expected_state = state

    try:
        server = http.server.HTTPServer(('localhost', LOOPBACK_PORT), _CallbackHandler)
    except OSError as e:
        raise AuthError(f'Could not bind loopback port {LOOPBACK_PORT}: {e}')

    authorize_params = {
        'client_id': COGNITO_CLIENT_ID,
        'response_type': 'code',
        'scope': COGNITO_SCOPES,
        'redirect_uri': REDIRECT_URI,
        'state': state,
        'code_challenge': challenge,
        'code_challenge_method': 'S256',
    }
    # Deep-link straight to a specific IdP (e.g. Amazon employee SSO) when hinted.
    if IDENTITY_PROVIDER:
        authorize_params['identity_provider'] = IDENTITY_PROVIDER
    authorize_url = (
        f'https://{COGNITO_DOMAIN}/oauth2/authorize?'
        + urllib.parse.urlencode(authorize_params)
    )

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        webbrowser.open(authorize_url)
        deadline = time.time() + timeout
        while _CallbackHandler.code is None and _CallbackHandler.error is None:
            if time.time() > deadline:
                raise AuthError('Timed out waiting for browser login.')
            time.sleep(0.2)
    finally:
        server.shutdown()
        server.server_close()

    if _CallbackHandler.error or not _CallbackHandler.code:
        err = _CallbackHandler.error or 'no authorization code'
        if _CallbackHandler.error_description:
            err = f'{err}: {_CallbackHandler.error_description}'
        raise AuthError(f'Login failed: {err}')

    tokens = _exchange_code(_CallbackHandler.code, verifier)
    _persist(tokens)
    return tokens


def _token_endpoint_post(fields):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(
        f'https://{COGNITO_DOMAIN}/oauth2/token',
        data=data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _exchange_code(code, verifier):
    try:
        return _token_endpoint_post({
            'grant_type': 'authorization_code',
            'client_id': COGNITO_CLIENT_ID,
            'code': code,
            'redirect_uri': REDIRECT_URI,
            'code_verifier': verifier,
        })
    except Exception as e:  # noqa: BLE001
        raise AuthError(f'Token exchange failed: {e}')


def _refresh(refresh_token):
    """Exchange a refresh token for a new access token; returns token set or None."""
    try:
        tokens = _token_endpoint_post({
            'grant_type': 'refresh_token',
            'client_id': COGNITO_CLIENT_ID,
            'refresh_token': refresh_token,
        })
    except Exception:  # noqa: BLE001 - refresh is best-effort; fall back to login
        return None
    # Cognito refresh responses omit the refresh_token; keep the existing one.
    tokens.setdefault('refresh_token', refresh_token)
    _persist(tokens)
    return tokens


def _persist(tokens):
    cache = _load_cache()
    # Prefer the access token for API calls; the backend accepts id or access.
    if 'access_token' in tokens:
        cache['access_token'] = tokens['access_token']
    if 'id_token' in tokens:
        cache['id_token'] = tokens['id_token']
    if 'refresh_token' in tokens:
        cache['refresh_token'] = tokens['refresh_token']
    _save_cache(cache)
