"""
Add missing KB editor endpoints to API Gateway
"""
import boto3

apigateway = boto3.client('apigateway', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

API_ID = 'xox05733ce'
REGION = 'us-east-1'
LAMBDA_ARN = 'arn:aws:lambda:us-east-1:031421429609:function:aws-blog-api'
ACCOUNT_ID = '031421429609'

def get_root_resource_id():
    """Get the root resource ID"""
    response = apigateway.get_resources(restApiId=API_ID)
    for item in response['items']:
        if item['path'] == '/':
            return item['id']
    raise Exception("Root resource not found")

def create_resource_if_not_exists(parent_id, path_part):
    """Create a resource if it doesn't exist"""
    response = apigateway.get_resources(restApiId=API_ID)
    for item in response['items']:
        if item.get('pathPart') == path_part and item.get('parentId') == parent_id:
            print(f"  ℹ️  Resource /{path_part} already exists (ID: {item['id']})")
            return item['id']
    
    response = apigateway.create_resource(
        restApiId=API_ID,
        parentId=parent_id,
        pathPart=path_part
    )
    print(f"  ✅ Created resource /{path_part} (ID: {response['id']})")
    return response['id']

def configure_endpoint(resource_id, http_method, resource_path):
    """Configure a complete endpoint with method, integration, and permissions"""
    lambda_uri = f'arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{LAMBDA_ARN}:${{stageVariables.lambdaAlias}}/invocations'
    
    # Create method
    try:
        apigateway.put_method(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod=http_method,
            authorizationType='NONE',
            apiKeyRequired=False
        )
        print(f"    ✅ Created {http_method} method")
    except Exception as e:
        print(f"    ℹ️  Method exists: {str(e)[:50]}")
    
    # Create integration
    try:
        apigateway.put_integration(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod=http_method,
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=lambda_uri
        )
        print(f"    ✅ Created Lambda integration")
    except Exception as e:
        print(f"    ℹ️  Integration exists: {str(e)[:50]}")
    
    # Add Lambda permission for qualified ARN
    statement_id = f'apigateway-{resource_path.replace("/", "-")}-{http_method}-staging-qualified'
    source_arn = f'arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{API_ID}/staging/{http_method}{resource_path}'
    
    try:
        lambda_client.add_permission(
            FunctionName='aws-blog-api:staging',
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=source_arn
        )
        print(f"    ✅ Added Lambda permission")
    except lambda_client.exceptions.ResourceConflictException:
        print(f"    ℹ️  Permission already exists")
    except Exception as e:
        print(f"    ⚠️  Permission error: {str(e)[:50]}")
    
    # Add OPTIONS for CORS
    try:
        apigateway.put_method(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE',
            apiKeyRequired=False
        )
        
        apigateway.put_integration(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates={'application/json': '{"statusCode": 200}'}
        )
        
        apigateway.put_method_response(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True
            }
        )
        
        apigateway.put_integration_response(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            }
        )
        print(f"    ✅ Added CORS support")
    except Exception as e:
        print(f"    ℹ️  CORS exists: {str(e)[:50]}")

print("\n🔧 Adding missing KB editor endpoints...")
print("=" * 70)

root_id = get_root_resource_id()

# 1. /kb-contributors
print("\n1. Creating /kb-contributors endpoint...")
kb_contributors_id = create_resource_if_not_exists(root_id, 'kb-contributors')
configure_endpoint(kb_contributors_id, 'GET', '/kb-contributors')

# 2. /kb-my-contributions
print("\n2. Creating /kb-my-contributions endpoint...")
kb_my_contributions_id = create_resource_if_not_exists(root_id, 'kb-my-contributions')
configure_endpoint(kb_my_contributions_id, 'GET', '/kb-my-contributions')

# Deploy API
print("\n3. Deploying API to staging...")
response = apigateway.create_deployment(
    restApiId=API_ID,
    stageName='staging',
    description='Added kb-contributors and kb-my-contributions endpoints'
)
print(f"  ✅ Deployed (ID: {response['id']})")

print("\n" + "=" * 70)
print("✅ Missing endpoints added successfully!")
print("=" * 70)
