#!/usr/bin/env python3
"""
Download the deployed crawler code to see what's actually running
"""
import boto3
import json
import zipfile
import io

lambda_client = boto3.client('lambda', region_name='us-east-1')

print("="*80)
print("DOWNLOADING PRODUCTION CRAWLER CODE")
print("="*80)

function_name = 'aws-blog-crawler'

# Get the production alias
print(f"\n1. Getting production alias...")
try:
    alias_response = lambda_client.get_alias(
        FunctionName=function_name,
        Name='production'
    )
    version = alias_response['FunctionVersion']
    print(f"   Production alias → v{version}")
except Exception as e:
    print(f"   ERROR: {e}")
    exit(1)

# Get the function code
print(f"\n2. Downloading code for v{version}...")
try:
    response = lambda_client.get_function(
        FunctionName=function_name,
        Qualifier=version
    )
    
    code_location = response['Code']['Location']
    print(f"   Code location: {code_location[:80]}...")
    
    # Download the zip
    import urllib.request
    print(f"   Downloading zip file...")
    with urllib.request.urlopen(code_location) as response:
        zip_data = response.read()
    
    print(f"   Downloaded {len(zip_data)} bytes")
    
    # Extract and check the code
    print(f"\n3. Examining code...")
    with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
        print(f"   Files in deployment package:")
        for name in z.namelist():
            info = z.getinfo(name)
            print(f"     - {name} ({info.file_size} bytes)")
        
        # Check if it has the ECS invocation code
        if 'lambda_function.py' in z.namelist():
            code = z.read('lambda_function.py').decode('utf-8')
            
            print(f"\n4. Checking for key features...")
            
            # Check for Builder.AWS crawler
            if 'BuilderAWSCrawler' in code:
                print(f"   ✓ Has BuilderAWSCrawler class")
            else:
                print(f"   ✗ Missing BuilderAWSCrawler class")
            
            # Check for ECS invocation
            if 'ecs_client' in code or 'run_task' in code:
                print(f"   ✓ Has ECS invocation code")
            else:
                print(f"   ✗ Missing ECS invocation code")
            
            # Check for changed_post_ids tracking
            if 'changed_post_ids' in code:
                print(f"   ✓ Tracks changed post IDs")
            else:
                print(f"   ✗ Does NOT track changed post IDs")
            
            # Look for the lambda_handler
            print(f"\n5. Checking lambda_handler...")
            if "source in ['all', 'builder']" in code:
                print(f"   ✓ Supports Builder.AWS crawling")
            else:
                print(f"   ✗ Does NOT support Builder.AWS crawling")
            
            # Check if ECS invocation is present
            if 'Invoke ECS Selenium crawler' in code or 'invoking ECS' in code:
                print(f"   ✓ Has ECS invocation logic")
            else:
                print(f"   ✗ Missing ECS invocation logic")
            
            # Save the code for inspection
            with open('deployed_crawler_v5.py', 'w', encoding='utf-8') as f:
                f.write(code)
            print(f"\n6. Saved deployed code to: deployed_crawler_v5.py")
            
        else:
            print(f"   ERROR: lambda_function.py not found in package")
    
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("DIAGNOSIS")
print("="*80)
print("\nCheck deployed_crawler_v5.py to see what code is actually running.")
print("Compare it with enhanced_crawler_lambda.py to see what's different.")
