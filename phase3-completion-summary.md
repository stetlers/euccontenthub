# Phase 3: DynamoDB Strategy - Completion Summary

## What Was Completed

### 1. Created Staging DynamoDB Tables ✅
- **aws-blog-posts-staging**: Staging table for blog posts
  - Same schema as production (post_id as primary key)
  - PAY_PER_REQUEST billing mode
  - Status: ACTIVE
  
- **euc-user-profiles-staging**: Staging table for user profiles
  - Same schema as production (user_id as primary key)
  - PAY_PER_REQUEST billing mode
  - Status: ACTIVE

### 2. Copied Sample Data ✅
- **50 blog posts** copied from production to staging
- **3 user profiles** copied from production to staging
- Script created: `copy_data_to_staging.py` for future data refreshes

### 3. Configured Lambda Environment Variables ✅
Updated all 6 Lambda functions with environment variables:
- aws-blog-api
- aws-blog-crawler
- aws-blog-builder-selenium-crawler
- aws-blog-summary-generator
- aws-blog-classifier
- aws-blog-chat-assistant

Added variables:
- `POSTS_TABLE`: aws-blog-posts
- `PROFILES_TABLE`: euc-user-profiles
- `TABLE_SUFFIX`: (empty for production, will be set per environment)

### 4. Configured API Gateway Stage Variables ✅
Updated staging stage with:
- `TABLE_SUFFIX`: -staging
- `environment`: staging
- `lambdaAlias`: staging

---

## What Needs to Be Done Next

### Critical: Update Lambda Code
The Lambda functions need code changes to use the environment variables for table selection.

**Current code pattern:**
```python
table = dynamodb.Table('aws-blog-posts')
```

**New code pattern needed:**
```python
import os

# Get table suffix from stage variable (passed through event context)
# or from environment variable
TABLE_SUFFIX = os.environ.get('TABLE_SUFFIX', '')

# Use suffix to select correct table
posts_table = dynamodb.Table(f'aws-blog-posts{TABLE_SUFFIX}')
profiles_table = dynamodb.Table(f'euc-user-profiles{TABLE_SUFFIX}')
```

**How stage variables reach Lambda:**
API Gateway passes stage variables through the event context. Lambda needs to:
1. Extract stage variable from event
2. Set it as environment variable for the function execution
3. Use it to construct table names

**Example for API Lambda:**
```python
def lambda_handler(event, context):
    # Get stage variables from API Gateway
    stage_variables = event.get('stageVariables', {})
    table_suffix = stage_variables.get('TABLE_SUFFIX', '')
    
    # Or use environment variable set on the Lambda
    if not table_suffix:
        table_suffix = os.environ.get('TABLE_SUFFIX', '')
    
    # Use suffix for table selection
    posts_table = dynamodb.Table(f'aws-blog-posts{table_suffix}')
    profiles_table = dynamodb.Table(f'euc-user-profiles{table_suffix}')
    
    # Rest of handler code...
```

### Files That Need Updates
1. **api_lambda.py** (or lambda_function.py in deployment)
2. **enhanced_crawler_lambda.py**
3. **builder_selenium_crawler.py**
4. **summary_lambda.py**
5. **classifier_lambda.py**
6. **chat_lambda.py**

---

## Testing Plan

Once Lambda code is updated:

### 1. Test Staging Environment
```bash
# Test API endpoint with staging
curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/posts

# Should return the 50 posts from staging table
```

### 2. Test Data Isolation
- Make a change in staging (e.g., add a test post)
- Verify it doesn't appear in production
- Verify production data is unchanged

### 3. Test Crawler in Staging
- Trigger crawler through staging API
- Verify new posts go to staging table only
- Verify summaries are generated in staging table

### 4. Test User Operations in Staging
- Test login with staging frontend
- Test bookmarks, votes, comments
- Verify changes only affect staging tables

---

## Cost Impact

**Additional Monthly Costs:**
- aws-blog-posts-staging: ~$0.25/month (50 items, minimal reads/writes)
- euc-user-profiles-staging: ~$0.25/month (3 items, minimal reads/writes)

**Total: ~$0.50/month** (negligible)

---

## Rollback Plan

If issues arise:
1. Staging tables can be deleted without affecting production
2. Lambda environment variables can be removed
3. API Gateway stage variables can be removed
4. Production continues to work unchanged

---

## Next Phase

After Lambda code updates are complete, move to:
- **Phase 4**: Create deployment scripts
- **Phase 5**: Documentation and final testing

---

## Commands for Reference

### Refresh Staging Data
```bash
python copy_data_to_staging.py
```

### Check Table Status
```bash
aws dynamodb describe-table --table-name aws-blog-posts-staging
aws dynamodb describe-table --table-name euc-user-profiles-staging
```

### View Stage Variables
```bash
aws apigateway get-stage --rest-api-id xox05733ce --stage-name staging
```

### Delete Staging Tables (if needed)
```bash
aws dynamodb delete-table --table-name aws-blog-posts-staging
aws dynamodb delete-table --table-name euc-user-profiles-staging
```
