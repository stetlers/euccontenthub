#!/usr/bin/env python3
"""
Deploy crawler and summary Lambda with staging environment fix.
Both Lambdas now properly handle table_name from event payload.
"""
import boto3
import zipfile
import os
import time

def create_crawler_zip():
    """Create deployment package for crawler Lambda"""
    print("Creating crawler Lambda deployment package...")
    
    zip_filename = 'enhanced_crawler_lambda.zip'
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write('enhanced_crawler_lambda.py')
    
    print(f"✓ Created {zip_filename}")
    return zip_filename

def create_summary_zip():
    """Create deployment package for summary Lambda"""
    print("Creating summary Lambda deployment package...")
    
    zip_filename = 'summary_lambda.zip'
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add summary_lambda.py as lambda_function.py (handler expects this name)
        zipf.write('summary_lambda.py', 'lambda_function.py')
    
    print(f"✓ Created {zip_filename}")
    return zip_filename

def deploy_lambda(function_name, zip_filename):
    """Deploy Lambda function"""
    print(f"\nDeploying {function_name}...")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Read the zip file
    with open(zip_filename, 'rb') as f:
        zip_content = f.read()
    
    # Update Lambda function code
    response = lambda_client.update_function_code(
        FunctionName=function_name,
        ZipFile=zip_content,
        Publish=True  # Publish a new version
    )
    
    version = response['Version']
    print(f"✓ Deployed {function_name} version {version}")
    
    # Wait for function to be updated
    print("  Waiting for function to be ready...")
    waiter = lambda_client.get_waiter('function_updated')
    waiter.wait(FunctionName=function_name)
    
    return version

def create_classifier_zip():
    """Create deployment package for classifier Lambda"""
    print("Creating classifier Lambda deployment package...")
    
    zip_filename = 'classifier_lambda.zip'
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add classifier_lambda.py as lambda_function.py (handler expects this name)
        zipf.write('classifier_lambda.py', 'lambda_function.py')
    
    print(f"✓ Created {zip_filename}")
    return zip_filename

def main():
    print("="*60)
    print("DEPLOYING STAGING ENVIRONMENT FIX")
    print("="*60)
    print("\nThis deployment fixes:")
    print("1. Crawler passes table_name to summary Lambda")
    print("2. Summary Lambda reads table_name from event payload")
    print("3. Summary Lambda passes table_name to classifier Lambda")
    print("4. Classifier Lambda reads table_name from event payload")
    print("5. All Lambdas respect staging/production environment")
    print()
    
    # Create deployment packages
    crawler_zip = create_crawler_zip()
    summary_zip = create_summary_zip()
    classifier_zip = create_classifier_zip()
    
    # Deploy crawler Lambda
    crawler_version = deploy_lambda('aws-blog-crawler', crawler_zip)
    
    # Deploy summary Lambda
    summary_version = deploy_lambda('aws-blog-summary-generator', summary_zip)
    
    # Deploy classifier Lambda
    classifier_version = deploy_lambda('aws-blog-classifier', classifier_zip)
    
    # Clean up zip files
    os.remove(crawler_zip)
    os.remove(summary_zip)
    os.remove(classifier_zip)
    
    print("\n" + "="*60)
    print("DEPLOYMENT COMPLETE")
    print("="*60)
    print(f"\nCrawler Lambda: version {crawler_version}")
    print(f"Summary Lambda: version {summary_version}")
    print(f"Classifier Lambda: version {classifier_version}")
    print("\nNext steps:")
    print("1. Test staging crawler: Click 'Crawl' on staging site")
    print("2. Verify summaries are generated for staging posts")
    print("3. Verify labels are generated for staging posts")
    print("4. Check CloudWatch logs for all Lambdas")
    print("5. Confirm staging table is used (aws-blog-posts-staging)")

if __name__ == '__main__':
    main()
