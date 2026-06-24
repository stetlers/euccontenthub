"""
EUC Content Hub API client.

The Content Hub crawler accumulates AWS Blog and Builder.AWS posts about Amazon
WorkSpaces / End User Computing (EUC) services into a backing store, enriches
them with AI summaries and content-type labels, and exposes them over a public
HTTP API. This module fetches and normalizes that data using only the Python
standard library, so the MCP server has no runtime dependency beyond the MCP SDK.

The read endpoints used here are public (no credentials required):

    GET /posts       -> the full crawled corpus
    GET /proposals   -> community content proposals (article/feature ideas)

The API base can be overridden with the ``CONTENT_HUB_API`` environment variable,
e.g. to target the staging stage.

Posts are cached in-process after the first fetch (see ``fetch_posts``). The
corpus is ~500 items and changes only when the crawler runs, so caching avoids
re-scanning the backing table on every search. It also keeps agent traffic out
of the Hub's search analytics, which would otherwise be polluted by calling the
server-side ``/posts?q=`` filter (that path logs every query as a "real" user
search and feeds the content-gap signal).
"""

import html
import json
import os
import re
import time
import urllib.parse
import urllib.request

DEFAULT_API_BASE = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod'

_USER_AGENT = 'euc-content-hub-mcp/1.0 (+https://gitlab.aws.dev/aws-euc/euc-content-hub-mcp)'
_TAG_RE = re.compile(r'<[^>]+>')

# Human-friendly source aliases -> the raw ``source`` value stored on posts.
SOURCE_ALIASES = {
    'aws-blog': 'aws-blog',
    'aws blog': 'aws-blog',
    'blog': 'aws-blog',
    'builder': 'builder.aws.com',
    'builder.aws': 'builder.aws.com',
    'builder.aws.com': 'builder.aws.com',
}

_posts_cache = None


def _api_base():
    return os.environ.get('CONTENT_HUB_API', DEFAULT_API_BASE).rstrip('/')


def clean_text(raw, max_len=600):
    """Strip HTML tags/entities from text and collapse whitespace."""
    if not raw:
        return ''
    text = html.unescape(_TAG_RE.sub('', raw)).strip()
    text = re.sub(r'\s+', ' ', text)
    if len(text) > max_len:
        text = text[:max_len].rstrip() + '...'
    return text


def _get_json(path, retries=3, timeout=30, token=None):
    """GET ``path`` from the Content Hub API and return the parsed JSON body.

    Retries with exponential backoff; raises the last error if all attempts fail.
    If ``token`` is given, it is sent as a Bearer ``Authorization`` header.
    """
    url = f'{_api_base()}{path}'
    headers = {
        'User-Agent': _USER_AGENT,
        'Accept': 'application/json',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    backoff = 1
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                charset = resp.headers.get_content_charset() or 'utf-8'
                return json.loads(resp.read().decode(charset, errors='replace'))
        except Exception as e:  # noqa: BLE001 - retried/raised below
            last_error = e
            if attempt < retries:
                time.sleep(backoff)
                backoff *= 2

    raise last_error


def _normalize_post(it):
    """Project a raw post record onto the fields the MCP tools expose."""
    return {
        'post_id': it.get('post_id', ''),
        'title': it.get('title', ''),
        'authors': it.get('authors', '') or '',
        'url': it.get('url', ''),
        'source': it.get('source', ''),
        'label': it.get('label', '') or '',
        'date_published': it.get('date_published', ''),
        'summary': it.get('summary', '') or '',
        'tags': it.get('tags', '') or '',
        'description': clean_text(it.get('content', '')),
    }


def fetch_posts(force_refresh=False):
    """Fetch and normalize the full crawled corpus from ``GET /posts``.

    Returns a list of normalized post dicts (most recent first). The result is
    cached in-process; pass ``force_refresh=True`` to bypass the cache.
    """
    global _posts_cache
    if _posts_cache is not None and not force_refresh:
        return _posts_cache

    payload = _get_json('/posts')
    raw_items = payload.get('posts', []) if isinstance(payload, dict) else []
    results = [_normalize_post(it) for it in raw_items]
    results.sort(key=lambda r: r['date_published'], reverse=True)
    _posts_cache = results
    return results


def search_posts(query, source='', label='', limit=10):
    """Rank the cached corpus against ``query`` with optional source/label filters.

    Scoring is a simple keyword overlap across title (weighted highest), tags,
    summary, authors, and body. Done locally so it covers more fields than the
    Hub's server-side title/author/tags-only filter and never pollutes the Hub's
    search analytics.
    """
    posts = fetch_posts()
    posts = _apply_facets(posts, source, label)

    terms = [t for t in re.split(r'\W+', query.lower()) if t]
    if not terms:
        ranked = posts
    else:
        scored = []
        for p in posts:
            title = p['title'].lower()
            tags = p['tags'].lower()
            summary = p['summary'].lower()
            authors = p['authors'].lower()
            body = p['description'].lower()
            score = 0
            for t in terms:
                if t in title:
                    score += 5
                if t in tags:
                    score += 3
                if t in summary:
                    score += 2
                if t in authors:
                    score += 2
                if t in body:
                    score += 1
            if score:
                scored.append((score, p))
        scored.sort(key=lambda sp: (sp[0], sp[1]['date_published']), reverse=True)
        ranked = [p for _, p in scored]

    if limit and limit > 0:
        ranked = ranked[:limit]
    return ranked


def list_posts(source='', label='', limit=25):
    """Return posts (most recent first) filtered by source and/or label."""
    posts = _apply_facets(fetch_posts(), source, label)
    if limit and limit > 0:
        posts = posts[:limit]
    return posts


def _apply_facets(posts, source, label):
    if source:
        wanted = SOURCE_ALIASES.get(source.strip().lower(), source.strip().lower())
        posts = [p for p in posts if p['source'].lower() == wanted]
    if label:
        needle = label.strip().lower()
        posts = [p for p in posts if needle in p['label'].lower()]
    return posts


def known_sources_and_labels():
    """Return the distinct source and label values present in the corpus."""
    posts = fetch_posts()
    sources = sorted({p['source'] for p in posts if p['source']})
    labels = sorted({p['label'] for p in posts if p['label']})
    return {'sources': sources, 'labels': labels}


def fetch_proposals(status=''):
    """Fetch existing community proposals from ``GET /proposals``.

    Returns normalized proposal dicts (newest first). ``status`` optionally
    filters server-side (e.g. "pending", "approved").
    """
    path = '/proposals'
    if status:
        path += f'?status={urllib.parse.quote(status.strip())}'
    payload = _get_json(path)
    raw_items = payload.get('proposals', []) if isinstance(payload, dict) else []

    results = []
    for it in raw_items:
        results.append({
            'proposal_id': it.get('proposal_id', ''),
            'title': it.get('title', ''),
            'proposal_type': it.get('proposal_type', 'article'),
            'status': it.get('status', ''),
            'category': it.get('category', '') or '',
            'votes': it.get('votes', 0),
            'display_name': it.get('display_name', '') or '',
            'created_at': it.get('created_at', ''),
            'description': clean_text(it.get('description', '')),
        })

    results.sort(key=lambda r: r['created_at'], reverse=True)
    return results


# Fields surfaced from a gap record. Deliberately excludes ``last_user_alias``
# (PII, irrelevant to gap analysis).
_GAP_FIELDS = (
    'normalized_query',
    'last_query_raw',
    'count',
    'unique_user_count',
    'last_result_count',
    'flag_zero_results',
    'flag_low_coverage',
    'first_seen_at',
    'last_seen_at',
)


def fetch_gaps(token, zero_only=False, low_only=False, min_count=1, limit=50):
    """Fetch search-analytics content gaps from ``GET /search-analytics/gaps``.

    This endpoint is authenticated; ``token`` must be a Cognito JWT (see
    ``auth.get_token``). Returns normalized gap dicts (highest count first):
    queries EUC specialists ran against the Hub that returned zero or few
    results — i.e. demand the corpus doesn't yet satisfy.

    Args:
        token: Cognito bearer token (without the "Bearer " prefix).
        zero_only: Only queries that returned zero results.
        low_only: Only low-coverage queries (includes zero); ignored if
            ``zero_only`` is set.
        min_count: Minimum number of times a query was seen.
        limit: Maximum rows to return (default 50; server caps at 500).
    """
    params = {'min_count': min_count, 'limit': limit}
    if zero_only:
        params['zero_only'] = 'true'
    elif low_only:
        params['low_only'] = 'true'
    path = '/search-analytics/gaps?' + urllib.parse.urlencode(params)

    payload = _get_json(path, token=token)
    raw_items = payload.get('gaps', []) if isinstance(payload, dict) else []

    results = []
    for it in raw_items:
        results.append({k: it.get(k, '') for k in _GAP_FIELDS})
    return results
