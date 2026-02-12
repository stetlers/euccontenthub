# GitHub Issue #26: Investigate Summary Loss After Crawler Runs

## Problem Statement

AI-generated summaries and labels are disappearing from posts after the crawler runs, even when post content hasn't changed. This is a critical data integrity issue that affects user experience.

## Observed Behavior

**Timeline (2026-02-11):**
- Morning: Production site had summaries and labels on all posts
- Afternoon (15:24): Crawler ran in staging environment
- Evening: User reports production posts missing summaries and labels
- Investigation: 115 posts in production missing summaries (24% of total posts)

**Expected Behavior:**
- Crawler should ONLY clear summaries when post content actually changes
- Unchanged posts should retain their existing summaries and labels
- Issue #20 implemented change detection to prevent this exact problem

## Investigation Findings

### Crawler Logs Analysis

**Staging Crawler Run (15:24 UTC):**
```
Environment: staging
Using table: aws-blog-posts-staging
Posts processed: 351
Posts created: 0
Posts updated: 351
Posts changed: 0
Posts unchanged: 0
Posts needing summaries: 0
```

**Key Observations:**
1. ✅ Crawler correctly detected 0 content changes
2. ✅ Crawler reported 0 posts needing summaries
3. ✅ Change detection logic appears to be working
4. ❌ But 115 posts in production are missing summaries

### Data Analysis

**Production Table Scan:**
- Total posts: 479
- Posts with summaries: 364 (76%)
- Posts without summaries: 115 (24%)

**Staging Table Scan (before copy):**
- Total posts: 479
- Posts with summaries: 35 (7%)
- Posts without summaries: 444 (93%)

### Possible Root Causes

1. **UpdateExpression Bug**: The crawler's `UpdateExpression` might be inadvertently clearing summaries even when `content_changed = False`

2. **Conditional Logic Error**: The `if content_changed:` block might not be working as expected

3. **DynamoDB Update Behavior**: `update_item()` might be clearing attributes not explicitly set in the expression

4. **Race Condition**: Multiple crawler invocations running simultaneously could be overwriting each other's updates

5. **Lambda Version Mismatch**: Production might be running an older version of the crawler without the fix from Issue #20

6. **Manual Intervention**: Someone might have manually run the crawler with different parameters

## Code Review Needed

### Current Change Detection Logic (enhanced_crawler_lambda.py)

```python
# Check if content changed
content_changed = False
try:
    response = self.table.get_item(Key={'post_id': post_id})
    if 'Item' in response:
        existing_item = response['Item']
        old_content = existing_item.get('content', '')
        new_content = metadata['content']
        if old_content != new_content:
            content_changed = True
except:
    content_changed = True  # New post

# Build update expression
if content_changed:
    # Clear summary and label
    update_expression = '''SET ... summary = :empty, label = :empty ...'''
else:
    # Keep existing summary
    update_expression = '''SET ... (no summary/label fields) ...'''
```

**Potential Issue**: The `else` branch doesn't explicitly preserve summary/label. If DynamoDB's `update_item()` behavior changed or if there's a bug in the expression, summaries could be cleared.

## Reproduction Steps

1. Verify production has summaries on all posts
2. Run crawler in production: `aws lambda invoke --function-name aws-blog-crawler:production`
3. Wait for crawler to complete
4. Check if summaries are still present
5. Compare before/after counts

## Testing Plan

**Tomorrow's Test (2026-02-12):**
1. Take snapshot of production summaries (count posts with/without summaries)
2. Run crawler in staging first
3. Verify staging summaries are preserved
4. If staging works, run crawler in production
5. Immediately check if production summaries are preserved
6. If summaries are lost, capture CloudWatch logs immediately

## Mitigation

**Immediate Actions Taken:**
- ✅ Triggered summary regeneration for 115 missing posts in production
- ✅ Copied summaries from production to staging
- ✅ Created this issue to track investigation

**Preventive Measures Needed:**
1. Add summary preservation test to crawler test suite
2. Add CloudWatch alarm for sudden drop in posts with summaries
3. Implement summary backup before crawler runs
4. Add explicit `if_not_exists()` in UpdateExpression to preserve summaries

## Proposed Fix

### Option 1: Explicit Preservation (Safest)

```python
if content_changed:
    update_expression = '''
        SET ... summary = :empty, label = :empty ...
    '''
else:
    update_expression = '''
        SET ... 
        summary = if_not_exists(summary, :empty),
        label = if_not_exists(label, :empty),
        ...
    '''
```

### Option 2: Separate Update Calls

```python
# Always update metadata
self.table.update_item(
    Key={'post_id': post_id},
    UpdateExpression='SET title = :title, authors = :authors, ...',
    ...
)

# Only clear summaries if content changed
if content_changed:
    self.table.update_item(
        Key={'post_id': post_id},
        UpdateExpression='SET summary = :empty, label = :empty',
        ...
    )
```

### Option 3: Add Logging

```python
if content_changed:
    print(f"  Content changed - clearing summary for {post_id}")
    # Clear summary
else:
    print(f"  Content unchanged - preserving summary for {post_id}")
    # Keep summary
```

## Success Criteria

- [ ] Root cause identified and documented
- [ ] Fix implemented and tested in staging
- [ ] Crawler runs without losing summaries
- [ ] Test passes: Run crawler 3 times, verify summaries preserved
- [ ] CloudWatch alarm configured for summary count drops
- [ ] Backup/restore procedure documented

## Related Issues

- Issue #20: Crawler Change Detection (original fix)
- Issue #19: Staging Environment Setup

## Priority

**Critical** - This affects data integrity and user experience on the production site.

## Estimated Time

- Investigation: 2-3 hours
- Fix implementation: 1-2 hours
- Testing: 1-2 hours
- Total: 4-7 hours

## Notes

- This issue was discovered during Amazon Email Verification testing (Issue #25)
- The crawler's change detection logic from Issue #20 appears to work in logs but summaries are still being lost
- Need to determine if this is a code bug, DynamoDB behavior, or operational issue
