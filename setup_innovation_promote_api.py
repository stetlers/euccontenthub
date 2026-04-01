"""
Add Innovation Promote API Gateway resource and method.

Creates:
  /innovations/{id}/promote — POST, OPTIONS (CORS)

Uses the same pattern as setup_innovation_api_gateway.py.
"""
import boto3

apigateway = boto3.client('apigateway', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

API_ID = 'xox05733ce'
REGION = 'us-east-1'
ACCOUNT_ID = '031421429609'
LAMBDA_ARN = 'arn:aws:lambda:us-east-1:031421429609:function:aws-blog-api'


def find_resource_by_path(target_path):
    response = apigateway.get_resources(restApiId=API_ID, limit=500)
    for item in response['items']:
        if item['path'] == target_path:
            return item['id']
    return None


def create_resource_if_not_exists(parent_id, path_part):
    response = apigateway.get_resources(restApiId=API_ID, limit=500)
    for item in response['items']:
        if item.get('pathPart') == path_part and item.get('parentId') == parent_id:
            print(f"  ℹ️  Resource '{path_part}' already exists (ID: {item['id']})")
            return item['id']
    response = apigateway.create_resource(
        restApiId=API_ID, parentId=parent_id, pathPart=path_part
    )
    print(f"  ✅ Created resource '{path_part}' (ID: {response['id']})")
    return response['id']


def add_method_with_lambda_integration(resource_id, http_method, resource_path):
    lambda_uri = (
        f'arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/'
        f'{LAMBDA_ARN}/invocations'
    )
    try:
        apigateway.put_method(
            restApiId=API_ID, resourceId=resource_id,
            httpMethod=http_method, authorizationType='NONE', apiKeyRequired=False
        )
        print(f"    ✅ Created {http_method} method")
    except Exception as e:
        print(f"    ℹ️  {http_method} method exists: {str(e)[:60]}")

    try:
        apigateway.put_integration(
            restApiId=API_ID, resourceId=resource_id,
            httpMethod=http_method, type='AWS_PROXY',
            integrationHttpMethod='POST', uri=lambda_uri
        )
        print(f"    ✅ Created Lambda integration for {http_method}")
    except Exception as e:
        print(f"    ℹ️  Integration exists: {str(e)[:60]}")

    # Add Lambda invoke permissions
    for stage in ['staging', 'prod']:
        for qualifier in [f'aws-blog-api', f'aws-blog-api:production']:
            statement_id = (
                f'innov-promote-{http_method}-{stage}'
                f'{"-prodalias" if ":production" in qualifier else ""}'
            )
            source_arn = (
                f'arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{API_ID}'
                f'/{stage}/{http_method}{resource_path}'
            )
            try:
                lambda_client.add_permission(
                    FunctionName=qualifier,
                    StatementId=statement_id,
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=source_arn
                )
                print(f"    ✅ Added Lambda permission ({stage}, {qualifier})")
            except lambda_client.exceptions.ResourceConflictException:
                print(f"    ℹ️  Permission already exists ({stage}, {qualifier})")
            except Exception as e:
                print(f"    ⚠️  Permission error ({stage}, {qualifier}): {str(e)[:60]}")


def add_cors_options(resource_id, resource_path, allowed_methods):
    try:
        apigateway.put_method(
            restApiId=API_ID, resourceId=resource_id,
            httpMethod='OPTIONS', authorizationType='NONE', apiKeyRequired=False
        )
        apigateway.put_integration(
            restApiId=API_ID, resourceId=resource_id,
            httpMethod='OPTIONS', type='MOCK',
            requestTemplates={'application/json': '{"statusCode": 200}'}
        )
        apigateway.put_method_response(
            restApiId=API_ID, resourceId=resource_id,
            httpMethod='OPTIONS', statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True
            }
        )
        methods_str = ','.join(allowed_methods + ['OPTIONS'])
        apigateway.put_integration_response(
            restApiId=API_ID, resourceId=resource_id,
            httpMethod='OPTIONS', statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': f"'{methods_str}'",
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            }
        )
        print(f"    ✅ Added CORS OPTIONS for {resource_path}")
    except Exception as e:
        print(f"    ℹ️  CORS OPTIONS exists for {resource_path}: {str(e)[:60]}")


print("\n🔧 Adding Innovation Promote API Gateway endpoint...")
print("=" * 60)

# Find the existing /innovations/{id} resource
innovation_id_resource = find_resource_by_path('/innovations/{id}')
if not innovation_id_resource:
    print("❌ /innovations/{id} resource not found! Run setup_innovation_api_gateway.py first.")
    exit(1)

# Create /innovations/{id}/promote
print("\n1. /innovations/{id}/promote")
promote_id = create_resource_if_not_exists(innovation_id_resource, 'promote')
add_method_with_lambda_integration(promote_id, 'POST', '/innovations/{id}/promote')
add_cors_options(promote_id, '/innovations/{id}/promote', ['POST'])

# Deploy
print("\n2. Deploying API...")
for stage in ['staging', 'prod']:
    try:
        resp = apigateway.create_deployment(
            restApiId=API_ID, stageName=stage,
            description=f'Added Innovation Promote endpoint ({stage})'
        )
        print(f"  ✅ Deployed to {stage} (ID: {resp['id']})")
    except Exception as e:
        print(f"  ⚠️  Deploy to {stage} failed: {str(e)[:80]}")

print("\n" + "=" * 60)
print("✅ Innovation Promote endpoint setup complete!")
print("  POST /innovations/{id}/promote")
print("  OPTIONS /innovations/{id}/promote (CORS)")
