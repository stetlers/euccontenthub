# Selenium Crawler ECS/Fargate Migration - Design

## Architecture Overview

```
┌─────────────────────┐
│  Sitemap Crawler    │
│  (Lambda)           │
└──────────┬──────────┘
           │ Detects changed posts
           │ Invokes with post_ids
           ▼
┌─────────────────────┐
│  ECS Fargate Task   │
│  ┌───────────────┐  │
│  │ Selenium      │  │
│  │ + Chrome      │  │
│  │ + Python      │  │
│  └───────────────┘  │
└──────────┬──────────┘
           │ Extracts authors/content
           │ Updates DynamoDB
           │ Invokes Summary Lambda
           ▼
┌─────────────────────┐
│  Summary Generator  │
│  (Lambda)           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Classifier         │
│  (Lambda)           │
└─────────────────────┘
```

## Component Design

### 1. Docker Container

**Base Image**: `selenium/standalone-chrome:latest`
- Pre-configured Chrome + ChromeDriver
- Proven stability in containerized environments
- Regular security updates

**Custom Additions**:
```dockerfile
FROM selenium/standalone-chrome:latest

# Install Python and dependencies
USER root
RUN apt-get update && apt-get install -y python3 python3-pip
COPY requirements.txt /app/
RUN pip3 install -r /app/requirements.txt

# Copy crawler code
COPY crawler.py /app/
WORKDIR /app

# Run as non-root user
USER seluser

# Entry point
CMD ["python3", "crawler.py"]
```

**Dependencies** (requirements.txt):
```
boto3==1.34.0
selenium==4.16.0
```

### 2. ECS Task Definition

**Compute Configuration**:
- **Launch Type**: Fargate (serverless)
- **CPU**: 2048 (2 vCPU)
- **Memory**: 4096 MB (4 GB)
- **Platform**: Linux/AMD64

**Network Configuration**:
- **VPC**: Default VPC
- **Subnets**: Public subnets (for internet access)
- **Security Group**: Allow outbound HTTPS (443)
- **Assign Public IP**: Yes (required for internet access)

**Task Role Permissions**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:031421429609:table/aws-blog-posts",
        "arn:aws:dynamodb:us-east-1:031421429609:table/aws-blog-posts-staging"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": [
        "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-summary-generator:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:031421429609:log-group:/ecs/selenium-crawler:*"
    }
  ]
}
```

**Environment Variables**:
- `DYNAMODB_TABLE_NAME`: Table name (passed at runtime)
- `ENVIRONMENT`: "staging" or "production"
- `POST_IDS`: Comma-separated list of post IDs (passed at runtime)

### 3. Crawler Application (crawler.py)

**Entry Point**:
```python
def main():
    # Read environment variables
    table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')
    environment = os.environ.get('ENVIRONMENT', 'production')
    post_ids_str = os.environ.get('POST_IDS', '')
    
    # Parse post IDs
    post_ids = [pid.strip() for pid in post_ids_str.split(',') if pid.strip()]
    
    # Initialize crawler
    crawler = SeleniumCrawler(table_name, environment)
    
    # Run crawler
    results = crawler.crawl(post_ids)
    
    # Invoke summary generator if posts were updated
    if results['posts_updated'] > 0:
        invoke_summary_generator(environment, results['posts_updated'])
    
    # Exit with status code
    sys.exit(0 if results['posts_failed'] == 0 else 1)
```

**Chrome Configuration**:
```python
def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Connect to standalone Chrome (running in same container)
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    
    return driver
```

**Error Handling**:
```python
def extract_page_content(driver, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extract author and content
            author = extract_author(driver)
            content = extract_content(driver)
            
            return {'authors': author, 'content': content}
            
        except TimeoutException:
            if attempt < max_retries - 1:
                print(f"  Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(2)
            else:
                print(f"  Failed after {max_retries} attempts")
                return None
                
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None
```

### 4. Sitemap Crawler Integration

**Invocation Code** (in enhanced_crawler_lambda.py):
```python
def invoke_selenium_ecs_task(post_ids, environment='staging'):
    """Invoke ECS Fargate task for Selenium crawling"""
    import boto3
    
    ecs_client = boto3.client('ecs', region_name='us-east-1')
    
    # Determine table name based on environment
    table_name = 'aws-blog-posts' if environment == 'production' else 'aws-blog-posts-staging'
    
    # Task configuration
    cluster = 'selenium-crawler-cluster'
    task_definition = f'selenium-crawler-task:{environment}'
    
    # Convert post_ids list to comma-separated string
    post_ids_str = ','.join(post_ids)
    
    try:
        response = ecs_client.run_task(
            cluster=cluster,
            taskDefinition=task_definition,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': ['subnet-xxxxx'],  # Public subnet
                    'securityGroups': ['sg-xxxxx'],  # Allow outbound HTTPS
                    'assignPublicIp': 'ENABLED'
                }
            },
            overrides={
                'containerOverrides': [
                    {
                        'name': 'selenium-crawler',
                        'environment': [
                            {'name': 'DYNAMODB_TABLE_NAME', 'value': table_name},
                            {'name': 'ENVIRONMENT', 'value': environment},
                            {'name': 'POST_IDS', 'value': post_ids_str}
                        ]
                    }
                ]
            }
        )
        
        task_arn = response['tasks'][0]['taskArn']
        print(f"✓ Invoked ECS task: {task_arn}")
        return True
        
    except Exception as e:
        print(f"✗ Error invoking ECS task: {e}")
        return False
```

### 5. CloudWatch Logging

**Log Group**: `/ecs/selenium-crawler`

**Log Format**:
```
[2026-02-12 19:00:00] Starting Selenium crawler
[2026-02-12 19:00:00] Environment: staging
[2026-02-12 19:00:00] Table: aws-blog-posts-staging
[2026-02-12 19:00:00] Post IDs: builder-post-1, builder-post-2, builder-post-3
[2026-02-12 19:00:05] [1/3] Processing: https://builder.aws.com/...
[2026-02-12 19:00:10]   ✓ Extracted author: John Doe
[2026-02-12 19:00:10]   ✓ Updated DynamoDB
[2026-02-12 19:00:15] [2/3] Processing: https://builder.aws.com/...
[2026-02-12 19:00:20]   ✓ Extracted author: Jane Smith
[2026-02-12 19:00:20]   ✓ Updated DynamoDB
[2026-02-12 19:00:25] [3/3] Processing: https://builder.aws.com/...
[2026-02-12 19:00:30]   ✓ Extracted author: Bob Johnson
[2026-02-12 19:00:30]   ✓ Updated DynamoDB
[2026-02-12 19:00:35] 3 posts updated - invoking summary generator
[2026-02-12 19:00:36]   ✓ Invoked summary batch 1/1
[2026-02-12 19:00:36] Crawler completed successfully
```

## Data Flow

### Input (from Sitemap Crawler)
```json
{
  "post_ids": [
    "builder-post-1",
    "builder-post-2",
    "builder-post-3"
  ],
  "environment": "staging"
}
```

### Processing
1. ECS task starts
2. Reads environment variables
3. Queries DynamoDB for post URLs
4. For each post:
   - Load page with Selenium
   - Extract author name
   - Extract content (first 3000 chars)
   - Update DynamoDB
5. Invoke Summary Generator Lambda
6. Task terminates

### Output (DynamoDB Update)
```python
{
  'post_id': 'builder-post-1',
  'authors': 'John Doe',  # Real author name
  'content': '...',  # First 3000 chars
  'last_crawled': '2026-02-12T19:00:10.000Z'
}
```

## Infrastructure as Code

### ECS Cluster
```bash
aws ecs create-cluster \
  --cluster-name selenium-crawler-cluster \
  --region us-east-1
```

### ECR Repository
```bash
aws ecr create-repository \
  --repository-name selenium-crawler \
  --region us-east-1
```

### Task Definition (JSON)
```json
{
  "family": "selenium-crawler-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::031421429609:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::031421429609:role/selenium-crawler-task-role",
  "containerDefinitions": [
    {
      "name": "selenium-crawler",
      "image": "031421429609.dkr.ecr.us-east-1.amazonaws.com/selenium-crawler:latest",
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/selenium-crawler",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "environment": [
        {
          "name": "DYNAMODB_TABLE_NAME",
          "value": "aws-blog-posts"
        },
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ]
    }
  ]
}
```

## Deployment Process

### 1. Build Docker Image
```bash
# Build image
docker build -t selenium-crawler:latest .

# Tag for ECR
docker tag selenium-crawler:latest \
  031421429609.dkr.ecr.us-east-1.amazonaws.com/selenium-crawler:latest

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  031421429609.dkr.ecr.us-east-1.amazonaws.com

# Push to ECR
docker push 031421429609.dkr.ecr.us-east-1.amazonaws.com/selenium-crawler:latest
```

### 2. Register Task Definition
```bash
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region us-east-1
```

### 3. Update Sitemap Crawler
```bash
# Deploy updated sitemap crawler with ECS invocation code
aws lambda update-function-code \
  --function-name aws-blog-crawler \
  --zip-file fileb://crawler_with_ecs.zip \
  --region us-east-1
```

## Testing Strategy

### Unit Tests
- Test Chrome configuration
- Test author extraction logic
- Test content extraction logic
- Test DynamoDB updates
- Test error handling

### Integration Tests
1. **Local Docker Test**:
   ```bash
   docker run -e POST_IDS="builder-post-1" \
              -e DYNAMODB_TABLE_NAME="aws-blog-posts-staging" \
              -e ENVIRONMENT="staging" \
              selenium-crawler:latest
   ```

2. **ECS Task Test**:
   ```bash
   aws ecs run-task \
     --cluster selenium-crawler-cluster \
     --task-definition selenium-crawler-task:staging \
     --launch-type FARGATE \
     --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}" \
     --overrides '{"containerOverrides":[{"name":"selenium-crawler","environment":[{"name":"POST_IDS","value":"builder-post-1"}]}]}'
   ```

3. **End-to-End Test**:
   - Modify post date in staging DynamoDB
   - Invoke sitemap crawler
   - Verify ECS task starts
   - Verify real author extracted
   - Verify Summary/Classifier invoked

## Monitoring and Alerts

### CloudWatch Metrics
- Task start count
- Task success count
- Task failure count
- Task duration
- Chrome crash count

### CloudWatch Alarms
- Alert if task failure rate > 5%
- Alert if task duration > 10 minutes
- Alert if no tasks run for 7 days (indicates orchestration broken)

## Rollback Plan

If ECS migration fails:
1. Revert sitemap crawler to invoke Lambda (old behavior)
2. Keep ECS infrastructure for future attempts
3. Document lessons learned

## Cost Estimate

**Per Invocation** (40 posts):
- ECS Fargate: 2 vCPU × 4 GB × 5 minutes = $0.02
- Data transfer: Negligible
- CloudWatch logs: Negligible

**Monthly** (assuming 4 crawls/month):
- Total: ~$0.08/month

**Comparison to Lambda**:
- Lambda was free (within free tier)
- ECS adds ~$1/year
- Acceptable cost for reliability

## Security Considerations

1. **Task Role**: Least privilege (only DynamoDB + Lambda access)
2. **Network**: Public subnet required for internet, but no inbound access
3. **Secrets**: No secrets needed (uses IAM roles)
4. **Container**: Use official Selenium image (regularly updated)

## Success Metrics

- ✅ Chrome crash rate < 5%
- ✅ Content extraction success rate > 95%
- ✅ Task completion rate > 99%
- ✅ Real author names for 100% of Builder.AWS posts
- ✅ End-to-end orchestration working

## Future Enhancements

1. **Parallel Processing**: Run multiple tasks concurrently for large batches
2. **Caching**: Cache extracted content to avoid re-crawling
3. **Monitoring Dashboard**: Custom CloudWatch dashboard
4. **Auto-scaling**: Scale task count based on post_ids length
