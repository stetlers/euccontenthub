# Docker Build Quick Start Guide

## Prerequisites Check

Before starting, verify you have:
- [ ] Docker installed and running
- [ ] AWS CLI configured
- [ ] Access to AWS account 031421429609
- [ ] All files present in project directory

## Quick Start (5 Minutes)

### Step 1: Verify Files Exist
```bash
ls -la builder_selenium_crawler.py
ls -la Dockerfile.selenium
ls -la requirements-selenium.txt
```

All three files should exist.

### Step 2: Build Docker Image
```bash
docker build -t builder-selenium-crawler:latest -f Dockerfile.selenium .
```

Expected output: "Successfully built..." and "Successfully tagged..."

### Step 3: Run Deployment Script
```bash
python deploy_selenium_crawler.py
```

This script will:
1. Tag the image for ECR
2. Login to ECR
3. Push image to ECR
4. Update Lambda function
5. Wait for Lambda to be ready

### Step 4: Verify Deployment
```bash
aws lambda get-function-configuration \
    --function-name aws-blog-builder-selenium-crawler \
    --region us-east-1 \
    --query 'LastUpdateStatus'
```

Should return: `"Successful"`

### Step 5: Test It
```bash
# Test with a specific post ID
aws lambda invoke \
    --function-name aws-blog-builder-selenium-crawler \
    --invocation-type RequestResponse \
    --payload '{"post_ids": ["builder-getting-started-appstream"], "table_name": "aws-blog-posts-staging"}' \
    response.json \
    --region us-east-1

# Check the response
cat response.json
```

## If You Don't Have Docker Locally

### Option A: AWS Cloud9 (Recommended)

1. Go to AWS Console → Cloud9
2. Create new environment (t3.small, Amazon Linux 2)
3. Wait for environment to be ready
4. In Cloud9 terminal:
   ```bash
   # Clone repo
   git clone https://github.com/stetlers/euccontenthub.git
   cd euccontenthub
   
   # Install Docker
   sudo yum update -y
   sudo yum install -y docker
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   
   # Log out and back in
   exit
   # (reconnect to Cloud9)
   
   # Run deployment
   python deploy_selenium_crawler.py
   ```

### Option B: Use My Machine

If you want me to guide you through building on your local machine:

1. **Check if Docker is installed:**
   - Windows: Open PowerShell and run `docker --version`
   - Mac: Open Terminal and run `docker --version`
   - Linux: Open Terminal and run `docker --version`

2. **If Docker is not installed:**
   - Windows: Install Docker Desktop from https://www.docker.com/products/docker-desktop
   - Mac: Install Docker Desktop from https://www.docker.com/products/docker-desktop
   - Linux: Run `sudo apt-get install docker.io` (Ubuntu/Debian) or `sudo yum install docker` (RHEL/CentOS)

3. **Once Docker is installed:**
   - Navigate to the project directory
   - Run `python deploy_selenium_crawler.py`

## Troubleshooting

### "docker: command not found"
- Docker is not installed or not in PATH
- Install Docker Desktop (Windows/Mac) or docker package (Linux)

### "permission denied while trying to connect to Docker daemon"
- Run: `sudo usermod -a -G docker $USER`
- Log out and back in
- Or prefix commands with `sudo`

### "authentication required" when pushing to ECR
- Run: `aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 031421429609.dkr.ecr.us-east-1.amazonaws.com`

### Build fails with Chrome errors
- The Dockerfile will download Chrome automatically
- If it fails, check internet connection
- Try building again (sometimes downloads fail)

### Lambda update takes too long
- Lambda needs to pull the Docker image (can take 2-3 minutes)
- Wait for status to change to "Successful"
- Check AWS Console → Lambda → aws-blog-builder-selenium-crawler

## What Happens After Deployment

Once deployed, the complete orchestration will work:

1. **Sitemap Crawler** runs (already deployed to staging)
   - Detects 3 changed Builder.AWS posts
   - Invokes Selenium crawler with `post_ids=['builder-post-1', 'builder-post-2', 'builder-post-3']`

2. **Selenium Crawler** runs (newly deployed)
   - Receives post_ids
   - Queries DynamoDB for URLs
   - Crawls only those 3 posts with Chrome
   - Extracts real author names and content
   - Updates DynamoDB
   - Invokes Summary Generator

3. **Summary Generator** runs
   - Generates summaries for the 3 posts
   - Invokes Classifier

4. **Classifier** runs
   - Classifies the 3 posts

**Result:** 3 posts updated with real data, 125 posts unchanged (0% data loss)

## Next Steps After Deployment

1. Test complete orchestration in staging
2. Verify real authors fetched
3. Verify 0% data loss
4. Deploy to production
5. Close Issue #26

## Need Help?

If you encounter issues:
1. Check the full guide: `SELENIUM-CRAWLER-DEPLOYMENT-GUIDE.md`
2. Check CloudWatch logs for error messages
3. Verify AWS credentials are valid
4. Ensure all files are present

## Summary

The deployment is straightforward:
1. Build Docker image (5 minutes)
2. Push to ECR (2 minutes)
3. Update Lambda (2 minutes)
4. Test (1 minute)

**Total time: ~10 minutes**

Once deployed, the Builder.AWS crawler will work correctly with real authors and 0% data loss.
