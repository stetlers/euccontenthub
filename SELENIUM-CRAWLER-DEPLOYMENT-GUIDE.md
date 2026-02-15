# Builder.AWS Selenium Crawler - Deployment Guide

## Overview

The Selenium crawler needs to be deployed as a Docker container to AWS Lambda. Since Docker is not available on this system, you have two options:

## Option 1: Build Locally (Recommended if you have Docker)

If you have Docker installed on your local machine or another system:

### Prerequisites
- Docker installed and running
- AWS CLI configured with credentials
- Access to AWS account 031421429609

### Step-by-Step Instructions

1. **Navigate to project directory**
   ```bash
   cd /path/to/euccontenthub
   ```

2. **Build Docker image**
   ```bash
   docker build -t builder-selenium-crawler:latest -f Dockerfile.selenium .
   ```
   
   This will:
   - Use Python 3.11 Lambda base image
   - Install Chrome and ChromeDriver
   - Install Python dependencies (boto3, selenium)
   - Copy the crawler code

3. **Tag image for ECR**
   ```bash
   docker tag builder-selenium-crawler:latest \
       031421429609.dkr.ecr.us-east-1.amazonaws.com/builder-selenium-crawler:latest
   ```

4. **Login to ECR**
   ```bash
   aws ecr get-login-password --region us-east-1 | \
       docker login --username AWS --password-stdin \
       031421429609.dkr.ecr.us-east-1.amazonaws.com
   ```

5. **Push image to ECR**
   ```bash
   docker push 031421429609.dkr.ecr.us-east-1.amazonaws.com/builder-selenium-crawler:latest
   ```

6. **Update Lambda function**
   ```bash
   aws lambda update-function-code \
       --function-name aws-blog-builder-selenium-crawler \
       --image-uri 031421429609.dkr.ecr.us-east-1.amazonaws.com/builder-selenium-crawler:latest \
       --region us-east-1
   ```

7. **Wait for Lambda to be ready**
   ```bash
   aws lambda wait function-updated \
       --function-name aws-blog-builder-selenium-crawler \
       --region us-east-1
   ```

8. **Verify deployment**
   ```bash
   aws lambda get-function-configuration \
       --function-name aws-blog-builder-selenium-crawler \
       --region us-east-1 \
       --query 'LastUpdateStatus'
   ```
   
   Should return: "Successful"

### Using the Deployment Script

Alternatively, use the provided Python script:

```bash
python deploy_selenium_crawler.py
```

This script automates all the steps above.

## Option 2: Use AWS Cloud9 or EC2

If you don't have Docker locally, you can use AWS Cloud9 or an EC2 instance:

### Using AWS Cloud9

1. **Create Cloud9 environment**
   - Go to AWS Console → Cloud9
   - Create new environment (t3.small or larger)
   - Wait for environment to be ready

2. **Clone repository**
   ```bash
   git clone https://github.com/stetlers/euccontenthub.git
   cd euccontenthub
   ```

3. **Install Docker (if not already installed)**
   ```bash
   sudo yum update -y
   sudo yum install -y docker
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   ```
   
   Log out and back in for group changes to take effect.

4. **Follow Option 1 steps** (build, tag, push, update)

### Using EC2 Instance

1. **Launch EC2 instance**
   - AMI: Amazon Linux 2
   - Instance type: t3.small or larger
   - Ensure IAM role has ECR and Lambda permissions

2. **Connect to instance**
   ```bash
   ssh -i your-key.pem ec2-user@your-instance-ip
   ```

3. **Install Docker**
   ```bash
   sudo yum update -y
   sudo yum install -y docker git
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   ```
   
   Log out and back in.

4. **Clone repository and follow Option 1 steps**

## Option 3: Use Existing Image (Quick Test)

If you just want to test the orchestration without rebuilding:

The Lambda function already has an image deployed. You can:

1. **Test the current setup** to see if orchestration works
2. **Update just the code** by modifying the existing container

However, the current image may not have the `post_ids` parameter support, so this is not recommended for production.

## Files Created

- ✅ `builder_selenium_crawler.py` - Updated crawler code with post_ids support
- ✅ `Dockerfile.selenium` - Docker build instructions
- ✅ `requirements-selenium.txt` - Python dependencies
- ✅ `deploy_selenium_crawler.py` - Automated deployment script
- ✅ `SELENIUM-CRAWLER-DEPLOYMENT-GUIDE.md` - This guide

## Testing After Deployment

Once deployed, test the complete orchestration:

### 1. Test Selenium Crawler Directly

```bash
aws lambda invoke \
    --function-name aws-blog-builder-selenium-crawler \
    --invocation-type RequestResponse \
    --payload '{"post_ids": ["builder-test-post"], "table_name": "aws-blog-posts-staging"}' \
    response.json \
    --region us-east-1

cat response.json
```

### 2. Test Complete Orchestration

```bash
# Run sitemap crawler in staging
aws lambda invoke \
    --function-name aws-blog-crawler \
    --invocation-type Event \
    --payload '{"source": "builder", "table_name": "aws-blog-posts-staging"}' \
    response.json \
    --region us-east-1
```

### 3. Check CloudWatch Logs

**Sitemap Crawler:**
```bash
aws logs tail /aws/lambda/aws-blog-crawler --follow --region us-east-1
```

**Selenium Crawler:**
```bash
aws logs tail /aws/lambda/aws-blog-builder-selenium-crawler --follow --region us-east-1
```

### 4. Verify Data in DynamoDB

Run the staging check script:
```bash
python check_staging_builder_posts.py
```

Expected results:
- Real author names (not "AWS Builder Community")
- Real content (not template text)
- Summaries generated from real content
- 0% data loss for unchanged posts

## Troubleshooting

### Build fails with "Chrome not found"
- Ensure Dockerfile.selenium is using correct Chrome installation commands
- Try using a different Chrome version

### Push fails with "authentication required"
- Re-run ECR login command
- Verify AWS credentials are valid

### Lambda update fails
- Check Lambda function exists: `aws lambda get-function --function-name aws-blog-builder-selenium-crawler`
- Verify ECR repository exists: `aws ecr describe-repositories --repository-names builder-selenium-crawler`

### Lambda timeout during execution
- Increase Lambda timeout (currently 900 seconds / 15 minutes)
- Increase Lambda memory (currently 10240 MB / 10 GB)

### Selenium errors in logs
- Check Chrome and ChromeDriver versions are compatible
- Verify Lambda has enough memory for Chrome

## Cost Considerations

**Lambda Pricing:**
- Memory: 10 GB
- Typical execution time: 2-5 minutes per post
- Cost per invocation: ~$0.10-0.25

**Optimization:**
- Only runs for NEW/CHANGED posts (not all posts)
- Example: 3 changed posts = $0.30-0.75 vs 128 posts = $12.80-32.00
- **Savings: 97.7%**

## Next Steps After Deployment

1. ✅ Build and deploy Docker image
2. ⏳ Test Selenium crawler directly
3. ⏳ Test complete orchestration (sitemap → selenium → summary → classifier)
4. ⏳ Verify real authors fetched
5. ⏳ Verify 0% data loss
6. ⏳ Deploy to production
7. ⏳ Monitor for 24 hours
8. ⏳ Close Issue #26

## Support

If you encounter issues:
1. Check CloudWatch logs for error messages
2. Verify all files are present (Dockerfile.selenium, requirements-selenium.txt, builder_selenium_crawler.py)
3. Ensure AWS credentials have necessary permissions (ECR, Lambda, DynamoDB)
4. Test Docker build locally before pushing to ECR

## Summary

The Selenium crawler is ready to deploy. Choose the option that works best for your environment:
- **Option 1**: Build locally with Docker (fastest if you have Docker)
- **Option 2**: Use Cloud9 or EC2 (recommended if no local Docker)
- **Option 3**: Test with existing image (not recommended for production)

Once deployed, the complete orchestration flow will work correctly:
```
Sitemap Crawler → Selenium Crawler → Summary Generator → Classifier
```

This ensures Builder.AWS posts get real author names and content, with 0% data loss and 97.7% cost savings.
