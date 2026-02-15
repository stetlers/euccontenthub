"""
Verify ECS Infrastructure is Ready for Production Deployment

Checks:
1. ECS cluster exists
2. ECS task definition exists
3. Task role has correct permissions
4. Enhanced crawler Lambda has correct configuration
"""

import json
import boto3

ecs = boto3.client('ecs', region_name='us-east-1')
iam = boto3.client('iam')
lambda_client = boto3.client('lambda', region_name='us-east-1')

print("=" * 80)
print("ECS PRODUCTION READINESS CHECK")
print("=" * 80)

all_checks_passed = True

# Check 1: ECS Cluster
print("\n1. Checking ECS cluster...")
try:
    response = ecs.describe_clusters(clusters=['selenium-crawler-cluster'])
    if response['clusters'] and response['clusters'][0]['status'] == 'ACTIVE':
        print("   ✅ Cluster 'selenium-crawler-cluster' exists and is ACTIVE")
    else:
        print("   ❌ Cluster 'selenium-crawler-cluster' not found or not active")
        all_checks_passed = False
except Exception as e:
    print(f"   ❌ Error checking cluster: {e}")
    all_checks_passed = False

# Check 2: ECS Task Definition
print("\n2. Checking ECS task definition...")
try:
    response = ecs.describe_task_definition(taskDefinition='selenium-crawler-task')
    task_def = response['taskDefinition']
    print(f"   ✅ Task definition 'selenium-crawler-task' exists (revision {task_def['revision']})")
    print(f"      - CPU: {task_def['cpu']}")
    print(f"      - Memory: {task_def['memory']}")
    print(f"      - Task role: {task_def.get('taskRoleArn', 'NOT SET')}")
    
    # Check container definition
    if task_def['containerDefinitions']:
        container = task_def['containerDefinitions'][0]
        print(f"      - Container: {container['name']}")
        print(f"      - Image: {container['image']}")
except Exception as e:
    print(f"   ❌ Error checking task definition: {e}")
    all_checks_passed = False

# Check 3: Task Role Permissions
print("\n3. Checking task role permissions...")
try:
    response = iam.get_role_policy(
        RoleName='builder-crawler-task-role',
        PolicyName='BuilderCrawlerTaskPolicy'
    )
    
    policy = json.loads(response['PolicyDocument'])
    
    # Check DynamoDB permissions
    dynamodb_resources = []
    lambda_resources = []
    
    for statement in policy['Statement']:
        if 'dynamodb' in str(statement.get('Action', [])):
            dynamodb_resources.extend(statement.get('Resource', []))
        if 'lambda' in str(statement.get('Action', [])):
            lambda_resources.extend(statement.get('Resource', []))
    
    # Verify production table access
    prod_table = 'arn:aws:dynamodb:us-east-1:031421429609:table/aws-blog-posts'
    staging_table = 'arn:aws:dynamodb:us-east-1:031421429609:table/aws-blog-posts-staging'
    
    if prod_table in dynamodb_resources:
        print("   ✅ Has access to production DynamoDB table")
    else:
        print("   ❌ Missing access to production DynamoDB table")
        all_checks_passed = False
    
    if staging_table in dynamodb_resources:
        print("   ✅ Has access to staging DynamoDB table")
    else:
        print("   ⚠️  Missing access to staging DynamoDB table (optional)")
    
    # Verify Lambda invocation permissions
    prod_lambda = 'arn:aws:lambda:us-east-1:031421429609:function:aws-blog-summary-generator:production'
    staging_lambda = 'arn:aws:lambda:us-east-1:031421429609:function:aws-blog-summary-generator:staging'
    
    if prod_lambda in lambda_resources:
        print("   ✅ Can invoke production summary generator Lambda")
    else:
        print("   ❌ Missing permission to invoke production summary generator Lambda")
        all_checks_passed = False
    
    if staging_lambda in lambda_resources:
        print("   ✅ Can invoke staging summary generator Lambda")
    else:
        print("   ⚠️  Missing permission to invoke staging summary generator Lambda (optional)")
    
except iam.exceptions.NoSuchEntityException:
    print("   ❌ Task role policy 'BuilderCrawlerTaskPolicy' not found")
    print("   Run: python update_ecs_task_role_policy.py")
    all_checks_passed = False
except Exception as e:
    print(f"   ❌ Error checking task role: {e}")
    all_checks_passed = False

# Check 4: Enhanced Crawler Lambda Configuration
print("\n4. Checking enhanced crawler Lambda configuration...")
try:
    response = lambda_client.get_function_configuration(
        FunctionName='aws-blog-enhanced-crawler',
        Qualifier='production'
    )
    
    env_vars = response.get('Environment', {}).get('Variables', {})
    
    print(f"   ✅ Lambda 'aws-blog-enhanced-crawler:production' exists")
    print(f"      - Runtime: {response['Runtime']}")
    print(f"      - Timeout: {response['Timeout']}s")
    
    # Check environment variables
    environment = env_vars.get('ENVIRONMENT', 'NOT SET')
    if environment == 'production':
        print(f"      - ENVIRONMENT: {environment} ✅")
    else:
        print(f"      - ENVIRONMENT: {environment} ⚠️  (should be 'production')")
    
except lambda_client.exceptions.ResourceNotFoundException:
    print("   ❌ Lambda 'aws-blog-enhanced-crawler:production' not found")
    all_checks_passed = False
except Exception as e:
    print(f"   ❌ Error checking Lambda: {e}")
    all_checks_passed = False

# Summary
print("\n" + "=" * 80)
if all_checks_passed:
    print("✅ ALL CHECKS PASSED - ECS infrastructure is ready for production")
else:
    print("❌ SOME CHECKS FAILED - Review errors above before deploying to production")
    print("\nRecommended actions:")
    print("  1. Run: python update_ecs_task_role_policy.py")
    print("  2. Verify Lambda environment variables are set correctly")
    print("  3. Re-run this script to confirm all checks pass")
print("=" * 80)
