#!/usr/bin/env python3
"""
Check ECS task definition for Selenium crawler
"""
import boto3
import json

ecs_client = boto3.client('ecs', region_name='us-east-1')

print("="*80)
print("ECS TASK DEFINITION CHECK")
print("="*80)

try:
    # Get the active task definition
    response = ecs_client.describe_task_definition(
        taskDefinition='selenium-crawler-task'
    )
    
    task_def = response['taskDefinition']
    
    print(f"\nTask Definition: {task_def['family']}:{task_def['revision']}")
    print(f"Status: {task_def['status']}")
    print(f"Task Role: {task_def.get('taskRoleArn', 'None')}")
    print(f"Execution Role: {task_def.get('executionRoleArn', 'None')}")
    
    # Check container definition
    container = task_def['containerDefinitions'][0]
    print(f"\nContainer: {container['name']}")
    print(f"Image: {container['image']}")
    print(f"CPU: {container.get('cpu', 'N/A')}")
    print(f"Memory: {container.get('memory', 'N/A')}")
    
    # Check environment variables
    print("\nEnvironment Variables:")
    env_vars = container.get('environment', [])
    if env_vars:
        for env in env_vars:
            print(f"  {env['name']} = {env['value']}")
    else:
        print("  (None defined in task definition)")
    
    # Check log configuration
    print("\nLog Configuration:")
    log_config = container.get('logConfiguration', {})
    if log_config:
        print(f"  Driver: {log_config.get('logDriver', 'N/A')}")
        options = log_config.get('options', {})
        for key, value in options.items():
            print(f"  {key}: {value}")
    else:
        print("  (No logging configured)")
    
    # Check IAM permissions
    print("\n" + "="*80)
    print("CHECKING IAM PERMISSIONS")
    print("="*80)
    
    iam_client = boto3.client('iam')
    
    # Extract role name from ARN
    task_role_arn = task_def.get('taskRoleArn', '')
    if task_role_arn:
        role_name = task_role_arn.split('/')[-1]
        print(f"\nTask Role: {role_name}")
        
        # Get attached policies
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        print("\nAttached Policies:")
        for policy in response['AttachedPolicies']:
            print(f"  - {policy['PolicyName']}")
        
        # Get inline policies
        response = iam_client.list_role_policies(RoleName=role_name)
        if response['PolicyNames']:
            print("\nInline Policies:")
            for policy_name in response['PolicyNames']:
                print(f"  - {policy_name}")
                
                # Get policy document
                policy_response = iam_client.get_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
                
                policy_doc = policy_response['PolicyDocument']
                print(f"\n    Permissions:")
                for statement in policy_doc.get('Statements', []):
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    for action in actions:
                        print(f"      - {action}")
    
    print("\n" + "="*80)
    print("KEY CHECKS")
    print("="*80)
    print("\n✓ Task definition exists")
    print(f"✓ Container image: {container['image']}")
    print(f"✓ Log group: {log_config.get('options', {}).get('awslogs-group', 'N/A')}")
    
    # Check for required permissions
    print("\nRequired permissions for task role:")
    print("  - dynamodb:GetItem (to read posts)")
    print("  - dynamodb:UpdateItem (to update posts)")
    print("  - lambda:InvokeFunction (to invoke summary generator)")
    
except Exception as e:
    print(f"\nERROR: {e}")
    print("\nPossible causes:")
    print("1. Task definition doesn't exist")
    print("2. AWS credentials expired")
    print("3. Insufficient permissions to describe task")
