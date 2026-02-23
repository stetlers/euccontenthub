# Builder.AWS Posts Restoration Failure - Root Cause Analysis

## Problem
When users click "Start Crawl", Builder.AWS posts lose their summaries and labels, but they are NOT being restored.

## Investigation Results

### What's Working ✓
1. **Sitemap Crawler** - Running successfully
   - Detects 17 changed Builder.AWS posts
   - Wipes summaries/labels (by design)
   - Invokes ECS Selenium crawler

2. **ECS Task Creation** - Successful
   - Task ID: `b899db46b4774287946b8b48f4e88edc`
   - Created at: 13:30:10
   - Command executed successfully

### What's Broken ✗
3. **ECS Task Execution** - FAILING
   - Task was created but NEVER RAN
   - No logs in `/ecs/selenium-crawler`
   - Task not found in stopped tasks (cleaned up)
   - This breaks the entire restoration chain

## Root Cause

**The ECS Selenium crawler tasks are being created but failing to start.**

Possible reasons:
1. **Docker image issue** - Image doesn't exist or can't be pulled
2. **IAM permissions** - Task role lacks required permissions
3. **Network configuration** - Can't reach ECR or other AWS services
4. **Resource constraints** - Not enough CPU/memory available
5. **Task definition issue** - Invalid configuration

## Impact

When the ECS task fails:
- Posts keep placeholder authors ("Builder.AWS Team")
- Posts keep placeholder content
- Summaries remain empty
- Labels remain empty
- Summary generator is never invoked
- Classifier is never invoked

## Current State

- **85 Builder.AWS posts total**
- **26 posts (30.6%) have summaries** - These are old, from before the issue started
- **59 posts (69.4%) missing summaries** - These lost summaries and were never restored

## Next Steps

1. **Check ECS task definition**
   ```bash
   python check_ecs_task_definition.py
   ```

2. **Check Docker image exists**
   ```bash
   aws ecr describe-images --repository-name selenium-crawler --region us-east-1
   ```

3. **Check task role permissions**
   - Needs: `dynamodb:GetItem`, `dynamodb:UpdateItem`, `lambda:InvokeFunction`

4. **Check CloudWatch Logs configuration**
   - Log group: `/ecs/selenium-crawler`
   - Must exist and have correct permissions

5. **Manual test**
   ```bash
   aws ecs run-task \
     --cluster selenium-crawler-cluster \
     --task-definition selenium-crawler-task \
     --launch-type FARGATE \
     --network-configuration "awsvpcConfiguration={subnets=[subnet-b2a60bed],securityGroups=[sg-06c921b4472e87b70],assignPublicIp=ENABLED}"
   ```

## Temporary Workaround

Manually regenerate summaries for the 59 posts without them:
```bash
python generate_all_builder_summaries.py
```

This will:
1. Find all posts without summaries
2. Invoke summary generator in batches
3. Auto-chain to classifier
4. Restore summaries and labels

## Timeline

- **Before**: System worked, posts were restored automatically
- **Now**: ECS tasks fail silently, posts never get restored
- **Change**: Something changed in ECS configuration, Docker image, or IAM permissions
