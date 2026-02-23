"""
Build Docker image using CodeBuild and push to ECR
"""

import boto3
import zipfile
import os
import time

# AWS clients
s3_client = boto3.client('s3', region_name='us-east-1')
codebuild_client = boto3.client('codebuild', region_name='us-east-1')

# Configuration
BUCKET_NAME = 'codebuild-source-031421429609'  # Will create if doesn't exist
SOURCE_ZIP = 'selenium-crawler-source.zip'
PROJECT_NAME = 'selenium-crawler-docker-build'

def create_source_zip():
    """Create zip file with Docker build context"""
    print("Creating source zip file...")
    
    files_to_include = [
        'Dockerfile.ecs-selenium',
        'requirements-ecs-selenium.txt',
        'ecs_selenium_crawler.py',
        'buildspec.yml'
    ]
    
    with zipfile.ZipFile(SOURCE_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_include:
            if os.path.exists(file):
                zipf.write(file)
                print(f"  Added: {file}")
            else:
                print(f"  WARNING: {file} not found")
    
    print(f"✓ Created {SOURCE_ZIP}")


def create_bucket_if_needed():
    """Create S3 bucket for CodeBuild source if it doesn't exist"""
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        print(f"✓ Bucket {BUCKET_NAME} exists")
    except:
        print(f"Creating bucket {BUCKET_NAME}...")
        s3_client.create_bucket(Bucket=BUCKET_NAME)
        print(f"✓ Created bucket {BUCKET_NAME}")


def upload_source_to_s3():
    """Upload source zip to S3"""
    print(f"Uploading {SOURCE_ZIP} to S3...")
    s3_client.upload_file(SOURCE_ZIP, BUCKET_NAME, SOURCE_ZIP)
    print(f"✓ Uploaded to s3://{BUCKET_NAME}/{SOURCE_ZIP}")


def start_codebuild():
    """Start CodeBuild project"""
    print(f"\nStarting CodeBuild project: {PROJECT_NAME}")
    
    response = codebuild_client.start_build(
        projectName=PROJECT_NAME
    )
    
    build_id = response['build']['id']
    build_number = response['build']['buildNumber']
    
    print(f"✓ Build started: {build_id}")
    print(f"  Build number: {build_number}")
    
    return build_id


def monitor_build(build_id):
    """Monitor CodeBuild progress"""
    print("\nMonitoring build progress...")
    print("(You can also view in AWS Console: CodeBuild > Build projects > selenium-crawler-docker-build)")
    
    while True:
        response = codebuild_client.batch_get_builds(ids=[build_id])
        build = response['builds'][0]
        
        status = build['buildStatus']
        phase = build.get('currentPhase', 'UNKNOWN')
        
        print(f"  Status: {status} | Phase: {phase}")
        
        if status in ['SUCCEEDED', 'FAILED', 'STOPPED']:
            break
        
        time.sleep(10)
    
    if status == 'SUCCEEDED':
        print("\n✅ Build succeeded!")
        print(f"   Docker image pushed to: 031421429609.dkr.ecr.us-east-1.amazonaws.com/selenium-crawler:latest")
        return True
    else:
        print(f"\n✗ Build {status}")
        print("   Check CloudWatch logs for details")
        return False


def create_codebuild_project_if_needed():
    """Create CodeBuild project if it doesn't exist"""
    try:
        codebuild_client.batch_get_projects(names=[PROJECT_NAME])
        print(f"✓ CodeBuild project {PROJECT_NAME} exists")
    except:
        print(f"Creating CodeBuild project {PROJECT_NAME}...")
        
        import json
        with open('codebuild-project.json', 'r') as f:
            project_config = json.load(f)
        
        codebuild_client.create_project(**project_config)
        print(f"✓ Created CodeBuild project {PROJECT_NAME}")


def main():
    print("=== Building Docker Image with CodeBuild ===\n")
    
    # Step 1: Create source zip
    create_source_zip()
    
    # Step 2: Create S3 bucket if needed
    create_bucket_if_needed()
    
    # Step 3: Upload source to S3
    upload_source_to_s3()
    
    # Step 3.5: Create CodeBuild project if needed
    create_codebuild_project_if_needed()
    
    # Step 4: Start CodeBuild
    build_id = start_codebuild()
    
    # Step 5: Monitor build
    success = monitor_build(build_id)
    
    # Cleanup
    if os.path.exists(SOURCE_ZIP):
        os.remove(SOURCE_ZIP)
        print(f"\nCleaned up {SOURCE_ZIP}")
    
    if success:
        print("\n=== Next Steps ===")
        print("1. Register ECS task definition")
        print("2. Test ECS task with: aws ecs run-task ...")
        print("3. Update sitemap crawler to invoke ECS task")
    
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
