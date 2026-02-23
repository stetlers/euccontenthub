# Auto-Chain Root Cause Analysis

## Issue Summary

Builder.AWS posts in staging had authors and content, but many were missing summaries and labels. Investigation revealed the auto-chaining feature was not working, causing summary generation to stop after processing only one batch instead of continuing until all posts were complete.

## Root Cause

**Variable Name Collision in Classifier Invocation Loop**

The summary generator Lambda had TWO separate loops that both used the variable name `post_id`:

1. **Line 105**: `post_id = event.get('post_id')` - Extracts from event (None for batch mode)
2. **Line 228**: `for post_id in summarized_post_ids:` - Loop to invoke classifier

The second loop **overwrote** the `post_id` variable, changing it from `None` to the last processed post ID.

### Auto-Chain Logic

The auto-chain check (line 243) uses this condition:

```python
if not post_id and posts_processed >= batch_size and not force:
    # Auto-chain to process next batch
```

When `post_id` has a value (from the classifier loop), the condition evaluates to `False`, preventing auto-chaining.

## Evidence

### Log Analysis

```
Auto-chain check: post_id=builder-microsoft-pki-smart-card-authentication-amazon-workspaces, 
posts_processed=5, batch_size=5, force=False
```

This shows `post_id` had a value when it should have been `None`, causing the auto-chain condition to fail.

### Deployment History

- **Deployment marker NOT found** in earlier logs - The auto-chain code was never actually deployed to $LATEST
- After proper deployment, the marker `[AUTOCHAIN-V2-DEPLOYED]` appeared in logs
- However, auto-chaining still didn't work due to the variable collision bug

## Fix Applied

Changed the classifier invocation loop to use a different variable name:

```python
# BEFORE (line 228)
for post_id in summarized_post_ids:
    lambda_client.invoke(...)

# AFTER
for summarized_post_id in summarized_post_ids:
    lambda_client.invoke(
        Payload=json.dumps({'post_id': summarized_post_id})
    )
```

This preserves the original `post_id` variable (None) so the auto-chain condition works correctly.

## Verification

After deploying the fix:

```
Builder.AWS Posts Status in Staging
================================================================================
Total posts: 84
Posts with real authors: 84/84
Posts with content (>100 chars): 84/84
Posts with summaries: 84/84
Posts with labels: 84/84
```

All posts now have complete data, confirming auto-chaining works correctly.

## Answer to User's Question

The user asked which of three potential issues caused the auto-chain failure:
1. Auto-chaining logic failed ✅ **THIS WAS THE CAUSE**
2. Bedrock timeout/throttling ❌
3. AWS execution limits ❌

**Answer**: The auto-chaining logic failed due to a variable name collision. The loop that invoked the classifier Lambda reused the `post_id` variable name, overwriting the original value and breaking the auto-chain condition check.

## Lessons Learned

1. **Variable naming matters**: Using descriptive, unique variable names prevents subtle bugs
2. **Deployment verification**: Always check logs for deployment markers to confirm new code is running
3. **Debug logging**: The debug statements we added (`DEBUG: Extracted post_id=...`) were crucial for identifying the issue
4. **Staging testing**: Testing in staging caught this bug before it affected production

## Next Steps

1. ✅ Fix deployed to $LATEST (staging)
2. ⏳ Test auto-chaining with a larger dataset to confirm it chains correctly
3. ⏳ Deploy to production after staging verification
4. ⏳ Consider adding unit tests for auto-chain logic
