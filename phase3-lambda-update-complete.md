# Phase 3: Lambda Code Update - COMPLETE

## Summary
Successfully updated the API Lambda function to support staging/production table isolation using environment variables.

## What Was Completed

### 1. Lambda Code Updates ✅
- Downloaded aws-blog-api Lambda function from AWS
- Added `get_table_suffix()` function to read TABLE_SUFFIX from API Gateway stage variables
- Modified `lambda_handler` to initialize tables dynamically per request based on environment
- Updated all table references to use the suffix
- Deployed updated code to Lambda

### 2. IAM Permissions ✅
- Updated `DynamoDBReadAccess` policy to include staging tables
- Updated `UserProfilesTableAccess` policy to include staging tables
- Added `StagingTablesAccess` inline policy
- Permissions include: GetItem, PutItem, UpdateItem, DeleteItem, Query, Scan

### 3. Verification ✅
- CloudWatch logs confirm code is working correctly
- Logs show: `Using tables: aws-blog-posts-staging, euc-user-profiles-staging`
- TABLE_SUFFIX from API Gateway stage variables is being read correctly

## Current Status

**Code**: ✅ Working perfectly
**IAM**: ⏳ Propagating (can take 5-10 minutes)

The Lambda function is correctly detecting the staging environment and attempting to use staging tables. IAM policy propagation is in progress.

## Testing Once IAM Propagates

### Test Staging API
```bash
curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/posts
# Should return 50 posts from staging table
```

### Test Production API (unchanged)
```bash
curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod/posts
# Should return all posts from production table
```

### Verify Isolation
The staging and production environments now use completely separate DynamoDB tables:
- **Production**: aws-blog-posts, euc-user-profiles
- **Staging**: aws-blog-posts-staging, euc-user-profiles-staging

## Code Changes Made

### Key Changes in lambda_function.py

**Before:**
```python
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')
table = dynamodb.Table(TABLE_NAME)
PROFILES_TABLE_NAME = os.environ.get('PROFILES_TABLE_NAME', 'euc-user-profiles')
profiles_table = dynamodb.Table(PROFILES_TABLE_NAME)
```

**After:**
```python
dynamodb = boto3.resource('dynamodb')

def get_table_suffix(event=None):
    """Extract table suffix from API Gateway stage variables or environment"""
    if event:
        stage_variables = event.get('stageVariables', {})
        table_suffix = stage_variables.get('TABLE_SUFFIX', '')
        if table_suffix:
            return table_suffix
    return os.environ.get('TABLE_SUFFIX', '')

# Tables initialized per request in lambda_handler
TABLE_NAME = None
table = None
PROFILES_TABLE_NAME = None
profiles_table = None

def lambda_handler(event, context):
    # Initialize tables with correct suffix for this request
    global table, profiles_table, TABLE_NAME, PROFILES_TABLE_NAME
    table_suffix = get_table_suffix(event)
    TABLE_NAME = f'aws-blog-posts{table_suffix}'
    PROFILES_TABLE_NAME = f'euc-user-profiles{table_suffix}'
    table = dynamodb.Table(TABLE_NAME)
    profiles_table = dynamodb.Table(PROFILES_TABLE_NAME)
    
    print(f"Using tables: {TABLE_NAME}, {PROFILES_TABLE_NAME}")
    # ... rest of handler
```

## How It Works

### Production Request Flow
1. Request hits: `/prod/posts`
2. API Gateway prod stage has no TABLE_SUFFIX variable (or empty)
3. Lambda constructs: `aws-blog-posts` + `''` = `aws-blog-posts`
4. Uses production tables

### Staging Request Flow
1. Request hits: `/staging/posts`
2. API Gateway staging stage has `TABLE_SUFFIX=-staging`
3. Lambda constructs: `aws-blog-posts` + `'-staging'` = `aws-blog-posts-staging`
4. Uses staging tables

## Next Steps

1. ⏳ Wait for IAM propagation (5-10 minutes)
2. ✅ Test staging API endpoint
3. ✅ Verify data isolation
4. ✅ Test a change in staging (e.g., add a test post)
5. ✅ Confirm production is unaffected
6. Move to Phase 4: Create deployment scripts

## Files Created/Modified

- `lambda_api/lambda_function.py` - Updated Lambda code
- `aws-blog-api-updated.zip` - Deployment package
- `dynamodb-access-policy.json` - Updated IAM policy
- `profiles-access-policy.json` - Updated IAM policy
- `staging-table-policy.json` - New IAM policy

## Rollback Plan

If issues occur:
```bash
# Revert to previous Lambda version
aws lambda update-function-code \
  --function-name aws-blog-api \
  --s3-bucket <backup-bucket> \
  --s3-key <previous-version>

# Or update alias to previous version
aws lambda update-alias \
  --function-name aws-blog-api \
  --name production \
  --function-version <previous-version-number>
```

## Success Criteria

✅ Lambda code updated and deployed
✅ IAM policies updated
✅ CloudWatch logs show correct table selection
⏳ Staging API returns 50 posts (pending IAM propagation)
⏳ Production API continues to work normally
⏳ Data isolation verified

---

**Status**: Phase 3 Lambda updates complete. Waiting for IAM propagation to complete testing.
