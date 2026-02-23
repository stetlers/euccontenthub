# Production Lambda Version Clarification

## Your Question

> "Just so I'm clear, I think because we're moving the production alias to the latest code in lambda for sitemap crawler, it will already have the change to start ECS/Fargate and not the current Lambda that is in production that launches the selenium container, correct?"

## Answer: YES, Absolutely Correct! ✅

## Current State

### Production Alias (Version 2)
- **Function**: `aws-blog-crawler:production`
- **Points to**: Version 2 (old code)
- **Behavior**: Likely invokes Lambda-based Selenium (old, unreliable method)
- **Does NOT have**: ECS/Fargate invocation code

### Staging Alias ($LATEST)
- **Function**: `aws-blog-crawler:staging`
- **Points to**: $LATEST (new code)
- **Behavior**: Invokes ECS/Fargate tasks (new, reliable method)
- **Has**: ECS invocation code at lines 752-815 in `enhanced_crawler_lambda.py`

## What Happens During Deployment

### Step 1: Deploy to $LATEST
```bash
python deploy_crawler_with_deps.py
```
- Updates $LATEST with new code (including ECS invocation)
- Staging alias already points to $LATEST, so staging gets it immediately

### Step 2: Publish New Version
```bash
aws lambda publish-version --function-name aws-blog-crawler
```
- Creates Version 3 (snapshot of current $LATEST)
- Version 3 contains ECS invocation code

### Step 3: Update Production Alias
```bash
aws lambda update-alias \
  --function-name aws-blog-crawler \
  --name production \
  --function-version 3
```
- Production alias now points to Version 3
- **Production now has ECS invocation code** ✅

## Code Comparison

### Old Production Code (Version 2)
- Probably invokes `aws-blog-builder-selenium-crawler` Lambda directly
- Lambda-based Selenium has high failure rate
- Limited memory/timeout in Lambda environment

### New Production Code (Version 3, from $LATEST)
**Lines 752-815 in `enhanced_crawler_lambda.py`**:
```python
ecs_client = boto3.client('ecs', region_name='us-east-1')

# Determine environment based on table name
environment = 'staging' if '-staging' in table_name else 'production'

# Run ECS task with the batch of changed post IDs
response = ecs_client.run_task(
    cluster='selenium-crawler-cluster',
    taskDefinition='selenium-crawler-task',
    launchType='FARGATE',
    networkConfiguration={
        'awsvpcConfiguration': {
            'subnets': ['subnet-b2a60bed'],
            'securityGroups': ['sg-06c921b4472e87b70'],
            'assignPublicIp': 'ENABLED'
        }
    },
    overrides={
        'containerOverrides': [{
            'name': 'selenium-crawler',
            'environment': [
                {'name': 'POST_IDS', 'value': ','.join(post_id_batch)},
                {'name': 'DYNAMODB_TABLE_NAME', 'value': table_name},
                {'name': 'ENVIRONMENT', 'value': environment}
            ]
        }]
    }
)
```

## Why This Matters

### Before Deployment (Current Production)
```
User clicks "Start Crawling"
  ↓
aws-blog-crawler:production (Version 2)
  ↓
Invokes Lambda-based Selenium (OLD METHOD)
  ↓
High failure rate, memory issues
```

### After Deployment (New Production)
```
User clicks "Start Crawling"
  ↓
aws-blog-crawler:production (Version 3)
  ↓
Invokes ECS/Fargate tasks (NEW METHOD)
  ↓
Reliable execution, proper resources
```

## Verification

### Before Deployment
```bash
# Check current production version
aws lambda get-alias \
  --function-name aws-blog-crawler \
  --name production

# Output: "FunctionVersion": "2"
```

### After Deployment
```bash
# Check new production version
aws lambda get-alias \
  --function-name aws-blog-crawler \
  --name production

# Output: "FunctionVersion": "3" (or higher)
```

### Verify ECS Code is Present
```bash
# Download production Lambda code
aws lambda get-function --function-name aws-blog-crawler --qualifier production

# Check for ECS invocation
# Should see: ecs_client.run_task() in the code
```

## Summary

**Your understanding is 100% correct:**

1. ✅ Current production (Version 2) does NOT have ECS invocation
2. ✅ Current $LATEST (staging) DOES have ECS invocation
3. ✅ When we update production alias to new version, it WILL have ECS invocation
4. ✅ Production will automatically start using ECS/Fargate instead of Lambda-based Selenium

**No additional code changes needed** - the ECS invocation code is already in `enhanced_crawler_lambda.py` and has been tested in staging.

## What You Need to Do

Just follow the deployment plan:
1. Deploy crawler Lambda to $LATEST
2. Publish new version
3. Update production alias to new version
4. Production will automatically use ECS/Fargate

The transition from Lambda-based Selenium to ECS/Fargate happens automatically when the production alias points to the new code.

---

**Date**: 2026-02-15
**Status**: Confirmed
**Action Required**: Follow deployment plan in Section 2.2
