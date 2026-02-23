# Implementation Plan: Automated Comment Moderation System

## Overview

This implementation plan breaks down the comment moderation system into discrete coding tasks. The approach is incremental: first implement core moderation logic, then integrate with comment submission, then add frontend display logic, and finally add testing. Each task builds on previous work to ensure continuous integration.

## Tasks

- [ ] 1. Set up Bedrock client and moderation infrastructure
  - Create `moderate_comment()` function in `lambda_api/lambda_function.py`
  - Initialize Bedrock Runtime client with Claude Haiku model
  - Implement timeout mechanism using `signal.alarm()` or `threading.Timer`
  - Add error handling for Bedrock API exceptions
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 8.1, 8.2, 8.3_

- [ ] 1.1 Write property test for moderation status validity
  - **Property 1: Moderation Status Validity**
  - **Validates: Requirements 1.3, 2.1**

- [ ] 2. Implement moderation prompt and response parsing
  - Create structured moderation prompt with evaluation criteria
  - Include post context (title, tags) in prompt
  - Implement JSON response parsing from Bedrock
  - Handle malformed JSON responses gracefully
  - Add confidence score validation (0.0 to 1.0)
  - _Requirements: 1.2, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 7.4_

- [ ] 2.1 Write unit tests for spam detection
  - Test promotional language detection
  - Test repetitive text pattern detection
  - Test multiple link detection
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 2.2 Write unit tests for dangerous link detection
  - Test IP address URL detection
  - Test URL shortener detection
  - Test uncommon TLD detection
  - Test legitimate domain approval
  - _Requirements: 5.1, 5.2_

- [ ] 2.3 Write property test for link count threshold
  - **Property 7: Link Count Threshold**
  - **Validates: Requirements 4.3, 5.3**

- [ ] 2.4 Write property test for suspicious URL pattern detection
  - **Property 8: Suspicious URL Pattern Detection**
  - **Validates: Requirements 5.1**

- [ ] 2.5 Write unit tests for harassment detection
  - Test profanity detection
  - Test personal attack detection
  - Test threat detection
  - Test respectful criticism approval
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 2.6 Write unit tests for off-topic detection
  - Test unrelated topic detection
  - Test AWS-related topic approval
  - Test clarifying question approval
  - _Requirements: 7.1, 7.2, 7.3_

- [ ] 3. Integrate moderation into comment submission flow
  - Modify `add_comment()` function to call `moderate_comment()`
  - Fetch post context (title, tags) before moderation
  - Add moderation metadata to comment object (status, reason, confidence, timestamp)
  - Handle moderation errors by defaulting to 'approved'
  - Update DynamoDB comment structure with new fields
  - _Requirements: 1.1, 2.1, 2.2, 2.3_

- [ ] 3.1 Write property test for moderation precedes storage
  - **Property 2: Moderation Precedes Storage**
  - **Validates: Requirements 1.1, 2.3**

- [ ] 3.2 Write property test for flagged comments include reason
  - **Property 3: Flagged Comments Include Reason**
  - **Validates: Requirements 2.2**

- [ ] 3.3 Write unit tests for timeout handling
  - Mock slow Bedrock response
  - Verify system defaults to 'approved'
  - Verify timeout is logged
  - _Requirements: 1.4, 8.2_

- [ ] 3.4 Write unit tests for error handling
  - Mock Bedrock API errors (throttling, service unavailable)
  - Verify system defaults to 'approved'
  - Verify errors are logged
  - _Requirements: 8.3_

- [ ] 4. Checkpoint - Test moderation integration in staging
  - Deploy Lambda to staging environment
  - Submit test comments with various content types
  - Verify moderation results in DynamoDB
  - Check CloudWatch logs for errors
  - Ensure all tests pass, ask the user if questions arise

- [ ] 5. Implement comment filtering logic
  - Modify `get_comments()` function to filter by moderation status
  - Extract current user ID from JWT token (if authenticated)
  - Filter comments: show approved to all, show pending only to author
  - Handle legacy comments without moderation_status (treat as approved)
  - Update comment count to exclude pending comments
  - _Requirements: 2.4, 2.5, 3.1, 3.2, 3.5_

- [ ] 5.1 Write property test for comment filtering by viewer identity
  - **Property 4: Comment Filtering by Viewer Identity**
  - **Validates: Requirements 3.1, 3.2**

- [ ] 5.2 Write property test for public comment count accuracy
  - **Property 6: Public Comment Count Accuracy**
  - **Validates: Requirements 3.5**

- [ ] 5.3 Write property test for legacy comment compatibility
  - **Property 9: Legacy Comment Compatibility**
  - **Validates: Requirements 2.4, 2.5**

- [ ] 5.4 Write unit tests for backward compatibility
  - Create comments without moderation fields
  - Verify system doesn't crash
  - Verify comments are treated as approved
  - _Requirements: 2.4, 2.5_

- [ ] 6. Implement frontend comment display logic
  - Modify `renderComment()` function in `frontend/app.js`
  - Add logic to detect pending comments for current user
  - Add CSS classes for pending comment styling
  - Add "Pending Administrative Review" message for pending comments
  - Update comment count display to use filtered count
  - _Requirements: 3.3, 3.4, 3.5_

- [ ] 6.1 Write property test for pending comment visual distinction
  - **Property 5: Pending Comment Visual Distinction**
  - **Validates: Requirements 3.3, 3.4**

- [ ] 6.2 Write unit tests for frontend rendering
  - Test approved comment rendering
  - Test pending comment rendering for author
  - Test pending comment hiding for other users
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 7. Add CSS styling for pending comments
  - Create `.comment-pending` class in `frontend/styles.css`
  - Add orange/yellow background color
  - Add orange border-left indicator
  - Style `.pending-text` with orange text color
  - Style `.comment-status` badge with orange background
  - _Requirements: 3.3_

- [ ] 8. Checkpoint - Test end-to-end flow in staging
  - Deploy frontend to staging
  - Submit comments as authenticated user
  - Verify pending comments visible to author
  - Verify pending comments hidden from other users
  - Verify comment count excludes pending comments
  - Test with multiple users and comment types
  - Ensure all tests pass, ask the user if questions arise

- [ ] 9. Add CloudWatch monitoring and logging
  - Add custom CloudWatch metrics for moderation latency
  - Add metrics for timeout and error counts
  - Add metrics for flagged vs approved comment counts
  - Log moderation results (status, confidence, reason) without comment text
  - Log timeouts and errors with comment_id
  - _Requirements: 8.1, 8.2, 8.3_

- [ ] 9.1 Write property test for moderation performance
  - **Property 10: Moderation Performance**
  - **Validates: Requirements 8.1**

- [ ] 10. Update IAM permissions for Bedrock access
  - Add `bedrock:InvokeModel` permission to API Lambda role
  - Specify Claude Haiku model ARN in policy
  - Test permissions in staging environment
  - _Requirements: 1.5_

- [ ] 11. Integration testing and documentation
  - Run full integration test suite in staging
  - Verify all property tests pass (100+ iterations each)
  - Verify all unit tests pass
  - Update API documentation with new comment fields
  - Document moderation behavior for users
  - _Requirements: All_

- [ ] 12. Final checkpoint - Production deployment preparation
  - Review all test results
  - Verify staging environment is stable
  - Check CloudWatch metrics and logs
  - Prepare rollback plan
  - Ensure all tests pass, ask the user if questions arise

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (minimum 100 iterations each)
- Unit tests validate specific examples and edge cases
- Deploy to staging first, then production after thorough testing
- Use blue-green deployment strategy (staging → production)
- Lambda rollback is instant via alias update if issues occur
