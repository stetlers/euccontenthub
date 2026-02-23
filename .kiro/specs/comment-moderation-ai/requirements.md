# Requirements Document: Automated Comment Moderation System

## Introduction

The EUC Content Hub requires an automated comment moderation system to maintain content quality and community safety. The system will use AWS Bedrock (Claude Haiku) to analyze comments in real-time and flag inappropriate content for administrative review. This ensures a safe, on-topic community environment while maintaining transparency with comment authors.

## Glossary

- **Moderation_System**: The AWS Bedrock-powered AI service that analyzes comment content for appropriateness
- **Comment**: User-submitted text associated with a blog post, stored in DynamoDB
- **Flagged_Comment**: A comment identified by the Moderation_System as potentially inappropriate
- **Public_View**: The comment display visible to all users except the comment author
- **Author_View**: The comment display visible only to the comment author, showing pending moderation status
- **Moderation_Status**: An enumeration with values: 'approved', 'pending_review', 'rejected'
- **API_Lambda**: The Lambda function handling comment submission via POST /posts/{post_id}/comments
- **Comment_Author**: The authenticated user who submitted the comment

## Requirements

### Requirement 1: Automated Content Analysis

**User Story:** As a platform administrator, I want comments to be automatically analyzed when submitted, so that inappropriate content can be identified without manual review of every comment.

#### Acceptance Criteria

1. WHEN a comment is submitted via POST /posts/{post_id}/comments, THE Moderation_System SHALL analyze the comment text before storing it in DynamoDB
2. WHEN analyzing a comment, THE Moderation_System SHALL evaluate the content for spam, promotional content, dangerous links, harassment, and off-topic content
3. WHEN the analysis completes, THE Moderation_System SHALL assign a moderation_status of either 'approved' or 'pending_review'
4. WHEN the Moderation_System cannot complete analysis within 2 seconds, THE System SHALL default to 'approved' status to avoid blocking comment submission
5. THE Moderation_System SHALL use AWS Bedrock with Claude Haiku model for cost efficiency and speed

### Requirement 2: Comment Storage with Moderation Metadata

**User Story:** As a developer, I want comments to include moderation metadata, so that the system can track and display moderation status appropriately.

#### Acceptance Criteria

1. WHEN a comment is stored in DynamoDB, THE System SHALL include a moderation_status field with value 'approved' or 'pending_review'
2. WHEN a comment is flagged, THE System SHALL include a moderation_reason field describing why the comment was flagged
3. WHEN a comment is flagged, THE System SHALL include a moderation_timestamp field recording when the analysis occurred
4. THE System SHALL maintain backward compatibility with existing comments that lack moderation fields
5. WHEN retrieving comments, THE System SHALL treat comments without moderation_status as 'approved'

### Requirement 3: Differential Comment Display

**User Story:** As a user, I want to see only approved comments from other users, so that I am not exposed to potentially inappropriate content.

#### Acceptance Criteria

1. WHEN a user views comments on a post, THE System SHALL display only comments with moderation_status 'approved' from other users
2. WHEN the Comment_Author views comments on a post, THE System SHALL display their own pending_review comments in addition to all approved comments
3. WHEN displaying a pending_review comment to its author, THE System SHALL render it with distinct visual styling (orange/yellow text color)
4. WHEN displaying a pending_review comment to its author, THE System SHALL include the text "Pending Administrative Review"
5. THE System SHALL exclude pending_review comments from the public comment count displayed on post cards

### Requirement 4: Spam and Promotional Content Detection

**User Story:** As a community moderator, I want spam and promotional content to be automatically flagged, so that the platform remains focused on EUC-related technical discussions.

#### Acceptance Criteria

1. WHEN a comment contains promotional language unrelated to AWS EUC services, THE Moderation_System SHALL flag it as pending_review
2. WHEN a comment contains repetitive text patterns characteristic of spam, THE Moderation_System SHALL flag it as pending_review
3. WHEN a comment contains multiple external links, THE Moderation_System SHALL flag it as pending_review
4. WHEN a comment discusses AWS EUC services or related technical topics, THE Moderation_System SHALL approve it even if it contains links to official AWS documentation
5. THE Moderation_System SHALL prefer false negatives over false positives (let borderline content through rather than incorrectly flagging legitimate comments)

### Requirement 5: Dangerous Link Detection

**User Story:** As a security-conscious administrator, I want comments with potentially dangerous links to be flagged, so that users are protected from malicious websites.

#### Acceptance Criteria

1. WHEN a comment contains URLs with suspicious patterns (IP addresses, URL shorteners, uncommon TLDs), THE Moderation_System SHALL flag it as pending_review
2. WHEN a comment contains links to known legitimate domains (aws.amazon.com, github.com, stackoverflow.com), THE Moderation_System SHALL not flag it solely for containing links
3. WHEN a comment contains more than 3 URLs, THE Moderation_System SHALL flag it as pending_review regardless of domain reputation
4. THE Moderation_System SHALL analyze URL patterns without performing external network requests to validate domains
5. WHEN a comment contains no URLs, THE Moderation_System SHALL not flag it for link-related reasons

### Requirement 6: Harassment and Abusive Content Detection

**User Story:** As a community member, I want harassment and abusive content to be automatically flagged, so that the platform maintains a respectful environment.

#### Acceptance Criteria

1. WHEN a comment contains profanity, slurs, or personal attacks, THE Moderation_System SHALL flag it as pending_review
2. WHEN a comment contains aggressive or threatening language, THE Moderation_System SHALL flag it as pending_review
3. WHEN a comment contains technical criticism or disagreement expressed respectfully, THE Moderation_System SHALL approve it
4. THE Moderation_System SHALL distinguish between technical debate and personal harassment
5. WHEN a comment contains mild frustration about technical issues, THE Moderation_System SHALL approve it

### Requirement 7: Off-Topic Content Detection

**User Story:** As a content curator, I want off-topic comments to be flagged, so that discussions remain focused on AWS EUC content.

#### Acceptance Criteria

1. WHEN a comment discusses topics unrelated to AWS, cloud computing, or EUC services, THE Moderation_System SHALL flag it as pending_review
2. WHEN a comment discusses AWS services outside the EUC domain but relevant to the post, THE Moderation_System SHALL approve it
3. WHEN a comment asks clarifying questions about the blog post content, THE Moderation_System SHALL approve it
4. WHEN a comment shares personal experiences with AWS EUC services, THE Moderation_System SHALL approve it
5. THE Moderation_System SHALL consider the context of the blog post when evaluating topic relevance

### Requirement 8: Performance and Reliability

**User Story:** As a user, I want comment submission to be fast and reliable, so that moderation does not significantly impact my experience.

#### Acceptance Criteria

1. WHEN the Moderation_System analyzes a comment, THE analysis SHALL complete within 2 seconds under normal conditions
2. WHEN the Moderation_System exceeds the 2-second timeout, THE System SHALL default to 'approved' status and log the timeout
3. WHEN the Moderation_System encounters an error, THE System SHALL default to 'approved' status and log the error
4. THE System SHALL process moderation asynchronously if synchronous processing would exceed timeout limits
5. WHEN moderation is processed asynchronously, THE comment SHALL initially be stored with 'approved' status and updated if flagged

### Requirement 9: Administrative Review Interface (Future)

**User Story:** As an administrator, I want to review flagged comments, so that I can make final decisions on content appropriateness.

#### Acceptance Criteria

1. WHEN a comment is flagged as pending_review, THE System SHALL store sufficient metadata for administrative review
2. THE System SHALL support future implementation of an admin interface without requiring data migration
3. WHEN an administrator reviews a comment (future functionality), THE System SHALL support updating moderation_status to 'approved' or 'rejected'
4. THE comment data structure SHALL include fields for admin_reviewed_by and admin_review_timestamp for future use
5. THE initial implementation SHALL focus on flagging only, with admin interface deferred to future work

### Requirement 10: Moderation Transparency

**User Story:** As a comment author, I want to know when my comment is pending review, so that I understand why it is not immediately visible to others.

#### Acceptance Criteria

1. WHEN a comment is flagged as pending_review, THE System SHALL display a clear message to the author: "Pending Administrative Review"
2. WHEN displaying a pending_review comment to its author, THE System SHALL use distinct visual styling (orange or yellow text color)
3. THE System SHALL not display the specific moderation_reason to the comment author to avoid gaming the system
4. WHEN a comment is approved after review (future functionality), THE System SHALL display it normally to all users
5. WHEN a comment is rejected after review (future functionality), THE System SHALL remove it from the author's view
