"""Behavioral tests for Issue 3 — enrichment alias routing in the multi-source crawler.

Verifies that the summary/classifier aliases (and the classifier payload) are selected
from the EVENT-resolved environment, not the crawler's static ENVIRONMENT env var. The
prod crawler is pinned ENVIRONMENT=production, so a staging-triggered run must still reach
the :staging aliases (otherwise staging labels never refill — the 40-stuck-label bug).

No real boto3 calls: lambda_client.invoke is captured, and AWSBlogCrawler is stubbed so the
handler runs the aws-blog enrichment path without network/Bedrock.
"""
import os
import sys
import types

# lambda_function creates boto3.resource('dynamodb') at import; give it a region.
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')

# The Lambda imports requests, bs4, and euc_filter at module load. Stub them so we can
# import lambda_function without those deps (mirrors test_save_change_detection.py).
for name in ('requests',):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
if 'bs4' not in sys.modules:
    bs4 = types.ModuleType('bs4')
    bs4.BeautifulSoup = object
    sys.modules['bs4'] = bs4
if 'euc_filter' not in sys.modules:
    ef = types.ModuleType('euc_filter')
    ef.filter_post = lambda url, title: types.SimpleNamespace(
        accepted=True, stage='keyword', reason='')
    sys.modules['euc_filter'] = ef

import lambda_function as lf


class FakeLambdaClient:
    """Captures invoke() kwargs so we can assert on FunctionName + Payload."""
    def __init__(self):
        self.invocations = []

    def invoke(self, **kwargs):
        self.invocations.append(kwargs)
        return {'StatusCode': 202}


class StubBlogCrawler:
    """Stands in for AWSBlogCrawler: reports posts that need enrichment, no real crawl."""
    def __init__(self, base_url, table_name):
        pass

    def crawl_all_posts(self, max_pages=None):
        return {
            'total_posts': 5,
            'posts_processed': 5,
            'posts_created': 0,
            'posts_updated': 5,
            'posts_needing_summaries': 5,
            'posts_needing_classification': 5,
        }


def _run_handler(event, monkeypatch_attrs):
    """Run the aws-blog-only path with a fake lambda client; return its invocations.

    monkeypatch_attrs temporarily swaps module globals; restored before returning.
    """
    fake = FakeLambdaClient()
    saved = {}

    def fake_boto3_client(service, *a, **k):
        assert service == 'lambda', f"only lambda client expected, got {service}"
        return fake

    saved['client'] = lf.boto3.client
    saved['crawler'] = lf.AWSBlogCrawler
    saved['sleep'] = lf.time.sleep
    lf.boto3.client = fake_boto3_client
    lf.AWSBlogCrawler = StubBlogCrawler
    lf.time.sleep = lambda *_: None
    try:
        # source='aws-blog' avoids the Builder branch (which would call ECS).
        ev = {'source': 'aws-blog'}
        ev.update(event)
        lf.lambda_handler(ev, None)
    finally:
        lf.boto3.client = saved['client']
        lf.AWSBlogCrawler = saved['crawler']
        lf.time.sleep = saved['sleep']
    return fake.invocations


def _names(invocations):
    return [c['FunctionName'] for c in invocations]


def test_staging_event_routes_to_staging_aliases():
    """A staging click on a prod-pinned crawler must hit the :staging aliases (Issue 3)."""
    os.environ['ENVIRONMENT'] = 'production'   # crawler's own static env (prod pinned)
    invs = _run_handler({'environment': 'staging'}, {})
    names = _names(invs)
    assert any(n == 'aws-blog-summary-generator:staging' for n in names), names
    assert any(n == 'aws-blog-classifier:staging' for n in names), names
    # And NEVER the production aliases on a staging run.
    assert not any(n.endswith(':production') for n in names), names


def test_production_event_routes_to_production_aliases():
    """A prod click stays all-production."""
    os.environ['ENVIRONMENT'] = 'production'
    invs = _run_handler({'environment': 'production'}, {})
    names = _names(invs)
    assert any(n == 'aws-blog-summary-generator:production' for n in names), names
    assert any(n == 'aws-blog-classifier:production' for n in names), names
    assert not any(n.endswith(':staging') for n in names), names


def test_classifier_payload_carries_table_and_environment():
    """Classifier payload must reach parity with summary (table_name + environment)."""
    import json
    os.environ['ENVIRONMENT'] = 'production'
    invs = _run_handler({'environment': 'staging'}, {})
    classifier = [c for c in invs if c['FunctionName'].startswith('aws-blog-classifier')]
    assert classifier, "expected a classifier invocation"
    payload = json.loads(classifier[0]['Payload'])
    assert payload['environment'] == 'staging', payload
    assert payload['table_name'] == 'aws-blog-posts-staging', payload


def test_summary_payload_still_carries_table_and_environment():
    """Summary payload behavior is unchanged by the fix."""
    import json
    os.environ['ENVIRONMENT'] = 'production'
    invs = _run_handler({'environment': 'staging'}, {})
    summary = [c for c in invs if c['FunctionName'].startswith('aws-blog-summary-generator')]
    assert summary, "expected a summary invocation"
    payload = json.loads(summary[0]['Payload'])
    assert payload['environment'] == 'staging', payload
    assert payload['table_name'] == 'aws-blog-posts-staging', payload


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
