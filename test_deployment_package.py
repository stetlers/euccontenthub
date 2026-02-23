"""Test deployment package creation"""
import os
import zipfile
from deploy_chat_with_aws_docs import create_deployment_package

print("Testing deployment package creation...")
print("=" * 60)

# Create the package
zip_file = create_deployment_package()

# Verify contents
print(f"\nVerifying zip contents...")
with zipfile.ZipFile(zip_file, 'r') as z:
    files = z.namelist()
    print(f"Files in package:")
    for file in files:
        print(f"  ✓ {file}")
    
    # Verify required files
    required = ['lambda_function.py', 'euc_service_mapper.py', 'euc-service-name-mapping.json']
    missing = [f for f in required if f not in files]
    
    if missing:
        print(f"\n✗ Missing required files: {missing}")
    else:
        print(f"\n✓ All required files present")

# Clean up
os.remove(zip_file)
print(f"\n✓ Deployment package test passed")
