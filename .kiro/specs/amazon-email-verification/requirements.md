# Requirements Document: Amazon Email Verification

## Introduction

This feature enables Amazon employees to verify their @amazon.com email addresses to gain administrative privileges on the EUC Content Hub platform. The system uses time-limited verification tokens sent via email, with automatic expiration and renewal reminders to ensure only current Amazon employees maintain admin access.

## Glossary

- **Verification_System**: The email verification subsystem responsible for token generation, validation, and expiration management
- **Admin_User**: A user who has successfully verified an @amazon.com email address and has current (non-expired) verification status
- **Verification_Token**: A unique, time-limited identifier used to confirm email ownership
- **Token_Store**: DynamoDB table storing verification tokens with TTL for automatic cleanup
- **Email_Service**: AWS SES service for sending verification and reminder emails
- **Verification_Status**: The current state of a user's email verification (verified, expired, pending, or none)
- **Profile_Manager**: Frontend component managing user profile display and verification UI
- **API_Gateway**: REST API endpoint handler for verification-related requests
- **Verification_Checker**: Scheduled Lambda function that monitors and manages verification expiration

## Requirements

### Requirement 1: Email Verification Initiation

**User Story:** As an Amazon employee, I want to enter my @amazon.com email address in my profile, so that I can initiate the verification process to gain admin access.

#### Acceptance Criteria

1. WHEN a user enters an email address in the profile page, THE Verification_System SHALL validate that the email ends with @amazon.com
2. WHEN a non-@amazon.com email is submitted, THE Verification_System SHALL reject the request and return a descriptive error message
3. WHEN a valid @amazon.com email is submitted, THE Verification_System SHALL generate a unique verification token with 1-hour expiration
4. WHEN a verification token is generated, THE Email_Service SHALL send a verification email to the provided address within 30 seconds
5. WHEN the verification email is sent, THE Profile_Manager SHALL display a confirmation message indicating the email was sent

### Requirement 2: Verification Token Management

**User Story:** As a system administrator, I want verification tokens to be secure and time-limited, so that unauthorized users cannot gain admin access through stolen or leaked tokens.

#### Acceptance Criteria

1. THE Verification_System SHALL generate cryptographically random tokens with at least 128 bits of entropy
2. WHEN a verification token is created, THE Token_Store SHALL store it with a 1-hour TTL (time-to-live)
3. WHEN a token expires (1 hour), THE Token_Store SHALL automatically delete it using DynamoDB TTL
4. WHEN a token is used successfully, THE Verification_System SHALL mark it as consumed to prevent reuse
5. WHEN a consumed token is submitted again, THE Verification_System SHALL reject it with an error message

### Requirement 3: Email Verification Confirmation

**User Story:** As an Amazon employee, I want to click a verification link in my email, so that I can confirm my email ownership and gain admin access.

#### Acceptance Criteria

1. WHEN a user clicks a verification link, THE Verification_System SHALL validate the token exists and is not expired
2. WHEN a valid token is submitted, THE Verification_System SHALL update the user profile with verified status and 90-day expiration date
3. WHEN verification succeeds, THE Verification_System SHALL mark the token as consumed
4. WHEN an invalid or expired token is submitted, THE Verification_System SHALL display an error page with instructions to request a new verification email
5. WHEN verification succeeds, THE Verification_System SHALL redirect the user to their profile page with a success message

### Requirement 4: Verification Status Display

**User Story:** As a verified Amazon employee, I want to see my verification status and expiration date in my profile, so that I know when I need to re-verify.

#### Acceptance Criteria

1. WHEN a user has verified status, THE Profile_Manager SHALL display an "Amazon Verified ✓" badge
2. WHEN displaying verification status, THE Profile_Manager SHALL show the expiration date in human-readable format
3. WHEN a user's verification is expired, THE Profile_Manager SHALL display "Verification Expired" with option to re-verify
4. WHEN a user has no verification, THE Profile_Manager SHALL display the email input form
5. WHEN a user has pending verification, THE Profile_Manager SHALL display "Verification Pending" with option to resend email

### Requirement 5: Verification Expiration Management

**User Story:** As a system, I want to automatically expire verifications after 90 days, so that former Amazon employees lose admin access without manual intervention.

#### Acceptance Criteria

1. WHEN a user is verified, THE Verification_System SHALL set expiration date to 90 days from verification time
2. WHEN current time exceeds expiration date, THE Verification_Checker SHALL mark the verification as expired
3. WHEN verification expires, THE Verification_System SHALL revoke admin privileges immediately
4. WHEN an expired user attempts admin actions, THE API_Gateway SHALL reject the request with 403 Forbidden status
5. THE Verification_Checker SHALL run daily to check and expire verifications

### Requirement 6: Expiration Reminder Notifications

**User Story:** As a verified Amazon employee, I want to receive a reminder email 7 days before my verification expires, so that I can re-verify without losing admin access.

#### Acceptance Criteria

1. WHEN verification expiration is 7 days away, THE Verification_Checker SHALL send a reminder email
2. WHEN a reminder email is sent, THE Email_Service SHALL include the expiration date and re-verification instructions
3. WHEN a reminder is sent, THE Verification_System SHALL record the reminder timestamp to prevent duplicate reminders
4. WHEN a user re-verifies before expiration, THE Verification_System SHALL extend expiration by 90 days from re-verification time
5. THE Verification_Checker SHALL check for upcoming expirations daily

### Requirement 7: Admin Action Authorization

**User Story:** As a system, I want to verify admin status before allowing admin actions, so that only currently verified Amazon employees can perform administrative operations.

#### Acceptance Criteria

1. WHEN a user attempts an admin action, THE API_Gateway SHALL check verification status before processing the request
2. WHEN verification status is expired or missing, THE API_Gateway SHALL reject the request with 403 Forbidden status
3. WHEN verification status is valid and current, THE API_Gateway SHALL allow the admin action to proceed
4. WHEN checking verification status, THE API_Gateway SHALL validate expiration date is in the future
5. WHEN verification check fails, THE API_Gateway SHALL return a descriptive error message indicating verification is required

### Requirement 8: Manual Verification Revocation

**User Story:** As a super administrator, I want to manually revoke a user's verification, so that I can immediately remove admin access in emergency situations.

#### Acceptance Criteria

1. WHEN a super admin requests revocation, THE Verification_System SHALL immediately mark the user's verification as revoked
2. WHEN verification is revoked, THE Verification_System SHALL record the revocation timestamp and reason
3. WHEN a revoked user attempts admin actions, THE API_Gateway SHALL reject the request with 403 Forbidden status
4. WHEN verification is revoked, THE Verification_System SHALL send a notification email to the affected user
5. WHERE manual revocation is performed, THE Verification_System SHALL log the action for audit purposes

### Requirement 9: Multi-Environment Support

**User Story:** As a developer, I want the verification system to work in both staging and production environments, so that I can test changes safely before deploying to production.

#### Acceptance Criteria

1. WHEN deployed to staging, THE Verification_System SHALL use staging-specific DynamoDB tables with `-staging` suffix
2. WHEN deployed to staging, THE Email_Service SHALL use staging-verified sender addresses
3. WHEN deployed to production, THE Verification_System SHALL use production DynamoDB tables without suffix
4. WHEN environment changes, THE Verification_System SHALL automatically detect and use correct resources based on API Gateway stage variables
5. WHEN testing in staging, THE Verification_System SHALL function identically to production except for data isolation

### Requirement 10: Data Persistence and Integrity

**User Story:** As a system, I want to reliably store and retrieve verification data, so that verification status is consistent and accurate across all operations.

#### Acceptance Criteria

1. WHEN verification data is written, THE Token_Store SHALL persist it with strong consistency
2. WHEN verification status is queried, THE Verification_System SHALL return the most current data
3. WHEN a user profile is deleted, THE Verification_System SHALL delete all associated verification data
4. WHEN verification data is updated, THE Verification_System SHALL use conditional updates to prevent race conditions
5. THE Token_Store SHALL maintain verification history for audit purposes for at least 1 year
