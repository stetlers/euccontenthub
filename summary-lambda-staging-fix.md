# Summary Lambda Staging Fix

## Date
February 21, 2026

## Problem
Staging has 22 posts without summaries. The summary Lambda was not respecting the staging environment when invoked by the crawler.

## Root Cause
1. **Crawler** invoked summary Lambda without passing `table_name` or `environment`
2. **Summary Lambda** used hardcoded environment variable (always `production`)
3. **Result**: Staging crawler triggered summary generation, but summaries were written to production table

## Solution

### 1. Updated Crawler Lambda (`enhanced_crawler_lambda.py`)
Modified the summary Lambda invocation to pass table name and environment:

```python
lambda_client.invoke(
    FunctionName=function_name,
    InvocationType='Event',
    Payload=json.dumps({
        'batch_size': batch_size,
        'force': False,
        'table_name': table_name,  # NEW: Pass table name
        'environment': environment  # NEW: Pass environment
    })
)
```

### 2. Updated Summary Lambda (`summary_lambda.py`)
Modified to read table name from event payload:

```python
def lambda_handler(event, context):
    # Determine table name from event or environment
    if event and event.get('table_name'):
        table_name = event['table_name']
        print(f"Using table from event: {table_name}")
    else:
        table_suffix = get_table_suffix()
        table_name = f"aws-blog-posts{table_suffix}"
        print(f"Using table from environment: {table_name}")
    
    # Use the specified table
    table = dynamodb.Table(table_name)
```

Also removed global table initialization to allow dynamic table selection per invocation.

## Files Modified
1. `enhanced_crawler_lambda.py` - Pass table_name to summary Lambda
2. `summary_lambda.py` - Read table_name from event payload

## Files Created
1. `deploy_summary_staging_fix.py` - Deployment script
2. `trigger_staging_summaries.py` - Script to manually trigger summary generation for staging
3. `summary-lambda-staging-fix.md` - This document

## Deployment Status
✅ **COMPLETE** - Both Lambdas deployed and verified (Feb 21, 2026)

### Deployed Versions
- ✅ Crawler Lambda: version 7
- ✅ Summary Lambda: version 5 (fixed handler issue)

### Verification Results
- ✅ Summaries are now visible on staging site
- ✅ Summary Lambda correctly reads table_name from event payload
- ✅ Staging and production environments properly isolated

## Testing Plan

### 1. Deploy Both Lambdas
```bash
python deploy_summary_staging_fix.py
```

### 2. Trigger Staging Summaries
```bash
python trigger_staging_summaries.py
```

### 3. Verify Summary Generation
```bash
# Check staging posts without summaries (should decrease)
aws dynamodb scan --table-name aws-blog-posts-staging \
  --filter-expression "attribute_not_exists(summary) OR summary = :empty" \
  --expression-attribute-values '{":empty":{"S":""}}' \
  --select COUNT

# Check CloudWatch logs
aws logs tail /aws/lambda/aws-blog-summary-generator --since 5m --follow
```

### 4. Verify Staging Isolation
- Staging summaries should be written to `aws-blog-posts-staging`
- Production table should remain unchanged
- CloudWatch logs should show correct table name

## Expected Behavior After Fix

### Staging Environment
- Crawler invokes summary Lambda with `table_name=aws-blog-posts-staging`
- Summary Lambda writes to staging table
- Logs show: "Using table from event: aws-blog-posts-staging"
- 22 posts should get summaries

### Production Environment
- Crawler invokes summary Lambda with `table_name=aws-blog-posts`
- Summary Lambda writes to production table
- Logs show: "Using table from event: aws-blog-posts"
- Production remains unaffected

## Benefits
1. **True Staging Environment**: Summary generation respects staging/production
2. **Proper Isolation**: Staging and production data remain separate
3. **Consistent Pattern**: Same fix as crawler Lambda (event payload > environment variable)
4. **No Manual Configuration**: Environment automatically detected from crawler invocation

## Success Criteria
- ✅ Both Lambdas deployed successfully
- ✅ Staging summaries generated for posts
- ✅ Production table unchanged
- ✅ CloudWatch logs show correct table names
- ✅ Staging and production remain isolated
- ✅ Summaries visible on staging website

## Conclusion

✅ **FIX COMPLETE AND VERIFIED**

The summary Lambda now properly respects the staging environment when invoked by the crawler. Both the crawler and summary Lambda read the table_name from the event payload, ensuring proper isolation between staging and production environments.

**Key Fix**: The deployment script was updated to rename `summary_lambda.py` to `lambda_function.py` in the zip file to match the Lambda handler configuration.
