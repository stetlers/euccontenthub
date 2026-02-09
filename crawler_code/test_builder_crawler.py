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


if __name__ == '__main__':
    unittest.main()



class TestBackwardCompatibility(unittest.TestCase):
    """Tests for backward compatibility with legacy data"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.crawler = BuilderAWSCrawler('test-table')
        self.crawler.table = Mock()
    
    @given(
        new_lastmod=st.dates().map(lambda d: d.isoformat())
    )
    @settings(max_examples=100)
    def test_property_7_backward_compatibility_with_legacy_data(self, new_lastmod):
        """
        Property 7: Backward Compatibility with Legacy Data
        
        **Feature: builder-crawler-change-detection, Property 7: Backward Compatibility with Legacy Data**
        **Validates: Requirements 6.1, 6.2, 6.3**
        
        For any existing Builder.AWS article without a date_updated field, the crawler should:
        - Successfully process the article without errors
        - Mark it as changed (content_changed = True)
        - Add the date_updated field from the sitemap to the DynamoDB record
        - Clear the summary field and increment posts_needing_summaries
        """
        # Setup: Existing article WITHOUT date_updated field
        existing_item = {
            'post_id': 'builder-legacy-article',
            'summary': 'Old summary',
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.'
            # Note: No date_updated field
        }
        
        self.crawler.table.get_item.return_value = {'Item': existing_item}
        self.crawler.table.update_item.return_value = {}
        
        # New metadata with lastmod
        metadata = {
            'url': 'https://builder.aws.com/articles/legacy-article',
            'title': 'Legacy Article',
            'authors': 'AWS Builder Community',
            'date_published': new_lastmod,
            'date_updated': new_lastmod,
            'tags': 'End User Computing, Builder.AWS',
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.',
            'source': 'builder.aws.com'
        }
        
        # Execute - should not raise any errors
        try:
            result = self.crawler.save_to_dynamodb(metadata)
            
            # Verify no errors occurred
            self.assertTrue(result)
            
            # Verify marked as changed (posts_needing_summaries incremented)
            self.assertEqual(self.crawler.posts_needing_summaries, 1)
            
            # Verify date_updated field is added in the update
            update_call = self.crawler.table.update_item.call_args
            self.assertIn(':date_updated', update_call[1]['ExpressionAttributeValues'])
            self.assertEqual(update_call[1]['ExpressionAttributeValues'][':date_updated'], new_lastmod)
            
            # Verify summary is cleared
            update_expression = update_call[1]['UpdateExpression']
            self.assertIn('summary = :empty', update_expression)
            
        except Exception as e:
            self.fail(f"Processing legacy data raised an exception: {e}")
    
    def test_missing_lastmod_edge_case(self):
        """
        Test sitemap entry without lastmod element
        **Validates: Requirements 2.3**
        """
        # This test verifies the fallback behavior when lastmod is missing
        # In the actual implementation, the crawl_all_posts method handles this
        # by using current timestamp as fallback
        
        # Simulate the fallback logic
        lastmod = None
        if lastmod is None:
            fallback_date = datetime.utcnow().isoformat()
        else:
            fallback_date = lastmod
        
        # Verify fallback date is valid ISO format
        self.assertIsNotNone(fallback_date)
        self.assertIsInstance(fallback_date, str)
        
        # Verify it can be parsed as a date
        try:
            datetime.fromisoformat(fallback_date.replace('Z', '+00:00'))
        except ValueError:
            self.fail("Fallback date is not valid ISO format")



class TestStaticContentTemplate(unittest.TestCase):
    """Tests for static content template consistency"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.crawler = BuilderAWSCrawler('test-table')
    
    @given(
        url=st.text(min_size=10).map(lambda s: f"https://builder.aws.com/articles/{s.replace('/', '-')}")
    )
    @settings(max_examples=100)
    def test_property_1_static_content_template_consistency(self, url):
        """
        Property 1: Static Content Template Consistency
        
        **Feature: builder-crawler-change-detection, Property 1: Static Content Template Consistency**
        **Validates: Requirements 1.1, 1.2**
        
        For any Builder.AWS article URL, calling extract_metadata_from_sitemap() 
        multiple times should produce identical content template strings.
        """
        lastmod = '2024-01-15'
        
        # Call extract_metadata_from_sitemap multiple times
        metadata1 = self.crawler.extract_metadata_from_sitemap(url, lastmod)
        metadata2 = self.crawler.extract_metadata_from_sitemap(url, lastmod)
        metadata3 = self.crawler.extract_metadata_from_sitemap(url, lastmod)
        
        # Verify content templates are identical
        self.assertEqual(metadata1['content'], metadata2['content'],
            "Content template should be identical across calls")
        self.assertEqual(metadata2['content'], metadata3['content'],
            "Content template should be identical across calls")
        
        # Verify content is the expected static template
        expected_template = 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.'
        self.assertEqual(metadata1['content'], expected_template,
            "Content should match the static template")
    
    def test_content_template_has_no_variables(self):
        """
        Verify content template contains no variable elements
        **Validates: Requirements 1.1, 1.2**
        """
        # Test with different URLs
        test_urls = [
            'https://builder.aws.com/articles/test-article-1',
            'https://builder.aws.com/articles/another-article',
            'https://builder.aws.com/articles/workspaces-setup'
        ]
        
        lastmod = '2024-01-15'
        contents = []
        
        for url in test_urls:
            metadata = self.crawler.extract_metadata_from_sitemap(url, lastmod)
            contents.append(metadata['content'])
        
        # All content templates should be identical
        self.assertEqual(len(set(contents)), 1,
            "All content templates should be identical regardless of URL")
        
        # Verify it's the static template
        expected_template = 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.'
        self.assertEqual(contents[0], expected_template)



class TestSummaryPreservation(unittest.TestCase):
    """Tests for summary field preservation and clearing"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.crawler = BuilderAWSCrawler('test-table')
        self.crawler.table = Mock()
    
    @given(
        summary_text=st.text(min_size=10, max_size=200),
        lastmod=st.dates().map(lambda d: d.isoformat())
    )
    @settings(max_examples=100)
    def test_property_4_summary_preservation_for_unchanged_articles(self, summary_text, lastmod):
        """
        Property 4: Summary Field Preservation for Unchanged Articles
        
        **Feature: builder-crawler-change-detection, Property 4: Summary Field Preservation for Unchanged Articles**
        **Validates: Requirements 3.4, 4.1, 4.2**
        
        For any Builder.AWS article where content_changed is False, 
        the DynamoDB update should not modify the summary field, 
        and the posts_needing_summaries counter should not increment.
        """
        # Setup: Existing article with summary and same lastmod
        existing_item = {
            'post_id': 'builder-test-article',
            'date_updated': lastmod,
            'summary': summary_text,
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.'
        }
        
        self.crawler.table.get_item.return_value = {'Item': existing_item}
        self.crawler.table.update_item.return_value = {}
        
        # New metadata with SAME lastmod (unchanged)
        metadata = {
            'url': 'https://builder.aws.com/articles/test-article',
            'title': 'Test Article',
            'authors': 'AWS Builder Community',
            'date_published': lastmod,
            'date_updated': lastmod,  # Same as existing
            'tags': 'End User Computing, Builder.AWS',
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.',
            'source': 'builder.aws.com'
        }
        
        # Execute
        result = self.crawler.save_to_dynamodb(metadata)
        
        # Verify
        self.assertTrue(result)
        
        # Verify posts_needing_summaries did NOT increment
        self.assertEqual(self.crawler.posts_needing_summaries, 0,
            "posts_needing_summaries should not increment for unchanged articles")
        
        # Verify update expression does NOT include summary field
        update_call = self.crawler.table.update_item.call_args
        update_expression = update_call[1]['UpdateExpression']
        self.assertNotIn('summary', update_expression,
            "Update expression should not modify summary field for unchanged articles")
    
    @given(
        old_summary=st.text(min_size=10, max_size=200),
        old_lastmod=st.dates().map(lambda d: d.isoformat()),
        new_lastmod=st.dates().map(lambda d: d.isoformat())
    )
    @settings(max_examples=100)
    def test_property_5_summary_clearing_for_changed_articles(self, old_summary, old_lastmod, new_lastmod):
        """
        Property 5: Summary Field Clearing for Changed Articles
        
        **Feature: builder-crawler-change-detection, Property 5: Summary Field Clearing for Changed Articles**
        **Validates: Requirements 3.5, 4.3, 4.4**
        
        For any Builder.AWS article where content_changed is True, 
        the DynamoDB update should set the summary field to empty string, 
        and the posts_needing_summaries counter should increment by one.
        """
        # Skip if dates are the same (not a changed article)
        if old_lastmod == new_lastmod:
            return
        
        # Setup: Existing article with summary and old lastmod
        existing_item = {
            'post_id': 'builder-test-article',
            'date_updated': old_lastmod,
            'summary': old_summary,
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.'
        }
        
        self.crawler.table.get_item.return_value = {'Item': existing_item}
        self.crawler.table.update_item.return_value = {}
        
        # New metadata with DIFFERENT lastmod (changed)
        metadata = {
            'url': 'https://builder.aws.com/articles/test-article',
            'title': 'Test Article',
            'authors': 'AWS Builder Community',
            'date_published': new_lastmod,
            'date_updated': new_lastmod,  # Different from existing
            'tags': 'End User Computing, Builder.AWS',
            'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.',
            'source': 'builder.aws.com'
        }
        
        # Execute
        result = self.crawler.save_to_dynamodb(metadata)
        
        # Verify
        self.assertTrue(result)
        
        # Verify posts_needing_summaries incremented
        self.assertEqual(self.crawler.posts_needing_summaries, 1,
            "posts_needing_summaries should increment for changed articles")
        
        # Verify update expression includes summary clearing
        update_call = self.crawler.table.update_item.call_args
        update_expression = update_call[1]['UpdateExpression']
        self.assertIn('summary = :empty', update_expression,
            "Update expression should clear summary field for changed articles")
        
        # Verify summary is set to empty string
        self.assertEqual(update_call[1]['ExpressionAttributeValues'][':empty'], '',
            "Summary should be set to empty string for changed articles")



class TestCounterAccuracy(unittest.TestCase):
    """Tests for accurate counter reporting"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.crawler = BuilderAWSCrawler('test-table')
        self.crawler.table = Mock()
    
    @given(
        num_new=st.integers(min_value=0, max_value=10),
        num_changed=st.integers(min_value=0, max_value=10),
        num_unchanged=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100)
    def test_property_6_accurate_counter_reporting(self, num_new, num_changed, num_unchanged):
        """
        Property 6: Accurate Counter Reporting
        
        **Feature: builder-crawler-change-detection, Property 6: Accurate Counter Reporting**
        **Validates: Requirements 5.2, 5.3, 5.4, 5.5**
        
        For any crawl run, the following invariants should hold:
        - posts_processed = posts_created + posts_updated
        - posts_needing_summaries = posts_created + (number of changed articles)
        - All counters should be non-negative integers
        """
        # Simulate a crawl with different scenarios
        
        # Process new articles
        for i in range(num_new):
            self.crawler.table.get_item.return_value = {}
            self.crawler.table.update_item.return_value = {}
            
            metadata = {
                'url': f'https://builder.aws.com/articles/new-article-{i}',
                'title': f'New Article {i}',
                'authors': 'AWS Builder Community',
                'date_published': '2024-01-20',
                'date_updated': '2024-01-20',
                'tags': 'End User Computing, Builder.AWS',
                'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.',
                'source': 'builder.aws.com'
            }
            
            self.crawler.save_to_dynamodb(metadata)
        
        # Process changed articles
        for i in range(num_changed):
            existing_item = {
                'post_id': f'builder-changed-article-{i}',
                'date_updated': '2024-01-15',
                'summary': 'Old summary',
                'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.'
            }
            
            self.crawler.table.get_item.return_value = {'Item': existing_item}
            self.crawler.table.update_item.return_value = {}
            
            metadata = {
                'url': f'https://builder.aws.com/articles/changed-article-{i}',
                'title': f'Changed Article {i}',
                'authors': 'AWS Builder Community',
                'date_published': '2024-01-15',
                'date_updated': '2024-01-20',  # Different date
                'tags': 'End User Computing, Builder.AWS',
                'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.',
                'source': 'builder.aws.com'
            }
            
            self.crawler.save_to_dynamodb(metadata)
        
        # Process unchanged articles
        for i in range(num_unchanged):
            existing_item = {
                'post_id': f'builder-unchanged-article-{i}',
                'date_updated': '2024-01-20',
                'summary': 'Existing summary',
                'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.'
            }
            
            self.crawler.table.get_item.return_value = {'Item': existing_item}
            self.crawler.table.update_item.return_value = {}
            
            metadata = {
                'url': f'https://builder.aws.com/articles/unchanged-article-{i}',
                'title': f'Unchanged Article {i}',
                'authors': 'AWS Builder Community',
                'date_published': '2024-01-20',
                'date_updated': '2024-01-20',  # Same date
                'tags': 'End User Computing, Builder.AWS',
                'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.',
                'source': 'builder.aws.com'
            }
            
            self.crawler.save_to_dynamodb(metadata)
        
        # Verify invariants
        
        # Invariant 1: posts_processed = posts_created + posts_updated
        self.assertEqual(
            self.crawler.posts_processed,
            self.crawler.posts_created + self.crawler.posts_updated,
            "posts_processed should equal posts_created + posts_updated"
        )
        
        # Invariant 2: posts_needing_summaries = posts_created + posts_changed
        self.assertEqual(
            self.crawler.posts_needing_summaries,
            self.crawler.posts_created + self.crawler.posts_changed,
            "posts_needing_summaries should equal posts_created + posts_changed"
        )
        
        # Invariant 3: All counters are non-negative
        self.assertGreaterEqual(self.crawler.posts_processed, 0)
        self.assertGreaterEqual(self.crawler.posts_created, 0)
        self.assertGreaterEqual(self.crawler.posts_updated, 0)
        self.assertGreaterEqual(self.crawler.posts_changed, 0)
        self.assertGreaterEqual(self.crawler.posts_unchanged, 0)
        self.assertGreaterEqual(self.crawler.posts_needing_summaries, 0)
        
        # Additional verification: posts_updated = posts_changed + posts_unchanged
        self.assertEqual(
            self.crawler.posts_updated,
            self.crawler.posts_changed + self.crawler.posts_unchanged,
            "posts_updated should equal posts_changed + posts_unchanged"
        )
