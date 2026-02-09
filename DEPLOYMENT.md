# Deployment Runbook

## Overview

This runbook provides step-by-step instructions for deploying changes to the EUC Content Hub using the blue-green deployment strategy.

**Key Principle**: Always deploy to staging first, test thoroughly, then promote to production.

---

## Prerequisites

### Required Tools
- Python 3.x with boto3
- AWS CLI configured with valid credentials
- Git
- Access to AWS account 031421429609

### Environment Setup

Before deploying, ensure your environment is configured:

```powershell
# Set AWS credentials (8-hour expiry)
$Env:AWS_ACCESS_KEY_ID="ASIA..."
$Env:AWS_SECRET_ACCESS_KEY="..."
$Env:AWS_SESSION_TOKEN="IQoJb3JpZ2luX2VjE..."
$Env:AWS_DEFAULT_REGION="us-east-1"

# Verify credentials
aws sts get-caller-identity
```

---

## Deployment Workflows

### Frontend Deployment

#### 1. Deploy to Staging

```bash
# Deploy frontend files to staging
python deploy_frontend.py staging
```

**What happens:**
- Uploads 7 frontend files to S3 bucket: `aws-blog-viewer-staging-031421429609`
- Sets correct content types and cache headers
- Invalidates CloudFront distribution: `E1IB9VDMV64CQA`
- Files available at: https://staging.awseuccontent.com

#### 2. Test Staging

**Manual Testing Checklist:**
- [ ] Site loads at https://staging.awseuccontent.com
- [ ] No console errors in browser
- [ ] Authentication works (sign in/sign out)
- [ ] Posts load correctly
- [ ] Filtering works (by source, label, search)
- [ ] User profile loads
- [ ] Bookmarks work
- [ ] Voting works
- [ ] Comments work
- [ ] Chat widget works
- [ ] All links functional

**API Testing:**
```bash
# Test staging API
curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/posts
```

#### 3. Deploy to Production (if tests pass)

```bash
# Deploy frontend files to production
python deploy_frontend.py production
```

**What happens:**
- Uploads files to S3 bucket: `aws-blog-viewer-031421429609`
- Invalidates CloudFront distribution: `E20CC1TSSWTCWN`
- Files available at: https://awseuccontent.com

#### 4. Verify Production

- [ ] Site loads at https://awseuccontent.com
- [ ] Quick smoke test of critical features
- [ ] Monitor CloudWatch logs for errors
- [ ] Check user reports/feedback

---

### Lambda Deployment

#### 1. Deploy to Staging

```bash
# Deploy Lambda function to staging
python deploy_lambda.py <function_name> staging

# Examples:
python deploy_lambda.py api_lambda staging
python deploy_lambda.py crawler staging
python deploy_lambda.py summary staging
```

**Available Functions:**
- `api_lambda` - API Lambda for blog posts viewer
- `crawler` - AWS Blog crawler
- `builder_crawler` - Builder.AWS Selenium crawler
- `summary` - AI summary generator
- `classifier` - Content classifier
- `chat` - AI chat assistant

**What happens:**
- Creates deployment package from source file
- Uploads to Lambda function
- Staging uses `$LATEST` version (immediate deployment)
- Changes available immediately in staging

#### 2. Test Staging

**API Testing:**
```bash
# Test staging API endpoint
curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/posts

# Test specific functionality based on what changed
# For crawler: Trigger crawler and verify posts are created
# For summary: Check that summaries are generated
# For classifier: Verify labels are assigned
```

**CloudWatch Logs:**
```bash
# Check for errors in staging
aws logs tail /aws/lambda/<function-name> --since 5m --follow
```

**Staging Database Check:**
```bash
# Verify staging tables are being used
aws logs tail /aws/lambda/aws-blog-api --since 5m --filter-pattern "Using tables"
# Should show: "Using tables: aws-blog-posts-staging, euc-user-profiles-staging"
```

#### 3. Deploy to Production (if tests pass)

```bash
# Deploy Lambda function to production
python deploy_lambda.py <function_name> production
```

**What happens:**
- Creates deployment package
- Uploads to Lambda function
- Publishes new version
- Updates production alias to point to new version
- Changes available immediately in production

#### 4. Verify Production

```bash
# Test production API
curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod/posts

# Monitor CloudWatch logs
aws logs tail /aws/lambda/<function-name> --since 5m --follow

# Verify production tables are being used
aws logs tail /aws/lambda/aws-blog-api --since 5m --filter-pattern "Using tables"
# Should show: "Using tables: aws-blog-posts, euc-user-profiles"
```

---

## Rollback Procedures

### Frontend Rollback

**Option 1: Redeploy Previous Version**
```bash
# Checkout previous commit
git log --oneline  # Find the commit hash
git checkout <previous-commit-hash>

# Redeploy to production
python deploy_frontend.py production

# Return to latest
git checkout main
```

**Option 2: Manual S3 Restore**
- Use AWS Console to restore previous versions from S3 versioning
- Invalidate CloudFront cache

**Time to Rollback**: 2-3 minutes

---

### Lambda Rollback

**Instant Rollback (Recommended)**
```bash
# List recent versions
aws lambda list-versions-by-function --function-name aws-blog-api

# Update production alias to previous version
aws lambda update-alias \
  --function-name aws-blog-api \
  --name production \
  --function-version <previous-version-number>
```

**Time to Rollback**: Instant (< 10 seconds)

**Example:**
```bash
# Rollback API Lambda to version 5
aws lambda update-alias \
  --function-name aws-blog-api \
  --name production \
  --function-version 5
```

---

## Common Deployment Scenarios

### Scenario 1: Bug Fix in Frontend

```bash
# 1. Fix the bug in code
# 2. Test locally
# 3. Deploy to staging
python deploy_frontend.py staging

# 4. Test staging thoroughly
# Visit https://staging.awseuccontent.com

# 5. Deploy to production
python deploy_frontend.py production

# 6. Verify production
# Visit https://awseuccontent.com
```

**Time**: 5-10 minutes

---

### Scenario 2: API Lambda Update

```bash
# 1. Update lambda_api/lambda_function.py
# 2. Deploy to staging
python deploy_lambda.py api_lambda staging

# 3. Test staging API
curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/posts

# 4. Check CloudWatch logs
aws logs tail /aws/lambda/aws-blog-api --since 5m

# 5. Deploy to production
python deploy_lambda.py api_lambda production

# 6. Verify production
curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod/posts
```

**Time**: 5-10 minutes

---

### Scenario 3: Crawler Update (High Risk)

**Why High Risk**: Crawler bugs can corrupt data or wipe summaries

```bash
# 1. Update crawler code
# 2. Deploy to staging
python deploy_lambda.py crawler staging

# 3. Test in staging with REAL crawl
# Trigger crawler through staging API or AWS Console
# Wait for completion

# 4. Verify staging data integrity
# Check that posts were created correctly
# Verify summaries weren't wiped
# Check that existing data is intact

# 5. If all tests pass, deploy to production
python deploy_lambda.py crawler production

# 6. Monitor production closely
# Watch CloudWatch logs
# Check DynamoDB for data integrity
```

**Time**: 15-30 minutes (includes crawl time)

---

### Scenario 4: Emergency Rollback

**If production is broken:**

```bash
# Lambda (instant)
aws lambda update-alias \
  --function-name aws-blog-api \
  --name production \
  --function-version <last-known-good-version>

# Frontend (2-3 minutes)
git checkout <last-known-good-commit>
python deploy_frontend.py production
git checkout main
```

**Time**: < 1 minute for Lambda, 2-3 minutes for frontend

---

## Monitoring & Validation

### CloudWatch Logs

**View recent logs:**
```bash
aws logs tail /aws/lambda/aws-blog-api --since 10m --follow
```

**Search for errors:**
```bash
aws logs tail /aws/lambda/aws-blog-api --since 1h --filter-pattern "ERROR"
```

**Check table selection:**
```bash
aws logs tail /aws/lambda/aws-blog-api --since 5m --filter-pattern "Using tables"
```

### DynamoDB Monitoring

**Check table item counts:**
```bash
# Staging
aws dynamodb scan --table-name aws-blog-posts-staging --select COUNT

# Production
aws dynamodb scan --table-name aws-blog-posts --select COUNT
```

### API Health Checks

**Staging:**
```bash
curl -I https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/posts
```

**Production:**
```bash
curl -I https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod/posts
```

---

## Troubleshooting

### Issue: "Unable to locate credentials"

**Cause**: AWS credentials not set in environment

**Solution:**
```powershell
$Env:AWS_ACCESS_KEY_ID="ASIA..."
$Env:AWS_SECRET_ACCESS_KEY="..."
$Env:AWS_SESSION_TOKEN="IQoJb3JpZ2luX2VjE..."
$Env:AWS_DEFAULT_REGION="us-east-1"
```

---

### Issue: Deployment script fails to upload

**Cause**: Network issue or permission problem

**Solution:**
1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check network connectivity
3. Verify IAM permissions for S3/Lambda
4. Retry deployment

---

### Issue: CloudFront still serving old content

**Cause**: Cache invalidation in progress or failed

**Solution:**
1. Wait 1-2 minutes for invalidation to complete
2. Check invalidation status in AWS Console
3. Hard refresh browser (Ctrl+F5)
4. Create manual invalidation if needed:
```bash
aws cloudfront create-invalidation \
  --distribution-id E20CC1TSSWTCWN \
  --paths "/*"
```

---

### Issue: Staging shows production data

**Cause**: Lambda not using staging tables

**Solution:**
1. Check CloudWatch logs for table selection
2. Verify API Gateway stage variables:
```bash
aws apigateway get-stage --rest-api-id xox05733ce --stage-name staging
```
3. Ensure `TABLE_SUFFIX=-staging` is set
4. Redeploy Lambda if needed

---

## Best Practices

### ✅ DO

- Always deploy to staging first
- Test thoroughly in staging before production
- Monitor CloudWatch logs after deployment
- Keep deployment scripts up to date
- Document any manual steps taken
- Verify environment variables before deploying
- Use version control for all code changes
- Test rollback procedures periodically

### ❌ DON'T

- Deploy directly to production without staging test
- Deploy on Friday afternoon (limited monitoring time)
- Deploy multiple changes at once (hard to debug)
- Skip testing in staging
- Ignore CloudWatch errors
- Deploy without valid AWS credentials
- Make manual changes without documenting
- Deploy when tired or rushed

---

## Deployment Checklist

### Pre-Deployment
- [ ] Code changes committed to Git
- [ ] AWS credentials configured and valid
- [ ] Environment variables set
- [ ] Deployment scripts tested locally
- [ ] Staging environment ready

### Staging Deployment
- [ ] Deployed to staging successfully
- [ ] Staging site/API tested
- [ ] CloudWatch logs checked
- [ ] No errors found
- [ ] Data integrity verified

### Production Deployment
- [ ] Staging tests passed
- [ ] Deployed to production successfully
- [ ] Production site/API verified
- [ ] CloudWatch logs monitored
- [ ] No errors detected
- [ ] User-facing features working

### Post-Deployment
- [ ] Monitoring in place
- [ ] Team notified of deployment
- [ ] Documentation updated if needed
- [ ] Rollback plan ready if needed

---

## Contact & Resources

- **AWS Account**: 031421429609
- **Region**: us-east-1
- **Production Site**: https://awseuccontent.com
- **Staging Site**: https://staging.awseuccontent.com
- **GitHub**: https://github.com/stetlers/euccontenthub
- **CloudWatch Logs**: AWS Console → CloudWatch → Log Groups

---

## Deployment History

Track major deployments here:

| Date | Type | Environment | Changes | Result |
|------|------|-------------|---------|--------|
| 2026-02-09 | Frontend | Staging | Tested deployment script | ✅ Success |
| 2026-02-08 | Frontend | Staging | GitHub footer link fix | ✅ Success |
| 2026-02-08 | Frontend | Production | GitHub footer link fix | ✅ Success |

---

**Last Updated**: 2026-02-09
**Version**: 1.0
