#!/usr/bin/env python3
"""
Deploy Builder.AWS Selenium Crawler to AWS Lambda

This script:
1. Builds Docker image with Chrome and Selenium
2. Tags image for ECR
3. Pushes to ECR repository
4. Updates Lambda function with new image
"""

import subprocess
import sys
import time

# Configuration
AWS_ACCOUNT_ID = "031421429609"
AWS_REGION = "us-east-1"
ECR_REPOSITORY = "builder-selenium-crawler"
LAMBDA_FUNCTION = "aws-blog-builder-selenium-crawler"
IMAGE_TAG = "latest"

# Construct image URIs
LOCAL_IMAGE = f"{ECR_REPOSITORY}:{IMAGE_TAG}"
ECR_IMAGE = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/{ECR_REPOSITORY}:{IMAGE_TAG}"


def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Command: {command}\n")
    
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.stdout:
        print(result.stdout)
    
    if result.returncode != 0:
        print(f"❌ Error: {description} failed")
        if result.stderr:
            print(f"Error output: {result.stderr}")
        return False
    
    print(f"✅ {description} completed successfully")
    return True


def main():
    print("="*60)
    print("Builder.AWS Selenium Crawler Deployment")
    print("="*60)
    print(f"ECR Repository: {ECR_REPOSITORY}")
    print(f"Lambda Function: {LAMBDA_FUNCTION}")
    print(f"Image Tag: {IMAGE_TAG}")
    print(f"Region: {AWS_REGION}")
    
    # Step 1: Build Docker image
    if not run_command(
        f"docker build -t {LOCAL_IMAGE} -f Dockerfile.selenium .",
        "Building Docker image"
    ):
        sys.exit(1)
    
    # Step 2: Tag image for ECR
    if not run_command(
        f"docker tag {LOCAL_IMAGE} {ECR_IMAGE}",
        "Tagging image for ECR"
    ):
        sys.exit(1)
    
    # Step 3: Login to ECR
    if not run_command(
        f"aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com",
        "Logging in to ECR"
    ):
        sys.exit(1)
    
    # Step 4: Push image to ECR
    if not run_command(
        f"docker push {ECR_IMAGE}",
        "Pushing image to ECR"
    ):
        sys.exit(1)
    
    # Step 5: Update Lambda function
    print("\n" + "="*60)
    print("Updating Lambda function...")
    print("="*60)
    print("⏳ This may take 1-2 minutes while Lambda pulls the new image\n")
    
    if not run_command(
        f"aws lambda update-function-code --function-name {LAMBDA_FUNCTION} --image-uri {ECR_IMAGE} --region {AWS_REGION}",
        "Updating Lambda function"
    ):
        sys.exit(1)
    
    # Step 6: Wait for Lambda to be ready
    print("\n" + "="*60)
    print("Waiting for Lambda function to be ready...")
    print("="*60)
    
    max_attempts = 30
    for attempt in range(max_attempts):
        result = subprocess.run(
            f"aws lambda get-function-configuration --function-name {LAMBDA_FUNCTION} --region {AWS_REGION} --query 'LastUpdateStatus' --output text",
            shell=True,
            capture_output=True,
            text=True
        )
        
        status = result.stdout.strip()
        print(f"Attempt {attempt + 1}/{max_attempts}: Status = {status}")
        
        if status == "Successful":
            print("\n✅ Lambda function is ready!")
            break
        elif status == "Failed":
            print("\n❌ Lambda function update failed!")
            sys.exit(1)
        
        time.sleep(10)
    else:
        print("\n⚠️  Timeout waiting for Lambda to be ready")
        print("Check AWS Console for status")
    
    # Summary
    print("\n" + "="*60)
    print("DEPLOYMENT COMPLETE")
    print("="*60)
    print(f"✅ Docker image built: {LOCAL_IMAGE}")
    print(f"✅ Image pushed to ECR: {ECR_IMAGE}")
    print(f"✅ Lambda function updated: {LAMBDA_FUNCTION}")
    print("\nNext steps:")
    print("1. Test the Selenium crawler in staging")
    print("2. Run sitemap crawler to trigger the orchestration")
    print("3. Verify real authors and content are fetched")
    print("4. Check CloudWatch logs for any errors")


if __name__ == "__main__":
    main()
