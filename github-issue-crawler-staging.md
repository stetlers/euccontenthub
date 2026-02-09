# Extend Staging Support to Crawler, Summary, and Classifier Lambdas

## Overview

Extend the blue-green deployment strategy (from Issue #1) to include crawler-related Lambda functions. This enables safe testing of crawler changes before production deployment, preventing data corruption and summary loss.

## Related Issue

- **Parent Issue**: #1 - Blue-Green Deployment Implementation
- **Builds On**: Phase 1-5 of Issue #1 (staging infrastructure, API Lambda staging)

## Problem Statement

Currently, only the API Lambda (`aws-blog-api`) has staging support. The crawler-related Lambda functions deploy directly to production, which is risky because:

1. **Crawler bugs can corrupt production data** - Posts may be created incorrectly or existing data overwritten
2. **Summary wipeout risk** - Content changes trigger summary regeneration, and bugs could wipe all summaries
3. **Slow testing cycle** - Testing crawler changes in production takes hours and affects users
4. **No rollback for data** - Once data is corrupted, it's difficult to restore
5. **Auto-trigger chain affects production** - Crawler → Summary → Classifier all run in production

## Proposed Solution

Extend staging support to all crawler-related Lambda functions using environment variables:

### Lambda Functions to Update

1. **aws-blog-crawler** - AWS Blog RSS crawler
2. **aws-blog-builder-selenium-crawler** - Builder.AWS Selenium crawler (future)
3. **aws-blog-summary-generator** - AI summary generator
4. **aws-blog-classifier** - Content classifier

### Implementation Approach

**Environment Variable Strategy:**
- Add `ENVIRONMENT` environment variable to each Lambda
- Set to `production` or `staging`
- Code detects environment and appends `-staging` to table names
- Lambda invocations use correct aliases (e.g., `function-name:staging`)

**Code Changes:**
```python
# Environment detection
def get_table_suffix():
    environment = os.environ.get('ENVIRONMENT', 'production')
    return '-staging' if environment == 'staging' else ''

TABLE_SUFFIX = get_table_suffix()
TABLE_NAME = f"aws-blog-posts{TABLE_SUFFIX}"
```

## Implementation Plan

### Step 1: Create Lambda Aliases ✅ COMPLETE

- [x] Publish Version 1 for all 4 Lambda functions
- [x] Create `production` alias → Version 1
- [x] Create `staging` alias → $LATEST

### Step 2: Modify Lambda Code ✅ COMPLETE

- [x] Update `enhanced_crawler_lambda.py` with environment detection
- [x] Update `summary_lambda.py` with environment detection
- [x] Update `classifier_lambda.py` with environment detection
- [x] Update Lambda invocations to use correct aliases

**Files Modified:**
- `enhanced_crawler_lambda.py` (838 lines)
- `summary_lambda.py`
- `classifier_lambda.py`

### Step 3: Deploy to Staging ⏳ PENDING

- [ ] Deploy crawler to staging with `ENVIRONMENT=staging`
- [ ] Deploy summary generator to staging with `ENVIRONMENT=staging`
- [ ] Deploy classifier to staging with `ENVIRONMENT=staging`
- [ ] Verify environment variables set correctly

### Step 4: Test Staging Environment ⏳ PENDING

- [ ] Invoke staging crawler manually
- [ ] Verify posts created in `aws-blog-posts-staging`
- [ ] Confirm summaries generated in staging
- [ ] Verify classifications assigned in staging
- [ ] Check CloudWatch logs for correct table usage
- [ ] Confirm production data untouched

### Step 5: Documentation ⏳ PENDING

- [ ] Update DEPLOYMENT.md with crawler deployment procedures
- [ ] Update AGENTS.md with crawler staging information
- [ ] Document testing workflow for crawler changes
- [ ] Add rollback procedures for crawler functions

## Benefits

### Risk Mitigation
- ✅ Test crawler changes without affecting production data
- ✅ Catch bugs that could wipe summaries or corrupt posts
- ✅ Verify auto-trigger chain (Crawler → Summary → Classifier) works correctly
- ✅ Test with real AWS services (DynamoDB, Bedrock) in isolated environment

### Safe Testing
- ✅ Staging has 50 sample posts for testing
- ✅ Complete data isolation from production (479 posts)
- ✅ Can test destructive operations safely
- ✅ Instant rollback if issues occur (<10 seconds)

### Development Speed
- ✅ No fear of breaking production
- ✅ Faster iteration on crawler improvements
- ✅ Can test multiple approaches in parallel
- ✅ Reduces time to validate changes (hours → minutes)

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
- Check CloudWatch logs show "Using table: aws-blog-posts-staging"
- Verify production table count unchanged (479 posts)
- Confirm staging table updated with new posts

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

**Time to Rollback**: <10 seconds (instant alias update)

## Cost Impact

**No additional cost** - Uses existing:
- Lambda functions (no new functions created)
- Staging DynamoDB tables (created in Issue #1 Phase 3)
- Existing Lambda execution time

## Success Criteria

- [x] Lambda aliases created for all 4 functions
- [x] Code modified with environment detection
- [ ] Deployed to staging successfully
- [ ] Staging crawler writes to staging tables only
- [ ] Production data remains untouched during staging tests
- [ ] Auto-trigger chain works in staging (Crawler → Summary → Classifier)
- [ ] Documentation updated
- [ ] Rollback procedures tested

## Files Changed

### Modified Files
- `enhanced_crawler_lambda.py` - Added environment detection, updated Lambda invocations
- `summary_lambda.py` - Added environment detection, updated classifier invocation
- `classifier_lambda.py` - Added environment detection

### New Files
- `crawler-staging-setup.md` - Implementation documentation

### Files to Update
- `DEPLOYMENT.md` - Add crawler deployment procedures
- `AGENTS.md` - Add crawler staging information

## Timeline

- **Step 1-2**: ✅ Complete (2026-02-09)
- **Step 3**: Deploy to staging (30 minutes)
- **Step 4**: Test and validate (1 hour)
- **Step 5**: Documentation (30 minutes)

**Total Time**: ~2 hours

## Priority

**HIGH** - Crawler changes are planned for this week. Having staging support prevents production issues and enables safe testing.

## Notes

- This extends the blue-green deployment from Issue #1 to cover all Lambda functions
- Uses the same staging tables created in Issue #1 Phase 3
- Follows the same deployment pattern as the API Lambda
- No infrastructure changes needed (aliases and tables already exist)
- Ready to deploy immediately

---

**Status**: Ready for deployment
**Assignee**: AI Agent (Kiro)
**Labels**: enhancement, staging, deployment, high-priority
**Related to**: #1
