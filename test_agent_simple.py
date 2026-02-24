#!/usr/bin/env python3
"""
Simple Agent Test - Just one query to verify it's working
"""

import boto3
import json
import uuid

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

AGENT_ID = config['agent_id']
AGENT_ALIAS_ID = config['agent_alias_id']
REGION = config['region']

# Initialize Bedrock Agent Runtime client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)

query = "What is EUC?"
session_id = str(uuid.uuid4())

print(f"Testing agent with query: {query}\n")
print("="*80)

try:
    response = bedrock_agent_runtime.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        sessionId=session_id,
        inputText=query
    )
    
    # Collect response
    full_response = ""
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                text = chunk['bytes'].decode('utf-8')
                full_response += text
                print(text, end='', flush=True)
    
    print("\n" + "="*80)
    print(f"\nSuccess! Response length: {len(full_response)} characters")
    
except Exception as e:
    print(f"\nError: {str(e)}")
    import traceback
    traceback.print_exc()
