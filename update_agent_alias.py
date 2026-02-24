#!/usr/bin/env python3
"""
Update Agent Alias to Point to Latest Version

After updating the agent model, we need to update the alias
to point to the new prepared version.
"""

import boto3
import json

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

AGENT_ID = config['agent_id']
AGENT_ALIAS_ID = config['agent_alias_id']
REGION = config['region']

# Initialize Bedrock Agent client
bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)

print(f"Updating agent alias...")
print(f"  Agent ID: {AGENT_ID}")
print(f"  Alias ID: {AGENT_ALIAS_ID}")

try:
    # Update alias to point to DRAFT (latest prepared version)
    response = bedrock_agent.update_agent_alias(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        agentAliasName='staging-alias',
        description='Stable alias for staging environment - updated to use Claude 3 Sonnet'
    )
    
    print(f"\nAlias updated successfully!")
    print(f"  Alias Status: {response['agentAlias']['agentAliasStatus']}")
    
    print(f"\nYou can now test the agent with: python test_bedrock_agent_staging.py")
    
except Exception as e:
    print(f"\nError: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
