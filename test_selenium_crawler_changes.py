"""Unit tests for the selenium crawler changes:
  - resolve_table_name (event/env routing)
  - save_to_dynamodb change detection (preserve vs regenerate)

Selenium/Chrome is not exercised (can't run headless Chrome here); we mock the
DynamoDB table and drive save_to_dynamodb directly.
"""
import os
import unittest
from unittest.mock import MagicMock, patch

import builder_selenium_crawler as sc


def _meta(**over):
    m = {
        'url': 'https://builder.aws.com/content/abc/managing-amazon-workspaces',
        'title': 'Managing Amazon WorkSpaces',
        'authors': 'Jane Doe',
        'date_published': '2026-01-01',
        'date_updated': '2026-01-01T00:00:00Z',
        'content': 'x' * 500,
        'source': 'builder.aws.com',
    }
    m.update(over)
    return m


class TestResolveTableName(unittest.TestCase):
    def test_explicit_table_name_wins(self):
        self.assertEqual(sc.resolve_table_name({'table_name': 'custom-tbl'}), 'custom-tbl')

    def test_environment_staging(self):
        with patch.dict(os.environ, {'DYNAMODB_TABLE_NAME': 'aws-blog-posts'}):
            self.assertEqual(sc.resolve_table_name({'environment': 'staging'}), 'aws-blog-posts-staging')

    def test_env_var_default(self):
        with patch.dict(os.environ, {'DYNAMODB_TABLE_NAME': 'aws-blog-posts-staging'}):
            self.assertEqual(sc.resolve_table_name(None), 'aws-blog-posts-staging')

    def test_staging_base_not_double_suffixed(self):
        with patch.dict(os.environ, {'DYNAMODB_TABLE_NAME': 'aws-blog-posts-staging'}):
            self.assertEqual(sc.resolve_table_name({'environment': 'staging'}), 'aws-blog-posts-staging')


class TestSaveChangeDetection(unittest.TestCase):
    def _crawler(self, existing_item=None):
        c = sc.BuilderSeleniumCrawler.__new__(sc.BuilderSeleniumCrawler)
        c.posts_processed = c.posts_created = c.posts_updated = c.posts_skipped = 0
        c.table = MagicMock()
        c.table.get_item.return_value = {'Item': existing_item} if existing_item else {}
        return c

    def _expr(self, c):
        # Return the UpdateExpression string from the single update_item call.
        return c.table.update_item.call_args.kwargs['UpdateExpression']

    def test_new_post_blanks_ai_fields(self):
        c = self._crawler(existing_item=None)
        self.assertTrue(c.save_to_dynamodb(_meta()))
        self.assertEqual(c.posts_created, 1)
        self.assertIn('summary = :empty', self._expr(c))

    def test_changed_lastmod_blanks_ai_fields(self):
        c = self._crawler(existing_item={'date_updated': '2025-01-01T00:00:00Z'})
        self.assertTrue(c.save_to_dynamodb(_meta(date_updated='2026-06-01T00:00:00Z')))
        self.assertEqual(c.posts_updated, 1)
        self.assertIn('summary = :empty', self._expr(c))

    def test_unchanged_preserves_ai_fields(self):
        same = '2026-01-01T00:00:00Z'
        c = self._crawler(existing_item={'date_updated': same})
        self.assertTrue(c.save_to_dynamodb(_meta(date_updated=same)))
        self.assertEqual(c.posts_updated, 1)
        expr = self._expr(c)
        self.assertNotIn('summary = :empty', expr)   # <- the storm-prevention guarantee
        self.assertIn('title = :title', expr)        # still refreshes scraped fields
        self.assertIn('last_crawled = :last_crawled', expr)


class TestBatchingWindow(unittest.TestCase):
    """skip + max_posts must slice DIFFERENT, stable windows so batches across
    invocations cover the whole set (the bug that made a full crawl never finish)."""

    def _run(self, n_urls, skip, max_posts):
        c = sc.BuilderSeleniumCrawler.__new__(sc.BuilderSeleniumCrawler)
        c.posts_processed = c.posts_created = c.posts_updated = c.posts_skipped = 0
        c.total_urls = 0
        c.driver = None
        processed = []

        # URLs come back in non-sorted order to prove the crawler sorts them.
        urls = [(f"https://builder.aws.com/content/x/post-{i:03d}", "2026-01-01")
                for i in range(n_urls)]
        urls_shuffled = urls[::-1]

        with patch.object(c, "setup_driver"), patch.object(c, "close_driver"), \
             patch.object(c, "get_article_sitemaps", return_value=["sm"]), \
             patch.object(c, "is_euc_related", return_value=True), \
             patch("builder_selenium_crawler.requests.get") as rget, \
             patch("builder_selenium_crawler.ET.fromstring") as fromstr, \
             patch.object(c, "extract_page_content", side_effect=lambda u: (processed.append(u) or None)):
            # Make sitemap parsing yield our shuffled urls.
            root = MagicMock()
            elems = []
            for u, d in urls_shuffled:
                el = MagicMock()
                loc = MagicMock(); loc.text = u
                lm = MagicMock(); lm.text = d
                el.find.side_effect = lambda q, ns=None, _l=loc, _m=lm: _l if q.endswith("loc") else _m
                elems.append(el)
            root.findall.return_value = elems
            fromstr.return_value = root
            c.crawl_all_posts(max_posts=max_posts, skip=skip)
        return c.total_urls, processed

    def test_total_urls_counts_all(self):
        total, _ = self._run(100, skip=0, max_posts=40)
        self.assertEqual(total, 100)

    def test_window_is_sorted_and_offset(self):
        _, proc = self._run(100, skip=40, max_posts=40)
        # Should be posts 040..079 in sorted order.
        self.assertEqual(len(proc), 40)
        self.assertTrue(proc[0].endswith("post-040"))
        self.assertTrue(proc[-1].endswith("post-079"))

    def test_batches_tile_without_gaps_or_overlap(self):
        seen = []
        for skip in (0, 40, 80):
            _, proc = self._run(100, skip=skip, max_posts=40)
            seen += proc
        # 100 posts, batches of 40 -> 40+40+20, every post exactly once.
        self.assertEqual(len(seen), 100)
        self.assertEqual(len(set(seen)), 100)


if __name__ == '__main__':
    unittest.main(verbosity=2)
