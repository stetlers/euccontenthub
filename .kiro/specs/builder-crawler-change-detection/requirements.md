# Requirements Document

## Introduction

The Builder.AWS crawler currently regenerates summaries for all ~200 articles on every crawl run, even when articles haven't changed. This occurs because the crawler generates a template string containing the article title during metadata extraction, which causes the content comparison to always detect changes. This results in wasted Bedrock API calls, slow crawl completion, potential summary loss, and inconsistent behavior compared to the AWS Blog crawler.

This feature will implement proper change detection for Builder.AWS articles using lastmod dates from the sitemap, ensuring summaries are only regenerated when articles actually update.

## Glossary

- **Crawler**: The Lambda function that fetches article metadata from Builder.AWS sitemap
- **BuilderAWSCrawler**: The class in enhanced_crawler_lambda.py responsible for crawling Builder.AWS content
- **Lastmod**: The last modification date provided in the sitemap XML for each article
- **Content_Template**: The static text stored in DynamoDB representing article content (since full content isn't fetched)
- **Summary_Generator**: The Lambda function that generates AI summaries using AWS Bedrock
- **Change_Detection**: The process of determining whether an article has been modified since the last crawl
- **DynamoDB_Post**: A record in the aws-blog-posts table representing a single article

## Requirements

### Requirement 1: Static Content Template

**User Story:** As a system administrator, I want the Builder.AWS crawler to use a static content template, so that content comparison doesn't falsely detect changes on every crawl.

#### Acceptance Criteria

1. WHEN the BuilderAWSCrawler extracts metadata from sitemap, THE Crawler SHALL generate a content template without variable elements
2. THE Content_Template SHALL contain only static text that remains identical across crawl runs
3. WHEN comparing existing posts to new crawl data, THE Crawler SHALL detect no content changes if the article hasn't been modified
4. THE Content_Template SHALL be sufficient for AI summary generation while remaining static

### Requirement 2: Lastmod Date Extraction

**User Story:** As a system administrator, I want the crawler to extract and store lastmod dates from the sitemap, so that I can track when articles were last updated.

#### Acceptance Criteria

1. WHEN the BuilderAWSCrawler parses a sitemap entry, THE Crawler SHALL extract the lastmod date if present
2. WHEN saving a post to DynamoDB, THE Crawler SHALL store the lastmod date in a dedicated field
3. IF a sitemap entry lacks a lastmod date, THEN THE Crawler SHALL use the current timestamp as a fallback
4. THE Crawler SHALL parse lastmod dates in ISO 8601 format from the sitemap XML

### Requirement 3: Lastmod-Based Change Detection

**User Story:** As a system administrator, I want the crawler to use lastmod dates to detect article changes, so that summaries are only regenerated when articles actually update.

#### Acceptance Criteria

1. WHEN comparing an existing post to new crawl data, THE Crawler SHALL compare the stored lastmod date with the new lastmod date
2. IF the new lastmod date is more recent than the stored date, THEN THE Crawler SHALL mark the article as changed
3. IF the new lastmod date matches the stored date, THEN THE Crawler SHALL mark the article as unchanged
4. WHEN an article is marked as unchanged, THE Crawler SHALL preserve the existing summary field
5. WHEN an article is marked as changed, THE Crawler SHALL clear the summary field to trigger regeneration

### Requirement 4: Summary Preservation

**User Story:** As a system administrator, I want existing summaries to be preserved for unchanged articles, so that I don't waste Bedrock API calls or risk losing summaries.

#### Acceptance Criteria

1. WHEN updating an unchanged article in DynamoDB, THE Crawler SHALL not modify the summary field
2. WHEN updating an unchanged article in DynamoDB, THE Crawler SHALL not add the post to the posts_needing_summaries list
3. WHEN updating a changed article in DynamoDB, THE Crawler SHALL clear the summary field
4. WHEN updating a changed article in DynamoDB, THE Crawler SHALL add the post to the posts_needing_summaries list

### Requirement 5: Accurate Change Reporting

**User Story:** As a system administrator, I want accurate logging of article changes, so that I can monitor crawler behavior and verify change detection is working correctly.

#### Acceptance Criteria

1. WHEN the Crawler processes an article, THE Crawler SHALL log whether the article is new, changed, or unchanged
2. WHEN the Crawler completes a run, THE Crawler SHALL report the count of new articles
3. WHEN the Crawler completes a run, THE Crawler SHALL report the count of changed articles
4. WHEN the Crawler completes a run, THE Crawler SHALL report the count of unchanged articles
5. WHEN the Crawler completes a run, THE Crawler SHALL report the count of posts needing summaries

### Requirement 6: Backward Compatibility

**User Story:** As a system administrator, I want the crawler to handle existing posts without lastmod dates, so that the system continues to work with legacy data.

#### Acceptance Criteria

1. WHEN the Crawler encounters an existing post without a lastmod field, THE Crawler SHALL treat it as requiring an update
2. WHEN updating a post without a lastmod field, THE Crawler SHALL add the lastmod field from the sitemap
3. THE Crawler SHALL not fail or error when processing posts lacking lastmod dates

### Requirement 7: Staging Environment Testing

**User Story:** As a developer, I want to test the crawler changes in staging before production deployment, so that I can verify the fix works correctly without affecting production data.

#### Acceptance Criteria

1. WHEN deploying the crawler changes, THE deployment process SHALL target the staging environment first
2. WHEN testing in staging, THE test SHALL verify that a second crawl run shows "Article unchanged" for unchanged posts
3. WHEN testing in staging, THE test SHALL verify that existing summaries are preserved across crawl runs
4. WHEN testing in staging, THE test SHALL verify that posts_needing_summaries is 0 when no articles changed
5. WHEN staging tests pass, THEN THE deployment process SHALL promote the changes to production
