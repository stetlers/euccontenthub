#!/usr/bin/env python3
"""
Test Bedrock Knowledge Base Retrieval - Staging

This script tests the knowledge base by running sample queries
and checking the retrieved results.
"""

import boto3
import json
from datetime import datetime

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

KB_ID = config['knowledge_base_id']
REGION = config['region']

# Initialize Bedrock Agent Runtime client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)

def test_retrieval(query, num_results=5):
    """Test knowledge base retrieval with a query"""
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}\n")
    
    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': num_results
                }
            }
        )
        
        results = response.get('retrievalResults', [])
        
        if not results:
            print("❌ No results found")
            return False
        
        print(f"✓ Found {len(results)} results:\n")
        
        for i, result in enumerate(results, 1):
            score = result.get('score', 0)
            content = result.get('content', {}).get('text', '')
            location = result.get('location', {})
            
            print(f"Result {i} (Score: {score:.4f}):")
            print(f"  Location: {location.get('type', 'unknown')}")
            if location.get('s3Location'):
                print(f"  S3 URI: {location['s3Location'].get('uri', 'N/A')}")
            print(f"  Content Preview: {content[:200]}...")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def check_ingestion_status():
    """Check the status of the ingestion job"""
    print(f"\n{'='*80}")
    print("Checking Ingestion Job Status")
    print(f"{'='*80}\n")
    
    try:
        bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)
        
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=config['data_source_id'],
            ingestionJobId=config['ingestion_job_id']
        )
        
        job = response['ingestionJob']
        status = job['status']
        
        print(f"Ingestion Job ID: {config['ingestion_job_id']}")
        print(f"Status: {status}")
        print(f"Started: {job.get('startedAt', 'N/A')}")
        
        if status == 'COMPLETE':
            print(f"Completed: {job.get('updatedAt', 'N/A')}")
            stats = job.get('statistics', {})
            print(f"\nStatistics:")
            print(f"  Documents Scanned: {stats.get('numberOfDocumentsScanned', 0)}")
            print(f"  Documents Indexed: {stats.get('numberOfNewDocumentsIndexed', 0)}")
            print(f"  Documents Modified: {stats.get('numberOfModifiedDocumentsIndexed', 0)}")
            print(f"  Documents Deleted: {stats.get('numberOfDocumentsDeleted', 0)}")
            print(f"  Documents Failed: {stats.get('numberOfDocumentsFailed', 0)}")
            return True
        elif status == 'IN_PROGRESS':
            print("\n⏳ Ingestion is still in progress. Please wait and try again.")
            return False
        elif status == 'FAILED':
            print(f"\n❌ Ingestion failed!")
            if 'failureReasons' in job:
                print(f"Failure reasons: {job['failureReasons']}")
            return False
        else:
            print(f"\n⚠️  Unknown status: {status}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking ingestion status: {str(e)}")
        return False

def main():
    """Main test function"""
    print(f"\n{'#'*80}")
    print(f"# Bedrock Knowledge Base Retrieval Test - STAGING")
    print(f"# Knowledge Base ID: {KB_ID}")
    print(f"# Region: {REGION}")
    print(f"# Timestamp: {datetime.now().isoformat()}")
    print(f"{'#'*80}\n")
    
    # Check ingestion status first
    ingestion_complete = check_ingestion_status()
    
    if not ingestion_complete:
        print("\n⚠️  Ingestion not complete. Retrieval tests may not work properly.")
        print("Please wait for ingestion to complete and run this script again.")
        return 1
    
    # Test queries
    test_queries = [
        "What is EUC?",
        "How do I set up Amazon WorkSpaces Personal?",
        "What's the difference between WorkSpaces and WorkSpaces Personal?",
        "How do I secure my WorkSpaces deployment?",
        "What services were renamed in November 2024?",
        "Tell me about AppStream 2.0",
        "What is Amazon WorkSpaces Applications?",
        "How do I troubleshoot WorkSpaces connection issues?"
    ]
    
    print(f"\n{'='*80}")
    print("Running Test Queries")
    print(f"{'='*80}\n")
    
    passed = 0
    failed = 0
    
    for query in test_queries:
        if test_retrieval(query, num_results=3):
            passed += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{'='*80}")
    print("Test Summary")
    print(f"{'='*80}\n")
    print(f"Total Queries: {len(test_queries)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n✅ All tests passed! Knowledge Base is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")
        return 1

if __name__ == '__main__':
    exit(main())
