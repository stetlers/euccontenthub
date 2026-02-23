import boto3
import json
import time

# Configuration
API_ID = 'xox05733ce'
REGION = 'us-east-1'
LAMBDA_FUNCTION_NAME = 'aws-blog-api'
LAMBDA_ARN = f'arn:aws:lambda:{REGION}:031421429609:function:{LAMBDA_FUNCTION_NAME}'

client = boto3.client('apigateway', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)

print("=" * 60)
print("Configuring API Gateway for Cart Endpoints")
print("=" * 60)

# Get root resource
resources = client.get_resources(restApiId=API_ID)
root_resource = None
for resource in resources['items']:
    if resource.get('path') == '/':
        root_resource = resource
        break

if not root_resource:
    print("❌ Root resource not found")
    exit(1)

root_id = root_resource['id']
print(f"\n✅ Found root resource: {root_id}")

# Step 1: Create /cart resource
print("\n" + "=" * 60)
print("Step 1: Creating /cart resource")
print("=" * 60)

try:
    cart_resource = client.create_resource(
        restApiId=API_ID,
        parentId=root_id,
        pathPart='cart'
    )
    cart_resource_id = cart_resource['id']
    print(f"✅ Created /cart resource: {cart_resource_id}")
except client.exceptions.ConflictException:
    # Resource already exists, get it
    for resource in resources['items']:
        if resource.get('path') == '/cart':
            cart_resource_id = resource['id']
            print(f"✅ /cart resource already exists: {cart_resource_id}")
            break

# Step 2: Create /cart/{post_id} resource
print("\n" + "=" * 60)
print("Step 2: Creating /cart/{post_id} resource")
print("=" * 60)

try:
    cart_item_resource = client.create_resource(
        restApiId=API_ID,
        parentId=cart_resource_id,
        pathPart='{post_id}'
    )
    cart_item_resource_id = cart_item_resource['id']
    print(f"✅ Created /cart/{{post_id}} resource: {cart_item_resource_id}")
except client.exceptions.ConflictException:
    # Resource already exists, get it
    resources = client.get_resources(restApiId=API_ID)
    for resource in resources['items']:
        if resource.get('path') == '/cart/{post_id}':
            cart_item_resource_id = resource['id']
            print(f"✅ /cart/{{post_id}} resource already exists: {cart_item_resource_id}")
            break

# Step 3: Add methods to /cart
print("\n" + "=" * 60)
print("Step 3: Adding methods to /cart")
print("=" * 60)

methods_cart = ['GET', 'POST', 'DELETE', 'OPTIONS']

for method in methods_cart:
    try:
        # Create method
        client.put_method(
            restApiId=API_ID,
            resourceId=cart_resource_id,
            httpMethod=method,
            authorizationType='NONE' if method == 'OPTIONS' else 'NONE',
            apiKeyRequired=False
        )
        print(f"✅ Created {method} method on /cart")
        
        if method != 'OPTIONS':
            # Set up Lambda integration
            client.put_integration(
                restApiId=API_ID,
                resourceId=cart_resource_id,
                httpMethod=method,
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=f'arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{LAMBDA_ARN}/invocations'
            )
            print(f"  ✅ Configured Lambda integration for {method}")
        else:
            # OPTIONS method for CORS - create method response first
            client.put_method_response(
                restApiId=API_ID,
                resourceId=cart_resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': True,
                    'method.response.header.Access-Control-Allow-Methods': True,
                    'method.response.header.Access-Control-Allow-Origin': True
                }
            )
            
            client.put_integration(
                restApiId=API_ID,
                resourceId=cart_resource_id,
                httpMethod='OPTIONS',
                type='MOCK',
                requestTemplates={
                    'application/json': '{"statusCode": 200}'
                }
            )
            
            client.put_integration_response(
                restApiId=API_ID,
                resourceId=cart_resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Methods': "'GET,POST,DELETE,OPTIONS'",
                    'method.response.header.Access-Control-Allow-Origin': "'*'"
                }
            )
            print(f"  ✅ Configured CORS for OPTIONS")
            
    except client.exceptions.ConflictException:
        print(f"⚠️  {method} method already exists on /cart")

# Step 4: Add methods to /cart/{post_id}
print("\n" + "=" * 60)
print("Step 4: Adding methods to /cart/{post_id}")
print("=" * 60)

methods_cart_item = ['DELETE', 'OPTIONS']

for method in methods_cart_item:
    try:
        # Create method
        client.put_method(
            restApiId=API_ID,
            resourceId=cart_item_resource_id,
            httpMethod=method,
            authorizationType='NONE' if method == 'OPTIONS' else 'NONE',
            apiKeyRequired=False,
            requestParameters={
                'method.request.path.post_id': True
            } if method != 'OPTIONS' else {}
        )
        print(f"✅ Created {method} method on /cart/{{post_id}}")
        
        if method != 'OPTIONS':
            # Set up Lambda integration
            client.put_integration(
                restApiId=API_ID,
                resourceId=cart_item_resource_id,
                httpMethod=method,
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=f'arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{LAMBDA_ARN}/invocations'
            )
            print(f"  ✅ Configured Lambda integration for {method}")
        else:
            # OPTIONS method for CORS - create method response first
            client.put_method_response(
                restApiId=API_ID,
                resourceId=cart_item_resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': True,
                    'method.response.header.Access-Control-Allow-Methods': True,
                    'method.response.header.Access-Control-Allow-Origin': True
                }
            )
            
            client.put_integration(
                restApiId=API_ID,
                resourceId=cart_item_resource_id,
                httpMethod='OPTIONS',
                type='MOCK',
                requestTemplates={
                    'application/json': '{"statusCode": 200}'
                }
            )
            
            client.put_integration_response(
                restApiId=API_ID,
                resourceId=cart_item_resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Methods': "'DELETE,OPTIONS'",
                    'method.response.header.Access-Control-Allow-Origin': "'*'"
                }
            )
            print(f"  ✅ Configured CORS for OPTIONS")
            
    except client.exceptions.ConflictException:
        print(f"⚠️  {method} method already exists on /cart/{{post_id}}")

# Step 5: Grant API Gateway permission to invoke Lambda
print("\n" + "=" * 60)
print("Step 5: Granting API Gateway permissions")
print("=" * 60)

# For each stage (prod and staging)
for stage in ['prod', 'staging']:
    source_arn = f'arn:aws:execute-api:{REGION}:031421429609:{API_ID}/{stage}/*/cart'
    source_arn_item = f'arn:aws:execute-api:{REGION}:031421429609:{API_ID}/{stage}/*/cart/*'
    
    for arn in [source_arn, source_arn_item]:
        try:
            lambda_client.add_permission(
                FunctionName=LAMBDA_FUNCTION_NAME,
                StatementId=f'apigateway-cart-{stage}-{int(time.time())}',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=arn
            )
            print(f"✅ Granted permission for {stage} stage: {arn}")
        except lambda_client.exceptions.ResourceConflictException:
            print(f"⚠️  Permission already exists for {stage} stage")

# Step 6: Deploy to stages
print("\n" + "=" * 60)
print("Step 6: Deploying to stages")
print("=" * 60)

for stage in ['prod', 'staging']:
    try:
        deployment = client.create_deployment(
            restApiId=API_ID,
            stageName=stage,
            description=f'Deploy cart endpoints to {stage}'
        )
        print(f"✅ Deployed to {stage} stage: {deployment['id']}")
    except Exception as e:
        print(f"❌ Failed to deploy to {stage}: {e}")

print("\n" + "=" * 60)
print("✅ API Gateway Configuration Complete!")
print("=" * 60)
print("\nCart endpoints are now available:")
print(f"  GET    https://{API_ID}.execute-api.{REGION}.amazonaws.com/prod/cart")
print(f"  POST   https://{API_ID}.execute-api.{REGION}.amazonaws.com/prod/cart")
print(f"  DELETE https://{API_ID}.execute-api.{REGION}.amazonaws.com/prod/cart")
print(f"  DELETE https://{API_ID}.execute-api.{REGION}.amazonaws.com/prod/cart/{{post_id}}")
print("\nStaging:")
print(f"  GET    https://{API_ID}.execute-api.{REGION}.amazonaws.com/staging/cart")
print(f"  POST   https://{API_ID}.execute-api.{REGION}.amazonaws.com/staging/cart")
print(f"  DELETE https://{API_ID}.execute-api.{REGION}.amazonaws.com/staging/cart")
print(f"  DELETE https://{API_ID}.execute-api.{REGION}.amazonaws.com/staging/cart/{{post_id}}")
