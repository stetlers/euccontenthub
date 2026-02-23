import boto3
import json

# Configuration
API_ID = 'xox05733ce'
REGION = 'us-east-1'

client = boto3.client('apigateway', region_name=REGION)

print("=" * 60)
print("Diagnosing Cart CORS Issue")
print("=" * 60)

# Get resources
resources = client.get_resources(restApiId=API_ID)

# Find /cart resource
cart_resource = None
for resource in resources['items']:
    if resource.get('path') == '/cart':
        cart_resource = resource
        break

if not cart_resource:
    print("❌ /cart resource not found")
    exit(1)

cart_resource_id = cart_resource['id']
print(f"\n✅ Found /cart resource: {cart_resource_id}")

# Check OPTIONS method
print("\n" + "=" * 60)
print("Checking OPTIONS Method Configuration")
print("=" * 60)

try:
    method = client.get_method(
        restApiId=API_ID,
        resourceId=cart_resource_id,
        httpMethod='OPTIONS'
    )
    print("\n✅ OPTIONS method exists")
    print(f"Authorization Type: {method.get('authorizationType')}")
    print(f"API Key Required: {method.get('apiKeyRequired')}")
    
    # Check integration
    try:
        integration = client.get_integration(
            restApiId=API_ID,
            resourceId=cart_resource_id,
            httpMethod='OPTIONS'
        )
        print(f"\n✅ Integration exists")
        print(f"Type: {integration.get('type')}")
        print(f"URI: {integration.get('uri', 'N/A')}")
        
        # Check integration response
        try:
            int_response = client.get_integration_response(
                restApiId=API_ID,
                resourceId=cart_resource_id,
                httpMethod='OPTIONS',
                statusCode='200'
            )
            print(f"\n✅ Integration Response exists")
            print(f"Response Parameters: {json.dumps(int_response.get('responseParameters', {}), indent=2)}")
        except Exception as e:
            print(f"\n❌ Integration Response error: {e}")
            
    except Exception as e:
        print(f"\n❌ Integration error: {e}")
        
    # Check method response
    try:
        method_response = client.get_method_response(
            restApiId=API_ID,
            resourceId=cart_resource_id,
            httpMethod='OPTIONS',
            statusCode='200'
        )
        print(f"\n✅ Method Response exists")
        print(f"Response Parameters: {json.dumps(method_response.get('responseParameters', {}), indent=2)}")
    except Exception as e:
        print(f"\n❌ Method Response error: {e}")
        
except Exception as e:
    print(f"\n❌ OPTIONS method error: {e}")

print("\n" + "=" * 60)
print("Checking Lambda Handler for CORS")
print("=" * 60)
print("\nThe Lambda function should handle OPTIONS requests and return CORS headers.")
print("Check lambda_api/lambda_function.py for OPTIONS handling.")
