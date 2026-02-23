## Root Cause Found - Crawler Orchestration Problem

Through staging environment testing today (2026-02-12), we've identified the root cause of summary loss for Builder.AWS posts. It's a **two-part problem**:

### Part 1: Data Overwriting Bug (FIXED ✅)
The sitemap crawler was overwriting existing authors, content, and summaries even for UNCHANGED posts.

**Fix Applied:**
- Used DynamoDB's `if_not_exists()` function for authors and content fields
- Removed summary/label fields from unchanged post updates
- Tested in staging: **0 summaries lost** after crawler run

### Part 2: Incorrect Orchestration (IDENTIFIED 🔍)
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

### Why Two Crawlers for Builder.AWS?

Builder.AWS doesn't provide an RSS feed with full content, forcing a two-stage approach:

1. **Sitemap Crawler** (fast, cheap): Reads XML sitemap, extracts URL/title/dates, detects NEW/CHANGED posts via lastmod date
2. **Selenium Crawler** (slow, expensive): Loads full web pages with Chrome, extracts real author names and content

**The Bug:** Sitemap was skipping Selenium and going straight to Summary/Classifier, resulting in:
- Generic "AWS Builder Community" author for all posts
- Template content instead of real content  
- Summaries generated from useless template text

### Testing Results

**Staging Test (128 Builder.AWS posts):**
- Before fix: 115 posts missing summaries (90% loss)
- After fix: **0 summaries lost** for unchanged posts ✅
- All 128 posts crawled successfully
- 13 posts with summaries kept their summaries
- 115 posts without summaries remained unchanged

### Changes Made

**Code:**
- ✅ Fixed data preservation in `enhanced_crawler_lambda.py`
- ⏳ Orchestration fix in progress (sitemap invokes Selenium, not Summary)

**Documentation:**
- ✅ Updated AGENTS.md with correct crawler orchestration
- ✅ Created SUMMARY-GENERATOR-RULES.md with batch size best practices
- ✅ Updated batch sizes to 5 (optimized for 3000-char content)
- ✅ Created comprehensive root cause analysis document

**Commit:** 2a5a8b2

### Next Steps

1. ⏳ Implement orchestration changes (sitemap invokes Selenium)
2. ⏳ Update Selenium crawler to accept post_ids parameter
3. ⏳ Test complete flow in staging
4. ⏳ Deploy to production
5. ⏳ Close this issue

### Key Insight

The staging environment proved **invaluable** in discovering this complex orchestration bug. Without staging, we would have been debugging data loss in production with real user impact.

See `github-issue-26-root-cause-found.md` for complete analysis.
