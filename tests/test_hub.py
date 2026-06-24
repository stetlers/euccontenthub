"""Tests for the Content Hub API client's normalization, search, and faceting.

Network fetching is not exercised; we monkeypatch ``_get_json`` with canned
payloads and reset the in-process post cache between tests.
"""

import pytest

from euc_content_hub_mcp import hub


_POSTS_PAYLOAD = {
    'posts': [
        {
            'post_id': 'p1',
            'title': 'Deploying AppStream 2.0 with GPU instances',
            'authors': 'Jane Doe',
            'url': 'https://example/appstream-gpu',
            'source': 'aws-blog',
            'label': 'Technical How-To',
            'date_published': '2026-05-01T00:00:00Z',
            'summary': 'How to pick GPU fleets for AppStream.',
            'tags': 'appstream, gpu',
            'content': '<p>Long body about <b>GPU</b> fleets.</p>',
        },
        {
            'post_id': 'p2',
            'title': 'WorkSpaces cost optimization tips',
            'authors': 'John Smith',
            'url': 'https://example/workspaces-cost',
            'source': 'builder.aws.com',
            'label': 'Best Practices',
            'date_published': '2026-01-01T00:00:00Z',
            'summary': 'Save money on WorkSpaces.',
            'tags': 'workspaces, cost',
            'content': '<p>Body about cost.</p>',
        },
    ]
}

_PROPOSALS_PAYLOAD = {
    'proposals': [
        {
            'proposal_id': 'pr1',
            'title': 'Guide: WorkSpaces Core migration',
            'proposal_type': 'article',
            'status': 'pending',
            'category': 'How-To',
            'votes': 3,
            'display_name': 'Alice',
            'created_at': '2026-06-01T00:00:00Z',
            'description': '<p>We need a migration guide.</p>',
        },
    ]
}


@pytest.fixture(autouse=True)
def _reset_cache():
    hub._posts_cache = None
    yield
    hub._posts_cache = None


def test_clean_text_strips_html_and_truncates():
    raw = "<p>Amazon WorkSpaces&nbsp;adds <a href='x'>support</a>.</p>"
    assert hub.clean_text(raw) == "Amazon WorkSpaces adds support."
    long = "<p>" + ("word " * 300) + "</p>"
    out = hub.clean_text(long, max_len=50)
    assert len(out) <= 53
    assert out.endswith("...")


def test_fetch_posts_normalizes_sorts_and_caches(monkeypatch):
    calls = {'n': 0}

    def fake_get(path, **kw):
        calls['n'] += 1
        return _POSTS_PAYLOAD

    monkeypatch.setattr(hub, '_get_json', fake_get)

    posts = hub.fetch_posts()
    # Sorted most-recent first.
    assert [p['post_id'] for p in posts] == ['p1', 'p2']
    # HTML stripped from body into 'description'.
    assert posts[0]['description'] == 'Long body about GPU fleets.'
    # Second call is served from cache (no extra fetch).
    hub.fetch_posts()
    assert calls['n'] == 1


def test_search_ranks_title_over_body(monkeypatch):
    monkeypatch.setattr(hub, '_get_json', lambda path, **kw: _POSTS_PAYLOAD)
    results = hub.search_posts('appstream gpu', limit=10)
    assert results[0]['post_id'] == 'p1'  # title+tags+summary hits outrank p2


def test_search_with_source_alias(monkeypatch):
    monkeypatch.setattr(hub, '_get_json', lambda path, **kw: _POSTS_PAYLOAD)
    results = hub.search_posts('cost', source='builder', limit=10)
    assert [p['post_id'] for p in results] == ['p2']


def test_list_posts_filters_by_label(monkeypatch):
    monkeypatch.setattr(hub, '_get_json', lambda path, **kw: _POSTS_PAYLOAD)
    results = hub.list_posts(label='best practices')
    assert [p['post_id'] for p in results] == ['p2']


def test_known_sources_and_labels(monkeypatch):
    monkeypatch.setattr(hub, '_get_json', lambda path, **kw: _POSTS_PAYLOAD)
    facets = hub.known_sources_and_labels()
    assert facets['sources'] == ['aws-blog', 'builder.aws.com']
    assert 'Technical How-To' in facets['labels']


def test_fetch_proposals_normalizes(monkeypatch):
    monkeypatch.setattr(hub, '_get_json', lambda path, **kw: _PROPOSALS_PAYLOAD)
    proposals = hub.fetch_proposals()
    assert proposals[0]['proposal_id'] == 'pr1'
    assert proposals[0]['description'] == 'We need a migration guide.'


_GAPS_PAYLOAD = {
    'gaps': [
        {
            'normalized_query': 'workspaces gpu pricing',
            'last_query_raw': 'WorkSpaces GPU pricing',
            'count': 12,
            'unique_user_count': 7,
            'last_result_count': 0,
            'flag_zero_results': True,
            'flag_low_coverage': True,
            'first_seen_at': '2026-05-01T00:00:00Z',
            'last_seen_at': '2026-06-10T00:00:00Z',
            'last_user_alias': 'someone',  # PII — must be dropped
        },
    ],
    'count': 1,
}


def test_fetch_gaps_sends_token_and_drops_pii(monkeypatch):
    captured = {}

    def fake_get(path, token=None, **kw):
        captured['path'] = path
        captured['token'] = token
        return _GAPS_PAYLOAD

    monkeypatch.setattr(hub, '_get_json', fake_get)
    gaps = hub.fetch_gaps('tok123', zero_only=True, min_count=3, limit=10)

    assert captured['token'] == 'tok123'
    assert 'zero_only=true' in captured['path']
    assert 'min_count=3' in captured['path']
    assert gaps[0]['normalized_query'] == 'workspaces gpu pricing'
    assert 'last_user_alias' not in gaps[0]  # PII stripped
