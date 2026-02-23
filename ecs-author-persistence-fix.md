# ECS Author Persistence Issue - Root Cause & Fix

## Issue Summary

ECS task logs showed "✓ Updated: [Author Name]" for 39 posts, but only 17 posts actually had real authors in DynamoDB. The remaining posts still showed "AWS Builder Community" instead of real author names.

## Root Cause

The sitemap crawler was sending **duplicate post IDs** to the ECS task. Looking at the ECS task logs (task ID: `6384b8a6ba9f468ebaab2e237d530bb2`), we can see the same URL being processed multiple times:

```
[32/39] Processing: https://builder.aws.com/content/2y6XQVt601LaNN4i8CvDi4WTbhN/security-checks-using-amazon-q-developer-cli
✓ Updated: Pierre-Yves Gillier

[35/39] Processing: https://builder.aws.com/content/2y6XQVt601LaNN4i8CvDi4WTbhN/security-checks-using-amazon-q-developer-cli
✓ Updated: Pierre-Yves Gillier

[38/39] Processing: https://builder.aws.com/content/2y6XQVt601LaNN4i8CvDi4WTbhN/security-checks-using-amazon-q-developer-cli
✓ Updated: Pierre-Yves Gillier
```

The same post was processed 3 times! This means:
- ECS task claimed to update 39 posts
- But only ~17 unique posts were actually updated
- The rest were duplicates wasting time and resources

## Why Duplicates Occurred

In `enhanced_crawler_lambda.py`, the `changed_post_ids` was a **list**:

```python
self.changed_post_ids = []  # Track post IDs that changed (for Selenium crawler)
```

When posts were detected as changed, they were appended to the list:

```python
if content_changed:
    self.changed_post_ids.append(post_id)
```

If the sitemap contained duplicate entries (which can happen), or if the same post was detected as changed multiple times during processing, the same post ID would be added to the list multiple times.

## The Fix

Changed `changed_post_ids` from a **list** to a **set** to automatically deduplicate:

```python
self.changed_post_ids = set()  # Track post IDs that changed (for Selenium crawler) - use set to avoid duplicates
```

And updated the append operation to use `add()`:

```python
if content_changed:
    self.changed_post_ids.add(post_id)  # Use add() for set
```

When passing to ECS, convert the set to a list:

```python
changed_post_ids = list(builder_crawler.changed_post_ids)  # Convert set to list
```

## Files Modified

1. `enhanced_crawler_lambda.py` - Main crawler Lambda (deployed to staging)
2. `crawler_code/lambda_function.py` - Backup copy (kept in sync)

## Deployment Status

✅ Deployed to staging: `python deploy_lambda.py crawler staging`

## Testing Plan

1. **Delete all Builder.AWS posts from staging** to start fresh
2. **Run crawler from website** (click "Start Crawling" button)
3. **Verify complete flow**:
   - Sitemap crawler detects NEW posts
   - ECS task processes unique posts only (no duplicates)
   - Real authors are extracted and saved
   - Summaries are generated
   - Labels are classified
4. **Check staging website** to confirm all posts have:
   - Real author names (not "AWS Builder Community")
   - AI-generated summaries
   - Content type labels

## Expected Outcome

After the fix:
- ECS task will process only unique posts
- No wasted processing on duplicates
- All Builder.AWS posts will have real author names
- Complete orchestration chain will work: Sitemap → ECS → Summary → Classifier

## Next Steps

1. Wait for user to delete Builder.AWS posts from staging
2. User clicks "Start Crawling" on staging website
3. Monitor ECS task logs to verify no duplicates
4. Check staging status to verify all posts have real authors
5. If successful, deploy to production
