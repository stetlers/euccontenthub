"""Tests for the SPA-shell guard in the requests-based fallback.

Regression coverage for the 2026-06-17 incident, where the requests fallback
(no JS rendering) scraped builder.aws.com's unrendered shell and wrote 21 posts
titled "AWS Builder Center". The guard must return None (skip) for shell pages
and still return metadata for genuinely-rendered pages.
"""
import unittest
from unittest.mock import patch, MagicMock

import lambda_function as lf


def _resp(html):
    m = MagicMock()
    m.text = html
    m.raise_for_status = MagicMock()
    return m


REAL_URL = "https://builder.aws.com/content/abc123/managing-amazon-workspaces"


class TestSpaShellGuard(unittest.TestCase):
    def test_shell_title_is_skipped(self):
        html = "<html><head><title>AWS Builder Center</title></head><body></body></html>"
        with patch.object(lf.requests, "get", return_value=_resp(html)):
            self.assertIsNone(lf.extract_page_content_requests(REAL_URL, "2026-01-01"))

    def test_shell_title_with_suffix_is_skipped(self):
        # Suffix-strip reduces "AWS Builder Center | Builder.AWS" but the bare
        # shell title that remains must still be rejected.
        html = "<html><head><title>AWS Builder Center</title></head><body></body></html>"
        with patch.object(lf.requests, "get", return_value=_resp(html)):
            self.assertIsNone(lf.extract_page_content_requests(REAL_URL, "2026-01-01"))

    def test_title_equals_content_is_skipped(self):
        # Both fields collapsing to the same string => page never rendered.
        html = "<html><head><title>Some Slug Title</title></head><body>Some Slug Title</body></html>"
        with patch.object(lf.requests, "get", return_value=_resp(html)):
            self.assertIsNone(lf.extract_page_content_requests(REAL_URL, "2026-01-01"))

    def test_short_content_is_skipped(self):
        html = "<html><head><title>A Real Looking Title</title></head><body>tiny</body></html>"
        with patch.object(lf.requests, "get", return_value=_resp(html)):
            self.assertIsNone(lf.extract_page_content_requests(REAL_URL, "2026-01-01"))

    def test_rendered_article_is_kept(self):
        body = "Amazon WorkSpaces is a managed desktop service. " * 10
        html = f"<html><head><title>Managing Amazon WorkSpaces</title></head><body><article>{body}</article></body></html>"
        with patch.object(lf.requests, "get", return_value=_resp(html)):
            md = lf.extract_page_content_requests(REAL_URL, "2026-01-01")
        self.assertIsNotNone(md)
        self.assertEqual(md["title"], "Managing Amazon WorkSpaces")
        self.assertGreater(len(md["content"]), 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
