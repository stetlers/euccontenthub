# ECS Migration - Phase 1 & 2 Complete

## Phase 1: Infrastructure Setup ✅

### ECS Cluster
- **Name**: selenium-crawler-cluster
- **Status**: ACTIVE
- **ARN**: arn:aws:ecs:us-east-1:031421429609:cluster/selenium-crawler-cluster

### ECR Repository
- **Name**: selenium-crawler
- **URI**: 031421429609.dkr.ecr.us-east-1.amazonaws.com/selenium-crawler
- **Lifecycle Policy**: Keep last 5 images
- **ARN**: arn:aws:ecr:us-east-1:031421429609:repository/selenium-crawler

### IAM Roles
**Task Execution Role** (for pulling images, writing logs):
- **Name**: selenium-crawler-task-execution-role
- **ARN**: arn:aws:iam::031421429609:role/selenium-crawler-task-execution-role
- **Policies**: AmazonECSTaskExecutionRolePolicy

**Task Role** (for DynamoDB + Lambda access):
- **Name**: selenium-crawler-task-role
- **ARN**: arn:aws:iam::031421429609:role/selenium-crawler-task-role
- **Permissions**:
  - DynamoDB: GetItem, UpdateItem, Query on aws-blog-posts and aws-blog-posts-staging
  - Lambda: InvokeFunction on aws-blog-summary-generator
  - CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents

### CloudWatch Log Group
- **Name**: /ecs/selenium-crawler
- **Retention**: 30 days

## Phase 2: Docker Container Development ✅

### Files Created

**Dockerfile.ecs-selenium**:
- Base image: selenium/standalone-chrome:latest (proven stability)
- Python 3 + pip installed
- Dependencies: boto3, selenium
- Entry point: ecs_selenium_crawler.py
- Runs as seluser (non-root) for security

**requirements-ecs-selenium.txt**:
- boto3==1.34.0
- selenium==4.16.0

**ecs_selenium_crawler.py**:
- Adapted from builder_selenium_crawler.py for ECS environment
- Reads environment variables: DYNAMODB_TABLE_NAME, ENVIRONMENT, POST_IDS
- Connects to Chrome in same container
- Extracts real author names and content
- Updates DynamoDB with extracted data
- Auto-invokes Summary Generator Lambda
- Proper exit codes (0 for success, 1 for failure)
- Comprehensive logging

### Key Features

1. **Environment Variable Configuration**:
   - `DYNAMODB_TABLE_NAME`: Table to update (staging or production)
   - `ENVIRONMENT`: "staging" or "production" (determines Lambda alias)
   - `POST_IDS`: Comma-separated list of post IDs to crawl

2. **Chrome Configuration**:
   - Headless mode
   - Optimized flags for stability (--no-sandbox, --disable-dev-shm-usage)
   - 30-second page load timeout
   - Retry logic (3 attempts per page)

3. **Content Extraction**:
   - Multiple selector strategies for author names
   - Multiple selector strategies for content
   - Fallback to "AWS Builder Community" if author not found
   - Content limited to 3000 characters (matching AWS Blog crawler)

4. **Error Handling**:
   - Graceful handling of timeouts
   - Retry logic for failed extractions
   - Proper cleanup of Chrome driver
   - Exit codes indicate success/failure

5. **Auto-Trigger Chain**:
   - Invokes Summary Generator Lambda after completion
   - Batches of 5 posts per invocation
   - Uses correct Lambda alias based on environment

## Next Steps

### Phase 3: ECS Deployment
- [ ] Build Docker image locally
- [ ] Test Docker image locally
- [ ] Push image to ECR
- [ ] Create ECS task definition
- [ ] Configure network resources (subnets, security groups)

### Phase 4: Sitemap Crawler Integration
- [ ] Update sitemap crawler to invoke ECS task instead of Lambda
- [ ] Deploy updated sitemap crawler to staging

### Phase 5: Testing in Staging
- [ ] Test ECS task directly
- [ ] Test end-to-end orchestration
- [ ] Verify data quality
- [ ] Performance testing

## Files Created

```
Dockerfile.ecs-selenium
requirements-ecs-selenium.txt
ecs_selenium_crawler.py
ecs-task-execution-trust-policy.json
ecs-trust-policy-clean.json
selenium-crawler-task-role-policy.json
ecr-lifecycle-policy.json
```

## Deployment Date

2026-02-13

