# Builder.AWS Crawler Fix - Requirements

## Problem Statement

The Builder.AWS crawler (`BuilderAWSCrawler` class in `enhanced_crawler_lambda.py`) has critical bugs that cause data loss:

1. **Author Loss**: Overwrites real author names with generic "AWS Builder Community"
2. **Summary Loss**: Clears summaries for unchanged posts (90% summary loss observed in staging)
3. **Content Loss**: Replaces real content with template text

These issues were discovered in staging on 2026-02-12 after a crawler run.

## Root Cause

The `BuilderAWSCrawler` uses sitemap metadata only and does NOT fetch actual page content. It:
- Hardcodes `authors = 'AWS Builder Community'` (line 509)
- Hardcodes `content = 'Builder.AWS article. Visit...'` (line 511)
- Overwrites these fields even for UNCHANGED posts (lines 595-597)

The Selenium crawler (`builder_selenium_crawler.py`) fetches real content/authors, but the sitemap crawler runs after it and overwrites the good data with generic data.

## User Stories

### 1. Preserve Real Author Names
**As a** content curator  
**I want** Builder.AWS posts to show real author names  
**So that** authors get proper credit and users can find posts by author

**Acceptance Criteria:**
- 1.1 Crawler MUST NOT overwrite existing author field if it already has a real name
- 1.2 Crawler MUST NOT set author to "AWS Builder Community" if real author exists
- 1.3 Only set generic author for NEW posts that don't have an author yet

### 2. Preserve Existing Summaries
**As a** content curator  
**I want** summaries to persist across crawler runs  
**So that** users always see AI-generated summaries

**Acceptance Criteria:**
- 2.1 Crawler MUST NOT clear summary field for unchanged posts
- 2.2 Crawler MUST only clear summary when lastmod date changes (content updated)
- 2.3 Unchanged posts MUST keep their existing summary

### 3. Preserve Real Content
**As a** content curator  
**I want** Builder.AWS posts to show real content  
**So that** summaries can be generated from actual article text

**Acceptance Criteria:**
- 3.1 Crawler MUST NOT overwrite existing content with template text
- 3.2 Crawler MUST only update content when lastmod date changes
- 3.3 Template content should only be used for NEW posts

### 4. Change Detection Works Correctly
**As a** system operator  
**I want** crawler to only update changed posts  
**So that** unchanged posts retain all their data

**Acceptance Criteria:**
- 4.1 Crawler compares lastmod date to detect changes
- 4.2 If lastmod unchanged, crawler MUST NOT update: authors, content, summary, label
- 4.3 If lastmod changed, crawler MAY update all fields and clear summary for regeneration
- 4.4 Crawler MUST always update: last_crawled timestamp

## Critical Rules

### Rule 1: Author Field is Sacred
**NEVER overwrite a real author name with "AWS Builder Community"**

- If existing author != "AWS Builder Community", keep it
- Only use generic author for NEW posts without an author

### Rule 2: Summary Preservation
**NEVER clear summaries for unchanged posts**

- Only clear summary when lastmod date changes
- Unchanged posts keep their summary

### Rule 3: Content Preservation
**NEVER overwrite real content with template text**

- If existing content length > 200 chars, keep it
- Only use template for NEW posts

## Success Criteria

- [ ] Run crawler in staging
- [ ] Verify 0 author names changed to "AWS Builder Community"
- [ ] Verify 0 summaries lost for unchanged posts
- [ ] Verify 0 real content replaced with template
- [ ] Verify lastmod-based change detection works
- [ ] Deploy to production
- [ ] Monitor for 1 week with no regressions

## Out of Scope

- Fetching real content/authors in this crawler (Selenium crawler does that)
- Changing how lastmod dates are used for change detection
- Modifying the Selenium crawler

## Related Issues

- Issue #26: Summary Loss Investigation
- Issue #20: Crawler Change Detection (AWS Blog)
- Builder Crawler Problem (github-issue-builder-crawler-problem.md)
