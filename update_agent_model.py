#!/usr/bin/env python3
"""
Update Agent Model to Use Inference Profile

Claude 3.5 Sonnet v2 requires an inference profile for on-demand usage.
This script updates the agent to use the correct model.
"""

import boto3
import json
import time

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

AGENT_ID = config['agent_id']
REGION = config['region']

# Initialize Bedrock Agent client
bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)

# Use Claude 3.5 Sonnet (v1) which doesn't require inference profile
# Or use Claude 3 Sonnet which is more widely available
NEW_MODEL = 'anthropic.claude-3-sonnet-20240229-v1:0'

print(f"Updating agent model...")
print(f"  Agent ID: {AGENT_ID}")
print(f"  New Model: {NEW_MODEL}")

try:
    # Get current agent
    agent_response = bedrock_agent.get_agent(agentId=AGENT_ID)
    agent = agent_response['agent']
    
    # Update agent with new model
    update_response = bedrock_agent.update_agent(
        agentId=AGENT_ID,
        agentName=agent['agentName'],
        agentResourceRoleArn=agent['agentResourceRoleArn'],
        foundationModel=NEW_MODEL,
        instruction=agent['instruction']
    )
    
    print(f"\n✓ Agent updated to use {NEW_MODEL}")
    
    # Prepare agent
    print("\nPreparing agent...")
    bedrock_agent.prepare_agent(agentId=AGENT_ID)
    
    # Wait for preparation
    max_wait = 120
    wait_interval = 10
    elapsed = 0
    
    while elapsed < max_wait:
        time.sleep(wait_interval)
        elapsed += wait_interval
        
        agent_response = bedrock_agent.get_agent(agentId=AGENT_ID)
        status = agent_response['agent']['agentStatus']
        print(f"  Status: {status} ({elapsed}s elapsed)")
        
        if status == 'PREPARED':
            print(f"\n✓ Agent is prepared and ready to use!")
            print(f"\nYou can now test the agent with: python test_bedrock_agent_staging.py")
            break
        elif status == 'FAILED':
            raise Exception("Agent preparation failed")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
