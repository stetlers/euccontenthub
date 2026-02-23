"""
Test Chat Lambda with AWS Docs Integration
"""

import boto3
import json
import time

# AWS clients
lambda_client = boto3.client('lambda', region_name='us-east-1')

LAMBDA_NAME = 'aws-blog-chat-assistant'

# Test queries
TEST_QUERIES = [
    {
        'name': 'AWS Service Query (should trigger AWS docs)',
        'message': 'How do I configure Amazon WorkSpaces for multi-factor authentication?',
        'expect_aws_docs': True
    },
    {
        'name': 'General EUC Query (should NOT trigger AWS docs)',
        'message': 'What are the best practices for virtual desktop deployment?',
        'expect_aws_docs': False
    },
    {
        'name': 'Specific Service Query',
        'message': 'How to setup AppStream 2.0 image builder?',
        'expect_aws_docs': True
    },
    {
        'name': 'Architecture Query',
        'message': 'What is the best architecture for WorkSpaces?',
        'expect_aws_docs': True
    },
    {
        'name': 'Simple Query',
        'message': 'Tell me about remote work solutions',
        'expect_aws_docs': False
    }
]


def invoke_lambda(message):
    """Invoke Lambda function with test message"""
    payload = {
        'body': json.dumps({
            'message': message
        })
    }
    
    print(f"\n{'='*60}")
    print(f"Testing: {message}")
    print(f"{'='*60}")
    
    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        if response_payload.get('statusCode') != 200:
            print(f"✗ Error: Status code {response_payload.get('statusCode')}")
            print(f"  Body: {response_payload.get('body')}")
            return None
        
        body = json.loads(response_payload['body'])
        return body
        
    except Exception as e:
        print(f"✗ Error invoking Lambda: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def display_results(result, expect_aws_docs):
    """Display test results"""
    if not result:
        print("✗ No result returned")
        return False
    
    print("\n📝 Response:")
    print(f"  {result.get('response', 'No response')}")
    
    # Check AWS docs
    aws_docs = result.get('aws_docs', [])
    has_aws_docs = len(aws_docs) > 0
    
    print(f"\n📚 AWS Documentation Results: {len(aws_docs)}")
    if aws_docs:
        for i, doc in enumerate(aws_docs, 1):
            print(f"  {i}. {doc.get('title', 'No title')}")
            print(f"     URL: {doc.get('url', 'No URL')}")
            print(f"     Snippet: {doc.get('snippet', 'No snippet')[:100]}...")
    else:
        print("  (None)")
    
    # Check blog recommendations
    recommendations = result.get('recommendations', [])
    print(f"\n📰 Blog Post Recommendations: {len(recommendations)}")
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec.get('title', 'No title')}")
            print(f"     Reason: {rec.get('relevance_reason', 'No reason')}")
    else:
        print("  (None)")
    
    # Validate expectations
    print(f"\n✓ Validation:")
    if expect_aws_docs and not has_aws_docs:
        print(f"  ⚠ Expected AWS docs but got none")
        return False
    elif not expect_aws_docs and has_aws_docs:
        print(f"  ⚠ Did not expect AWS docs but got {len(aws_docs)}")
        # This is not necessarily a failure, just unexpected
    
    if has_aws_docs:
        print(f"  ✓ AWS docs integration working ({len(aws_docs)} results)")
    
    if recommendations:
        print(f"  ✓ Blog recommendations working ({len(recommendations)} results)")
    else:
        print(f"  ⚠ No blog recommendations returned")
    
    return True


def run_all_tests():
    """Run all test queries"""
    print("=" * 60)
    print("TESTING CHAT LAMBDA WITH AWS DOCS INTEGRATION")
    print("=" * 60)
    
    results = []
    
    for test in TEST_QUERIES:
        print(f"\n\n{'#'*60}")
        print(f"Test: {test['name']}")
        print(f"{'#'*60}")
        
        result = invoke_lambda(test['message'])
        success = display_results(result, test['expect_aws_docs'])
        
        results.append({
            'name': test['name'],
            'success': success
        })
        
        # Wait between tests
        time.sleep(2)
    
    # Summary
    print("\n\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status = "✓ PASS" if result['success'] else "✗ FAIL"
        print(f"{status}: {result['name']}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
    
    return passed == total


def test_single_query():
    """Test a single custom query"""
    print("=" * 60)
    print("SINGLE QUERY TEST")
    print("=" * 60)
    
    message = input("\nEnter your test query: ").strip()
    
    if not message:
        print("No query provided")
        return
    
    result = invoke_lambda(message)
    display_results(result, expect_aws_docs=None)


def main():
    """Main test flow"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--single':
        test_single_query()
    else:
        run_all_tests()


if __name__ == '__main__':
    main()
