import boto3
import time

# Configuration
API_ID = 'xox05733ce'
REGION = 'us-east-1'
LAMBDA_FUNCTION_NAME = 'aws-blog-api'
LAMBDA_ARN = f'arn:aws:lambda:{REGION}:031421429609:function:{LAMBDA_FUNCTION_NAME}'

client = boto3.client('apigateway', region_name=REGION)

print("=" * 60)
print("Fixing Cart CORS Issue")
print("=" * 60)
print("\nProblem: OPTIONS method configured as MOCK integration")
print("Solution: Change to Lambda proxy integration")

# Get resources
resources = client.get_resources(restApiId=API_ID)

# Find /cart and /cart/{post_id} resources
cart_resources = []
for resource in resources['items']:
    if resource.get('path') in ['/cart', '/cart/{post_id}']:
        cart_resources.append(resource)

if not cart_resources:
    print("\n❌ Cart resources not found")
    exit(1)

print(f"\n✅ Found {len(cart_resources)} cart resources")

for resource in cart_resources:
    path = resource.get('path')
    resource_id = resource['id']
    
    print(f"\n" + "=" * 60)
    print(f"Fixing: {path}")
    print("=" * 60)
    
    try:
        # Delete existing OPTIONS integration
        print(f"\n1. Deleting MOCK integration...")
        try:
            client.delete_integration(
                restApiId=API_ID,
                resourceId=resource_id,
                httpMethod='OPTIONS'
            )
            print("   ✅ Deleted MOCK integration")
        except Exception as e:
            print(f"   ⚠️  {e}")
        
        # Delete existing OPTIONS method
        print(f"\n2. Deleting OPTIONS method...")
        try:
            client.delete_method(
                restApiId=API_ID,
                resourceId=resource_id,
                httpMethod='OPTIONS'
            )
            print("   ✅ Deleted OPTIONS method")
        except Exception as e:
            print(f"   ⚠️  {e}")
        
        # Recreate OPTIONS method
        print(f"\n3. Creating OPTIONS method...")
        client.put_method(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE',
            apiKeyRequired=False
        )
        print("   ✅ Created OPTIONS method")
        
        # Create Lambda proxy integration
        print(f"\n4. Creating Lambda proxy integration...")
        client.put_integration(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=f'arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{LAMBDA_ARN}/invocations'
        )
        print("   ✅ Created Lambda proxy integration")
        print("   ℹ️  Lambda will handle CORS headers")
        
    except Exception as e:
        print(f"\n❌ Error fixing {path}: {e}")

# Deploy to stages
print("\n" + "=" * 60)
print("Deploying Changes")
print("=" * 60)

for stage in ['prod', 'staging']:
    try:
        deployment = client.create_deployment(
            restApiId=API_ID,
            stageName=stage,
            description=f'Fix cart CORS - use Lambda proxy for OPTIONS'
        )
        print(f"\n✅ Deployed to {stage} stage: {deployment['id']}")
    except Exception as e:
        print(f"\n❌ Failed to deploy to {stage}: {e}")

print("\n" + "=" * 60)
print("✅ CORS Fix Complete!")
print("=" * 60)
print("\nChanges:")
print("  - OPTIONS methods now use Lambda proxy integration")
print("  - Lambda handles CORS headers directly")
print("  - No more MOCK integration issues")
print("\nTest the cart functionality now - CORS errors should be resolved.")
