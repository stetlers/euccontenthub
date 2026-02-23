"""
Rollback summary generator to working version (without auto-chaining)
"""
import zipfile
import boto3
import os

print("=" * 80)
print("Rolling Back Summary Generator to Working Version")
print("=" * 80)

# Create zip file from the working version in summary_code/
zip_file = 'summary_rollback.zip'

print("\n1. Creating deployment package from summary_code/...")
with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    # Read the original working version
    with open('summary_code/summary_lambda.py', 'r') as f:
        original_code = f.read()
    
    # Remove the auto-chaining code we added
    # Find the section we added and remove it
    if 'AUTO-CHAINING' in original_code:
        print("   Removing auto-chaining code...")
        # Split at the auto-chaining section
        parts = original_code.split('# AUTO-CHAINING')
        if len(parts) == 2:
            # Keep everything before auto-chaining, and the return statement after
            before = parts[0]
            after = parts[1]
            # Find the return statement
            return_idx = after.find('return {')
            if return_idx != -1:
                original_code = before + after[return_idx:]
    
    # Write to zip as lambda_function.py
    zf.writestr('lambda_function.py', original_code)

print(f"   ✓ Created {zip_file}")

# Get file size
zip_size = os.path.getsize(zip_file) / 1024
print(f"   📦 Package size: {zip_size:.2f} KB")

# Upload to Lambda
print("\n2. Uploading to Lambda...")
try:
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    with open(zip_file, 'rb') as f:
        zip_content = f.read()
    
    response = lambda_client.update_function_code(
        FunctionName='aws-blog-summary-generator',
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
    waiter.wait(FunctionName='aws-blog-summary-generator')
    print("   ✓ Lambda update complete")
except Exception as e:
    print(f"   ⚠️  Warning: {e}")

# Cleanup
os.remove(zip_file)
print("\n4. Cleaned up deployment package")

print("\n" + "=" * 80)
print("✅ Rollback Complete!")
print("=" * 80)
print("\nSummary generator restored to working version.")
print("You can now trigger it manually: python trigger_remaining_summaries.py")
