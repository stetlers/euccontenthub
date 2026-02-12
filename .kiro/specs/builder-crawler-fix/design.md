# Builder.AWS Crawler Fix - Design

## Overview

Fix the Builder.AWS crawler orchestration to properly handle the two-stage crawling process:
1. **Sitemap Crawler** (fast, metadata only) - detects new/changed posts
2. **Selenium Crawler** (slow, full content) - fetches real authors and content for new/changed posts only

The sitemap crawler must preserve existing data and only invoke the Selenium crawler (not Summary/Classifier directly).

## Current Behavior (BROKEN)

```python
# UNCHANGED posts (lastmod same)
else:
    update_expression = '''
        SET #url = :url,
            title = :title,
            authors = :authors,        # ❌ OVERWRITES real author
            content = :content,         # ❌ OVERWRITES real content
            last_crawled = :last_crawled
    '''
    # Uses generic "AWS Builder Community" and template content
```

**Problem**: Even unchanged posts get their authors/content overwritten with generic values.

## Proposed Solution

### Strategy: Proper Crawler Orchestration

**Correct Flow:**
```
1. Sitemap Crawler (BuilderAWSCrawler)
   ↓ Detects NEW or CHANGED posts (via lastmod date)
   ↓ Preserves existing authors/content/summaries for UNCHANGED posts
   ↓
2. Selenium Crawler (builder_selenium_crawler.py)
   ↓ Fetches real content and authors for NEW/CHANGED posts only
   ↓
3. Summary Generator
   ↓ Generates AI summaries for NEW/CHANGED posts only
   ↓
4. Classifier
   ↓ Generates AI labels for NEW/CHANGED posts only
```

**Key Principle:** Only the actual Builder.AWS article change (detected by lastmod) should trigger the downstream pipeline. DynamoDB table enrichment (adding real authors) should NOT trigger summary regeneration.

### For UNCHANGED Posts

The sitemap crawler should be extremely conservative:

```python
else:  # Post unchanged (lastmod same)
    update_expression = '''
        SET #url = :url,
            title = :title,
            date_published = if_not_exists(date_published, :date_published),
            date_updated = :date_updated,
            tags = :tags,
            last_crawled = :last_crawled,
            #source = :source,
            authors = if_not_exists(authors, :authors),
            content = if_not_exists(content, :content)
    '''
    # Does NOT touch: summary, label, label_confidence, label_generated
    # Does NOT invoke: Selenium, Summary, or Classifier
```

**Behavior:**
- Updates metadata (title, dates, tags, last_crawled)
- Preserves existing authors (if Selenium already fetched them)
- Preserves existing content (if Selenium already fetched it)
- Preserves existing summaries and labels
- Does NOT invoke any downstream lambdas

### For CHANGED Posts

```python
if content_changed:  # lastmod date changed
    update_expression = '''
        SET #url = :url,
            title = :title,
            authors = :authors,
            date_published = :date_published,
            date_updated = :date_updated,
            tags = :tags,
            content = :content,
            last_crawled = :last_crawled,
            summary = :empty,
            label = :empty,
            label_confidence = :zero,
            label_generated = :empty,
            #source = :source
    '''
    # Invokes: Selenium Crawler (which then invokes Summary → Classifier)
```

**Behavior:**
- Updates all fields with sitemap data (temporary generic values)
- Clears summary and label for regeneration
- Invokes Selenium crawler to fetch real content/authors
- Selenium crawler then invokes Summary generator
- Summary generator then invokes Classifier

## Implementation Details

### Files to Modify

1. **enhanced_crawler_lambda.py** - `BuilderAWSCrawler.save_to_dynamodb()` method (lines 520-620)
2. **enhanced_crawler_lambda.py** - `BuilderAWSCrawler.crawl_all_posts()` method (lines 650-700)

### Changes Required

#### Change 1: Update else branch (lines 595-610)
- Add `if_not_exists()` for authors and content
- Remove summary/label fields entirely
- Keep title, dates, tags, last_crawled updates

#### Change 2: Remove Summary/Classifier invocation from sitemap crawler
**Current (WRONG):**
```python
# In BuilderAWSCrawler.crawl_all_posts() - AFTER processing all posts
if self.posts_needing_summaries > 0:
    # Invoke Summary Generator
    # Invoke Classifier
```

**New (CORRECT):**
```python
# In BuilderAWSCrawler.crawl_all_posts() - AFTER processing all posts
if self.posts_needing_summaries > 0:
    # Invoke Selenium Crawler (which will invoke Summary → Classifier)
    lambda_client.invoke(
        FunctionName='aws-blog-builder-selenium-crawler',
        InvocationType='Event',
        Payload=json.dumps({
            'post_ids': list_of_changed_post_ids
        })
    )
```

#### Change 3: Track changed post IDs
The sitemap crawler needs to track which posts changed so it can pass them to Selenium:

```python
class BuilderAWSCrawler:
    def __init__(self, table_name):
        # ... existing code ...
        self.changed_post_ids = []  # NEW: track changed posts
    
    def save_to_dynamodb(self, metadata):
        # ... existing code ...
        if content_changed:
            # ... update logic ...
            self.changed_post_ids.append(post_id)  # NEW: track this post
```

### DynamoDB if_not_exists() Function

```python
# Syntax
field_name = if_not_exists(field_name, :default_value)

# Behavior
- If field exists: keeps existing value
- If field missing: sets to default_value
```

## Edge Cases

### Case 1: New Post (Never Seen Before)
- `content_changed = True` (no existing item)
- Uses `if content_changed` branch
- Sets all fields including generic author/content
- ✅ Correct behavior

### Case 2: Unchanged Post with Real Data
- `content_changed = False` (lastmod same)
- Uses `else` branch with `if_not_exists()`
- Keeps existing author/content/summary
- Updates title/dates/tags
- ✅ Correct behavior

### Case 3: Changed Post (lastmod updated)
- `content_changed = True` (lastmod different)
- Uses `if content_changed` branch
- Overwrites all fields, clears summary
- ⚠️ May overwrite real author with generic
- **Mitigation**: Selenium crawler should run after sitemap crawler

### Case 4: Post with Generic Author Gets Real Author
- Selenium crawler runs, sets real author
- Sitemap crawler runs later
- `content_changed = False` (lastmod same)
- `if_not_exists(authors, :authors)` keeps real author
- ✅ Correct behavior

## Testing Plan

### Unit Tests
1. Test `if_not_exists()` preserves existing authors
2. Test `if_not_exists()` preserves existing content
3. Test unchanged posts keep summaries
4. Test changed posts clear summaries

### Integration Tests (Staging)
1. Copy production data to staging
2. Run sitemap crawler
3. Verify:
   - 0 authors changed to "AWS Builder Community"
   - 0 summaries lost
   - 0 content replaced with template
   - lastmod-based change detection works

### Production Deployment
1. Deploy to production
2. Run crawler
3. Monitor for 24 hours
4. Check for regressions

## Rollback Plan

If issues occur:
1. Revert Lambda code to previous version
2. Restore data from backup (if needed)
3. Investigate root cause
4. Fix and redeploy

## Success Metrics

- **Author Preservation**: 100% of real authors retained
- **Summary Preservation**: 100% of summaries retained for unchanged posts
- **Content Preservation**: 100% of real content retained
- **Change Detection**: Only posts with changed lastmod get summary regeneration

## Alternative Approaches Considered

### Alternative 1: Don't Update Unchanged Posts At All
**Rejected**: Need to update last_crawled timestamp and potentially fix title formatting

### Alternative 2: Fetch Real Content in Sitemap Crawler
**Rejected**: Would require HTTP requests for every post, defeating purpose of sitemap crawler

### Alternative 3: Run Selenium Crawler After Sitemap Crawler
**Rejected**: Selenium crawler is slow and expensive, should only run for new/changed posts

## Dependencies

- DynamoDB `if_not_exists()` function (already supported)
- No new libraries or services required

## Deployment

1. Update `enhanced_crawler_lambda.py`
2. Copy to `crawler_code/lambda_function.py`
3. Create deployment zip
4. Deploy to staging Lambda
5. Test in staging
6. Deploy to production Lambda

## Documentation Updates

- Update AGENTS.md with Builder crawler rules
- Update github-issue-builder-crawler-problem.md with resolution
- Create completion document for Issue #26
