"""
Deploy enhanced crawler Lambda with ECS invocation
"""
import zipfile
import boto3
import os

print("=" * 80)
print("Deploying Enhanced Crawler with ECS/Fargate Support")
print("=" * 80)

# Create zip file
zip_file = 'enhanced_crawler_deploy.zip'

print("\n1. Creating deployment package...")
with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('enhanced_crawler_lambda.py', 'lambda_function.py')

print(f"   ✓ Created {zip_file}")

# Get file size
zip_size = os.path.getsize(zip_file) / 1024
print(f"   📦 Package size: {zip_size:.2f} KB")

# Upload to Lambda using boto3
print("\n2. Uploading to Lambda...")
try:
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    with open(zip_file, 'rb') as f:
        zip_content = f.read()
    
    response = lambda_client.update_function_code(
        FunctionName='aws-blog-crawler',
        ZipFile=zip_content
    )
    
    print("   ✓ Code uploaded successfully")
    print(f"   📝 Code SHA256: {response['CodeSha256'][:16]}...")
    
except Exception as e:
    print(f"   ❌ Error uploading: {e}")
    os.remove(zip_file)
    exit(1)

# Wait for update
print("\n3. Waiting for Lambda update...")
try:
    waiter = lambda_client.get_waiter('function_updated')
    waiter.wait(FunctionName='aws-blog-crawler')
    print("   ✓ Lambda update complete")
except Exception as e:
    print(f"   ⚠️  Warning: {e}")

# Cleanup
os.remove(zip_file)
print("\n4. Cleaned up deployment package")

print("\n" + "=" * 80)
print("✅ Deployment Complete!")
print("=" * 80)
print("\nThe enhanced crawler now has:")
print("  - ECS/Fargate task invocation for Builder.AWS posts")
print("  - Deduplication fix (set instead of list)")
print("  - Environment detection (staging vs production)")
print("\nNext steps:")
print("  1. Publish new version: aws lambda publish-version --function-name aws-blog-crawler")
print("  2. Update production alias to new version")
