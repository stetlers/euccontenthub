# Final End-to-End Test Instructions

## Status: Ready to Begin! ✅

The staging table has been cleared (479 posts deleted). We're ready for the final test.

## Test Procedure

### Step 1: Start Monitoring (In Terminal 1)
```powershell
python monitor_final_test.py
```

This will show real-time progress every 30 seconds:
- Post counts (AWS Blog and Builder.AWS)
- Completion percentages (authors, summaries, labels)
- ECS tasks running
- Recent errors (if any)

### Step 2: Trigger Crawler (From Website)
1. Visit: https://staging.awseuccontent.com
2. Click the "Start Crawling" button
3. Wait for the orchestration to complete

### Expected Orchestration Flow

```
1. Enhanced Crawler Lambda
   ↓ Crawls AWS Blog RSS (immediate)
   ↓ Crawls Builder.AWS sitemap (immediate)
   ↓ Creates posts in DynamoDB
   ↓ Triggers ECS tasks for Builder.AWS posts
   
2. ECS Tasks (Selenium Crawler)
   ↓ Extracts real authors and content
   ↓ Updates DynamoDB
   ↓ Triggers summary generator
   
3. Summary Generator Lambda
   ↓ Generates AI summaries (batch of 5)
   ↓ AUTO-CHAINS to process remaining posts
   ↓ Triggers classifier for each batch
   
4. Classifier Lambda
   ↓ Assigns content type labels
   ✓ Complete!
```

### Expected Timeline

- **0-2 min**: Crawler creates all posts (AWS Blog + Builder.AWS)
- **2-10 min**: ECS tasks extract real authors/content
- **10-30 min**: Summary generator auto-chains through all posts
- **30-35 min**: Classifier assigns labels to all posts

### Success Criteria

✅ All AWS Blog posts have:
- Authors (from RSS feed)
- Content (from RSS feed)
- Summaries (AI-generated)
- Labels (AI-classified)

✅ All Builder.AWS posts have:
- Real authors (extracted by ECS, not "AWS Builder Community")
- Content (extracted by ECS)
- Summaries (AI-generated)
- Labels (AI-classified)

✅ No errors in Lambda logs
✅ No duplicate posts
✅ No missing data
✅ Auto-chaining works (processes all posts automatically)

### What to Watch For

**Good Signs**:
- Post count increases steadily
- ECS tasks show as running (1-5 tasks)
- Real authors percentage increases
- Summaries percentage increases
- No errors reported

**Warning Signs**:
- Post count stops increasing
- ECS tasks stuck at 0 or high number
- Errors appear in logs
- Percentages stop increasing

### If Something Goes Wrong

1. Check the monitoring output for errors
2. Check Lambda logs:
   ```powershell
   python check_latest_summary_logs.py
   ```
3. Check ECS task status:
   ```powershell
   python check_ecs_task_status.py
   ```
4. Let me know what you see and I'll help debug

## Ready to Begin!

When you're ready:
1. Start the monitor: `python monitor_final_test.py`
2. Click "Start Crawling" on https://staging.awseuccontent.com
3. Watch the magic happen! ✨
