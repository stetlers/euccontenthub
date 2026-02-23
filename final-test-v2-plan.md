# Final End-to-End Test V2 - With Exponential Backoff

## Status: Ready to Execute

The exponential backoff solution has been deployed. Now we'll do a clean final test to verify everything works correctly.

## Test Plan

### Phase 1: Wait for Current Invocations to Complete
```powershell
python wait_for_lambdas_to_complete.py
```

This will monitor Lambda activity and wait until:
- No invocations detected for 2 minutes
- All auto-chain cycles have completed
- Safe to clear the table

**Expected duration**: 5-15 minutes (depending on current activity)

### Phase 2: Clear Staging Table
```powershell
python clear_staging_for_final_test.py
```

This will:
- Delete all 479 posts from staging
- Verify table is empty
- Prepare for fresh test

**Expected duration**: 1-2 minutes

### Phase 3: Start Monitoring
```powershell
python monitor_final_test.py
```

This will show real-time progress:
- Post counts (AWS Blog and Builder.AWS)
- Completion percentages
- ECS tasks running
- Recent errors

**Keep this running throughout the test**

### Phase 4: Trigger Crawler from Website
1. Visit: https://staging.awseuccontent.com
2. Click: "Start Crawling" button
3. Watch the orchestration complete

### Phase 5: Monitor and Verify

**What to watch for**:

✅ **Good signs**:
- Posts created steadily
- ECS tasks running (1-5 concurrent)
- Summaries increasing
- No error summaries (throttling handled by backoff)
- Auto-chain cycles visible in logs
- Eventually reaches 100% completion

⚠️ **Warning signs**:
- Posts with error summaries (shouldn't happen now)
- ECS tasks stuck
- Summaries stop increasing
- Errors in logs

**Expected timeline**:
- 0-2 min: Crawler creates all posts
- 2-10 min: ECS tasks extract authors/content
- 10-40 min: Summary generator with exponential backoff
- 40-45 min: Classifier assigns labels
- **Total: ~45 minutes** (longer than before due to backoff delays)

## Success Criteria

✅ All AWS Blog posts have:
- Authors (from RSS)
- Content (from RSS)
- Summaries (AI-generated)
- Labels (AI-classified)

✅ All Builder.AWS posts have:
- Real authors (from ECS, not "AWS Builder Community")
- Content (from ECS)
- Summaries (AI-generated)
- Labels (AI-classified)

✅ No posts with error messages as summaries
✅ No duplicate posts
✅ No missing data
✅ Auto-chaining completes all posts
✅ Exponential backoff handles throttling gracefully

## Verification Commands

**Check current status**:
```powershell
python check_summary_progress.py
```

**Check for error summaries**:
```powershell
python count_error_summaries.py
```

**Check Lambda logs**:
```powershell
python check_latest_summary_logs.py
```

**Check ECS tasks**:
```powershell
python check_ecs_task_status.py
```

## What's Different from V1

### V1 (Previous Test)
- ❌ No exponential backoff
- ❌ Error messages saved as summaries
- ❌ Required manual cleanup
- ❌ High throttling rate

### V2 (This Test)
- ✅ Exponential backoff (1s, 2s, 4s, 8s, 16s)
- ✅ Failed posts skipped (not saved with errors)
- ✅ Auto-chain retries failed posts
- ✅ Graceful throttling handling
- ✅ No manual cleanup needed

## Expected Behavior with Exponential Backoff

**Scenario 1: Light Throttling**
- First attempt fails → Wait 1s → Retry succeeds
- Post gets summary on second attempt
- Minimal delay

**Scenario 2: Moderate Throttling**
- Attempts 1-3 fail → Wait 1s, 2s, 4s → Retry succeeds
- Post gets summary on fourth attempt
- ~7s total delay

**Scenario 3: Heavy Throttling**
- All 5 attempts fail → Post skipped
- Post remains without summary
- Auto-chain picks it up in next cycle
- Eventually succeeds when rate limit allows

## Logs to Watch

**Successful retry**:
```
Throttled, waiting 2s before retry 2/5...
✓ Summary generated: This blog post demonstrates...
```

**Failed after retries**:
```
Throttled, waiting 16s before retry 5/5...
Max retries reached after throttling
⚠️  Skipped - failed to generate summary after retries
```

**Auto-chain retry**:
```
Auto-chain check: post_id=None, posts_processed=5, batch_size=5, force=False
Checking for more posts to process...
Found 42 more posts without summaries
Auto-chaining: Invoking summary generator again...
```

## Ready to Begin!

When current invocations complete, execute the test plan above and monitor the results. This will be the definitive test of the complete system with proper throttling handling.
