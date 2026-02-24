#!/usr/bin/env python3
"""
Restart Ingestion Job

Starts a new ingestion job for the knowledge base data source.
"""

import boto3
import json

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

KB_ID = config['knowledge_base_id']
DATA_SOURCE_ID = config['data_source_id']
REGION = config['region']

# Initialize Bedrock Agent client
bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)

print(f"Starting new ingestion job...")
print(f"  Knowledge Base ID: {KB_ID}")
print(f"  Data Source ID: {DATA_SOURCE_ID}")

try:
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=KB_ID,
        dataSourceId=DATA_SOURCE_ID,
        description='Restarting ingestion after index fix'
    )
    
    job_id = response['ingestionJob']['ingestionJobId']
    status = response['ingestionJob']['status']
    
    print(f"\n✓ Ingestion job started!")
    print(f"  Job ID: {job_id}")
    print(f"  Status: {status}")
    
    # Update config with new job ID
    config['ingestion_job_id'] = job_id
    with open('kb-config-staging.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✓ Updated kb-config-staging.json with new job ID")
    print(f"\nWait 1-2 minutes, then run: python test_kb_retrieval_staging.py")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    exit(1)
