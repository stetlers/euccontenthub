# Issue #26 Update: Root Cause Found

## Date: 2026-02-12

## Summary

Through staging environment testing, we discovered the root cause of summary loss for Builder.AWS posts. The issue is a **crawler orchestration problem**, not just a data preservation bug.

## Root Cause Analysis

### Problem 1: Data Overwriting (FIXED)
The sitemap crawler was overwriting existing authors, content, and summaries even for UNCHANGED posts.

**Fix Applied:**
- Used `if_not_exists()` for authors and content fields
- Removed summary/label fields from unchanged post updates
- ✅ Tested in staging - 0 summaries lost

### Problem 2: Incorrect Orchestration (IDENTIFIED)
The sitemap crawler was invoking Summary/Classifier directly, bypassing the Selenium crawler that fetches real authors and content.

**Current Flow (WRONG):**
```
Sitemap Crawler → Summary Generator → Classifier
                  (missing real authors/content!)
```

**Correct Flow:**
```
Sitemap Crawler → Selenium Crawler → Summary Generator → Classifier
                  (fetches real data)
```

## Why This Matters

Builder.AWS requires a two-stage crawling process:

1. **Sitemap Crawler** (fast, cheap):
   - Reads XML sitemap
   - Extracts: URL, title (from slug), dates (from lastmod)
   - Does NOT have: real authors or content
   - Detects which posts are NEW or CHANGED

2. **Selenium Crawler** (slow, expensive):
   - Loads full web pages with Chrome
   - Extracts: real author names, full content
   - Should ONLY run for NEW/CHANGED posts

**The Bug:** Sitemap crawler was skipping Selenium and going straight to Summary/Classifier, which meant:
- Posts had generic "AWS Builder Community" author
- Posts had template content instead of real content
- Summaries were generated from template text (useless)

## Impact

**Before Fix:**
- 128 Builder.AWS posts in staging
- ALL had generic "AWS Builder Community" author
- 90% missing summaries (115 out of 128)
- Data loss on every crawler run

**After Partial Fix (if_not_exists):**
- ✅ Summaries preserved for unchanged posts
- ❌ Still no real authors (Selenium not invoked)
- ❌ Still no real content (Selenium not invoked)

**After Complete Fix (orchestration):**
- ✅ Summaries preserved for unchanged posts
- ✅ Real authors fetched for new/changed posts
- ✅ Real content fetched for new/changed posts
- ✅ Summaries generated from real content

## Changes Needed

### 1. Sitemap Crawler Changes
**File:** `enhanced_crawler_lambda.py`

**Change A:** Preserve existing data (DONE)
```python
# Use if_not_exists() for authors/content
authors = if_not_exists(authors, :authors)
content = if_not_exists(content, :content)
```

**Change B:** Invoke Selenium instead of Summary/Classifier (TODO)
```python
# OLD (WRONG):
if self.posts_needing_summaries > 0:
    invoke_summary_generator()
    invoke_classifier()

# NEW (CORRECT):
if self.posts_needing_summaries > 0:
    invoke_selenium_crawler(changed_post_ids)
```

### 2. Selenium Crawler Changes
**File:** `builder_selenium_crawler.py`

**Change:** Accept post_ids parameter (TODO)
```python
def lambda_handler(event, context):
    post_ids = event.get('post_ids', [])  # NEW: specific posts to crawl
    if post_ids:
        # Crawl only these specific posts
    else:
        # Crawl all EUC posts (current behavior)
```

### 3. Documentation Updates
- ✅ AGENTS.md - Added crawler orchestration section
- ⏳ README.md - Need to add architecture diagram
- ⏳ INFRASTRUCTURE.md - Need to document lambda invocation chain

## Testing Plan

### Phase 1: Staging Test (Current)
- ✅ Deploy if_not_exists() fix
- ✅ Verify summaries preserved
- ⏳ Deploy orchestration fix
- ⏳ Verify Selenium invoked for changed posts
- ⏳ Verify real authors fetched
- ⏳ Verify summaries generated from real content

### Phase 2: Production Deployment
- Only after ALL staging tests pass
- Monitor for 24 hours
- Verify no regressions

## Key Insights

1. **Staging Environment is Critical**: This complex orchestration bug would have been impossible to debug in production

2. **Two-Stage Crawling is Necessary**: Builder.AWS's lack of RSS feed forces this design

3. **Change Detection Must Be Precise**: Only actual article changes (lastmod) should trigger the expensive Selenium crawler

4. **Data Preservation is Essential**: DynamoDB enrichment (adding real authors) should NOT trigger summary regeneration

## Related Issues

- Issue #20: Crawler Change Detection (AWS Blog - working correctly)
- Builder Crawler Problem (github-issue-builder-crawler-problem.md)
- Batch Size Optimization (batch-size-optimization-complete.md)

## Next Steps

1. ⏳ Implement orchestration changes in sitemap crawler
2. ⏳ Update Selenium crawler to accept post_ids
3. ⏳ Test complete flow in staging
4. ⏳ Deploy to production
5. ⏳ Close Issue #26

## Lessons Learned

**For Future Development:**
- Document lambda invocation chains clearly
- Test orchestration in staging before production
- Use staging to validate complex multi-lambda workflows
- Always question "why do we need two crawlers?" - there's usually a good reason

**For Documentation:**
- Architecture diagrams should show lambda invocation flow
- README should explain why certain design decisions were made
- AGENTS.md should document orchestration patterns

## Status

- **Data Preservation Fix**: ✅ Complete and tested
- **Orchestration Fix**: ⏳ In progress (spec updated, code pending)
- **Production Deployment**: ⏳ Blocked until orchestration fix complete

## Conclusion

The root cause of Issue #26 (summary loss) is a combination of:
1. Data overwriting bug (FIXED)
2. Incorrect crawler orchestration (IDENTIFIED, fix in progress)

The staging environment proved invaluable in discovering this complex issue before it could impact production.
