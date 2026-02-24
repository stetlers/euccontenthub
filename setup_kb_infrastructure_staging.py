#!/usr/bin/env python3
"""
Setup Bedrock Knowledge Base Infrastructure - Staging Environment

This script sets up the complete infrastructure for the deterministic chatbot:
1. S3 bucket for knowledge base content
2. OpenSearch Serverless collection
3. Bedrock Knowledge Base
4. Bedrock Agent
5. IAM roles and policies

Phase 1 of the deterministic chatbot implementation.
"""

import boto3
import json
import time
from datetime import datetime

# AWS Configuration
REGION = 'us-east-1'
ACCOUNT_ID = '031421429609'
ENVIRONMENT = 'staging'

# Resource Names
S3_BUCKET_NAME = f'euc-content-hub-kb-{ENVIRONMENT}'
OPENSEARCH_COLLECTION_NAME = f'euc-kb-{ENVIRONMENT}'
KB_NAME = f'euc-content-assistant-kb-{ENVIRONMENT}'
AGENT_NAME = f'euc-content-assistant-{ENVIRONMENT}'

# Initialize AWS clients
s3 = boto3.client('s3', region_name=REGION)
iam = boto3.client('iam', region_name=REGION)
aoss = boto3.client('opensearchserverless', region_name=REGION)
bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)

def print_step(step_num, description):
    """Print formatted step header"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {description}")
    print(f"{'='*80}\n")

def create_s3_bucket():
    """Create S3 bucket for knowledge base content"""
    print_step(1, "Creating S3 Bucket for Knowledge Base Content")
    
    try:
        # Check if bucket exists
        try:
            s3.head_bucket(Bucket=S3_BUCKET_NAME)
            print(f"✓ Bucket {S3_BUCKET_NAME} already exists")
            return S3_BUCKET_NAME
        except:
            pass
        
        # Create bucket
        s3.create_bucket(Bucket=S3_BUCKET_NAME)
        print(f"✓ Created bucket: {S3_BUCKET_NAME}")
        
        # Enable versioning
        s3.put_bucket_versioning(
            Bucket=S3_BUCKET_NAME,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        print(f"✓ Enabled versioning on bucket")
        
        # Add tags
        s3.put_bucket_tagging(
            Bucket=S3_BUCKET_NAME,
            Tagging={
                'TagSet': [
                    {'Key': 'Environment', 'Value': ENVIRONMENT},
                    {'Key': 'Project', 'Value': 'EUC-Content-Hub'},
                    {'Key': 'Purpose', 'Value': 'Bedrock-Knowledge-Base'}
                ]
            }
        )
        print(f"✓ Added tags to bucket")
        
        return S3_BUCKET_NAME
        
    except Exception as e:
        print(f"✗ Error creating S3 bucket: {str(e)}")
        raise

def upload_kb_content():
    """Upload initial knowledge base content to S3"""
    print_step(2, "Uploading Knowledge Base Content to S3")
    
    import os
    
    kb_content_dir = 'kb-content'
    
    if not os.path.exists(kb_content_dir):
        print(f"✗ Knowledge base content directory not found: {kb_content_dir}")
        return
    
    uploaded_files = []
    
    # Walk through kb-content directory
    for root, dirs, files in os.walk(kb_content_dir):
        for file in files:
            local_path = os.path.join(root, file)
            # Remove 'kb-content/' prefix for S3 key
            s3_key = local_path.replace(kb_content_dir + os.sep, '').replace('\\', '/')
            
            try:
                # Determine content type
                content_type = 'text/markdown' if file.endswith('.md') else 'application/json'
                
                # Upload file
                s3.upload_file(
                    local_path,
                    S3_BUCKET_NAME,
                    s3_key,
                    ExtraArgs={'ContentType': content_type}
                )
                print(f"✓ Uploaded: {s3_key}")
                uploaded_files.append(s3_key)
                
            except Exception as e:
                print(f"✗ Error uploading {local_path}: {str(e)}")
    
    print(f"\n✓ Uploaded {len(uploaded_files)} files to S3")
    return uploaded_files

def create_kb_iam_role():
    """Create IAM role for Bedrock Knowledge Base"""
    print_step(3, "Creating IAM Role for Bedrock Knowledge Base")
    
    role_name = f'BedrockKnowledgeBaseRole-{ENVIRONMENT}'
    
    # Trust policy for Bedrock
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": ACCOUNT_ID
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:knowledge-base/*"
                    }
                }
            }
        ]
    }
    
    # Permissions policy
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{S3_BUCKET_NAME}",
                    f"arn:aws:s3:::{S3_BUCKET_NAME}/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel"
                ],
                "Resource": [
                    f"arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v2:0"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "aoss:APIAccessAll"
                ],
                "Resource": [
                    f"arn:aws:aoss:{REGION}:{ACCOUNT_ID}:collection/*"
                ]
            }
        ]
    }
    
    try:
        # Check if role exists
        try:
            role = iam.get_role(RoleName=role_name)
            print(f"✓ Role {role_name} already exists")
            role_arn = role['Role']['Arn']
        except iam.exceptions.NoSuchEntityException:
            # Create role
            role = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f'Role for Bedrock Knowledge Base - {ENVIRONMENT}',
                Tags=[
                    {'Key': 'Environment', 'Value': ENVIRONMENT},
                    {'Key': 'Project', 'Value': 'EUC-Content-Hub'}
                ]
            )
            role_arn = role['Role']['Arn']
            print(f"✓ Created role: {role_name}")
        
        # Attach inline policy
        policy_name = f'BedrockKBPolicy-{ENVIRONMENT}'
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(permissions_policy)
        )
        print(f"✓ Attached policy: {policy_name}")
        
        return role_arn
        
    except Exception as e:
        print(f"✗ Error creating IAM role: {str(e)}")
        raise

def create_opensearch_collection():
    """Create OpenSearch Serverless collection for vector storage"""
    print_step(4, "Creating OpenSearch Serverless Collection")
    
    try:
        # Check if collection exists
        try:
            collections = aoss.list_collections(
                collectionFilters={'name': OPENSEARCH_COLLECTION_NAME}
            )
            if collections['collectionSummaries']:
                collection_id = collections['collectionSummaries'][0]['id']
                collection_arn = collections['collectionSummaries'][0]['arn']
                print(f"✓ Collection {OPENSEARCH_COLLECTION_NAME} already exists")
                print(f"  Collection ID: {collection_id}")
                print(f"  Collection ARN: {collection_arn}")
                return collection_id, collection_arn
        except:
            pass
        
        # Create encryption policy
        encryption_policy_name = f'euc-kb-encryption-{ENVIRONMENT}'
        encryption_policy = {
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{OPENSEARCH_COLLECTION_NAME}"]
                }
            ],
            "AWSOwnedKey": True
        }
        
        try:
            aoss.create_security_policy(
                name=encryption_policy_name,
                type='encryption',
                policy=json.dumps(encryption_policy)
            )
            print(f"✓ Created encryption policy: {encryption_policy_name}")
        except aoss.exceptions.ConflictException:
            print(f"✓ Encryption policy already exists: {encryption_policy_name}")
        
        # Create network policy (public access for now)
        network_policy_name = f'euc-kb-network-{ENVIRONMENT}'
        network_policy = [
            {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{OPENSEARCH_COLLECTION_NAME}"]
                    },
                    {
                        "ResourceType": "dashboard",
                        "Resource": [f"collection/{OPENSEARCH_COLLECTION_NAME}"]
                    }
                ],
                "AllowFromPublic": True
            }
        ]
        
        try:
            aoss.create_security_policy(
                name=network_policy_name,
                type='network',
                policy=json.dumps(network_policy)
            )
            print(f"✓ Created network policy: {network_policy_name}")
        except aoss.exceptions.ConflictException:
            print(f"✓ Network policy already exists: {network_policy_name}")
        
        # Create data access policy
        data_policy_name = f'euc-kb-data-{ENVIRONMENT}'
        data_policy = [
            {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{OPENSEARCH_COLLECTION_NAME}"],
                        "Permission": [
                            "aoss:CreateCollectionItems",
                            "aoss:DeleteCollectionItems",
                            "aoss:UpdateCollectionItems",
                            "aoss:DescribeCollectionItems"
                        ]
                    },
                    {
                        "ResourceType": "index",
                        "Resource": [f"index/{OPENSEARCH_COLLECTION_NAME}/*"],
                        "Permission": [
                            "aoss:CreateIndex",
                            "aoss:DeleteIndex",
                            "aoss:UpdateIndex",
                            "aoss:DescribeIndex",
                            "aoss:ReadDocument",
                            "aoss:WriteDocument"
                        ]
                    }
                ],
                "Principal": [
                    f"arn:aws:iam::{ACCOUNT_ID}:role/BedrockKnowledgeBaseRole-{ENVIRONMENT}",
                    f"arn:aws:sts::{ACCOUNT_ID}:assumed-role/Admin/*"
                ]
            }
        ]
        
        try:
            aoss.create_access_policy(
                name=data_policy_name,
                type='data',
                policy=json.dumps(data_policy)
            )
            print(f"✓ Created data access policy: {data_policy_name}")
        except aoss.exceptions.ConflictException:
            print(f"✓ Data access policy already exists: {data_policy_name}")
        
        # Create collection
        print(f"Creating collection (this may take 2-3 minutes)...")
        response = aoss.create_collection(
            name=OPENSEARCH_COLLECTION_NAME,
            type='VECTORSEARCH',
            description=f'Vector store for EUC Content Hub Knowledge Base - {ENVIRONMENT}',
            tags=[
                {'key': 'Environment', 'value': ENVIRONMENT},
                {'key': 'Project', 'value': 'EUC-Content-Hub'}
            ]
        )
        
        collection_id = response['createCollectionDetail']['id']
        collection_arn = response['createCollectionDetail']['arn']
        
        print(f"✓ Collection creation initiated")
        print(f"  Collection ID: {collection_id}")
        print(f"  Collection ARN: {collection_arn}")
        
        # Wait for collection to be active
        print("Waiting for collection to become active...")
        max_wait = 300  # 5 minutes
        wait_interval = 10
        elapsed = 0
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            status_response = aoss.batch_get_collection(ids=[collection_id])
            if status_response['collectionDetails']:
                status = status_response['collectionDetails'][0]['status']
                print(f"  Status: {status} ({elapsed}s elapsed)")
                
                if status == 'ACTIVE':
                    print(f"✓ Collection is now active!")
                    endpoint = status_response['collectionDetails'][0]['collectionEndpoint']
                    print(f"  Endpoint: {endpoint}")
                    return collection_id, collection_arn
                elif status == 'FAILED':
                    raise Exception("Collection creation failed")
        
        raise Exception("Collection creation timed out")
        
    except Exception as e:
        print(f"✗ Error creating OpenSearch collection: {str(e)}")
        raise

def create_opensearch_index(collection_endpoint):
    """Create OpenSearch index for vector storage"""
    print_step(5, "Creating OpenSearch Index")
    
    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from requests_aws4auth import AWS4Auth
        import boto3
        
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
        
        # Check if index exists
        if client.indices.exists(index=index_name):
            print(f"✓ Index {index_name} already exists")
            return index_name
        
        # Create index with vector mapping
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
                    "metadata": {
                        "type": "object"
                    }
                }
            }
        }
        
        client.indices.create(index=index_name, body=index_body)
        print(f"✓ Created index: {index_name}")
        
        return index_name
        
    except Exception as e:
        print(f"✗ Error creating OpenSearch index: {str(e)}")
        raise

def create_knowledge_base(role_arn, collection_arn):
    """Create Bedrock Knowledge Base"""
    print_step(6, "Creating Bedrock Knowledge Base")
    
    try:
        # Check if KB exists
        try:
            kbs = bedrock_agent.list_knowledge_bases()
            for kb in kbs.get('knowledgeBaseSummaries', []):
                if kb['name'] == KB_NAME:
                    kb_id = kb['knowledgeBaseId']
                    print(f"✓ Knowledge Base {KB_NAME} already exists")
                    print(f"  KB ID: {kb_id}")
                    return kb_id
        except:
            pass
        
        # Extract collection ID from ARN
        collection_id = collection_arn.split('/')[-1]
        
        # Create knowledge base
        response = bedrock_agent.create_knowledge_base(
            name=KB_NAME,
            description=f'Knowledge base for EUC Content Hub chatbot - {ENVIRONMENT}',
            roleArn=role_arn,
            knowledgeBaseConfiguration={
                'type': 'VECTOR',
                'vectorKnowledgeBaseConfiguration': {
                    'embeddingModelArn': f'arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v2:0'
                }
            },
            storageConfiguration={
                'type': 'OPENSEARCH_SERVERLESS',
                'opensearchServerlessConfiguration': {
                    'collectionArn': collection_arn,
                    'vectorIndexName': 'euc-content-index',
                    'fieldMapping': {
                        'vectorField': 'embedding',
                        'textField': 'text',
                        'metadataField': 'metadata'
                    }
                }
            },
            tags={
                'Environment': ENVIRONMENT,
                'Project': 'EUC-Content-Hub'
            }
        )
        
        kb_id = response['knowledgeBase']['knowledgeBaseId']
        print(f"✓ Created Knowledge Base: {KB_NAME}")
        print(f"  KB ID: {kb_id}")
        
        return kb_id
        
    except Exception as e:
        print(f"✗ Error creating Knowledge Base: {str(e)}")
        raise

def create_data_source(kb_id):
    """Create data source for Knowledge Base"""
    print_step(7, "Creating Data Source for Knowledge Base")
    
    try:
        # Create data source
        response = bedrock_agent.create_data_source(
            knowledgeBaseId=kb_id,
            name=f'euc-kb-s3-source-{ENVIRONMENT}',
            description=f'S3 data source for EUC KB - {ENVIRONMENT}',
            dataSourceConfiguration={
                'type': 'S3',
                's3Configuration': {
                    'bucketArn': f'arn:aws:s3:::{S3_BUCKET_NAME}'
                    # No inclusionPrefixes - will index entire bucket
                }
            },
            vectorIngestionConfiguration={
                'chunkingConfiguration': {
                    'chunkingStrategy': 'FIXED_SIZE',
                    'fixedSizeChunkingConfiguration': {
                        'maxTokens': 300,
                        'overlapPercentage': 20
                    }
                }
            }
        )
        
        data_source_id = response['dataSource']['dataSourceId']
        print(f"✓ Created data source")
        print(f"  Data Source ID: {data_source_id}")
        
        # Start ingestion job
        print("Starting ingestion job...")
        ingestion_response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id,
            description='Initial ingestion of KB content'
        )
        
        ingestion_job_id = ingestion_response['ingestionJob']['ingestionJobId']
        print(f"✓ Started ingestion job")
        print(f"  Job ID: {ingestion_job_id}")
        
        return data_source_id, ingestion_job_id
        
    except Exception as e:
        print(f"✗ Error creating data source: {str(e)}")
        raise

def main():
    """Main setup function"""
    print(f"\n{'#'*80}")
    print(f"# Bedrock Knowledge Base Infrastructure Setup - {ENVIRONMENT.upper()}")
    print(f"# Region: {REGION}")
    print(f"# Account: {ACCOUNT_ID}")
    print(f"# Timestamp: {datetime.now().isoformat()}")
    print(f"{'#'*80}\n")
    
    try:
        # Step 1: Create S3 bucket
        bucket_name = create_s3_bucket()
        
        # Step 2: Upload KB content
        uploaded_files = upload_kb_content()
        
        # Step 3: Create IAM role
        role_arn = create_kb_iam_role()
        
        # Wait for IAM role to propagate
        print("\nWaiting 10 seconds for IAM role to propagate...")
        time.sleep(10)
        
        # Step 4: Create OpenSearch collection
        collection_id, collection_arn = create_opensearch_collection()
        
        # Get collection endpoint
        collection_details = aoss.batch_get_collection(ids=[collection_id])
        collection_endpoint = collection_details['collectionDetails'][0]['collectionEndpoint']
        
        # Step 5: Create OpenSearch index
        index_name = create_opensearch_index(collection_endpoint)
        
        # Step 6: Create Knowledge Base
        kb_id = create_knowledge_base(role_arn, collection_arn)
        
        # Step 7: Create data source and start ingestion
        data_source_id, ingestion_job_id = create_data_source(kb_id)
        
        # Summary
        print(f"\n{'='*80}")
        print("SETUP COMPLETE!")
        print(f"{'='*80}\n")
        
        print("Resources Created:")
        print(f"  S3 Bucket: {bucket_name}")
        print(f"  IAM Role: {role_arn}")
        print(f"  OpenSearch Collection: {collection_id}")
        print(f"  Knowledge Base ID: {kb_id}")
        print(f"  Data Source ID: {data_source_id}")
        print(f"  Ingestion Job ID: {ingestion_job_id}")
        
        print("\nNext Steps:")
        print("  1. Wait for ingestion job to complete (check AWS Console)")
        print("  2. Test knowledge base retrieval")
        print("  3. Create Bedrock Agent (Phase 2)")
        print("  4. Update chat Lambda to use KB + Agent")
        
        # Save configuration
        config = {
            'environment': ENVIRONMENT,
            'region': REGION,
            'account_id': ACCOUNT_ID,
            's3_bucket': bucket_name,
            'iam_role_arn': role_arn,
            'opensearch_collection_id': collection_id,
            'opensearch_collection_arn': collection_arn,
            'knowledge_base_id': kb_id,
            'data_source_id': data_source_id,
            'ingestion_job_id': ingestion_job_id,
            'created_at': datetime.now().isoformat()
        }
        
        with open(f'kb-config-{ENVIRONMENT}.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✓ Configuration saved to: kb-config-{ENVIRONMENT}.json")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print("SETUP FAILED!")
        print(f"{'='*80}\n")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
