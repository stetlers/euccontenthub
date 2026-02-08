# Lambda Code Updates for Staging Support

## Overview
All Lambda functions need to be updated to use environment variables for DynamoDB table selection. This enables staging/production isolation.

---

## Required Code Changes

### Pattern to Find and Replace

**FIND THIS PATTERN:**
```python
table = dynamodb.Table('aws-blog-posts')
# or
table = dynamodb.Table('euc-user-profiles')
```

**REPLACE WITH:**
```python
import os

# Get table suffix from stage variable or environment
def get_table_suffix(event):
    """Extract table suffix from API Gateway stage variables or environment"""
    # Try stage variables first (from API Gateway)
    stage_variables = event.get('stageVariables', {})
    table_suffix = stage_variables.get('TABLE_SUFFIX', '')
    
    # Fall back to environment variable
    if not table_suffix:
        table_suffix = os.environ.get('TABLE_SUFFIX', '')
    
    return table_suffix

# In lambda_handler:
def lambda_handler(event, context):
    table_suffix = get_table_suffix(event)
    
    # Use suffix for table names
    posts_table = dynamodb.Table(f'aws-blog-posts{table_suffix}')
    profiles_table = dynamodb.Table(f'euc-user-profiles{table_suffix}')
    
    # Rest of your code...
```

---

## Lambda Functions to Update

### 1. aws-blog-api (api_lambda.py)
**Tables used:** aws-blog-posts, euc-user-profiles

**Changes needed:**
```python
# At the top of the file
import os

def get_table_suffix(event):
    stage_variables = event.get('stageVariables', {})
    table_suffix = stage_variables.get('TABLE_SUFFIX', '')
    if not table_suffix:
        table_suffix = os.environ.get('TABLE_SUFFIX', '')
    return table_suffix

# In lambda_handler
def lambda_handler(event, context):
    table_suffix = get_table_suffix(event)
    posts_table = dynamodb.Table(f'aws-blog-posts{table_suffix}')
    profiles_table = dynamodb.Table(f'euc-user-profiles{table_suffix}')
    
    # Update all references throughout the function
    # Replace: table.scan() with posts_table.scan()
    # Replace: profiles_table references similarly
```

### 2. enhanced_crawler_lambda.py
**Tables used:** aws-blog-posts

**Changes needed:**
```python
import os

def lambda_handler(event, context):
    table_suffix = os.environ.get('TABLE_SUFFIX', '')
    table = dynamodb.Table(f'aws-blog-posts{table_suffix}')
    
    # Rest of crawler logic...
```

### 3. builder_selenium_crawler.py
**Tables used:** aws-blog-posts

**Changes needed:**
```python
import os

# In the main function or lambda_handler
table_suffix = os.environ.get('TABLE_SUFFIX', '')
table = dynamodb.Table(f'aws-blog-posts{table_suffix}')
```

### 4. summary_lambda.py
**Tables used:** aws-blog-posts

**Changes needed:**
```python
import os

def lambda_handler(event, context):
    table_suffix = os.environ.get('TABLE_SUFFIX', '')
    table = dynamodb.Table(f'aws-blog-posts{table_suffix}')
    
    # Rest of summary generation logic...
```

### 5. classifier_lambda.py
**Tables used:** aws-blog-posts

**Changes needed:**
```python
import os

def lambda_handler(event, context):
    table_suffix = os.environ.get('TABLE_SUFFIX', '')
    table = dynamodb.Table(f'aws-blog-posts{table_suffix}')
    
    # Rest of classification logic...
```

### 6. chat_lambda.py
**Tables used:** aws-blog-posts

**Changes needed:**
```python
import os

def lambda_handler(event, context):
    table_suffix = os.environ.get('TABLE_SUFFIX', '')
    table = dynamodb.Table(f'aws-blog-posts{table_suffix}')
    
    # Rest of chat logic...
```

---

## How It Works

### Production Environment
- API Gateway prod stage has no `TABLE_SUFFIX` variable (or empty string)
- Lambda uses: `aws-blog-posts` + `''` = `aws-blog-posts`
- Lambda uses: `euc-user-profiles` + `''` = `euc-user-profiles`

### Staging Environment
- API Gateway staging stage has `TABLE_SUFFIX=-staging`
- Lambda uses: `aws-blog-posts` + `'-staging'` = `aws-blog-posts-staging`
- Lambda uses: `euc-user-profiles` + `'-staging'` = `euc-user-profiles-staging`

---

## Testing After Updates

### 1. Deploy to Staging First
```bash
# Update Lambda code
# Deploy to staging alias (uses $LATEST)
python deploy_lambda.py aws-blog-api staging
```

### 2. Test Staging API
```bash
# Test posts endpoint
curl https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/posts

# Should return 50 posts from staging table
```

### 3. Verify Isolation
```python
# Check staging table
import boto3
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
staging_table = dynamodb.Table('aws-blog-posts-staging')
response = staging_table.scan()
print(f"Staging has {response['Count']} posts")

# Check production table
prod_table = dynamodb.Table('aws-blog-posts')
response = prod_table.scan()
print(f"Production has {response['Count']} posts")
```

### 4. Deploy to Production
Once staging tests pass:
```bash
python deploy_lambda.py aws-blog-api production
```

---

## Deployment Order

1. **aws-blog-api** (highest priority - handles all API requests)
2. **enhanced_crawler_lambda** (test crawler in staging)
3. **builder_selenium_crawler** (test crawler in staging)
4. **summary_lambda** (test summary generation in staging)
5. **classifier_lambda** (test classification in staging)
6. **chat_lambda** (test chat in staging)

---

## Rollback Plan

If issues occur after deployment:

### For Staging
- Staging uses $LATEST, so just redeploy previous code
- No impact to production

### For Production
- Update production alias to previous version:
```bash
aws lambda update-alias \
  --function-name aws-blog-api \
  --name production \
  --function-version <previous-version-number>
```

---

## Where to Get Lambda Source Code

The Lambda source files are not in this workspace. You need to:

1. **Download from AWS Lambda Console:**
   - Go to Lambda console
   - Select function
   - Download deployment package
   - Extract and edit

2. **Or retrieve from your repository:**
   - Check if you have a separate repo for Lambda functions
   - Clone and update there

3. **Or retrieve from S3 (if you have backups):**
   - Check if deployment packages are stored in S3

---

## Next Steps

1. ✅ Staging tables created
2. ✅ Environment variables configured
3. ✅ API Gateway stage variables set
4. ⏳ **UPDATE LAMBDA CODE** (this step)
5. ⏳ Test in staging
6. ⏳ Deploy to production
7. ⏳ Create deployment scripts (Phase 4)
8. ⏳ Final documentation (Phase 5)
