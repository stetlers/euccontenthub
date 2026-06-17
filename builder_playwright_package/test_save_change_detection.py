"""Behavioral tests for the Playwright Builder crawler's change-detection.

Verifies the fix that stops the Bedrock re-summarize/re-classify storm:
AI-generated fields (summary/label) are only blanked when the sitemap lastmod
actually changed. No real DynamoDB — a fake table records update_item calls.
"""
import sys
import types

# The Lambda imports `from euc_filter import filter_post` and `requests`/playwright
# at module load. Stub them so we can import lambda_function without those deps.
for name in ('requests',):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
if 'euc_filter' not in sys.modules:
    ef = types.ModuleType('euc_filter')
    ef.filter_post = lambda url, title: types.SimpleNamespace(
        accepted=True, stage='keyword', reason='')
    sys.modules['euc_filter'] = ef

import lambda_function as lf


class FakeTable:
    """Minimal DynamoDB Table double: canned get_item, records update_item kwargs."""
    def __init__(self, existing_item=None):
        self._item = existing_item
        self.update_calls = []

    def get_item(self, Key):
        return {'Item': self._item} if self._item is not None else {}

    def update_item(self, **kwargs):
        self.update_calls.append(kwargs)


def _metadata(date_updated):
    return {
        'url': 'https://builder.aws.com/content/abc/my-article',
        'title': 'My Article',
        'authors': 'Real Author',
        'date_published': '2026-01-01T00:00:00Z',
        'date_updated': date_updated,
        'content': 'real body text',
        'source': 'builder.aws.com',
    }


def _blanks_ai_fields(update_kwargs):
    """True if this update_item blanks summary AND label (regeneration path)."""
    expr = update_kwargs['UpdateExpression']
    vals = update_kwargs['ExpressionAttributeValues']
    return ('summary = :empty' in expr and 'label = :empty' in expr
            and vals.get(':empty') == '')


def test_unchanged_post_preserves_ai_fields():
    """Same lastmod -> must NOT blank summary/label (no Bedrock storm)."""
    existing = {'post_id': 'builder-my-article', 'date_updated': '2026-03-01T00:00:00Z',
                'summary': 'good summary', 'label': 'Technical How-To'}
    table = FakeTable(existing)
    ok = lf.save_to_dynamodb(table, _metadata('2026-03-01T00:00:00Z'))
    assert ok
    assert len(table.update_calls) == 1
    call = table.update_calls[0]
    assert not _blanks_ai_fields(call), "unchanged post should not blank AI fields"
    # last_crawled still refreshed
    assert ':last_crawled' in call['ExpressionAttributeValues']
    # summary/label not mentioned as direct sets
    assert 'summary = :empty' not in call['UpdateExpression']


def test_changed_lastmod_regenerates():
    """Newer lastmod -> blank summary/label so they regenerate."""
    existing = {'post_id': 'builder-my-article', 'date_updated': '2026-03-01T00:00:00Z',
                'summary': 'stale summary', 'label': 'Old Label'}
    table = FakeTable(existing)
    ok = lf.save_to_dynamodb(table, _metadata('2026-06-10T00:00:00Z'))
    assert ok
    assert _blanks_ai_fields(table.update_calls[0]), "changed post should regenerate AI fields"


def test_new_post_regenerates():
    """No existing item -> treated as new, generate summary/label."""
    table = FakeTable(existing_item=None)
    ok = lf.save_to_dynamodb(table, _metadata('2026-06-10T00:00:00Z'))
    assert ok
    assert _blanks_ai_fields(table.update_calls[0]), "new post should generate AI fields"


def test_missing_stored_date_regenerates():
    """Existing row without date_updated -> treat as changed (safe), regenerate."""
    existing = {'post_id': 'builder-my-article', 'summary': 's', 'label': 'l'}
    table = FakeTable(existing)
    ok = lf.save_to_dynamodb(table, _metadata('2026-06-10T00:00:00Z'))
    assert ok
    assert _blanks_ai_fields(table.update_calls[0])


def test_regeneration_with_scrape_miss_preserves_author():
    """Changed post BUT this run's scrape missed the author (author_needs_review):
    must NOT overwrite a stored author with 'Unknown Author' -> if_not_exists."""
    existing = {'post_id': 'builder-my-article', 'date_updated': '2026-03-01T00:00:00Z',
                'authors': 'Real Author', 'summary': 's', 'label': 'l'}
    table = FakeTable(existing)
    md = _metadata('2026-06-10T00:00:00Z')   # changed -> regeneration path
    md['authors'] = 'Unknown Author'
    md['author_needs_review'] = True
    ok = lf.save_to_dynamodb(table, md)
    assert ok
    expr = table.update_calls[0]['UpdateExpression']
    # author guarded by if_not_exists, summary/label still regenerate
    assert 'authors = if_not_exists(authors, :authors)' in expr
    assert _blanks_ai_fields(table.update_calls[0])


def test_regeneration_with_real_author_overwrites():
    """Changed post WITH a freshly-scraped real author: author set normally."""
    existing = {'post_id': 'builder-my-article', 'date_updated': '2026-03-01T00:00:00Z',
                'authors': 'Old Author', 'summary': 's', 'label': 'l'}
    table = FakeTable(existing)
    md = _metadata('2026-06-10T00:00:00Z')
    md['authors'] = 'New Real Author'   # no author_needs_review flag
    ok = lf.save_to_dynamodb(table, md)
    assert ok
    expr = table.update_calls[0]['UpdateExpression']
    assert 'authors = :authors' in expr
    assert 'if_not_exists(authors' not in expr
    assert table.update_calls[0]['ExpressionAttributeValues'][':authors'] == 'New Real Author'


def test_resolve_table_default_is_prod(monkeypatch=None):
    """No event / no staging hint -> the env-var (prod) table."""
    import os
    os.environ['DYNAMODB_TABLE_NAME'] = 'aws-blog-posts'
    assert lf.resolve_table_name(None) == 'aws-blog-posts'
    assert lf.resolve_table_name({}) == 'aws-blog-posts'
    assert lf.resolve_table_name({'debug': False}) == 'aws-blog-posts'


def test_resolve_table_staging_environment():
    """environment=staging -> staging table (the button-trap fix)."""
    import os
    os.environ['DYNAMODB_TABLE_NAME'] = 'aws-blog-posts'
    assert lf.resolve_table_name({'environment': 'staging'}) == 'aws-blog-posts-staging'


def test_resolve_table_explicit_override_wins():
    """Explicit table_name beats environment."""
    assert lf.resolve_table_name(
        {'table_name': 'custom-table', 'environment': 'staging'}) == 'custom-table'


def test_resolve_table_idempotent_when_env_already_staging():
    """If the env var itself is the staging table, don't double-suffix."""
    import os
    os.environ['DYNAMODB_TABLE_NAME'] = 'aws-blog-posts-staging'
    assert lf.resolve_table_name({'environment': 'staging'}) == 'aws-blog-posts-staging'
    # restore for other tests
    os.environ['DYNAMODB_TABLE_NAME'] = 'aws-blog-posts'


if __name__ == '__main__':
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
