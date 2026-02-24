#!/usr/bin/env python3
"""
Fix OpenSearch Index Mapping

The index was created with incorrect mapping for metadata field.
This script deletes and recreates the index with the correct mapping.
"""

import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

REGION = config['region']
COLLECTION_ID = config['opensearch_collection_id']

# Get collection endpoint
aoss = boto3.client('opensearchserverless', region_name=REGION)
collection_details = aoss.batch_get_collection(ids=[COLLECTION_ID])
collection_endpoint = collection_details['collectionDetails'][0]['collectionEndpoint']

print(f"Collection Endpoint: {collection_endpoint}")

# Get AWS credentials
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    REGION,
    'aoss',
    session_token=credentials.token
)

# Create OpenSearch client
client = OpenSearch(
    hosts=[{'host': collection_endpoint.replace('https://', ''), 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300
)

index_name = 'euc-content-index'

# Delete existing index
print(f"\nDeleting index: {index_name}")
try:
    client.indices.delete(index=index_name)
    print("✓ Index deleted")
except Exception as e:
    print(f"Note: {str(e)}")

# Create index with correct mapping
# The key fix: metadata should NOT have a type specified - let it be dynamic
index_body = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 512
        }
    },
    "mappings": {
        "properties": {
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "engine": "faiss",
                    "parameters": {
                        "ef_construction": 512,
                        "m": 16
                    }
                }
            },
            "text": {
                "type": "text"
            },
            "AMAZON_BEDROCK_TEXT_CHUNK": {
                "type": "text"
            },
            "AMAZON_BEDROCK_METADATA": {
                "type": "text",
                "index": False
            }
        }
    }
}

print(f"\nCreating index with correct mapping...")
client.indices.create(index=index_name, body=index_body)
print(f"✓ Created index: {index_name}")

print("\n✓ Index fixed! Now restart the ingestion job.")
print("\nTo restart ingestion:")
print(f"  1. Go to AWS Console > Bedrock > Knowledge Bases")
print(f"  2. Select knowledge base: {config['knowledge_base_id']}")
print(f"  3. Go to Data Sources tab")
print(f"  4. Click 'Sync' to start a new ingestion job")
