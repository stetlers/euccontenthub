# Implementation Plan: Amazon Email Verification

## Overview

This implementation plan breaks down the Amazon Email Verification feature into discrete, incremental tasks. The approach follows a layered implementation strategy: backend infrastructure first (Lambda functions, DynamoDB), then API integration, and finally frontend UI. Each task builds on previous work and includes testing to validate functionality early.

## Tasks

- [x] 1. Set up DynamoDB table and IAM roles
  - Create `email-verification-tokens` table in production (already exists in staging)
  - Enable TTL on `ttl` attribute
  - Create IAM role for Email Verification Lambda with permissions:
    - DynamoDB: PutItem, GetItem, UpdateItem on both token and user profile tables
    - SES: SendEmail permission
    - CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents
  - Create IAM role for Verification Checker Lambda with permissions:
    - DynamoDB: Scan, UpdateItem on user profile tables
    - SES: SendEmail permission
    - CloudWatch Logs permissions
  - _Requirements: 2.2, 9.1, 9.3, 10.1_

- [ ] 2. Implement Email Verification Lambda core functions
  - [ ] 2.1 Implement token generation and validation functions
    - Write `generate_verification_token()` using secrets.token_urlsafe(32)
    - Write `validate_amazon_email(email)` to check @amazon.com domain
    - Write `validate_token(token)` to check existence, expiration, and consumed status
    - Write `mark_token_consumed(token)` to update token state
    - _Requirements: 1.1, 2.1, 2.4, 3.1_
  
  - [ ] 2.2 Write property test for token generation
    - **Property 2: Token Uniqueness and Entropy**
    - **Validates: Requirements 2.1**
  
  - [ ] 2.3 Write property test for email validation
    - **Property 1: Email Domain Validation**
    - **Validates: Requirements 1.1, 1.2**
  
  - [ ] 2.4 Write property test for token validation
    - **Property 5: Token Validation Rejects Invalid Tokens**
    - **Validates: Requirements 3.1, 3.4**

  - [ ] 2.5 Implement DynamoDB token storage functions
    - Write `store_verification_token(user_id, email, token)` to save token with TTL
    - Write `get_token_data(token)` to retrieve token information
    - Implement environment-aware table name construction using TABLE_SUFFIX
    - _Requirements: 2.2, 9.1, 9.4_
  
  - [ ] 2.6 Write property test for token TTL
    - **Property 3: Token TTL Consistency**
    - **Validates: Requirements 2.2**
  
  - [ ] 2.7 Write property test for environment table names
    - **Property 16: Environment Determines Table Name Suffix**
    - **Validates: Requirements 9.1, 9.3, 9.4**

- [ ] 3. Implement email sending functionality
  - [ ] 3.1 Create verification email template
    - Design HTML email template with verification link
    - Include 1-hour expiration notice
    - Add branding and clear call-to-action button
    - _Requirements: 1.4_
  
  - [ ] 3.2 Implement SES email sending function
    - Write `send_verification_email(email, token, frontend_url)` using boto3 SES client
    - Construct verification link with token parameter
    - Handle SES errors with retry logic
    - Use environment-aware sender email address
    - _Requirements: 1.4, 9.2_
  
  - [ ] 3.3 Write property test for sender email configuration
    - **Property 17: Environment Determines Sender Email**
    - **Validates: Requirements 9.2**
  
  - [ ] 3.4 Create reminder email template
    - Design HTML email template for expiration reminders
    - Include expiration date and re-verification link
    - _Requirements: 6.2_
  
  - [ ] 3.5 Write unit tests for email sending
    - Test SES integration with mocked boto3 client
    - Test error handling for SES failures
    - Test email content includes required information
    - _Requirements: 1.4, 6.2_

- [ ] 4. Implement verification confirmation logic
  - [ ] 4.1 Write user profile update function
    - Implement `update_user_verification(user_id, email)` to set verification status
    - Calculate 90-day expiration date
    - Update amazon_verified, amazon_verified_at, amazon_verified_until fields
    - _Requirements: 3.2, 5.1_
  
  - [ ] 4.2 Write property test for expiration date calculation
    - **Property 6: Verification Sets 90-Day Expiration**
    - **Validates: Requirements 3.2, 5.1**
  
  - [ ] 4.3 Implement token consumption logic
    - Update `mark_token_consumed()` to set consumed flag and timestamp
    - Add validation to reject consumed tokens
    - _Requirements: 2.4, 2.5_
  
  - [ ] 4.4 Write property test for token consumption
    - **Property 4: Token Consumption Prevents Reuse**
    - **Validates: Requirements 2.4, 2.5, 3.3**

- [ ] 5. Complete Email Verification Lambda handler
  - [ ] 5.1 Implement POST /verify-email handler
    - Parse request body for email parameter
    - Validate email domain
    - Generate and store token
    - Send verification email
    - Return success response
    - _Requirements: 1.1, 1.3, 1.4, 1.5_
  
  - [ ] 5.2 Implement GET /verify-email handler
    - Parse token from query parameters
    - Validate token
    - Update user profile if valid
    - Mark token as consumed
    - Return redirect response or error page
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [ ] 5.3 Implement error handling for all endpoints
    - Add try-catch blocks with appropriate error responses
    - Return proper HTTP status codes (400, 403, 404, 409, 410, 500)
    - Log errors with context for debugging
    - _Requirements: All error handling requirements_
  
  - [ ] 5.4 Write unit tests for Lambda handlers
    - Test POST endpoint with valid and invalid emails
    - Test GET endpoint with valid, expired, and consumed tokens
    - Test error responses and status codes
    - _Requirements: 1.1, 1.2, 3.1, 3.4_

- [x] 6. Deploy and test Email Verification Lambda in staging
  - Deploy Lambda function to staging environment
  - Configure environment variables (TABLE_SUFFIX=-staging, SENDER_EMAIL, FRONTEND_URL)
  - Test POST endpoint with @amazon.com email
  - Verify email delivery via SES
  - Test GET endpoint with valid token
  - Verify user profile updated correctly
  - Test error cases (invalid email, expired token, consumed token)
  - _Requirements: 9.1, 9.2, 9.4_
  - ✅ **COMPLETED**: Lambda deployed, email sent successfully, profile verified

- [x] 7. Checkpoint - Ensure verification Lambda works in staging
  - Ensure all tests pass, ask the user if questions arise.
  - ✅ **COMPLETED**: Verification working end-to-end

- [ ] 8. Implement Verification Checker Lambda
  - [ ] 8.1 Implement expiration detection function
    - Write `scan_user_profiles()` to get all verified users
    - Write `is_verification_expired(profile)` to check expiration date
    - Write `revoke_verification(user_id)` to remove admin status
    - _Requirements: 5.2, 5.3_
  
  - [ ] 8.2 Write property test for expiration detection
    - **Property 8: Expiration Revokes Admin Status**
    - **Validates: Requirements 5.2, 5.3**
  
  - [ ] 8.3 Implement reminder detection function
    - Write `needs_reminder(profile)` to check if expiration is 7 days away
    - Write `send_reminder_email(email, expiration_date)` using SES
    - Write `record_reminder_sent(user_id)` to update profile
    - _Requirements: 6.1, 6.3_
  
  - [ ] 8.4 Write property test for reminder timing
    - **Property 10: Reminder Timing Accuracy**
    - **Validates: Requirements 6.1**
  
  - [ ] 8.5 Write property test for reminder deduplication
    - **Property 11: Reminder Prevents Duplicates**
    - **Validates: Requirements 6.3**
  
  - [ ] 8.6 Implement Lambda handler
    - Scan all user profiles
    - Check for expired verifications and revoke
    - Check for upcoming expirations and send reminders
    - Log all actions for audit
    - _Requirements: 5.2, 6.1_
  
  - [ ] 8.7 Write unit tests for Verification Checker
    - Test expiration detection with various dates
    - Test reminder sending logic
    - Test batch processing of multiple users
    - _Requirements: 5.2, 6.1, 6.3_

- [ ] 9. Deploy and test Verification Checker Lambda in staging
  - Deploy Lambda function to staging environment
  - Configure environment variables (TABLE_SUFFIX=-staging, SENDER_EMAIL)
  - Create EventBridge rule for daily execution (disabled initially)
  - Manually invoke Lambda to test
  - Verify expired verifications are revoked
  - Verify reminder emails sent for 7-day expirations
  - _Requirements: 9.1, 9.2_

- [ ] 10. Checkpoint - Ensure checker Lambda works in staging
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Update API Lambda with verification endpoints
  - [x] 11.1 Add /verify-email endpoint routing
    - Add POST and GET routes in lambda_handler()
    - Route POST to handle_verify_email_post()
    - Route GET to handle_verify_email_get()
    - _Requirements: 1.1, 3.1_
  
  - [x] 11.2 Implement POST handler
    - Extract user_id from JWT token
    - Validate email parameter
    - Invoke Email Verification Lambda asynchronously
    - Return success response with CORS headers
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [x] 11.3 Implement GET handler
    - Extract token from query parameters
    - Invoke Email Verification Lambda synchronously
    - Return redirect response or error page
    - _Requirements: 3.1, 3.5_
  
  - [x] 11.4 Write unit tests for new endpoints
    - Test POST with authenticated user
    - Test POST with invalid email
    - Test GET with valid and invalid tokens
    - _Requirements: 1.1, 1.2, 3.1_

- [ ] 12. Implement admin authorization helper
  - [ ] 12.1 Create check_admin_authorization function
    - Query user profile from DynamoDB
    - Check amazon_verified field is true
    - Check amazon_verified_until is in future
    - Check amazon_verification_revoked is false
    - Return boolean authorization result
    - _Requirements: 7.1, 7.4_
  
  - [ ] 12.2 Write property test for authorization logic
    - **Property 13: Admin Actions Require Verification Check**
    - **Validates: Requirements 7.1, 7.4**
  
  - [ ] 12.3 Write property test for valid verification
    - **Property 14: Valid Verification Allows Admin Actions**
    - **Validates: Requirements 7.3**
  
  - [ ] 12.4 Write property test for unauthorized rejection
    - **Property 9: Unauthorized Users Cannot Perform Admin Actions**
    - **Validates: Requirements 5.4, 7.2, 8.3**
  
  - [ ] 12.5 Create @require_admin decorator
    - Implement decorator that calls check_admin_authorization()
    - Return 403 Forbidden if authorization fails
    - Include descriptive error message
    - _Requirements: 7.2, 7.5_
  
  - [ ] 12.6 Apply decorator to admin endpoints
    - Add @require_admin to delete comment endpoint
    - Add @require_admin to any other admin-only endpoints
    - _Requirements: 7.1_
  
  - [ ] 12.7 Write unit tests for admin authorization
    - Test with valid verification (should allow)
    - Test with expired verification (should reject)
    - Test with no verification (should reject)
    - Test with revoked verification (should reject)
    - _Requirements: 7.2, 7.3, 7.4_

- [ ] 13. Implement manual revocation functionality
  - [ ] 13.1 Add /revoke-verification endpoint
    - Create POST endpoint for super admins
    - Validate requester is super admin
    - Extract target user_id and reason from body
    - _Requirements: 8.1_
  
  - [ ] 13.2 Implement revocation logic
    - Write `revoke_user_verification(user_id, reason)` function
    - Update profile with revoked flag, timestamp, and reason
    - Send notification email to affected user
    - Log revocation for audit
    - _Requirements: 8.1, 8.2, 8.4, 8.5_
  
  - [ ] 13.3 Write property test for revocation
    - **Property 15: Revocation Updates Profile State**
    - **Validates: Requirements 8.1, 8.2**
  
  - [ ] 13.4 Write unit tests for revocation
    - Test revocation updates profile correctly
    - Test notification email sent
    - Test audit logging
    - _Requirements: 8.1, 8.2, 8.4, 8.5_

- [ ] 14. Implement user deletion cascade
  - [ ] 14.1 Update delete user profile function
    - Add logic to delete verification tokens for user
    - Query email-verification-tokens table by user_id (requires GSI)
    - Delete all matching tokens
    - _Requirements: 10.3_
  
  - [ ] 14.2 Write property test for cascade deletion
    - **Property 18: User Deletion Cascades to Verification Data**
    - **Validates: Requirements 10.3**
  
  - [ ] 14.3 Write unit tests for cascade deletion
    - Test user deletion removes tokens
    - Test user deletion removes verification status
    - _Requirements: 10.3_

- [ ] 15. Deploy and test API Lambda in staging
  - Deploy updated API Lambda to staging
  - Test POST /verify-email endpoint
  - Test GET /verify-email endpoint
  - Test admin authorization on protected endpoints
  - Test revocation endpoint
  - Verify CORS headers on all responses
  - _Requirements: 9.1, 9.4_

- [ ] 16. Checkpoint - Ensure API Lambda works in staging
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Implement frontend profile page updates
  - [x] 17.1 Add verification status display HTML
    - Add verification-status div to profile page
    - Create templates for verified, expired, and unverified states
    - Add "Amazon Verified ✓" badge styling
    - _Requirements: 4.1, 4.3, 4.4_
    - ✅ **COMPLETED**: Verification UI added to profile.js
  
  - [x] 17.2 Add verification form HTML
    - Create email input field
    - Add "Send Verification Email" button
    - Add "Resend Email" button for pending state
    - _Requirements: 1.1, 4.5_
    - ✅ **COMPLETED**: Form added to profile modal
  
  - [x] 17.3 Implement displayVerificationStatus function
    - Check profile.amazon_verified and profile.amazon_verified_until
    - Render appropriate UI based on verification state
    - Format expiration date in human-readable format
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
    - ✅ **COMPLETED**: Status display working
  
  - [ ] 17.4 Write property test for date formatting
    - **Property 7: Date Formatting Consistency**
    - **Validates: Requirements 4.2**
  
  - [x] 17.5 Implement submitVerification function
    - Validate email format client-side
    - Send POST request to /verify-email endpoint
    - Handle success and error responses
    - Display notification messages
    - _Requirements: 1.1, 1.2, 1.5_
    - ✅ **COMPLETED**: Email sending working
  
  - [ ] 17.6 Write unit tests for verification form
    - Test email validation
    - Test API call with valid email
    - Test error handling
    - Test notification display
    - _Requirements: 1.1, 1.2, 1.5_

- [x] 18. Add verification styles to CSS
  - [x] 18.1 Create verification badge styles
    - Style .verification-badge.verified (green)
    - Style .verification-badge.expired (red)
    - Style .verification-badge.pending (yellow)
    - Add badge icon and expiration date styles
    - _Requirements: 4.1, 4.3_
    - ✅ **COMPLETED**: Styles added to styles.css
  
  - [x] 18.2 Create verification form styles
    - Style email input field
    - Style verification buttons
    - Add responsive design for mobile
    - Ensure dark mode compatibility
    - _Requirements: 1.1_
    - ✅ **COMPLETED**: Form styles added

- [x] 19. Implement verification confirmation page
  - [x] 19.1 Create verification result handler
    - Parse token from URL query parameters
    - Display loading state while verifying
    - Show success message and redirect to profile
    - Show error message for invalid tokens
    - _Requirements: 3.4, 3.5_
    - ✅ **COMPLETED**: checkVerificationCallback() added to profile.js
  
  - [ ] 19.2 Write unit tests for confirmation page
    - Test success flow
    - Test error handling for invalid tokens
    - Test redirect behavior
    - _Requirements: 3.4, 3.5_

- [x] 20. Deploy and test frontend in staging
  - Deploy frontend to staging S3 bucket
  - Invalidate CloudFront cache
  - Test verification form submission
  - Test email receipt and link clicking
  - Test verification status display
  - Test all verification states (verified, expired, unverified)
  - Test responsive design on mobile
  - _Requirements: 9.1, 9.4_
  - ✅ **COMPLETED**: Frontend deployed and tested successfully

- [x] 21. Checkpoint - Ensure frontend works in staging
  - Ensure all tests pass, ask the user if questions arise.
  - ✅ **COMPLETED**: End-to-end verification working!

- [ ] 22. End-to-end testing in staging
  - [ ] 22.1 Test complete verification flow
    - Create new user account
    - Enter @amazon.com email
    - Receive verification email
    - Click verification link
    - Verify badge appears in profile
    - Verify expiration date is 90 days in future
    - _Requirements: 1.1, 1.3, 1.4, 3.1, 3.2, 4.1_
  
  - [ ] 22.2 Test error cases
    - Try non-@amazon.com email (should reject)
    - Try expired token (should show error)
    - Try consumed token (should show error)
    - Try malformed token (should show error)
    - _Requirements: 1.2, 2.5, 3.4_
  
  - [ ] 22.3 Test admin authorization
    - Perform admin action with valid verification (should succeed)
    - Manually expire verification in DynamoDB
    - Perform admin action with expired verification (should reject)
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [ ] 22.4 Test expiration and reminders
    - Manually set verification to expire in 7 days
    - Run Verification Checker Lambda
    - Verify reminder email received
    - Manually set verification to expired
    - Run Verification Checker Lambda
    - Verify admin actions rejected
    - _Requirements: 5.2, 5.3, 6.1_
  
  - [ ] 22.5 Test re-verification
    - Re-verify with same email
    - Verify expiration extended by 90 days
    - Verify admin access restored
    - _Requirements: 6.4_
  
  - [ ] 22.6 Test revocation
    - Manually revoke verification
    - Verify admin actions rejected
    - Verify notification email sent
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 23. Production deployment preparation
  - [ ] 23.1 Create production DynamoDB table
    - Create `email-verification-tokens` table in production
    - Enable TTL on `ttl` attribute
    - Verify table configuration matches staging
    - _Requirements: 9.3_
  
  - [ ] 23.2 Update Lambda environment variables for production
    - Set TABLE_SUFFIX to empty string
    - Set SENDER_EMAIL to production sender
    - Set FRONTEND_URL to https://awseuccontent.com
    - _Requirements: 9.3_
  
  - [ ] 23.3 Deploy Email Verification Lambda to production
    - Deploy Lambda function
    - Create production alias
    - Test with production environment variables
    - _Requirements: 9.3_
  
  - [ ] 23.4 Deploy Verification Checker Lambda to production
    - Deploy Lambda function
    - Create EventBridge rule for daily execution
    - Test manual invocation
    - _Requirements: 9.3_
  
  - [ ] 23.5 Deploy API Lambda to production
    - Deploy updated Lambda function
    - Update production alias
    - Test new endpoints
    - _Requirements: 9.3_
  
  - [ ] 23.6 Deploy frontend to production
    - Deploy to production S3 bucket
    - Invalidate CloudFront cache
    - Verify all assets loaded correctly
    - _Requirements: 9.3_

- [ ] 24. Production verification testing
  - Test complete verification flow with real @amazon.com email
  - Verify email delivery in production
  - Test admin authorization
  - Monitor CloudWatch logs for errors
  - Verify DynamoDB metrics are normal
  - _Requirements: 9.3_

- [ ] 25. Final checkpoint - Production deployment complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Staging deployment and testing happens before production
- All Lambda functions support both staging and production environments via TABLE_SUFFIX
- All test tasks are required for comprehensive quality assurance
