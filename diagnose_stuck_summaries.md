# Diagnosing Stuck Summaries at 97%

## Possible Causes

### 1. Auto-Chain Stopped
**Symptoms**: No new Lambda invocations, percentage stuck
**Causes**:
- All remaining posts failed after max retries (returned None)
- Auto-chain condition not triggering
- Lambda timeout before auto-chain could trigger

**Check**: Look for "Auto-chain check" in recent logs

### 2. Posts with Error Summaries (Old Code)
**Symptoms**: 97% complete, ~3% have error messages
**Cause**: Some posts got error summaries before exponential backoff was deployed
**Fix**: Need to clear error summaries

**Check**: Count posts with "Error generating summary" in summary field

### 3. Exponential Backoff Taking Too Long
**Symptoms**: Lambda timeouts, posts skipped
**Cause**: Multiple retries with long waits (16s) hitting Lambda timeout
**Fix**: May need to reduce max_retries or batch_size

**Check**: Look for "Skipped - failed after retries" in logs

### 4. Specific Posts Consistently Failing
**Symptoms**: Same posts fail every time
**Cause**: Bad content, encoding issues, or Bedrock model issues
**Fix**: Identify and investigate specific posts

**Check**: Which posts don't have summaries?

## Diagnostic Steps

### Step 1: Check Recent Lambda Activity
```powershell
python check_latest_summary_logs.py
```
Look for:
- Recent invocations (are Lambdas still running?)
- Auto-chain messages (is it trying to continue?)
- Skip messages (are posts being skipped?)
- Error patterns (what's failing?)

### Step 2: Count Posts Without Summaries
```powershell
python count_error_summaries.py
```
This will show:
- Total posts
- Posts with good summaries
- Posts with error summaries
- Posts without summaries

### Step 3: Check Which Posts Are Missing
Create a script to identify the specific posts without summaries:
```python
# List posts without summaries
posts_without = [p for p in posts if not p.get('summary')]
for post in posts_without[:10]:
    print(f"{post['post_id']}: {post.get('title')}")
```

### Step 4: Check Lambda Invocation History
```powershell
python check_all_summary_invocations.py
```
Look for:
- When was the last invocation?
- How many invocations in last hour?
- Did they stop suddenly?

## Likely Scenario

Given that:
1. We deployed exponential backoff mid-test
2. It's stuck at 97%
3. Multiple monitoring rounds show no change

**Most likely**: The remaining 3% of posts have error summaries from BEFORE the exponential backoff was deployed. The auto-chain sees them as "complete" (they have a summary field) and skips them.

## Solution

### If Error Summaries Exist:
```powershell
python fix_throttled_summaries.py
```
This will:
1. Find posts with error messages as summaries
2. Remove the summary field
3. Allow auto-chain to retry them

### If Auto-Chain Stopped:
```powershell
python trigger_staging_summaries.py
```
Manually trigger one more cycle to pick up remaining posts

### If Specific Posts Failing:
1. Identify the posts
2. Check their content
3. May need to manually generate summaries or skip them

## Prevention for V2 Test

The exponential backoff code we just deployed should prevent this issue:
- Returns None instead of error message
- Posts without summaries get retried by auto-chain
- No manual cleanup needed

But we need to clear the current error summaries before starting V2 test.
