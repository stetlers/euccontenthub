"""
Deploy updated classifier Lambda to staging
"""
import boto3
import zipfile
import os

lambda_client = boto3.client('lambda', region_name='us-east-1')

print("=" * 80)
print("Deploying Classifier to Staging")
print("=" * 80)

# Create deployment package
zip_filename = 'classifier_staging_deploy.zip'
print(f"\nCreating deployment package: {zip_filename}")

with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add Lambda function
    zipf.write('classifier_code/classifier_lambda.py', 'classifier_lambda.py')
    print("  ✓ Added classifier_lambda.py")

print(f"\n✓ Package created: {os.path.getsize(zip_filename)} bytes")

# Upload to Lambda
print("\nUploading to Lambda...")
with open(zip_filename, 'rb') as f:
    lambda_client.update_function_code(
        FunctionName='aws-blog-classifier',
        ZipFile=f.read()
    )

print("✓ Code uploaded successfully")

print("\n" + "=" * 80)
print("Deployment Complete!")
print("=" * 80)
print("\nClassifier now has environment detection and proper table selection")
print("Staging alias points to $LATEST, so changes are live immediately")
