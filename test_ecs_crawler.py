"""Unit tests for the ported ECS selenium crawler (discovery + title + change-detection).

Chrome/Selenium and the network are mocked; we exercise the pure logic.
Run with DYNAMODB_TABLE_NAME set so module import doesn't hit a real table.
"""
import os
os.environ.setdefault("DYNAMODB_TABLE_NAME", "aws-blog-posts-staging")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

import unittest
from unittest.mock import MagicMock, patch

import ecs_selenium_crawler as ec


class TestEucFilter(unittest.TestCase):
    def test_accepts_workspaces(self):
        u = "https://builder.aws.com/content/x/managing-amazon-workspaces"
        self.assertTrue(ec.is_euc_related(u, ec.extract_title_from_slug(u)))

    def test_rejects_non_euc(self):
        u = "https://builder.aws.com/content/x/generating-animated-line-style-chat-slides"
        self.assertFalse(ec.is_euc_related(u, ec.extract_title_from_slug(u)))

    def test_slug_title_normalizes(self):
        u = "https://builder.aws.com/content/x/managing-appstream-and-workspaces"
        t = ec.extract_title_from_slug(u)
        self.assertIn("AppStream", t)
        self.assertIn("WorkSpaces", t)


class TestSaveChangeDetection(unittest.TestCase):
    def _meta(self, **o):
        m = {'url': 'https://builder.aws.com/content/x/managing-amazon-workspaces',
             'title': 'Managing Amazon WorkSpaces', 'authors': 'Jane Doe',
             'content': 'x' * 500, 'date_updated': '2026-01-01T00:00:00Z'}
        m.update(o); return m

    def _patch_table(self, existing=None):
        t = MagicMock()
        t.get_item.return_value = {'Item': existing} if existing else {}
        return patch.object(ec, "table", t), t

    def test_new_blanks_ai(self):
        p, t = self._patch_table(None)
        with p:
            self.assertEqual(ec.save_to_dynamodb(self._meta()), 'created')
        self.assertIn('summary = :empty', t.update_item.call_args.kwargs['UpdateExpression'])

    def test_changed_blanks_ai(self):
        p, t = self._patch_table({'date_updated': '2025-01-01T00:00:00Z'})
        with p:
            self.assertEqual(ec.save_to_dynamodb(self._meta(date_updated='2026-06-01T00:00:00Z')), 'changed')
        self.assertIn('summary = :empty', t.update_item.call_args.kwargs['UpdateExpression'])

    def test_unchanged_preserves_ai(self):
        same = '2026-01-01T00:00:00Z'
        p, t = self._patch_table({'date_updated': same})
        with p:
            self.assertEqual(ec.save_to_dynamodb(self._meta(date_updated=same)), 'unchanged')
        expr = t.update_item.call_args.kwargs['UpdateExpression']
        self.assertNotIn('summary = :empty', expr)
        self.assertIn('title = :title', expr)

    def test_new_post_gets_date_published(self):
        # Regression: a created row must always get a sortable date_published
        # (seeded from sitemap lastmod), else it sinks to the bottom of the site.
        p, t = self._patch_table(None)
        with p:
            ec.save_to_dynamodb(self._meta(date_updated='2026-06-22T00:00:00Z'))
        expr = t.update_item.call_args.kwargs['UpdateExpression']
        vals = t.update_item.call_args.kwargs['ExpressionAttributeValues']
        self.assertIn('date_published = if_not_exists(date_published, :date_published)', expr)
        self.assertEqual(vals[':date_published'], '2026-06-22T00:00:00Z')

    def test_writes_title(self):
        p, t = self._patch_table(None)
        with p:
            ec.save_to_dynamodb(self._meta())
        self.assertEqual(t.update_item.call_args.kwargs['ExpressionAttributeValues'][':title'],
                         'Managing Amazon WorkSpaces')


if __name__ == '__main__':
    unittest.main(verbosity=2)
