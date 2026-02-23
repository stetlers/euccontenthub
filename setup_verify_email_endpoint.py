import boto3
import json

# Initialize API Gateway client
apigateway = boto3.client('apigateway', region_name='us-east-1')

REST_API_ID = 'xox05733ce'
PARENT_RESOURCE_ID = 'w6n4sfgwa4'  # Root resource
LAMBDA_ARN = 'arn:aws:lambda:us-east-1:031421429609:function:aws-blog-api'

print("=== Creating /verify-email endpoint in API Gateway ===\n")

# Step 1: Create the /verify-email resource
print("1. Creating /verify-email resource...")
try:
    resource_response = apigateway.create_resource(
        restApiId=REST_API_ID,
        parentId=PARENT_RESOURCE_ID,
        pathPart='verify-email'
    )
    resource_id = resource_response['id']
    print(f"   ✅ Created resource: {resource_id}\n")
except apigateway.exceptions.ConflictException:
    # Resource already exists, get its ID
    print("   ℹ️  Resource already exists, fetching ID...")
    resources = apigateway.get_resources(restApiId=REST_API_ID)
    resource_id = None
    for resource in resources['items']:
        if resource.get('pathPart') == 'verify-email':
            resource_id = resource['id']
            break
    print(f"   ✅ Found existing resource: {resource_id}\n")

# Step 2: Create POST method
print("2. Creating POST method...")
try:
    apigateway.put_method(
        restApiId=REST_API_ID,
        resourceId=resource_id,
        httpMethod='POST',
        authorizationType='NONE'
    )
    print("   ✅ POST method created\n")
except Exception as e:
    print(f"   ℹ️  POST method may already exist: {e}\n")

# Step 3: Create POST integration
print("3. Creating POST integration with Lambda...")
try:
    apigateway.put_integration(
        restApiId=REST_API_ID,
        resourceId=resource_id,
        httpMethod='POST',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=f'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{LAMBDA_ARN}/invocations'
    )
    print("   ✅ POST integration created\n")
except Exception as e:
    print(f"   ℹ️  POST integration may already exist: {e}\n")

# Step 4: Create GET method
print("4. Creating GET method...")
try:
    apigateway.put_method(
        restApiId=REST_API_ID,
        resourceId=resource_id,
        httpMethod='GET',
        authorizationType='NONE'
    )
    print("   ✅ GET method created\n")
except Exception as e:
    print(f"   ℹ️  GET method may already exist: {e}\n")

# Step 5: Create GET integration
print("5. Creating GET integration with Lambda...")
try:
    apigateway.put_integration(
        restApiId=REST_API_ID,
        resourceId=resource_id,
        httpMethod='GET',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=f'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{LAMBDA_ARN}/invocations'
    )
    print("   ✅ GET integration created\n")
except Exception as e:
    print(f"   ℹ️  GET integration may already exist: {e}\n")

# Step 6: Create OPTIONS method for CORS
print("6. Creating OPTIONS method for CORS...")
try:
    apigateway.put_method(
        restApiId=REST_API_ID,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        authorizationType='NONE'
    )
    print("   ✅ OPTIONS method created\n")
except Exception as e:
    print(f"   ℹ️  OPTIONS method may already exist: {e}\n")

# Step 7: Create OPTIONS integration (MOCK)
print("7. Creating OPTIONS integration (MOCK)...")
try:
    apigateway.put_integration(
        restApiId=REST_API_ID,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        type='MOCK',
        requestTemplates={
            'application/json': '{"statusCode": 200}'
        }
    )
    print("   ✅ OPTIONS integration created\n")
except Exception as e:
    print(f"   ℹ️  OPTIONS integration may already exist: {e}\n")

# Step 8: Create OPTIONS method response
print("8. Creating OPTIONS method response...")
try:
    apigateway.put_method_response(
        restApiId=REST_API_ID,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Headers': False,
            'method.response.header.Access-Control-Allow-Methods': False,
            'method.response.header.Access-Control-Allow-Origin': False
        }
    )
    print("   ✅ OPTIONS method response created\n")
except Exception as e:
    print(f"   ℹ️  OPTIONS method response may already exist: {e}\n")

# Step 9: Create OPTIONS integration response
print("9. Creating OPTIONS integration response...")
try:
    apigateway.put_integration_response(
        restApiId=REST_API_ID,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
            'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
            'method.response.header.Access-Control-Allow-Origin': "'*'"
        }
    )
    print("   ✅ OPTIONS integration response created\n")
except Exception as e:
    print(f"   ℹ️  OPTIONS integration response may already exist: {e}\n")

# Step 10: Deploy to staging and prod
print("10. Deploying API to staging and prod...")
try:
    apigateway.create_deployment(
        restApiId=REST_API_ID,
        stageName='staging',
        description='Added /verify-email endpoint'
    )
    print("   ✅ Deployed to staging\n")
except Exception as e:
    print(f"   ❌ Error deploying to staging: {e}\n")

try:
    apigateway.create_deployment(
        restApiId=REST_API_ID,
        stageName='prod',
        description='Added /verify-email endpoint'
    )
    print("   ✅ Deployed to prod\n")
except Exception as e:
    print(f"   ❌ Error deploying to prod: {e}\n")

print("=" * 70)
print("✅ API Gateway configuration complete!")
print("=" * 70)
print("\nEndpoints:")
print(f"  Staging: https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging/verify-email")
print(f"  Production: https://xox05733ce.execute-api.us-east-1.amazonaws.com/prod/verify-email")
