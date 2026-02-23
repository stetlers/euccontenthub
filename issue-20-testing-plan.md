# Issue #20 Testing Plan - Option D Implementation

## Changes Deployed to Staging

### Change 1: Static Content Template
**Before:**
```python
'content': f"Learn more about {title}. Visit the full article on Builder.AWS for detailed information and insights."
```

**After:**
```python
'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.'
```

**Impact**: Prevents false content changes from title variations

### Change 2: Lastmod Date Comparison
**Before:**
```python
# Check if content changed
old_content = existing_item.get('content', '')
new_content = metadata['content']
if old_content != new_content:
    content_changed = True
```

**After:**
```python
# For Builder articles, use lastmod date instead of content for change detection
old_date = existing_item.get('date_updated', '')
new_date = metadata['date_updated']
if old_date != new_date:
    content_changed = True
    print(f"  Article updated (lastmod changed: {old_date} → {new_date})")
else:
    print(f"  Article unchanged (lastmod: {new_date})")
```

**Impact**: Accurate change detection based on Builder.AWS sitemap lastmod dates

---

## Testing Scenarios

### Test 1: Run Crawler Twice (No Changes)

**Purpose**: Verify unchanged articles don't trigger summary regeneration

**Steps**:
1. Check current summary count in staging
2. Run crawler first time
3. Wait for completion
4. Check summary count (should be same or higher)
5. Run crawler second time immediately
6. Check summary count (should be exactly the same)

**Expected Result**:
- First run: May create new posts or update changed posts
- Second run: Should show "Article unchanged" for all posts
- No summaries regenerated on second run
- CloudWatch logs show "Article unchanged (lastmod: ...)"

**Commands**:
```bash
# Check staging table count
aws dynamodb scan --table-name aws-blog-posts-staging --select COUNT

# Invoke crawler (first run)
aws lambda invoke \
  --function-name aws-blog-crawler:staging \
  --invocation-type RequestResponse \
  --payload '{"source":"builder"}' \
  response1.json

# Wait 2 minutes, then run again
aws lambda invoke \
  --function-name aws-blog-crawler:staging \
  --invocation-type RequestResponse \
  --payload '{"source":"builder"}' \
  response2.json

# Check CloudWatch logs
aws logs tail /aws/lambda/aws-blog-crawler --since 10m --follow
```

---

### Test 2: Verify Summary Preservation

**Purpose**: Confirm existing summaries are not cleared

**Steps**:
1. Query a Builder article with a summary
2. Note the summary text
3. Run crawler
4. Query same article
5. Verify summary is unchanged

**Expected Result**:
- Summary text identical before and after crawl
- No "summary" field cleared
- No unnecessary Bedrock API calls

**Commands**:
```bash
# Get a Builder article with summary
aws dynamodb get-item \
  --table-name aws-blog-posts-staging \
  --key '{"post_id":{"S":"builder-<some-id>"}}' \
  --query 'Item.summary.S'

# Run crawler
aws lambda invoke \
  --function-name aws-blog-crawler:staging \
  --invocation-type RequestResponse \
  --payload '{"source":"builder"}' \
  response.json

# Check same article again
aws dynamodb get-item \
  --table-name aws-blog-posts-staging \
  --key '{"post_id":{"S":"builder-<some-id>"}}' \
  --query 'Item.summary.S'
```

---

### Test 3: Check CloudWatch Logs

**Purpose**: Verify correct logging and behavior

**Steps**:
1. Run crawler
2. Check CloudWatch logs
3. Look for "Article unchanged" messages
4. Verify no "Content changed - will regenerate summary" for unchanged articles

**Expected Log Output**:
```
[1/50] Processing: https://builder.aws.com/articles/...
  Article unchanged (lastmod: 2024-12-15T10:30:00Z)
  ✓ Saved: Article Title...

[2/50] Processing: https://builder.aws.com/articles/...
  Article unchanged (lastmod: 2024-11-20T14:15:00Z)
  ✓ Saved: Article Title...
```

**Commands**:
```bash
# Tail logs during crawl
aws logs tail /aws/lambda/aws-blog-crawler --since 5m --follow

# Search for "unchanged" messages
aws logs tail /aws/lambda/aws-blog-crawler --since 10m --filter-pattern "unchanged"

# Search for "Content changed" messages (should be minimal)
aws logs tail /aws/lambda/aws-blog-crawler --since 10m --filter-pattern "Content changed"
```

---

### Test 4: Verify Summary Lambda Invocations

**Purpose**: Confirm summary Lambda only invoked for changed articles

**Steps**:
1. Run crawler
2. Check response for `posts_needing_summaries`
3. Verify it's 0 or very low (only new/changed articles)

**Expected Result**:
- `posts_needing_summaries: 0` (if no articles changed)
- `posts_needing_summaries: 1-5` (if a few articles updated)
- NOT `posts_needing_summaries: 50+` (which would indicate all articles marked as changed)

**Commands**:
```bash
# Run crawler and check response
aws lambda invoke \
  --function-name aws-blog-crawler:staging \
  --invocation-type RequestResponse \
  --payload '{"source":"builder"}' \
  response.json

# Check the response
cat response.json | python -m json.tool
```

---

## Success Criteria

- [ ] Second crawler run shows "Article unchanged" for all unchanged posts
- [ ] Existing summaries preserved across crawler runs
- [ ] `posts_needing_summaries` is 0 when no articles changed
- [ ] CloudWatch logs show accurate change detection
- [ ] No false positive content changes
- [ ] Summary Lambda only invoked for actually changed articles

---

## Rollback Plan

If testing fails:

```bash
# Rollback staging to previous version
aws lambda update-alias \
  --function-name aws-blog-crawler \
  --name staging \
  --function-version 1
```

---

## Production Deployment

**Only after all tests pass:**

```bash
python deploy_lambda.py crawler production
```

---

## Monitoring After Production Deployment

1. **First Production Crawl**:
   - Monitor CloudWatch logs
   - Check `posts_needing_summaries` count
   - Verify summaries preserved

2. **Second Production Crawl** (next day):
   - Should show minimal changes
   - Summaries should remain stable
   - Bedrock API usage should decrease

3. **Long-term Monitoring**:
   - Track summary count over time (should be stable)
   - Monitor Bedrock API costs (should decrease)
   - User feedback (should improve - consistent summaries)

---

**Status**: Deployed to staging, ready for testing  
**Date**: 2026-02-09  
**Issue**: #20
