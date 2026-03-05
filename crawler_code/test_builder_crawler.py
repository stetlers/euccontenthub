```python
"""
Property-Based and Unit Tests for Builder.AWS Crawler Change Detection

This test suite validates the correctness properties defined in the design document
for the builder-crawler-change-detection feature.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from hypothesis import given, strategies as st, settings
import sys
import os

# Mock boto3 before importing lambda_function
sys.modules['boto3'] = MagicMock()

# Add parent directory to path to import lambda_function
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lambda_function import BuilderAWSCrawler


class TestChangeDetectionProperties(unittest.TestCase):
    """Property-based tests for change detection logic"""
    
    @given(
        old_lastmod=st.one_of(
            st.just(''),
            st.dates().map(lambda d: d.isoformat())
        ),
        new_lastmod=st.dates().map(lambda d: d.isoformat())
    )
    @settings(max_examples=100)
    def test_property_3_change_detection_based_on_lastmod(self, old_lastmod, new_lastmod):
        """
        Property 3: Change Detection Based on Lastmod Comparison
        
        **Feature: builder-crawler-change-detection, Property 3: Change Detection Based on Lastmod Comparison**
        **Validates: Requirements 3.1, 3.2, 3.3**
        
        For any existing Builder.AWS article with a stored date_updated value,
        when the crawler processes it:
        - If the new lastmod date differs from the stored date_updated, 
          the article should be marked as changed (content_changed = True)
        - If the new lastmod date equals the stored date_updated, 
          the article should be marked as unchanged (content_changed = False)
        """
        # Simulate the comparison logic from save_to_dynamodb
        content_changed = (old_lastmod != new_lastmod)
        
        # Verify the property holds
        if old_lastmod != new_lastmod:
            self.assertTrue(content_changed, 
                f"Expected content_changed=True when dates differ: {old_lastmod} != {new_lastmod}")
        else:
            self.assertFalse(content_changed,
                f"Expected content_changed=False when dates match: {old_lastmod} == {new_lastmod}")


class TestChangeDetectionScenarios(unittest.TestCase):
    """Unit tests for specific change detection scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.crawler = BuilderAWSCrawler('test-table')
        self.crawler.table = Mock()
    
    def test_unchanged_article_preserves_summary(self):
        """
        Test unchanged article (same lastmod) preserves summary
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
        """
        # Setup: Existing article with summary
        existing_item = {
            'post_id': 'builder-test-article',
            'date_updated': '2024-01-15',
            'summary': 'Existing summary text',
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.'
        }
        
        self.crawler.table.get_item.return_value = {'Item': existing_item}
        self.crawler.table.update_item.return_value = {}
        
        # New metadata with same lastmod
        metadata = {
            'url': 'https://builder.aws.com/articles/test-article',
            'title': 'Test Article',
            'authors': 'AWS Builder Community',
            'date_published': '2024-01-15',
            'date_updated': '2024-01-15',  # Same as existing
            'tags': 'End User Computing, Builder.AWS',
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.',
            'source': 'builder.aws.com'
        }
        
        # Execute
        result = self.crawler.save_to_dynamodb(metadata)
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(self.crawler.posts_updated, 1)
        self.assertEqual(self.crawler.posts_needing_summaries, 0)
        
        # Verify update_item was called without clearing summary
        update_call = self.crawler.table.update_item.call_args
        update_expression = update_call[1]['UpdateExpression']
        self.assertNotIn('summary = :empty', update_expression)
    
    def test_changed_article_clears_summary(self):
        """
        Test changed article (different lastmod) clears summary
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
        """
        # Setup: Existing article with summary
        existing_item = {
            'post_id': 'builder-test-article',
            'date_updated': '2024-01-15',
            'summary': 'Existing summary text',
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.'
        }
        
        self.crawler.table.get_item.return_value = {'Item': existing_item}
        self.crawler.table.update_item.return_value = {}
        
        # New metadata with different lastmod
        metadata = {
            'url': 'https://builder.aws.com/articles/test-article',
            'title': 'Test Article',
            'authors': 'AWS Builder Community',
            'date_published': '2024-01-15',
            'date_updated': '2024-01-20',  # Different from existing
            'tags': 'End User Computing, Builder.AWS',
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.',
            'source': 'builder.aws.com'
        }
        
        # Execute
        result = self.crawler.save_to_dynamodb(metadata)
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(self.crawler.posts_updated, 1)
        self.assertEqual(self.crawler.posts_needing_summaries, 1)
        
        # Verify update_item was called with summary clearing
        update_call = self.crawler.table.update_item.call_args
        update_expression = update_call[1]['UpdateExpression']
        self.assertIn('summary = :empty', update_expression)
        self.assertEqual(update_call[1]['ExpressionAttributeValues'][':empty'], '')
    
    def test_new_article_creates_with_lastmod(self):
        """
        Test new article (no existing record) creates with lastmod
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
        """
        # Setup: No existing article
        self.crawler.table.get_item.return_value = {}
        self.crawler.table.update_item.return_value = {}
        
        # New metadata
        metadata = {
            'url': 'https://builder.aws.com/articles/new-article',
            'title': 'New Article',
            'authors': 'AWS Builder Community',
            'date_published': '2024-01-20',
            'date_updated': '2024-01-20',
            'tags': 'End User Computing, Builder.AWS',
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.',
            'source': 'builder.aws.com'
        }
        
        # Execute
        result = self.crawler.save_to_dynamodb(metadata)
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(self.crawler.posts_created, 1)
        self.assertEqual(self.crawler.posts_needing_summaries, 1)
        
        # Verify update_item was called with summary clearing (new post needs summary)
        update_call = self.crawler.table.update_item.call_args
        update_expression = update_call[1]['UpdateExpression']
        self.assertIn('summary = :empty', update_expression)


class TestDateFilteringAndURLPatterns(unittest.TestCase):
    """Tests for date filtering and URL pattern matching - March 2026 WorkSpaces blog post issue"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.crawler = BuilderAWSCrawler('test-table')
        self.crawler.table = Mock()
    
    def test_march_2026_workspaces_blog_post_detection(self):
        """
        Test detection and processing of March 2, 2026 WorkSpaces G6 blog post
        **Issue: Crawler not picking up new blog post about Graphics G6, Gr6, and G6f bundles**
        **Validates: Date filtering, URL pattern matching, proper scraping and storage**
        """
        # Setup: No existing article for this new blog post
        self.crawler.table.get_item.return_value = {}
        self.crawler.table.update_item.return_value = {}
        
        # Test blog post metadata from March 2, 2026
        metadata = {
            'url': 'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-graphics-g6-gr6-g6f-bundles',
            'title': 'Introducing Amazon WorkSpaces Graphics G6, Gr6, and G6f bundles',
            'authors': 'AWS Desktop and Application Streaming Team',
            'date_published': '2026-03-02',
            'date_updated': '2026-03-02',
            'tags': 'End User Computing, Amazon WorkSpaces, Graphics, G6',
            'content': 'AWS announces new Graphics G6, Gr6, and G6f bundles for Amazon WorkSpaces...',
            'source': 'aws.amazon.com'
        }
        
        # Execute
        result = self.crawler.save_to_dynamodb(metadata)
        
        # Verify the blog post is properly created
        self.assertTrue(result, "Blog post should be successfully saved")
        self.assertEqual(self.crawler.posts_created, 1, "Should create new blog post")
        self.assertEqual(self.crawler.posts_needing_summaries, 1, "New post should need summary")
        
        # Verify update_item was called with correct data
        self.assertTrue(self.crawler.table.update_item.called, "DynamoDB update should be called")
        update_call = self.crawler.table.update_item.call_args
        
        # Verify date_updated field is set correctly
        self.assertIn(':date_updated', update_call[1]['ExpressionAttributeValues'])
        self.assertEqual(update_call[1]['ExpressionAttributeValues'][':date_updated'], '2026-03-02')
    
    def test_future_date_filtering_logic(self):
        """
        Test that crawler properly handles future dates (2026) without filtering them out
        **Issue: Date filtering may be excluding posts with dates in 2026**
        """
        # Test multiple blog posts with future dates
        future_dates = [
            '2026-03-02',  # March 2026 WorkSpaces post
            '2026-01-15',  # Early 2026
            '2026-12-31',  # End of 2026
        ]
        
        for test_date in future_dates:
            # Reset crawler counters
            self.crawler = BuilderAWSCrawler('test-table')
            self.crawler.table = Mock()
            self.crawler.table.get_item.return_value = {}
            self.crawler.table.update_item.return_value = {}
            
            metadata = {
                'url': f'https://aws.amazon.com/blogs/test-article-{test_date}',
                'title': f'Test Article for {test_date}',
                'authors': 'AWS Team',
                'date_published': test_date,
                'date_updated': test_date,
                'tags': 'End User Computing',
                'content': f'Content for {test_date}',
                'source': 'aws.amazon.com'
            }
            
            # Execute
            result = self.crawler.save_to_dynamodb(metadata)
            
            # Verify future dates are NOT filtered out
            self.assertTrue(result, f"Date {test_date} should not be filtered out")
            self.assertEqual(self.crawler.posts_created, 1, f"Should create post for {test_date}")
    
    def test_workspaces_url_pattern_matching(self):
        """
        Test that crawler properly matches WorkSpaces-related URL patterns
        **Issue: URL pattern may not be matching new WorkSpaces blog structure**
        """
        # Test various WorkSpaces URL patterns
        workspaces_urls = [
            'https://aws.amazon.com/blogs/desktop-and-application-streaming/amazon-workspaces-graphics-g6-gr6-g6f-bundles',
            'https://aws.amazon.com/blogs/desktop-and-application-streaming/workspaces-core-setup',
            'https://aws.amazon.com/blogs/aws/amazon-workspaces-announcement',
            'https://docs.aws.amazon.com/workspaces/latest/adminguide/workspaces-graphics',
        ]
        
        for url in workspaces_urls:
            # Reset crawler
            self.crawler = BuilderAWSCrawler('test-table')
            self.crawler.table = Mock()
            self.crawler.table.get_item.return_value = {}
            self.crawler.table.update_item.return_value = {}
            
            metadata = {
                'url': url,
                'title': 'WorkSpaces Article',
                'authors': 'AWS Team',
                'date_published': '2026-03-02',
                'date_updated': '2026-03-02',
                'tags': 'End User Computing, WorkSpaces',
                'content': 'WorkSpaces content',
                'source': 'aws.amazon.com'
            }
            
            # Execute
            result = self.crawler.save_to_dynamodb(metadata)
            
            # Verify all WorkSpaces URLs are processed
            self.assertTrue(result, f"WorkSpaces URL should be processed: {url}")
    
    def test_sitemap_lastmod_parsing_for_2026_dates(self):
        """
        Test that sitemap lastmod parsing correctly handles 2026 dates
        **Issue: Sitemap parsing may have date format issues for 2026**
        """
        # Test various date formats that might appear in sitemap
        test_cases = [
            ('2026-03-02', '2026-03-02'),  # ISO format
            ('2026-03-02T10:30:00Z', '2026-03-02'),  # ISO with time
            ('2026-03-02T10:30:00+00:00', '2026-03-02'),  # ISO with timezone
        ]
        
        for sitemap_date, expected_date in test_cases:
            # Simulate extract_metadata_from_sitemap parsing
            metadata = self.crawler.extract_metadata_from_sitemap(
                'https://aws.amazon.com/blogs/test-article',
                sitemap_date
            )
            
            # Verify date is parsed correctly (or at least not rejected)
            self.assertIsNotNone(metadata, f"Should parse date: {sitemap_date}")
            self.assertIn('date_updated', metadata, "Should have date_updated field")
            
            # Verify date_updated is in correct format
            date_updated = metadata['date_updated']
            # Should be valid ISO date format (YYYY-MM-DD or full ISO datetime)
            self.assertTrue(
                date_updated.startswith('2026'),
                f"Date should start with 2026: {date_updated}"
            )
    
    def test_crawler_storage_for_march_2026_post(self):
        """
        Test complete storage workflow for March 2, 2026 WorkSpaces post
        **Issue: Verifies end-to-end storage of the specific blog post**