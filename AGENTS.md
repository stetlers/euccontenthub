# Agent Guide: EUC Content Hub

This guide is designed for AI agents (like Claude, GPT, etc.) to understand and work with the EUC Content Hub codebase.

## Project Overview

**EUC Content Hub** is a serverless AWS blog aggregator and community platform that:
- Aggregates AWS blog posts from multiple sources (AWS Blog, Builder.AWS)
- Generates AI summaries using AWS Bedrock (Claude Haiku)
- Automatically classifies content by topic
- Provides user authentication, profiles, bookmarks, voting, and comments
- Includes an AI chat assistant for content discovery

**Live Site**: https://awseuccontent.com  
**GitHub**: https://github.com/stetlers/euccontenthub

## Architecture

### Blue-Green Deployment (Issue #1 - COMPLETE)

The project uses a blue-green deployment strategy with separate staging and production environments:

**Benefits**:
- ✅ Test changes safely before production
- ✅ Complete data isolation (staging/production)
- ✅ Instant Lambda rollback capability
- ✅ No risk of staging affecting production

**Key Features**:
- Separate S3 buckets and CloudFront distributions
- Separate DynamoDB tables (staging has `-staging` suffix)
- Lambda aliases (production uses versions, staging uses $LATEST)
- API Gateway stages (prod and staging)
- Environment-aware Lambda code (reads TABLE_SUFFIX from stage variables)

**Deployment Rule**: Always deploy to staging first, test, then promote to production.

### AWS Services Used
- **Lambda**: 6 functions (API, crawlers, summary generator, classifier, chat assistant)
  - Production alias points to specific versions
  - Staging alias points to $LATEST
- **DynamoDB**: 4 tables
  - Production: `aws-blog-posts`, `euc-user-profiles`
  - Staging: `aws-blog-posts-staging`, `euc-user-profiles-staging`
- **S3**: Frontend hosting
  - **Production**: `aws-blog-viewer-031421429609` (serves awseuccontent.com)
  - **Staging**: `aws-blog-viewer-staging-031421429609` (serves staging.awseuccontent.com)
  - ❌ **NEVER USE**: `www.awseuccontent.com` (exists but NOT configured)
- **CloudFront**: CDN
  - **Production**: E20CC1TSSWTCWN
  - **Staging**: E1IB9VDMV64CQA
- **API Gateway**: REST API (xox05733ce)
  - **Production stage**: /prod
  - **Staging stage**: /staging (with TABLE_SUFFIX=-staging variable)
- **Cognito**: User authentication with Google OAuth
- **Bedrock**: AI summaries and chat (Claude models)
- **ECS/Fargate**: Selenium crawler for Builder.AWS

### Key Components

#### 1. Frontend (`frontend/`)
- **index.html**: Main SPA with modals for legal pages
- **app.js**: Core application logic, post loading, filtering, voting
- **auth.js**: Cognito authentication, JWT handling
- **profile.js**: User profile management, activity tracking
- **chat-widget.js**: AI assistant interface
- **styles.css**: Responsive design with dark mode support

#### 2. Backend Lambda Functions

**API Lambda** (`api_lambda.py`)
- Handler: `lambda_function.lambda_handler`
- Endpoints: /posts, /profile, /bookmarks, /vote, /comments, /crawl, /summaries, /chat
- **DELETE /profile**: Deletes user account and all associated data (votes, comments, bookmarks)
- JWT validation using Cognito public keys
- CORS enabled for cross-origin requests

**Enhanced Crawler** (`enhanced_crawler_lambda.py`)
- Crawls AWS Blog RSS feed
- Extracts metadata, content, authors
- Auto-triggers summary generation after crawl completes
- Filters for EUC-related content
- **Trigger Method**: Manual only (website button or direct invocation - NO automatic scheduling)

**Builder Selenium Crawler** (`builder_selenium_crawler.py`)
- Runs in ECS/Fargate container with Chrome
- Crawls Builder.AWS sitemap
- Extracts full content including real author names
- Handles dynamic JavaScript content
- Auto-triggers summary generation after crawl completes
- **Trigger Method**: Manual only (website button or direct invocation - NO automatic scheduling)

**Summary Generator** (`summary_lambda.py`)
- Uses AWS Bedrock (Claude Haiku)
- Generates 2-3 sentence summaries
- **Batch Processing**: Processes 10 posts per invocation
- **Does NOT auto-chain**: Must be invoked multiple times for large datasets
- Use `generate_all_builder_summaries.py` to loop through all posts needing summaries
- Auto-invokes classifier Lambda after each batch completes
- Automatically triggered by crawlers when new posts are created

**Classifier** (`classifier_lambda.py`)
- Uses AWS Bedrock (Claude Haiku)
- **Classifies by content TYPE**, not by service:
  - Technical How-To
  - Thought Leadership
  - Product Announcement
  - Best Practices
  - Case Study
- Provides confidence scores
- Batch processing (50 posts at a time)
- Automatically triggered by summary generator after summaries complete

**Chat Assistant** (`chat_lambda.py`)
- Uses AWS Bedrock (Claude Sonnet)
- Context-aware responses using post database
- Streaming responses for better UX

#### 3. Data Models

**DynamoDB: aws-blog-posts**
```python
{
    'post_id': 'string',           # Primary key
    'url': 'string',
    'title': 'string',
    'authors': 'string',
    'date_published': 'string',
    'tags': 'string',
    'content': 'string',           # First 3000 chars
    'summary': 'string',           # AI-generated
    'label': 'string',             # Classification
    'label_confidence': 'number',
    'source': 'string',            # 'aws.amazon.com' or 'builder.aws.com'
    'love_votes': 'number',
    'love_voters': ['user_id'],
    'needs_update_votes': 'number',
    'needs_update_voters': ['user_id'],
    'remove_post_votes': 'number',
    'remove_post_voters': ['user_id'],
    'comments': [
        {
            'comment_id': 'string',
            'user_id': 'string',
            'voter_id': 'string',
            'display_name': 'string',
            'text': 'string',
            'timestamp': 'string'
        }
    ],
    'comment_count': 'number'
}
```

**DynamoDB: euc-user-profiles**
```python
{
    'user_id': 'string',           # Primary key (Cognito sub)
    'email': 'string',
    'display_name': 'string',
    'bio': 'string',
    'credly_url': 'string',
    'builder_id': 'string',
    'bookmarks': ['post_id'],
    'created_at': 'string',
    'updated_at': 'string'
}
```

## Testing in Staging

Before deploying any changes to production, always test in staging first.

### Why Staging Exists

Staging prevents production issues by:
- Testing code changes in a production-like environment
- Verifying data operations don't corrupt production data
- Catching bugs before users see them
- Allowing safe testing of destructive operations (delete user, crawler changes)

### Staging Environment Details

- **Isolated Data**: Staging has 50 sample posts and 3 test user profiles
- **Same Infrastructure**: Uses same AWS services as production
- **Environment Detection**: Lambda automatically uses staging tables based on API Gateway stage
- **No Production Impact**: Changes in staging never affect production

### Testing Checklist

**Frontend Changes**:
- [ ] Deploy to staging: `python deploy_frontend.py staging`
- [ ] Visit https://staging.awseuccontent.com
- [ ] Test all changed functionality
- [ ] Check browser console for errors
- [ ] Test on mobile if UI changes
- [ ] Deploy to production: `python deploy_frontend.py production`

**Lambda Changes**:
- [ ] Deploy to staging: `python deploy_lambda.py <function> staging`
- [ ] Test staging API endpoint
- [ ] Check CloudWatch logs for errors
- [ ] Verify correct tables being used (staging tables)
- [ ] Test data operations don't corrupt data
- [ ] Deploy to production: `python deploy_lambda.py <function> production`

**High-Risk Changes** (crawler, summary, classifier):
- [ ] Deploy to staging
- [ ] Run full operation in staging (trigger crawler, generate summaries)
- [ ] Verify data integrity (summaries not wiped, posts created correctly)
- [ ] Check for any data corruption
- [ ] Monitor CloudWatch logs throughout
- [ ] Only deploy to production if all tests pass

## Common Agent Tasks

### Task 1: Add a New Feature to Frontend

**Files to modify**: `frontend/app.js`, `frontend/index.html`, `frontend/styles.css`

**Deployment**:
```python
# CRITICAL: Always use deploy_frontend_complete.py
# This script targets the CORRECT S3 bucket: aws-blog-viewer-031421429609
# NEVER manually deploy to www.awseuccontent.com bucket (it's not configured)
python deploy_frontend_complete.py
```

**Key patterns**:
- Use `showNotification(message, type)` for user feedback
- Check authentication with `window.authManager.isAuthenticated()`
- API calls use `fetch()` with JWT in Authorization header
- All modals use `.modal` class with `.modal-content`

### Task 2: Add a New API Endpoint

**Files to modify**: `api_lambda.py`

**Steps**:
1. Add route in `lambda_handler()` function
2. Create handler function (use `@require_auth` decorator if auth needed)
3. Return response with `cors_headers()`
4. Deploy with `rollback_api_lambda.py` (creates zip, uploads to Lambda)

**Example**:
```python
@require_auth
def my_new_endpoint(event, body):
    user_id = event['user']['sub']
    # Your logic here
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({'result': 'success'})
    }
```

### Task 3: Modify Crawler Logic

**AWS Blog Crawler**: `enhanced_crawler_lambda.py`
- Modify `extract_metadata()` for different parsing
- Update `is_euc_related()` for filtering logic
- Deploy: Update Lambda code via AWS Console or deployment script

**Builder.AWS Crawler**: `builder_selenium_crawler.py`
- Modify `extract_page_content()` for different selectors
- Update Chrome options in `setup_driver()` if needed
- Deploy: `redeploy_selenium_crawler.py` (builds Docker image, pushes to ECR, updates ECS task)

### Task 4: Modify AI Behavior

**Summaries**: Edit prompt in `summary_lambda.py` → `generate_summary()`
**Classification**: Edit prompt in `classifier_lambda.py` → `classify_post()`
**Chat**: Edit system prompt in `chat_lambda.py` → `lambda_handler()`

Deploy by updating Lambda code.

### Task 5: Add New DynamoDB Field

**Steps**:
1. Update data model in relevant Lambda function
2. Use `UpdateExpression` with `SET` to add field
3. Use `if_not_exists()` to avoid overwriting existing data
4. Update frontend to display new field

**Example**:
```python
table.update_item(
    Key={'post_id': post_id},
    UpdateExpression='SET new_field = :value',
    ExpressionAttributeValues={':value': 'default'}
)
```

## Important Patterns

### Authentication Flow
1. User clicks "Sign In" → Redirects to Cognito Hosted UI
2. Cognito redirects back with authorization code
3. Frontend exchanges code for JWT tokens
4. Tokens stored in localStorage
5. API requests include JWT in Authorization header
6. Lambda validates JWT using Cognito public keys

### Deployment Flow

**IMPORTANT**: Use the blue-green deployment strategy with staging environment.

#### Environments

**Production**:
- **Site**: https://awseuccontent.com
- **S3 Bucket**: `aws-blog-viewer-031421429609`
- **CloudFront**: E20CC1TSSWTCWN
- **API**: https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod
- **DynamoDB**: `aws-blog-posts`, `euc-user-profiles`

**Staging**:
- **Site**: https://staging.awseuccontent.com
- **S3 Bucket**: `aws-blog-viewer-staging-031421429609`
- **CloudFront**: E1IB9VDMV64CQA
- **API**: https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging
- **DynamoDB**: `aws-blog-posts-staging`, `euc-user-profiles-staging`

#### Deployment Scripts

**Frontend Deployment**:
```bash
# Deploy to staging first
python deploy_frontend.py staging

# Test staging thoroughly at https://staging.awseuccontent.com

# Deploy to production after testing
python deploy_frontend.py production
```

**Lambda Deployment**:
```bash
# Deploy to staging first
python deploy_lambda.py api_lambda staging

# Test staging API
curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/posts

# Deploy to production after testing
python deploy_lambda.py api_lambda production
```

**Available Lambda Functions**:
- `api_lambda` - API Lambda
- `crawler` - AWS Blog crawler
- `builder_crawler` - Builder.AWS crawler
- `summary` - Summary generator
- `classifier` - Content classifier
- `chat` - Chat assistant

#### Deployment Workflow

1. **Make changes** to code
2. **Deploy to staging** using deployment scripts
3. **Test staging** thoroughly (see DEPLOYMENT.md for checklists)
4. **Deploy to production** if tests pass
5. **Verify production** and monitor logs
6. **Rollback** if issues occur (instant for Lambda, 2-3 min for frontend)

**See DEPLOYMENT.md for complete runbook with detailed procedures.**

#### Quick Rollback

**Lambda** (instant):
```bash
aws lambda update-alias --function-name aws-blog-api \
  --name production --function-version <previous-version>
```

**Frontend** (2-3 minutes):
```bash
git checkout <previous-commit>
python deploy_frontend.py production
```

### Error Handling
- Frontend: Use try/catch and `showNotification()`
- Lambda: Return proper status codes (400, 401, 403, 500)
- Always log errors with `print()` for CloudWatch

### CORS
- All API responses must include `cors_headers()`
- Preflight OPTIONS requests handled in `lambda_handler()`

### Auto-Trigger Flow
The system has an automatic trigger chain for content processing:
1. **Crawler** (Enhanced or Builder Selenium) runs and creates new posts
2. Crawler automatically invokes **Summary Generator** Lambda
3. Summary Generator processes 10 posts and generates AI summaries
4. Summary Generator automatically invokes **Classifier** Lambda
5. Classifier processes posts and assigns content type labels

**Important Notes**:
- Crawlers must be triggered manually (website button or direct invocation)
- Summary Generator processes 10 posts per batch - does NOT auto-chain for remaining posts
- For large datasets, use `generate_all_builder_summaries.py` to loop through all posts
- Each step in the chain auto-triggers the next step, but crawlers themselves are manual only

## Testing

### Frontend Testing
1. Open https://awseuccontent.com in browser
2. Check browser console for errors
3. Test authentication flow
4. Verify API calls in Network tab

### Lambda Testing
```python
# Use test scripts:
python test_api_posts_endpoint.py
python check_api_lambda_errors.py
python check_summary_lambda_logs.py
```

### Manual Lambda Invocation
```python
import boto3
lambda_client = boto3.client('lambda', region_name='us-east-1')
response = lambda_client.invoke(
    FunctionName='aws-blog-api',
    InvocationType='RequestResponse',
    Payload='{"path": "/posts", "httpMethod": "GET"}'
)
```

## Common Issues

### Issue: Posts not loading
- Check API Lambda logs: `python check_api_lambda_errors.py`
- Verify DynamoDB table has data
- Check CORS headers in response
- **CRITICAL**: Verify you deployed to correct S3 bucket (`aws-blog-viewer-031421429609`)
- Verify CloudFront distribution `E20CC1TSSWTCWN` is serving latest files
- Check Lambda handler is `lambda_function.lambda_handler` (not `api_lambda.lambda_handler`)
- Verify deployment zip contains `lambda_function.py` (not `api_lambda.py`)

### Issue: Authentication failing
- Check Cognito configuration
- Verify JWT token is valid (not expired)
- Check Lambda has correct Cognito User Pool ID
- Verify callback URLs match

### Issue: Summaries not generating
- Check summary Lambda logs: `python check_summary_lambda_logs.py`
- Verify Bedrock access in Lambda role
- Check if posts have content field populated
- Verify Lambda timeout is sufficient (15 min)
- **Remember**: Summary Lambda processes 10 posts per batch and does NOT auto-chain
- For large datasets, use `generate_all_builder_summaries.py` to loop through all posts
- Crawler automatically triggers summary generation when new posts are created
- Summary Lambda automatically triggers classifier after completion

### Issue: Crawler not finding posts
- Check crawler Lambda logs
- Verify sitemap/RSS feed is accessible
- Check filtering logic in `is_euc_related()`
- For Builder.AWS: Check Chrome/Selenium setup
- **Remember**: Crawlers are triggered manually only (website button or direct invocation)
- There is NO automatic scheduling - crawlers must be manually invoked each time

## File Organization

```
.
├── frontend/              # Frontend SPA
│   ├── index.html        # Main page
│   ├── app.js            # Core logic
│   ├── auth.js           # Authentication
│   ├── profile.js        # User profiles
│   ├── chat-widget.js    # AI assistant
│   └── styles.css        # Styling
├── lambda_api/           # API Lambda source
│   └── lambda_function.py
├── api_lambda.py         # Main API (legacy location)
├── enhanced_crawler_lambda.py      # AWS Blog crawler
├── builder_selenium_crawler.py     # Builder.AWS crawler
├── summary_lambda.py     # AI summaries
├── classifier_lambda.py  # Content classification
├── chat_lambda.py        # AI chat assistant
├── deploy_frontend.py    # Frontend deployment script
├── deploy_lambda.py      # Lambda deployment script
├── copy_data_to_staging.py  # Copy data to staging tables
├── configure_lambda_staging.py  # Configure Lambda for staging
├── test_*.py             # Test scripts
├── check_*.py            # Diagnostic scripts
├── .gitignore            # Git exclusions
├── README.md             # Human-readable docs
├── AGENTS.md             # This file
├── DEPLOYMENT.md         # Deployment runbook
├── INFRASTRUCTURE.md     # AWS setup guide
└── blue-green-deployment-plan.md  # Blue-green implementation plan
```

## Agent Best Practices

1. **Always read existing code** before making changes
2. **Test locally** when possible (use test scripts)
3. **Deploy incrementally** - one change at a time
4. **Check logs** after deployment
5. **Preserve existing functionality** - don't break working features
6. **Follow existing patterns** - maintain code consistency
7. **Update documentation** when adding features
8. **Handle errors gracefully** - always include error handling
9. **Use descriptive commit messages**
10. **Ask for clarification** if requirements are unclear

## Useful Commands

```bash
# Check Lambda logs
python check_api_lambda_errors.py
python check_summary_lambda_logs.py

# Test API endpoint
python test_api_posts_endpoint.py

# Deploy frontend
python deploy_frontend_complete.py

# Deploy API Lambda
python rollback_api_lambda.py

# Trigger crawler
python trigger_crawler.py

# Generate summaries
python generate_all_builder_summaries.py

# Check DynamoDB data
python check_dynamodb_data.py
```

## Contact & Resources

- **AWS Account**: 031421429609
- **Region**: us-east-1
- **Website**: https://awseuccontent.com
- **GitHub**: https://github.com/stetlers/euccontenthub
- **API Endpoint**: https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod

For questions or issues, refer to the troubleshooting section or check CloudWatch logs.
