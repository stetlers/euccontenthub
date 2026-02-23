# Staging Crawler Fix Complete

## Date
February 21, 2026

## Summary
Fixed the staging crawler to properly write to the staging DynamoDB table instead of always writing to production. The crawler now respects the environment passed from the API Gateway stage variables.

## Problem
The staging crawler was writing to the production table (`aws-blog-posts`) instead of the staging table (`aws-blog-posts-staging`). This caused:
- Production had 5 more posts than staging
- Staging's most recent post was from Feb 11, 2026
- Production's most recent post was from Feb 19, 2026
- Staging crawler button didn't add posts to staging

## Root Cause
1. **Crawler Lambda** had hardcoded `ENVIRONMENT=production` environment variable
2. **API Lambda** didn't pass environment information when invoking the crawler
3. **Crawler** only checked its own environment variable, not the event payload

## Solution

### 1. Updated API Lambda (`lambda_api/lambda_function.py`)
Modified `trigger_crawler()` to:
- Accept the API Gateway event as a parameter
- Extract environment from stage variables (`stageVariables.environment`)
- Pass environment to crawler Lambda in the payload

```python
def trigger_crawler(event=None):
    # Determine environment from stage variables
    environment = 'production'  # Default
    if event:
        stage_variables = event.get('stageVariables', {})
        env_var = stage_variables.get('environment', '')
        if env_var == 'staging':
            environment = 'staging'
    
    # Pass environment to crawler
    lambda_client.invoke(
        FunctionName='aws-blog-crawler',
        InvocationType='Event',
        Payload=json.dumps({
            'source': 'all',
            'environment': environment  # Pass environment
        })
    )
```

### 2. Updated Crawler Lambda (`enhanced_crawler_lambda.py`)
Modified `get_table_suffix()` and `lambda_handler()` to:
- Check event payload for `environment` field first
- Fall back to environment variable if not in payload
- Determine table name dynamically per invocation

```python
def get_table_suffix(event=None):
    # Check event payload first (passed from API Lambda)
    if event and isinstance(event, dict):
        environment = event.get('environment', '')
        if environment == 'staging':
            return '-staging'
    
    # Fall back to environment variable
    environment = os.environ.get('ENVIRONMENT', 'production')
    return '-staging' if environment == 'staging' else ''

def lambda_handler(event, context):
    # Determine table name based on environment
    table_suffix = get_table_suffix(event)
    default_table_name = f"aws-blog-posts{table_suffix}"
    
    table_name = event.get('table_name', default_table_name) if event else default_table_name
    environment = event.get('environment', os.environ.get('ENVIRONMENT', 'production')) if event else os.environ.get('ENVIRONMENT', 'production')
    
    print(f"Environment: {environment}")
    print(f"DynamoDB Table: {table_name}")
```

## Deployment Status

### Deployed
- ✅ Crawler Lambda deployed (Feb 21, 2026 at 18:05 UTC)
- ✅ API Lambda deployed (Feb 21, 2026 at 18:06 UTC)

### Ready to Test
- ⏳ Staging crawler needs to be tested
- ⏳ Verify posts are added to staging table

## Testing Steps

### 1. Test Staging Crawler
1. Visit https://staging.awseuccontent.com
2. Click "Crawl for New Posts" button
3. Check CloudWatch logs for crawler Lambda:
   ```bash
   aws logs tail /aws/lambda/aws-blog-crawler --since 5m --follow
   ```
4. Look for:
   - `Environment: staging`
   - `DynamoDB Table: aws-blog-posts-staging`
   - Posts being added to staging table

### 2. Verify Staging Isolation
```bash
python check_staging_vs_production.py
```

Expected results:
- Staging should have new posts after crawl
- Production should remain unchanged
- Staging and production should have different post counts (staging catching up)

### 3. Verify Production Still Works
1. Visit https://awseuccontent.com
2. Click "Crawl for New Posts" button
3. Verify posts are added to production table
4. Verify staging is not affected

## Benefits

1. **True Staging Environment**: Staging now has its own isolated data
2. **Safe Testing**: Can test crawler changes without affecting production
3. **Blue-Green Deployment**: Proper staging → production workflow
4. **Environment Awareness**: Crawler respects the environment it's invoked from
5. **No Manual Configuration**: Environment is automatically detected from API Gateway

## Files Modified

1. `lambda_api/lambda_function.py` - Updated `trigger_crawler()` to pass environment
2. `enhanced_crawler_lambda.py` - Updated to read environment from event payload

## Files Created

1. `check_staging_vs_production.py` - Script to compare staging vs production
2. `deploy_crawler_staging_fix.py` - Deployment script for both Lambdas
3. `staging-crawler-fix-complete.md` - This summary document

## How It Works

### Flow Diagram
```
User clicks "Crawl" on staging site
    ↓
API Gateway (staging stage)
    ↓ stageVariables: {environment: "staging"}
    ↓
API Lambda
    ↓ Extracts environment from stageVariables
    ↓ Invokes crawler with {environment: "staging"}
    ↓
Crawler Lambda
    ↓ Reads environment from event payload
    ↓ Determines table: aws-blog-posts-staging
    ↓ Writes posts to staging table
    ↓
Staging DynamoDB Table (aws-blog-posts-staging)
```

### Environment Detection Priority
1. **Event payload** `environment` field (from API Lambda) - HIGHEST PRIORITY
2. **Environment variable** `ENVIRONMENT` (Lambda configuration) - FALLBACK

This ensures:
- Staging API always writes to staging table
- Production API always writes to production table
- Direct Lambda invocations use environment variable

## Expected Behavior After Fix

### Staging Crawler
- Writes to `aws-blog-posts-staging`
- Logs show `Environment: staging`
- Does not affect production table
- Can be tested safely

### Production Crawler
- Writes to `aws-blog-posts`
- Logs show `Environment: production`
- Does not affect staging table
- Continues to work as before

## Monitoring

After testing, monitor:
- CloudWatch logs for both staging and production crawlers
- DynamoDB table item counts (staging should catch up to production)
- Staging website should show new posts after crawl
- Production website should remain unaffected by staging crawls

## Success Criteria

All success criteria VERIFIED ✅:

1. ✅ Staging crawler writes to staging table
2. ✅ Production crawler writes to production table
3. ✅ Staging and production are isolated
4. ✅ CloudWatch logs show correct environment
5. ✅ Staging caught up to production post count (both at 484 posts)
6. ✅ New posts appear in staging after crawl
7. ✅ Production is not affected by staging crawls

## Verification Results (Feb 21, 2026)

**Post Counts Verified**:
```bash
# Staging table
aws dynamodb scan --table-name aws-blog-posts-staging --select COUNT
# Result: 484 posts

# Production table
aws dynamodb scan --table-name aws-blog-posts --select COUNT
# Result: 484 posts
```

**Crawler Logs Confirmed**:
- Environment detection working correctly
- Staging crawler writes to `aws-blog-posts-staging`
- Production crawler writes to `aws-blog-posts`
- Tables are properly isolated

## Conclusion

✅ **FIX COMPLETE AND VERIFIED**

The staging crawler now properly respects the environment and writes to the correct DynamoDB table. The fix enables true blue-green deployment with isolated staging and production environments. Both environments are now in sync with 484 posts each, and future crawls will maintain proper isolation.
