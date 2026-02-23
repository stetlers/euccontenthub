import boto3
import json

# API Gateway configuration
API_ID = 'xox05733ce'
REGION = 'us-east-1'

client = boto3.client('apigateway', region_name=REGION)

print("=" * 60)
print("API Gateway Configuration Check")
print("=" * 60)

# Get API details
api = client.get_rest_api(restApiId=API_ID)
print(f"\nAPI Name: {api['name']}")
print(f"API ID: {api['id']}")

# Get resources
resources = client.get_resources(restApiId=API_ID)

print("\n" + "=" * 60)
print("Current Resources and Methods")
print("=" * 60)

for resource in resources['items']:
    path = resource.get('path', '/')
    print(f"\nPath: {path}")
    print(f"Resource ID: {resource['id']}")
    
    if 'resourceMethods' in resource:
        methods = list(resource['resourceMethods'].keys())
        print(f"Methods: {', '.join(methods)}")
    else:
        print("Methods: None")

# Check for /cart resource
cart_resource = None
for resource in resources['items']:
    if resource.get('path') == '/cart':
        cart_resource = resource
        break

if cart_resource:
    print("\n✅ /cart resource exists")
else:
    print("\n❌ /cart resource does NOT exist - needs to be created")

# Check for /cart/{post_id} resource
cart_item_resource = None
for resource in resources['items']:
    if resource.get('path') == '/cart/{post_id}':
        cart_item_resource = resource
        break

if cart_item_resource:
    print("✅ /cart/{post_id} resource exists")
else:
    print("❌ /cart/{post_id} resource does NOT exist - needs to be created")

print("\n" + "=" * 60)
print("Required Cart Endpoints")
print("=" * 60)
print("\n1. GET /cart - Retrieve user's cart")
print("2. POST /cart - Add post to cart")
print("3. DELETE /cart - Clear all items")
print("4. DELETE /cart/{post_id} - Remove specific post")
