"""
Deploy enhanced crawler Lambda with dependencies
"""
import zipfile
import boto3
import os
import subprocess
import shutil

print("=" * 80)
print("Deploying Enhanced Crawler with Dependencies")
print("=" * 80)

# Create temp directory for dependencies
temp_dir = 'lambda_package'
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
os.makedirs(temp_dir)

print("\n1. Installing dependencies...")
subprocess.run([
    'pip', 'install',
    'requests',
    'beautifulsoup4',
    '-t', temp_dir
], check=True)

print("\n2. Creating deployment package...")
zip_file = 'enhanced_crawler_with_deps.zip'

with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    # Add dependencies
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, temp_dir)
            zf.write(file_path, arcname)
    
    # Add Lambda function
    zf.write('enhanced_crawler_lambda.py', 'lambda_function.py')

print(f"   ✓ Created {zip_file}")

# Get file size
zip_size = os.path.getsize(zip_file) / (1024 * 1024)
print(f"   📦 Package size: {zip_size:.2f} MB")

# Upload to Lambda
print("\n3. Uploading to Lambda...")
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
    shutil.rmtree(temp_dir)
    os.remove(zip_file)
    exit(1)

# Wait for update
print("\n4. Waiting for Lambda update...")
try:
    waiter = lambda_client.get_waiter('function_updated')
    waiter.wait(FunctionName='aws-blog-crawler')
    print("   ✓ Lambda update complete")
except Exception as e:
    print(f"   ⚠️  Warning: {e}")

# Cleanup
shutil.rmtree(temp_dir)
os.remove(zip_file)
print("\n5. Cleaned up temporary files")

print("\n" + "=" * 80)
print("✅ Deployment Complete!")
print("=" * 80)
print("\nNext steps:")
print("  1. Publish new version")
print("  2. Update production alias to new version")
