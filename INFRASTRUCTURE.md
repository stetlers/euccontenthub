# Infrastructure Guide: EUC Content Hub

Complete guide for setting up the AWS infrastructure for EUC Content Hub from scratch.

## Prerequisites

- AWS Account with admin access
- AWS CLI configured (`aws configure`)
- Python 3.11+ installed
- Git installed
- Domain name (optional, for custom domain)
- Basic knowledge of AWS services

## Architecture Overview

### Blue-Green Deployment Architecture

The platform uses separate staging and production environments for safe deployments:

```
┌─────────────────────────────────────────────────────────────┐
│                    STAGING ENVIRONMENT                       │
│  staging.awseuccontent.com                                  │
│                                                              │
│  CloudFront (E1IB9VDMV64CQA)                               │
│       │                                                      │
│       ▼                                                      │
│  S3: aws-blog-viewer-staging-031421429609                  │
│       │                                                      │
│       ▼                                                      │
│  API Gateway: /staging                                      │
│       │                                                      │
│       ├──► Lambda ($LATEST versions)                        │
│       ├──► DynamoDB: aws-blog-posts-staging                │
│       └──► DynamoDB: euc-user-profiles-staging             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   PRODUCTION ENVIRONMENT                     │
│  awseuccontent.com                                          │
│                                                              │
│  CloudFront (E20CC1TSSWTCWN)                               │
│       │                                                      │
│       ▼                                                      │
│  S3: aws-blog-viewer-031421429609                          │
│       │                                                      │
│       ▼                                                      │
│  API Gateway: /prod                                         │
│       │                                                      │
│       ├──► Lambda (versioned aliases)                       │
│       ├──► DynamoDB: aws-blog-posts                        │
│       └──► DynamoDB: euc-user-profiles                     │
└─────────────────────────────────────────────────────────────┘

Shared Services:
├── Cognito User Pool (authentication)
├── Bedrock (AI models)
└── ECS/Fargate (Builder.AWS crawler)
```

## Step-by-Step Setup

### 1. DynamoDB Tables

#### Production Tables

**Table 1: aws-blog-posts**

```bash
aws dynamodb create-table \
    --table-name aws-blog-posts \
    --attribute-definitions \
        AttributeName=post_id,AttributeType=S \
    --key-schema \
        AttributeName=post_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

**Table 2: euc-user-profiles**

```bash
aws dynamodb create-table \
    --table-name euc-user-profiles \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

#### Staging Tables

**Table 3: aws-blog-posts-staging**

```bash
aws dynamodb create-table \
    --table-name aws-blog-posts-staging \
    --attribute-definitions \
        AttributeName=post_id,AttributeType=S \
    --key-schema \
        AttributeName=post_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

**Table 4: euc-user-profiles-staging**

```bash
aws dynamodb create-table \
    --table-name euc-user-profiles-staging \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

**Table Attributes** (added dynamically):
- `post_id` (String, Primary Key)
- `url`, `title`, `authors`, `date_published`, `date_updated`, `tags`, `content`
- `summary`, `label`, `label_confidence`
- `source` (aws.amazon.com or builder.aws.com)
- `love_votes`, `love_voters[]`
- `needs_update_votes`, `needs_update_voters[]`
- `remove_post_votes`, `remove_post_voters[]`
- `comments[]`, `comment_count`

### 2. S3 Buckets for Frontend

#### Production Bucket

**CRITICAL - Bucket Configuration**:

There are TWO S3 buckets - only ONE is used for production:
- ✅ **CORRECT**: `aws-blog-viewer-031421429609` (serves awseuccontent.com)
- ❌ **WRONG**: `www.awseuccontent.com` (exists but NOT configured)

**Always deploy production to**: `aws-blog-viewer-031421429609`

```bash
# The correct bucket already exists in your account
# Verify it exists
aws s3 ls s3://aws-blog-viewer-031421429609
```

#### Staging Bucket

**Staging Bucket**: `aws-blog-viewer-staging-031421429609` (serves staging.awseuccontent.com)

```bash
# Verify staging bucket exists
aws s3 ls s3://aws-blog-viewer-staging-031421429609
```

# Enable static website hosting (if not already enabled)
aws s3 website s3://aws-blog-viewer-031421429609 \
    --index-document index.html \
    --error-document index.html

# Set bucket policy for public read
aws s3api put-bucket-policy \
    --bucket aws-blog-viewer-031421429609 \
    --policy '{
      "Version": "2012-10-17",
      "Statement": [{
        "Sid": "PublicReadGetObject",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::aws-blog-viewer-031421429609/*"
      }]
    }'
```

**Why This Matters**:
- CloudFront distribution `E20CC1TSSWTCWN` points to `aws-blog-viewer-031421429609`
- Domain `awseuccontent.com` resolves to this CloudFront distribution
- Deploying to wrong bucket breaks the website
- Always use `deploy_frontend_complete.py` which targets correct bucket

### 3. CloudFront Distribution

**Existing Distribution**: `E20CC1TSSWTCWN`

**Configuration**:
- **Origin**: `aws-blog-viewer-031421429609.s3-website-us-east-1.amazonaws.com`
- **Domain**: `awseuccontent.com` (no www)
- Viewer Protocol Policy: Redirect HTTP to HTTPS
- Allowed HTTP Methods: GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE
- Cache Policy: CachingOptimized
- Origin Request Policy: CORS-S3Origin
- SSL Certificate: ACM certificate for awseuccontent.com

**CRITICAL**: The origin MUST be `aws-blog-viewer-031421429609`, not `www.awseuccontent.com`

### 4. IAM Roles

#### Lambda Execution Role

```bash
# Create role
aws iam create-role \
    --role-name EUCContentHubLambdaRole \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }'

# Attach policies
aws iam attach-role-policy \
    --role-name EUCContentHubLambdaRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
    --role-name EUCContentHubLambdaRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam attach-role-policy \
    --role-name EUCContentHubLambdaRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

### 5. Lambda Functions

#### API Lambda

```bash
# Create deployment package
cd /path/to/project
zip -r api_lambda.zip api_lambda.py

# Create function
aws lambda create-function \
    --function-name aws-blog-api \
    --runtime python3.11 \
    --role arn:aws:iam::031421429609:role/EUCContentHubLambdaRole \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://api_lambda.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment Variables='{
      "DYNAMODB_TABLE_NAME":"aws-blog-posts",
      "PROFILES_TABLE_NAME":"euc-user-profiles",
      "COGNITO_USER_POOL_ID":"your-pool-id",
      "COGNITO_APP_CLIENT_ID":"your-client-id"
    }' \
    --region us-east-1
```

#### Enhanced Crawler Lambda

```bash
zip -r crawler_lambda.zip enhanced_crawler_lambda.py

aws lambda create-function \
    --function-name aws-blog-crawler \
    --runtime python3.11 \
    --role arn:aws:iam::031421429609:role/EUCContentHubLambdaRole \
    --handler enhanced_crawler_lambda.lambda_handler \
    --zip-file fileb://crawler_lambda.zip \
    --timeout 900 \
    --memory-size 512 \
    --region us-east-1
```

#### Summary Generator Lambda

```bash
zip -r summary_lambda.zip summary_lambda.py

aws lambda create-function \
    --function-name aws-blog-summary-generator \
    --runtime python3.11 \
    --role arn:aws:iam::031421429609:role/EUCContentHubLambdaRole \
    --handler summary_lambda.lambda_handler \
    --zip-file fileb://summary_lambda.zip \
    --timeout 900 \
    --memory-size 512 \
    --region us-east-1
```

#### Classifier Lambda

```bash
zip -r classifier_lambda.zip classifier_lambda.py

aws lambda create-function \
    --function-name aws-blog-classifier \
    --runtime python3.11 \
    --role arn:aws:iam::031421429609:role/EUCContentHubLambdaRole \
    --handler classifier_lambda.lambda_handler \
    --zip-file fileb://classifier_lambda.zip \
    --timeout 900 \
    --memory-size 512 \
    --region us-east-1
```

#### Chat Assistant Lambda

```bash
zip -r chat_lambda.zip chat_lambda.py

aws lambda create-function \
    --function-name aws-blog-chat \
    --runtime python3.11 \
    --role arn:aws:iam::031421429609:role/EUCContentHubLambdaRole \
    --handler chat_lambda.lambda_handler \
    --zip-file fileb://chat_lambda.zip \
    --timeout 60 \
    --memory-size 512 \
    --region us-east-1
```

### 6. API Gateway

```bash
# Create REST API
aws apigateway create-rest-api \
    --name aws-blog-api \
    --description "EUC Content Hub API" \
    --region us-east-1
```

**Resources to create**:
- `/posts` (GET, POST)
- `/posts/{id}` (GET)
- `/posts/{id}/vote` (POST)
- `/posts/{id}/comments` (GET, POST)
- `/posts/{id}/bookmark` (POST)
- `/profile` (GET, PUT, DELETE)
- `/profile/activity` (GET)
- `/bookmarks` (GET)
- `/chat` (POST)
- `/crawl` (POST)
- `/summaries` (POST)

**Integration**: Lambda Proxy Integration with aws-blog-api function

**CORS**: Enable for all resources

**Deployment**: Create `prod` stage

### 7. Cognito User Pool

```bash
# Create user pool
aws cognito-idp create-user-pool \
    --pool-name euc-content-hub-users \
    --policies '{
      "PasswordPolicy": {
        "MinimumLength": 8,
        "RequireUppercase": true,
        "RequireLowercase": true,
        "RequireNumbers": true,
        "RequireSymbols": false
      }
    }' \
    --auto-verified-attributes email \
    --region us-east-1
```

#### Create App Client

```bash
aws cognito-idp create-user-pool-client \
    --user-pool-id <your-pool-id> \
    --client-name euc-content-hub-web \
    --generate-secret \
    --allowed-o-auth-flows code implicit \
    --allowed-o-auth-scopes email openid profile \
    --callback-urls https://awseuccontent.com/callback https://awseuccontent.com \
    --logout-urls https://awseuccontent.com \
    --supported-identity-providers COGNITO Google \
    --region us-east-1
```

#### Configure Google OAuth

1. Go to Google Cloud Console
2. Create OAuth 2.0 credentials
3. Add to Cognito as identity provider:

```bash
aws cognito-idp create-identity-provider \
    --user-pool-id <your-pool-id> \
    --provider-name Google \
    --provider-type Google \
    --provider-details '{
      "client_id":"your-google-client-id",
      "client_secret":"your-google-client-secret",
      "authorize_scopes":"profile email openid"
    }' \
    --attribute-mapping '{
      "email":"email",
      "username":"sub"
    }' \
    --region us-east-1
```

#### Configure Hosted UI Domain

```bash
aws cognito-idp create-user-pool-domain \
    --user-pool-id <your-pool-id> \
    --domain euc-content-hub \
    --region us-east-1
```

### 8. ECS/Fargate for Selenium Crawler

#### Create ECR Repository

```bash
aws ecr create-repository \
    --repository-name builder-selenium-crawler \
    --region us-east-1
```

#### Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin \
    031421429609.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t builder-selenium-crawler:latest -f Dockerfile.selenium .

# Tag image
docker tag builder-selenium-crawler:latest \
    031421429609.dkr.ecr.us-east-1.amazonaws.com/builder-selenium-crawler:latest

# Push image
docker push 031421429609.dkr.ecr.us-east-1.amazonaws.com/builder-selenium-crawler:latest
```

#### Create ECS Cluster

```bash
aws ecs create-cluster \
    --cluster-name euc-content-hub-cluster \
    --region us-east-1
```

#### Create Task Definition

```bash
aws ecs register-task-definition \
    --family builder-selenium-crawler \
    --network-mode awsvpc \
    --requires-compatibilities FARGATE \
    --cpu 2048 \
    --memory 10240 \
    --execution-role-arn arn:aws:iam::031421429609:role/ecsTaskExecutionRole \
    --task-role-arn arn:aws:iam::031421429609:role/EUCContentHubLambdaRole \
    --container-definitions '[{
      "name": "builder-crawler",
      "image": "031421429609.dkr.ecr.us-east-1.amazonaws.com/builder-selenium-crawler:latest",
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/builder-selenium-crawler",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }]' \
    --region us-east-1
```

### 9. AWS Bedrock Setup

#### Enable Models

1. Go to AWS Bedrock Console
2. Navigate to Model access
3. Request access to:
   - Claude 3 Haiku
   - Claude 3 Sonnet

**Note**: Model access approval can take a few minutes to a few hours.

### 10. Custom Domain (Optional)

#### Request ACM Certificate

```bash
aws acm request-certificate \
    --domain-name awseuccontent.com \
    --subject-alternative-names www.awseuccontent.com \
    --validation-method DNS \
    --region us-east-1
```

#### Validate Certificate

Follow DNS validation instructions in ACM console.

#### Update CloudFront Distribution

Add custom domain and ACM certificate to CloudFront distribution.

#### Update Route 53

```bash
# Create A record for apex domain
aws route53 change-resource-record-sets \
    --hosted-zone-id <your-zone-id> \
    --change-batch '{
      "Changes": [{
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "awseuccontent.com",
          "Type": "A",
          "AliasTarget": {
            "HostedZoneId": "Z2FDTNDATAQYW2",
            "DNSName": "d2lo7dstdx8pwh.cloudfront.net",
            "EvaluateTargetHealth": false
          }
        }
      }]
    }'

# Create A record for www subdomain
aws route53 change-resource-record-sets \
    --hosted-zone-id <your-zone-id> \
    --change-batch '{
      "Changes": [{
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "www.awseuccontent.com",
          "Type": "A",
          "AliasTarget": {
            "HostedZoneId": "Z2FDTNDATAQYW2",
            "DNSName": "d2lo7dstdx8pwh.cloudfront.net",
            "EvaluateTargetHealth": false
          }
        }
      }]
    }'
```

## Deployment Scripts

### Deploy Frontend

```bash
python deploy_frontend_complete.py
```

**CRITICAL - This script**:
1. Replaces API endpoint placeholder in app.js
2. Uploads files to **CORRECT** S3 bucket: `aws-blog-viewer-031421429609`
3. Invalidates CloudFront cache: `E20CC1TSSWTCWN`

**DO NOT**:
- Upload to `www.awseuccontent.com` bucket
- Use generic S3 upload commands
- Skip CloudFront invalidation

**Verification**:
```bash
# Check files were uploaded to correct bucket
aws s3 ls s3://aws-blog-viewer-031421429609/

# Check CloudFront invalidation status
aws cloudfront list-invalidations \
    --distribution-id E20CC1TSSWTCWN \
    --region us-east-1
```

### Deploy API Lambda

```bash
python rollback_api_lambda.py
```

This script:
1. Creates deployment package
2. Uploads to Lambda
3. Waits for update to complete

### Deploy Selenium Crawler

```bash
python redeploy_selenium_crawler.py
```

This script:
1. Builds Docker image
2. Pushes to ECR
3. Updates ECS task definition
4. Runs task

## Initial Data Population

### Run Crawlers

**Important**: Crawlers are NOT scheduled - they must be triggered manually.

**Trigger Methods**:
1. **Website Button**: "Refresh Posts" (requires authentication)
2. **Python Script**: `python trigger_crawler.py`
3. **Direct Lambda Invocation**: Via AWS Console or CLI

```bash
# Trigger AWS Blog crawler
python trigger_crawler.py

# Or invoke directly
aws lambda invoke \
    --function-name aws-blog-crawler \
    --invocation-type Event \
    --region us-east-1 \
    response.json

# Run Builder.AWS crawler (ECS task)
aws ecs run-task \
    --cluster euc-content-hub-cluster \
    --task-definition builder-selenium-crawler \
    --launch-type FARGATE \
    --network-configuration '{
      "awsvpcConfiguration": {
        "subnets": ["subnet-xxx"],
        "securityGroups": ["sg-xxx"],
        "assignPublicIp": "ENABLED"
      }
    }' \
    --region us-east-1
```

**Crawler Workflow**:
1. Crawler runs and saves posts to DynamoDB
2. Crawler automatically invokes Summary Generator Lambda
3. Summary Generator processes 10 posts at a time
4. Summary Generator automatically invokes Classifier Lambda
5. Classifier processes 50 posts at a time

### Generate Summaries

**Batch Processing**: Summaries are generated in batches of 10 posts per invocation.

**For Large Batches**: Use the loop script to process all posts:

```bash
python generate_all_builder_summaries.py
```

This script:
1. Checks how many posts need summaries
2. Invokes Summary Lambda (10 posts per batch)
3. Waits for completion
4. Repeats until all posts have summaries
5. Each batch automatically triggers classification

**Manual Single Batch**:
```bash
aws lambda invoke \
    --function-name aws-blog-summary-generator \
    --invocation-type Event \
    --payload '{"batch_size": 10, "force": false}' \
    --region us-east-1 \
    response.json
```

**Summary Generation Flow**:
- Summary Lambda does NOT auto-chain for next batch
- Must be invoked multiple times for large datasets
- Each invocation processes 10 posts
- Automatically invokes Classifier after completion

## Monitoring and Maintenance

### CloudWatch Dashboards

Create dashboard with:
- Lambda invocation counts
- Lambda error rates
- Lambda duration
- DynamoDB read/write capacity
- API Gateway requests
- CloudFront requests

### Alarms

Set up alarms for:
- Lambda errors > 5 in 5 minutes
- API Gateway 5xx errors > 10 in 5 minutes
- DynamoDB throttling events

### Logs Retention

```bash
# Set log retention to 30 days
aws logs put-retention-policy \
    --log-group-name /aws/lambda/aws-blog-api \
    --retention-in-days 30
```

## Cost Optimization

### DynamoDB
- Use on-demand billing for unpredictable traffic
- Consider provisioned capacity if traffic is consistent

### Lambda
- Right-size memory allocation
- Use Lambda Power Tuning tool

### S3
- Enable S3 Intelligent-Tiering for old objects
- Set lifecycle policies

### CloudFront
- Use CloudFront caching effectively
- Set appropriate TTLs

## Security Best Practices

1. **Secrets Management**: Use AWS Secrets Manager or Parameter Store
2. **IAM Least Privilege**: Grant only necessary permissions
3. **API Rate Limiting**: Configure API Gateway throttling
4. **Input Validation**: Validate all user inputs
5. **HTTPS Only**: Enforce HTTPS everywhere
6. **Regular Updates**: Keep dependencies updated
7. **Monitoring**: Enable CloudTrail and GuardDuty

## Backup and Disaster Recovery

### DynamoDB Backups

```bash
# Enable point-in-time recovery
aws dynamodb update-continuous-backups \
    --table-name aws-blog-posts \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

aws dynamodb update-continuous-backups \
    --table-name euc-user-profiles \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### S3 Versioning

```bash
aws s3api put-bucket-versioning \
    --bucket www.awseuccontent.com \
    --versioning-configuration Status=Enabled
```

## Troubleshooting

### Posts Not Loading
1. Check API Lambda logs
2. Verify DynamoDB has data
3. Check CORS configuration
4. Verify CloudFront is serving latest files

### Authentication Issues
1. Check Cognito configuration
2. Verify JWT token validity
3. Check Lambda environment variables
4. Verify callback URLs

### Crawler Issues
1. Check crawler Lambda logs
2. Verify IAM permissions
3. Test RSS/sitemap accessibility
4. For Selenium: Check Chrome/driver compatibility

### Summary Generation Slow
1. Increase Lambda memory
2. Check Bedrock throttling
3. Verify batch size configuration
4. Monitor Bedrock quotas

## Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
- [Cognito Documentation](https://docs.aws.amazon.com/cognito/)

## Support

For infrastructure questions or issues:
- Check CloudWatch logs
- Review AWS service health dashboard
- Consult AWS documentation
- Open GitHub issue

---

Last Updated: February 2026
