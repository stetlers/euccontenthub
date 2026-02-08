# Blue-Green Deployment Implementation Plan
## Issue #1 - Critical Priority

## Current Problem
- Any deployment change can break the production site
- No way to test changes before they go live
- Recent deployments broke the API Lambda multiple times
- Users experience downtime during deployments

## Goal
Create a complete staging environment where changes can be tested safely before promoting to production.

---

## Architecture Overview

### Production Environment (Current)
- **Domain**: awseuccontent.com
- **S3 Bucket**: aws-blog-viewer-031421429609
- **CloudFront**: E20CC1TSSWTCWN
- **API Gateway**: xox05733ce (prod stage)
- **Lambda Functions**: Production versions
- **DynamoDB**: Shared tables (with isolation strategy)

### Staging Environment (New)
- **Domain**: staging.awseuccontent.com (or dev.awseuccontent.com)
- **S3 Bucket**: aws-blog-viewer-staging-031421429609 (new)
- **CloudFront**: New distribution for staging
- **API Gateway**: xox05733ce (staging stage - new)
- **Lambda Functions**: Staging aliases/versions
- **DynamoDB**: Same tables with staging data isolation

---

## Implementation Phases

### Phase 1: Infrastructure Setup (Day 1-2)

#### 1.1 Create Staging S3 Bucket
```bash
aws s3 mb s3://aws-blog-viewer-staging-031421429609 --region us-east-1
aws s3 website s3://aws-blog-viewer-staging-031421429609 --index-document index.html
```

**Bucket Policy** (same as production):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::aws-blog-viewer-staging-031421429609/*"
    }
  ]
}
```

#### 1.2 Create Staging CloudFront Distribution
- Origin: aws-blog-viewer-staging-031421429609.s3.us-east-1.amazonaws.com
- Alternate domain: staging.awseuccontent.com
- SSL Certificate: Request new ACM cert for staging.awseuccontent.com
- Cache behaviors: Same as production
- Error pages: Same as production

#### 1.3 Configure DNS
Add CNAME record in Route 53:
```
staging.awseuccontent.com -> [staging-cloudfront-domain].cloudfront.net
```

#### 1.4 Create API Gateway Staging Stage
```bash
# Create new stage in existing API Gateway
aws apigateway create-deployment \
  --rest-api-id xox05733ce \
  --stage-name staging \
  --description "Staging environment"
```

**Stage Variables**:
- `environment`: staging
- `lambdaAlias`: staging

---

### Phase 2: Lambda Configuration (Day 2-3)

#### 2.1 Lambda Aliases Strategy
For each Lambda function, create aliases:
- **Production Alias**: Points to specific version (e.g., v5)
- **Staging Alias**: Points to $LATEST or specific test version

**Lambda Functions to Configure**:
1. aws-blog-api
2. aws-blog-crawler
3. builder-selenium-crawler
4. aws-blog-summary-generator
5. aws-blog-classifier
6. aws-blog-chat-assistant

**Create Aliases** (example for API Lambda):
```bash
# Publish current production version
PROD_VERSION=$(aws lambda publish-version \
  --function-name aws-blog-api \
  --description "Production stable version" \
  --query 'Version' --output text)

# Create production alias pointing to this version
aws lambda create-alias \
  --function-name aws-blog-api \
  --name production \
  --function-version $PROD_VERSION

# Create staging alias pointing to $LATEST
aws lambda create-alias \
  --function-name aws-blog-api \
  --name staging \
  --function-version '$LATEST'
```

#### 2.2 Update API Gateway Integration
Update API Gateway to use Lambda aliases:
```
Production: arn:aws:lambda:us-east-1:031421429609:function:aws-blog-api:production
Staging: arn:aws:lambda:us-east-1:031421429609:function:aws-blog-api:staging
```

---

### Phase 3: DynamoDB Strategy (Day 3)

#### Option A: Shared Tables with Prefix (Recommended)
**Pros**: Cost-effective, simpler
**Cons**: Risk of data mixing if not careful

**Implementation**:
- Use same tables: aws-blog-posts, euc-user-profiles
- Add `environment` attribute to distinguish data
- Filter queries by environment in staging

**Code Changes**:
```python
# In Lambda functions
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')

# When querying
response = table.scan(
    FilterExpression='environment = :env',
    ExpressionAttributeValues={':env': ENVIRONMENT}
)

# When writing
item['environment'] = ENVIRONMENT
```

#### Option B: Separate Tables (Safer)
**Pros**: Complete isolation, no risk of data mixing
**Cons**: Higher cost, more complex

**Implementation**:
- Create: aws-blog-posts-staging, euc-user-profiles-staging
- Use environment variable to select table name
- Copy production data to staging for testing

```python
TABLE_SUFFIX = '-staging' if os.environ.get('ENVIRONMENT') == 'staging' else ''
table = dynamodb.Table(f'aws-blog-posts{TABLE_SUFFIX}')
```

**Recommendation**: Start with Option A, move to Option B if needed.

---

### Phase 4: Deployment Scripts (Day 4)

#### 4.1 Frontend Deployment Script
**File**: `deploy_frontend.py`

```python
import boto3
import sys
import os

def deploy_frontend(environment='production'):
    """Deploy frontend to specified environment"""
    
    if environment == 'production':
        bucket = 'aws-blog-viewer-031421429609'
        distribution_id = 'E20CC1TSSWTCWN'
    elif environment == 'staging':
        bucket = 'aws-blog-viewer-staging-031421429609'
        distribution_id = 'STAGING_DISTRIBUTION_ID'  # Update after creation
    else:
        raise ValueError(f"Unknown environment: {environment}")
    
    s3 = boto3.client('s3')
    cloudfront = boto3.client('cloudfront')
    
    # Upload files
    files = ['index.html', 'app.js', 'auth.js', 'profile.js', 
             'chat-widget.js', 'styles.css']
    
    for file in files:
        print(f"Uploading {file} to {bucket}...")
        s3.upload_file(
            f'frontend/{file}',
            bucket,
            file,
            ExtraArgs={'ContentType': get_content_type(file)}
        )
    
    # Invalidate CloudFront
    print(f"Invalidating CloudFront distribution {distribution_id}...")
    cloudfront.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            'Paths': {'Quantity': 1, 'Items': ['/*']},
            'CallerReference': str(time.time())
        }
    )
    
    print(f"✅ Frontend deployed to {environment}")
    if environment == 'staging':
        print(f"🔗 View at: https://staging.awseuccontent.com")
    else:
        print(f"🔗 View at: https://awseuccontent.com")

if __name__ == '__main__':
    env = sys.argv[1] if len(sys.argv) > 1 else 'staging'
    deploy_frontend(env)
```

**Usage**:
```bash
# Deploy to staging (default)
python deploy_frontend.py staging

# Deploy to production (after testing)
python deploy_frontend.py production
```

#### 4.2 Lambda Deployment Script
**File**: `deploy_lambda.py`

```python
import boto3
import sys
import zipfile
import os

def deploy_lambda(function_name, environment='staging'):
    """Deploy Lambda function to specified environment"""
    
    lambda_client = boto3.client('lambda')
    
    # Create deployment package
    zip_file = f'{function_name}.zip'
    with zipfile.ZipFile(zip_file, 'w') as zf:
        zf.write(f'{function_name}.py', 'lambda_function.py')
    
    # Upload to Lambda
    with open(zip_file, 'rb') as f:
        zip_content = f.read()
    
    print(f"Updating {function_name} code...")
    lambda_client.update_function_code(
        FunctionName=function_name,
        ZipFile=zip_content
    )
    
    # Wait for update to complete
    waiter = lambda_client.get_waiter('function_updated')
    waiter.wait(FunctionName=function_name)
    
    if environment == 'staging':
        # Staging uses $LATEST (no publish needed)
        print(f"✅ {function_name} updated in staging (using $LATEST)")
    else:
        # Production: publish new version and update alias
        print(f"Publishing new version for production...")
        version_response = lambda_client.publish_version(
            FunctionName=function_name,
            Description=f"Production deployment {datetime.now()}"
        )
        new_version = version_response['Version']
        
        # Update production alias
        lambda_client.update_alias(
            FunctionName=function_name,
            Name='production',
            FunctionVersion=new_version
        )
        print(f"✅ {function_name} deployed to production (version {new_version})")
    
    os.remove(zip_file)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python deploy_lambda.py <function_name> [environment]")
        sys.exit(1)
    
    function = sys.argv[1]
    env = sys.argv[2] if len(sys.argv) > 2 else 'staging'
    deploy_lambda(function, env)
```

**Usage**:
```bash
# Deploy to staging
python deploy_lambda.py api_lambda staging

# Deploy to production (after testing)
python deploy_lambda.py api_lambda production
```

---

### Phase 5: Testing & Validation (Day 5)

#### 5.1 Staging Environment Checklist
- [ ] Staging site loads at staging.awseuccontent.com
- [ ] All frontend files served correctly
- [ ] API endpoints respond (staging API Gateway)
- [ ] Authentication works (Cognito)
- [ ] Posts load from DynamoDB
- [ ] User profiles work
- [ ] Voting works
- [ ] Comments work
- [ ] Bookmarks work
- [ ] Chat assistant works
- [ ] Crawlers can be triggered
- [ ] Summaries generate
- [ ] Classification works

#### 5.2 Deployment Workflow Test
1. Make a small change to frontend (e.g., add test banner)
2. Deploy to staging: `python deploy_frontend.py staging`
3. Verify change on staging.awseuccontent.com
4. If good, deploy to production: `python deploy_frontend.py production`
5. Verify production unchanged until promotion

#### 5.3 Lambda Deployment Test
1. Make a small change to API Lambda (e.g., add log statement)
2. Deploy to staging: `python deploy_lambda.py api_lambda staging`
3. Test API on staging
4. If good, deploy to production: `python deploy_lambda.py api_lambda production`
5. Verify production works correctly

---

### Phase 6: Documentation & Rollback (Day 5)

#### 6.1 Deployment Runbook
**File**: `DEPLOYMENT.md`

```markdown
# Deployment Runbook

## Pre-Deployment Checklist
- [ ] Changes tested locally
- [ ] Code reviewed
- [ ] No breaking changes identified

## Deployment Process

### 1. Deploy to Staging
```bash
# Frontend
python deploy_frontend.py staging

# Backend (if needed)
python deploy_lambda.py api_lambda staging
```

### 2. Test Staging
- Visit https://staging.awseuccontent.com
- Test all changed functionality
- Check browser console for errors
- Verify API responses

### 3. Deploy to Production (if staging tests pass)
```bash
# Frontend
python deploy_frontend.py production

# Backend (if needed)
python deploy_lambda.py api_lambda production
```

### 4. Verify Production
- Visit https://awseuccontent.com
- Smoke test critical paths
- Monitor CloudWatch logs

## Rollback Procedures

### Frontend Rollback
```bash
# Re-deploy previous version from git
git checkout <previous-commit>
python deploy_frontend.py production
```

### Lambda Rollback
```bash
# Update production alias to previous version
aws lambda update-alias \
  --function-name aws-blog-api \
  --name production \
  --function-version <previous-version>
```
```

#### 6.2 Update AGENTS.md
Add deployment workflow section with staging/production process.

---

## Cost Estimate

### Additional AWS Resources
- **S3 Staging Bucket**: ~$0.50/month (minimal storage)
- **CloudFront Staging Distribution**: ~$1-5/month (low traffic)
- **API Gateway Staging Stage**: No additional cost
- **Lambda Aliases**: No additional cost
- **DynamoDB** (if separate tables): ~$5-10/month

**Total Additional Cost**: ~$7-16/month

---

## Success Criteria

✅ **Staging environment fully functional**
✅ **Can deploy to staging without affecting production**
✅ **Can test changes before production deployment**
✅ **One-command deployment to each environment**
✅ **Quick rollback capability**
✅ **Documentation complete**

---

## Timeline

- **Day 1**: Phase 1 - Infrastructure Setup (S3, CloudFront, DNS)
- **Day 2**: Phase 2 - Lambda Aliases & API Gateway
- **Day 3**: Phase 3 - DynamoDB Strategy
- **Day 4**: Phase 4 - Deployment Scripts
- **Day 5**: Phase 5 & 6 - Testing, Documentation, Rollback

**Total**: 5 days to complete implementation

---

## Next Steps

1. Review this plan
2. Get approval for additional AWS costs
3. Start with Phase 1 (Infrastructure Setup)
4. Test each phase before moving to next
5. Document any issues encountered
6. Update scripts based on real-world usage

---

## Notes

- Start with frontend-only staging, add Lambda staging later if needed
- Consider using AWS CDK or Terraform for infrastructure as code (future enhancement)
- Monitor staging costs and adjust if needed
- Set up CloudWatch alarms for staging environment
