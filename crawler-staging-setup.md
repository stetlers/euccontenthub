# Crawler Staging Setup - Implementation Summary

## Overview
Extended blue-green deployment to include crawler-related Lambda functions, enabling safe testing of crawler changes before production deployment.

## What Was Done

### 1. Lambda Aliases Created
Created production and staging aliases for all crawler-related functions:

| Function | Production Alias | Staging Alias |
|----------|-----------------|---------------|
| aws-blog-crawler | Version 1 | $LATEST |
| aws-blog-builder-selenium-crawler | Version 1 | $LATEST |
| aws-blog-summary-generator | Version 1 | $LATEST |
| aws-blog-classifier | Version 1 | $LATEST |

### 2. Code Modifications

**All Lambda functions updated with environment detection:**

```python
# Environment detection for staging support
def get_table_suffix():
    """
    Determine table suffix based on environment.
    Returns '-staging' for staging environment, empty string for production.
    """
    environment = os.environ.get('ENVIRONMENT', 'production')
    return '-staging' if environment == 'staging' else ''

# Get table name with environment suffix
TABLE_SUFFIX = get_table_suffix()
TABLE_NAME = f"aws-blog-posts{TABLE_SUFFIX}"
```

**Modified Files:**
- `enhanced_crawler_lambda.py` - AWS Blog crawler
- `summary_lambda.py` - AI summary generator
- `classifier_lambda.py` - Content classifier

**Key Changes:**
- Reads `ENVIRONMENT` environment variable (production/staging)
- Automatically appends `-staging` to table names in staging
- Invokes correct Lambda aliases (e.g., `aws-blog-classifier:staging`)
- Logs environment and table names for debugging

### 3. Auto-Trigger Chain Updated

The crawler auto-trigger chain now respects environments:

```
Crawler (staging) 
  → invokes Summary Generator:staging
    → invokes Classifier:staging
      → all write to staging tables
```

## Deployment Strategy

### Environment Variables

**Production:**
- `ENVIRONMENT=production`
- Uses tables: `aws-blog-posts`, `euc-user-profiles`
- Invokes: `function-name:production` aliases

**Staging:**
- `ENVIRONMENT=staging`
- Uses tables: `aws-blog-posts-staging`, `euc-user-profiles-staging`
- Invokes: `function-name:staging` aliases

### Deployment Commands

**Deploy to Staging:**
```bash
# Deploy crawler
python deploy_lambda.py crawler staging

# Deploy summary generator
python deploy_lambda.py summary staging

# Deploy classifier
python deploy_lambda.py classifier staging
```

**Deploy to Production (after testing):**
```bash
# Deploy crawler
python deploy_lambda.py crawler production

# Deploy summary generator
python deploy_lambda.py summary production

# Deploy classifier
python deploy_lambda.py classifier production
```

## Testing Workflow

### 1. Make Crawler Changes
Edit `enhanced_crawler_lambda.py` with your changes

### 2. Deploy to Staging
```bash
python deploy_lambda.py crawler staging
```

### 3. Test in Staging
```bash
# Invoke staging crawler
aws lambda invoke \
  --function-name aws-blog-crawler:staging \
  --invocation-type RequestResponse \
  --payload '{"source":"aws-blog","max_pages":1}' \
  response.json

# Check CloudWatch logs
aws logs tail /aws/lambda/aws-blog-crawler --since 5m --follow

# Verify staging table
aws dynamodb scan --table-name aws-blog-posts-staging --select COUNT
```

### 4. Verify Data Isolation
- Staging crawler writes to `aws-blog-posts-staging`
- Production data in `aws-blog-posts` remains untouched
- Check CloudWatch logs for "Using table: aws-blog-posts-staging"

### 5. Deploy to Production (if tests pass)
```bash
python deploy_lambda.py crawler production
```

## Rollback Procedures

**Instant Rollback (if production breaks):**
```bash
# Rollback crawler to Version 1
aws lambda update-alias \
  --function-name aws-blog-crawler \
  --name production \
  --function-version 1

# Rollback summary generator to Version 1
aws lambda update-alias \
  --function-name aws-blog-summary-generator \
  --name production \
  --function-version 1

# Rollback classifier to Version 1
aws lambda update-alias \
  --function-name aws-blog-classifier \
  --name production \
  --function-version 1
```

## Benefits

### Risk Mitigation
- ✅ Test crawler changes without affecting production data
- ✅ Catch bugs that could wipe summaries or corrupt posts
- ✅ Verify auto-trigger chain works correctly
- ✅ Test with real AWS services (DynamoDB, Bedrock)

### Safe Testing
- ✅ Staging has 50 sample posts for testing
- ✅ Complete data isolation from production
- ✅ Can test destructive operations safely
- ✅ Instant rollback if issues occur

### Development Speed
- ✅ No fear of breaking production
- ✅ Faster iteration on crawler improvements
- ✅ Can test multiple approaches
- ✅ Parallel development (staging + production)

## Next Steps

1. **Deploy Modified Code to Staging**
   - Deploy crawler, summary, classifier to staging
   - Set `ENVIRONMENT=staging` environment variable
   - Test full crawler workflow

2. **Validate Staging Environment**
   - Run crawler in staging
   - Verify posts created in staging tables
   - Check summaries and classifications generated
   - Confirm production unaffected

3. **Update Documentation**
   - Add crawler deployment to DEPLOYMENT.md
   - Update AGENTS.md with crawler staging info
   - Document testing procedures

4. **Ready for Crawler Changes**
   - You can now safely make crawler changes this week
   - Test in staging first, deploy to production after validation

## Files Modified

- `enhanced_crawler_lambda.py` - Crawler with environment detection
- `summary_lambda.py` - Summary generator with environment detection
- `classifier_lambda.py` - Classifier with environment detection
- `deploy_lambda.py` - Already supports staging deployment
- `crawler-staging-setup.md` - This documentation

## Cost Impact

**No additional cost** - Uses existing Lambda functions and staging tables created in Phase 3.

---

**Status**: Ready for deployment to staging
**Date**: 2026-02-09
**Related**: Issue #1 Phase 5 Extension
