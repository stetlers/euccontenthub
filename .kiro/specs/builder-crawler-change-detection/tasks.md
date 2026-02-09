# Implementation Plan: Builder.AWS Crawler Change Detection Fix

## Overview

This implementation plan converts the design into discrete coding tasks that fix the Builder.AWS crawler's unnecessary summary regeneration issue. The fix replaces content-based change detection with lastmod date comparison, ensuring summaries are only regenerated when articles actually update.

## Tasks

- [x] 1. Modify BuilderAWSCrawler.save_to_dynamodb() change detection logic
  - Replace content comparison with lastmod date comparison
  - Update the comparison logic to use `date_updated` field instead of `content` field
  - Update log messages to show lastmod dates and change status
  - Preserve all existing logic for summary clearing and counter increments
  - _Requirements: 1.3, 3.1, 3.2, 3.3_

- [x] 1.1 Write property test for change detection logic
  - **Property 3: Change Detection Based on Lastmod Comparison**
  - **Validates: Requirements 3.1, 3.2, 3.3**
  - Generate random pairs of (old_lastmod, new_lastmod) dates
  - Test that content_changed = True when dates differ
  - Test that content_changed = False when dates match
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 1.2 Write unit tests for change detection scenarios
  - Test unchanged article (same lastmod) preserves summary
  - Test changed article (different lastmod) clears summary
  - Test new article (no existing record) creates with lastmod
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 2. Add backward compatibility for legacy data
  - Ensure `get('date_updated', '')` returns empty string for missing field
  - Verify empty string comparison with new lastmod marks as changed
  - Test that legacy posts get date_updated field added
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 2.1 Write property test for backward compatibility
  - **Property 7: Backward Compatibility with Legacy Data**
  - **Validates: Requirements 6.1, 6.2, 6.3**
  - Generate random articles without date_updated field
  - Verify they're marked as changed
  - Verify date_updated field is added
  - Verify no errors occur
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 2.2 Write unit test for missing lastmod edge case
  - Test sitemap entry without lastmod element
  - Verify fallback to current timestamp
  - Verify warning is logged
  - _Requirements: 2.3_

- [x] 3. Verify static content template
  - Review extract_metadata_from_sitemap() method
  - Confirm content template contains no variable elements
  - Ensure template is: "Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights."
  - _Requirements: 1.1, 1.2_

- [x] 3.1 Write property test for static content template
  - **Property 1: Static Content Template Consistency**
  - **Validates: Requirements 1.1, 1.2**
  - Generate random article URLs
  - Call extract_metadata_from_sitemap() multiple times
  - Verify content field is identical across calls
  - _Requirements: 1.1, 1.2_

- [x] 4. Verify summary preservation logic
  - Review DynamoDB update expressions in save_to_dynamodb()
  - Confirm unchanged articles don't modify summary field
  - Confirm changed articles clear summary field (set to empty string)
  - Verify posts_needing_summaries counter logic
  - _Requirements: 3.4, 3.5, 4.1, 4.2, 4.3, 4.4_

- [x] 4.1 Write property test for summary preservation
  - **Property 4: Summary Field Preservation for Unchanged Articles**
  - **Validates: Requirements 3.4, 4.1, 4.2**
  - Generate random articles with existing summaries
  - Simulate unchanged crawl (same lastmod)
  - Verify summary field unchanged
  - Verify posts_needing_summaries doesn't increment
  - _Requirements: 3.4, 4.1, 4.2_

- [x] 4.2 Write property test for summary clearing
  - **Property 5: Summary Field Clearing for Changed Articles**
  - **Validates: Requirements 3.5, 4.3, 4.4**
  - Generate random articles with existing summaries
  - Simulate changed crawl (different lastmod)
  - Verify summary field set to empty string
  - Verify posts_needing_summaries increments
  - _Requirements: 3.5, 4.3, 4.4_

- [x] 5. Add counter tracking for changed/unchanged articles
  - Add `posts_changed` counter to BuilderAWSCrawler.__init__()
  - Add `posts_unchanged` counter to BuilderAWSCrawler.__init__()
  - Increment posts_changed when content_changed is True
  - Increment posts_unchanged when content_changed is False
  - Update crawl_all_posts() return dict to include new counters
  - Update lambda_handler() summary output to show new counters
  - _Requirements: 5.2, 5.3, 5.4_

- [x] 5.1 Write property test for counter accuracy
  - **Property 6: Accurate Counter Reporting**
  - **Validates: Requirements 5.2, 5.3, 5.4, 5.5**
  - Generate random crawl scenarios
  - Verify posts_processed = posts_created + posts_updated
  - Verify posts_needing_summaries = posts_created + posts_changed
  - Verify all counters are non-negative
  - _Requirements: 5.2, 5.3, 5.4, 5.5_

- [x] 6. Update logging messages
  - Update "Content changed" message to "Article updated (lastmod changed: {old} → {new})"
  - Update "Article unchanged" message to "Article unchanged (lastmod: {date})"
  - Add log message for new articles: "New article (lastmod: {date})"
  - Ensure all log messages include relevant lastmod information
  - _Requirements: 5.1_

- [x] 7. Checkpoint - Run all tests and verify functionality
  - Run all property tests (minimum 100 iterations each)
  - Run all unit tests
  - Verify all tests pass
  - Check test coverage for save_to_dynamodb() method
  - Ask the user if questions arise

- [x] 8. Deploy to staging environment
  - Use deployment script: `python deploy_lambda.py crawler staging`
  - Verify deployment successful
  - Check CloudWatch logs for staging Lambda
  - _Requirements: 7.1_

- [x] 9. Test in staging environment
  - Trigger first crawl run in staging
  - Verify posts are created/updated
  - Record posts_needing_summaries count
  - Wait for summaries to generate
  - Trigger second crawl run immediately
  - Verify posts_needing_summaries = 0 on second run
  - Verify CloudWatch logs show "Article unchanged" messages
  - Verify existing summaries preserved in DynamoDB
  - _Requirements: 7.2, 7.3, 7.4_

- [x] 10. Final checkpoint - Verify staging success
  - Confirm all staging tests passed
  - Review CloudWatch logs for any errors
  - Verify Bedrock API usage decreased
  - Document any issues found
  - Ask the user if ready to deploy to production

- [x] 11. Deploy to production environment
  - Use deployment script: `python deploy_lambda.py crawler production`
  - Verify deployment successful
  - Monitor first production crawl closely
  - Check CloudWatch logs for production Lambda
  - Verify Bedrock API usage decreases
  - _Requirements: 7.5_

## Notes

- All tasks are required for comprehensive testing and validation
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and edge cases
- Staging deployment and testing is critical before production
- The fix is minimal - only changes the comparison logic in save_to_dynamodb()
- All other crawler functionality remains unchanged
