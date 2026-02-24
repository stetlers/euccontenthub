#!/usr/bin/env python3
"""
Test Bedrock Agent - Staging

This script tests the Bedrock Agent by sending sample queries
and checking the responses for determinism and quality.
"""

import boto3
import json
import uuid
from datetime import datetime

# Load configuration
with open('kb-config-staging.json') as f:
    config = json.load(f)

AGENT_ID = config['agent_id']
AGENT_ALIAS_ID = config['agent_alias_id']
REGION = config['region']

# Initialize Bedrock Agent Runtime client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)

def test_agent_query(query, session_id=None):
    """Test agent with a query"""
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}\n")
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=query
        )
        
        # Collect response chunks
        full_response = ""
        citations = []
        
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    full_response += text
                    
                # Collect citations
                if 'attribution' in chunk:
                    attribution = chunk['attribution']
                    if 'citations' in attribution:
                        citations.extend(attribution['citations'])
        
        print("Response:")
        print("-" * 80)
        print(full_response)
        print("-" * 80)
        
        if citations:
            print(f"\nCitations ({len(citations)}):")
            for i, citation in enumerate(citations, 1):
                print(f"\n  Citation {i}:")
                if 'retrievedReferences' in citation:
                    for ref in citation['retrievedReferences']:
                        location = ref.get('location', {})
                        if 's3Location' in location:
                            print(f"    Source: {location['s3Location'].get('uri', 'N/A')}")
                        content = ref.get('content', {}).get('text', '')
                        if content:
                            print(f"    Content: {content[:150]}...")
        
        return {
            'response': full_response,
            'citations': citations,
            'session_id': session_id
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_determinism(query, num_runs=3):
    """Test if agent gives consistent responses"""
    print(f"\n{'='*80}")
    print(f"DETERMINISM TEST: {query}")
    print(f"Running {num_runs} times to check consistency...")
    print(f"{'='*80}\n")
    
    responses = []
    for i in range(num_runs):
        print(f"Run {i+1}/{num_runs}...")
        result = test_agent_query(query, session_id=str(uuid.uuid4()))
        if result:
            responses.append(result['response'])
    
    if len(responses) == num_runs:
        # Check similarity (simple check - responses should be very similar)
        first_response = responses[0]
        all_similar = all(
            len(set(first_response.split()) & set(r.split())) / len(set(first_response.split())) > 0.7
            for r in responses[1:]
        )
        
        if all_similar:
            print("\n✅ Responses are consistent (>70% word overlap)")
        else:
            print("\n⚠️  Responses vary significantly")
            print("\nResponse 1 length:", len(responses[0]))
            print("Response 2 length:", len(responses[1]))
            print("Response 3 length:", len(responses[2]))
    else:
        print("\n❌ Some queries failed")

def main():
    """Main test function"""
    print(f"\n{'#'*80}")
    print(f"# Bedrock Agent Test - STAGING")
    print(f"# Agent ID: {AGENT_ID}")
    print(f"# Agent Alias ID: {AGENT_ALIAS_ID}")
    print(f"# Region: {REGION}")
    print(f"# Timestamp: {datetime.now().isoformat()}")
    print(f"{'#'*80}\n")
    
    # Test queries
    test_queries = [
        "What is EUC?",
        "How do I set up Amazon WorkSpaces Personal?",
        "What's the difference between WorkSpaces and WorkSpaces Personal?",
        "What services were renamed in November 2024?",
        "Tell me about AppStream 2.0",
        "How do I secure my WorkSpaces deployment?",
        "What is Amazon WorkSpaces Applications?",
        "How do I troubleshoot WorkSpaces connection issues?"
    ]
    
    print("="*80)
    print("SINGLE QUERY TESTS")
    print("="*80)
    
    results = []
    for query in test_queries:
        result = test_agent_query(query)
        if result:
            results.append({
                'query': query,
                'response_length': len(result['response']),
                'has_citations': len(result['citations']) > 0,
                'success': True
            })
        else:
            results.append({
                'query': query,
                'success': False
            })
    
    # Test determinism with one query
    print("\n" + "="*80)
    print("DETERMINISM TEST")
    print("="*80)
    test_determinism("What is EUC?", num_runs=3)
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}\n")
    
    successful = sum(1 for r in results if r['success'])
    with_citations = sum(1 for r in results if r.get('has_citations', False))
    
    print(f"Total Queries: {len(test_queries)}")
    print(f"Successful: {successful}/{len(test_queries)}")
    print(f"With Citations: {with_citations}/{successful}")
    
    if successful == len(test_queries):
        print("\n✅ All tests passed! Agent is working correctly.")
        
        # Check response quality
        avg_length = sum(r['response_length'] for r in results if r['success']) / successful
        print(f"\nResponse Quality:")
        print(f"  Average response length: {avg_length:.0f} characters")
        print(f"  Citation rate: {with_citations}/{successful} ({with_citations/successful*100:.0f}%)")
        
        return 0
    else:
        print(f"\n⚠️  {len(test_queries) - successful} test(s) failed.")
        return 1

if __name__ == '__main__':
    exit(main())
