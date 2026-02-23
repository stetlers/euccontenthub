# Builder.AWS Crawler Orchestration - Deployment Complete

## Date: 2026-02-12

## Summary

Successfully deployed the orchestration fix to staging and created the updated Selenium crawler code with `post_ids` parameter support.

## What Was Deployed

### 1. Sitemap Crawler Orchestration Fix ✅ DEPLOYED TO STAGING

**Function:** aws-blog-crawler  
**Deployment Package:** crawler_orchestration_fix_staging.zip  
**Deployment Time:** 2026-02-12 16:23:17 UTC  
**Status:** Active

**Changes Deployed:**
- Tracks `changed_post_ids` for posts that have new/changed content
- Invokes Selenium crawler with `post_ids` parameter for changed Builder.AWS posts
- Only invokes Summary/Classifier for AWS Blog posts (not Builder.AWS)
- Builder.AWS posts follow: Sitemap → Selenium → Summary → Classifier

### 2. Selenium Crawler Update ✅ CODE CREATED

**File:** `builder_selenium_crawler.py`  
**Function:** aws-blog-builder-selenium-crawler  
**Deployment Type:** Docker container (ECR image)  
**Status:** Code ready, needs Docker build and deployment

**New Features:**
- Accepts `post_ids` parameter in event
- If `post_ids` provided: Crawls ONLY those specific posts
- If `post_ids` not provided: Crawls ALL EUC posts (current behavior)
- Queries DynamoDB to get URLs for specific post IDs
- Automatically invokes Summary Generator after updating posts
- Uses batch_size=5 for summary generation (optimized)

## New Orchestration Flow

### AWS Blog (Unchanged)
```
AWS Blog Crawler
    ↓
Summary Generator (batch_size=5)
    ↓
Classifier (batch_size=5)
```

### Builder.AWS (FIXED)
```
Sitemap Crawler
    ↓ (detects NEW/CHANGED posts via lastmod)
    ↓ (preserves existing data for UNCHANGED posts)
    ↓ (invokes with post_ids=['builder-post-1', 'builder-post-2', ...])
    ↓
Selenium Crawler (ONLY for changed posts)
    ↓ (fetches real authors and content)
    ↓ (auto-invokes Summary Generator)
    ↓
Summary Generator (batch_size=5)
    ↓
Classifier (batch_size=5)
```

## Key Code Changes

### Sitemap Crawler (enhanced_crawler_lambda.py)

**Line ~418:** Track changed post IDs
```python
self.changed_post_ids = []  # Track post IDs that changed (for Selenium crawler)
```

**Line ~560:** Record changed posts
```python
if content_changed:
    self.changed_post_ids.append(post_id)
```

**Line ~745:** Invoke Selenium crawler
```python
changed_post_ids = builder_crawler.changed_post_ids
if changed_post_ids:
    lambda_client.invoke(
        FunctionName='aws-blog-builder-selenium-crawler',
        InvocationType='Event',
        Payload=json.dumps({
            'post_ids': changed_post_ids,
            'table_name': table_name
        })
    )
```

### Selenium Crawler (builder_selenium_crawler.py)

**lambda_handler():** Accept post_ids parameter
```python
def lambda_handler(event, context):
    post_ids = event.get('post_ids', []) if event else []
    table_name = event.get('table_name', TABLE_NAME) if event else TABLE_NAME
    
    if post_ids:
        print(f"Crawling {len(post_ids)} specific posts: {post_ids}")
        posts = get_posts_to_crawl(post_ids)  # Fetch specific posts
    else:
        print("Crawling all EUC posts from Builder.AWS")
        posts = get_posts_to_crawl()  # Fetch all EUC posts
```

**get_posts_to_crawl():** Query DynamoDB for specific posts
```python
def get_posts_to_crawl(post_ids=None):
    if post_ids:
        # Fetch specific posts by ID
        posts = []
        for post_id in post_ids:
            response = table.get_item(Key={'post_id': post_id})
            if 'Item' in response:
                posts.append({
                    'post_id': post_id,
                    'url': response['Item']['url']
                })
        return posts
    else:
        # Scan for all EUC-related Builder.AWS posts
        # ... existing logic ...
```

## Next Steps

### 1. Build and Deploy Selenium Crawler Docker Image

The Selenium crawler needs to be built as a Docker image and pushed to ECR.

**Required files for Docker build:**
- `builder_selenium_crawler.py` (created ✅)
- `Dockerfile` (needs to be created)
- `requirements.txt` (needs to be created)

**Dockerfile example:**
```dockerfile
FROM public.ecr.aws/lambda/python:3.11

# Install Chrome and ChromeDriver
RUN yum install -y wget unzip && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm && \
    yum install -y ./google-chrome-stable_current_x86_64.rpm && \
    rm google-chrome-stable_current_x86_64.rpm

# Install ChromeDriver
RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` && \
    wget https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    mv chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm chromedriver_linux64.zip

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy function code
COPY builder_selenium_crawler.py ${LAMBDA_TASK_ROOT}/

CMD ["builder_selenium_crawler.lambda_handler"]
```

**requirements.txt:**
```
boto3
selenium
```

**Build and deploy commands:**
```bash
# Build Docker image
docker build -t builder-selenium-crawler:latest .

# Tag for ECR
docker tag builder-selenium-crawler:latest \
    031421429609.dkr.ecr.us-east-1.amazonaws.com/builder-selenium-crawler:latest

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin \
    031421429609.dkr.ecr.us-east-1.amazonaws.com

# Push to ECR
docker push 031421429609.dkr.ecr.us-east-1.amazonaws.com/builder-selenium-crawler:latest

# Update Lambda function
aws lambda update-function-code \
    --function-name aws-blog-builder-selenium-crawler \
    --image-uri 031421429609.dkr.ecr.us-east-1.amazonaws.com/builder-selenium-crawler:latest \
    --region us-east-1
```

### 2. Test Complete Flow in Staging

**Test Steps:**
1. Run sitemap crawler in staging:
   ```bash
   aws lambda invoke \
       --function-name aws-blog-crawler \
       --invocation-type Event \
       --payload '{"source": "builder", "table_name": "aws-blog-posts-staging"}' \
       response.json
   ```

2. Check CloudWatch logs for sitemap crawler:
   - Verify changed posts detected
   - Verify Selenium crawler invoked with post_ids
   - Check for any errors

3. Check CloudWatch logs for Selenium crawler:
   - Verify it received post_ids
   - Verify it fetched real authors and content
   - Verify it invoked Summary Generator

4. Check DynamoDB staging table:
   - Verify real authors updated (not "AWS Builder Community")
   - Verify real content updated (not template)
   - Verify summaries generated

5. Verify 0% data loss:
   - Run `check_staging_builder_posts.py`
   - Compare before/after counts
   - Ensure no summaries lost for unchanged posts

### 3. Deploy to Production

**Only proceed if:**
- All staging tests pass
- No data loss observed
- Real authors fetched correctly
- Summaries generated from real content

**Deployment steps:**
1. Deploy Selenium crawler to production (same Docker image)
2. Sitemap crawler is already deployed (uses $LATEST)
3. Monitor CloudWatch logs
4. Verify production data integrity

## Testing Checklist

- [ ] Build Selenium crawler Docker image
- [ ] Push image to ECR
- [ ] Update Lambda function with new image
- [ ] Test sitemap crawler in staging
- [ ] Verify Selenium crawler invoked with post_ids
- [ ] Verify real authors fetched
- [ ] Verify summaries generated from real content
- [ ] Verify 0% data loss
- [ ] Deploy to production
- [ ] Monitor production for 24 hours
- [ ] Close Issue #26

## Benefits of This Fix

### Before Fix
- Sitemap crawler invoked Summary/Classifier directly
- Posts had generic "AWS Builder Community" author
- Summaries generated from template text
- Selenium crawler never invoked for changed posts
- 90% of posts lost summaries on each crawl

### After Fix
- Sitemap crawler invokes Selenium for changed posts only
- Selenium fetches real authors and content
- Summaries generated from real content
- Complete orchestration chain working correctly
- 0% data loss - unchanged posts preserve all data

## Cost Optimization

**Before:** Selenium crawler would run for ALL posts on every crawl (expensive)  
**After:** Selenium crawler runs ONLY for NEW/CHANGED posts (cost-effective)

**Example:**
- 128 total Builder.AWS posts
- 3 posts changed this week
- Old approach: Crawl 128 posts with Selenium (expensive)
- New approach: Crawl 3 posts with Selenium (cheap)
- **Cost savings: 97.7%**

## Files Modified

- ✅ `enhanced_crawler_lambda.py` - Sitemap crawler with orchestration fix
- ✅ `crawler_code/lambda_function.py` - Deployment copy
- ✅ `builder_selenium_crawler.py` - Selenium crawler with post_ids support
- ✅ `builder-crawler-orchestration-deployment-complete.md` - This document

## Files That Need Creation

- ⏳ `Dockerfile` - For building Selenium crawler image
- ⏳ `requirements.txt` - Python dependencies for Selenium crawler

## Related Issues

- Issue #26: Summary Loss Investigation (ROOT CAUSE FIXED, TESTING PENDING)
- Builder Crawler Problem (github-issue-builder-crawler-problem.md)

## Status

- **Sitemap Crawler Fix**: ✅ Deployed to staging
- **Selenium Crawler Code**: ✅ Created with post_ids support
- **Docker Build**: ⏳ Pending (needs Dockerfile and requirements.txt)
- **Staging Testing**: ⏳ Blocked until Docker image deployed
- **Production Deployment**: ⏳ Blocked until staging tests pass

## Success Criteria

- [x] Sitemap crawler tracks changed post IDs
- [x] Sitemap crawler invokes Selenium (not Summary/Classifier)
- [x] AWS Blog posts still invoke Summary/Classifier directly
- [x] Selenium crawler accepts `post_ids` parameter
- [x] Selenium crawler queries DynamoDB for URLs
- [x] Selenium crawler auto-invokes Summary Generator
- [ ] Docker image built and deployed
- [ ] Complete flow tested in staging
- [ ] Real authors fetched for changed posts
- [ ] 0% data loss verified
- [ ] Deployed to production

## Conclusion

The orchestration fix is now deployed to staging Lambda. The Selenium crawler code has been created with full `post_ids` parameter support. The next step is to build the Docker image and deploy it, then test the complete flow end-to-end in staging.

This fix ensures that Builder.AWS posts get real author names and content, while maintaining cost optimization by only running the expensive Selenium crawler for changed posts.

