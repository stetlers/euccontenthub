"""
Test KB Editor endpoints in staging environment
"""
import boto3
import json
from datetime import datetime, timedelta

REGION = 'us-east-1'
API_URL = 'https://xox05733ce.execute-api.us-east-1.amazonaws.com/staging'

def check_recent_logs():
    """Check recent Lambda logs for KB editor errors"""
    print("\n" + "=" * 60)
    print("CHECKING LAMBDA LOGS FOR KB EDITOR")
    print("=" * 60)
    
    logs_client = boto3.client('logs', region_name=REGION)
    log_group = '/aws/lambda/aws-blog-api'
    
    # Get logs from last 10 minutes
    start_time = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)
    
    try:
        # Get recent log streams
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not streams_response['logStreams']:
            print("No recent log streams found")
            return
        
        print(f"\nChecking {len(streams_response['logStreams'])} most recent log streams...")
        
        kb_events = []
        error_events = []
        
        for stream in streams_response['logStreams']:
            stream_name = stream['logStreamName']
            
            try:
                events_response = logs_client.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream_name,
                    startTime=start_time,
                    limit=100
                )
                
                for event in events_response['events']:
                    message = event['message']
                    
                    # Look for KB-related events
                    if any(keyword in message.lower() for keyword in ['kb-', 'knowledge base', 'euc-qa', 'euc-service']):
                        kb_events.append({
                            'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                            'message': message
                        })
                    
                    # Look for errors
                    if any(keyword in message.lower() for keyword in ['error', 'exception', 'failed', 'forbidden', '403', '500']):
                        error_events.append({
                            'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                            'message': message
                        })
                        
            except Exception as e:
                print(f"Error reading stream {stream_name}: {e}")
                continue
        
        # Display KB-related events
        if kb_events:
            print(f"\n✅ Found {len(kb_events)} KB-related log entries:")
            for event in kb_events[-10:]:  # Show last 10
                print(f"\n[{event['timestamp']}]")
                print(event['message'][:500])  # Truncate long messages
        else:
            print("\n⚠️  No KB-related log entries found in last 10 minutes")
        
        # Display errors
        if error_events:
            print(f"\n❌ Found {len(error_events)} error entries:")
            for event in error_events[-5:]:  # Show last 5
                print(f"\n[{event['timestamp']}]")
                print(event['message'][:500])
        else:
            print("\n✅ No errors found in last 10 minutes")
            
    except Exception as e:
        print(f"Error checking logs: {e}")

def check_api_gateway_resources():
    """Check if API Gateway resources exist"""
    print("\n" + "=" * 60)
    print("CHECKING API GATEWAY RESOURCES")
    print("=" * 60)
    
    api_client = boto3.client('apigateway', region_name=REGION)
    api_id = 'xox05733ce'
    
    try:
        resources = api_client.get_resources(restApiId=api_id, limit=500)
        
        kb_resources = [r for r in resources['items'] if 'kb-' in r['path']]
        
        if kb_resources:
            print(f"\n✅ Found {len(kb_resources)} KB-related resources:")
            for resource in kb_resources:
                methods = resource.get('resourceMethods', {}).keys()
                print(f"  {resource['path']} - Methods: {', '.join(methods)}")
        else:
            print("\n❌ No KB-related resources found!")
            
    except Exception as e:
        print(f"Error checking API Gateway: {e}")

def check_lambda_permissions():
    """Check if Lambda has necessary permissions"""
    print("\n" + "=" * 60)
    print("CHECKING LAMBDA PERMISSIONS")
    print("=" * 60)
    
    iam_client = boto3.client('iam', region_name=REGION)
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    try:
        # Get Lambda function
        function = lambda_client.get_function(FunctionName='aws-blog-api')
        role_arn = function['Configuration']['Role']
        role_name = role_arn.split('/')[-1]
        
        print(f"\nLambda Role: {role_name}")
        
        # Get attached policies
        policies = iam_client.list_attached_role_policies(RoleName=role_name)
        
        print(f"\nAttached Policies:")
        for policy in policies['AttachedPolicies']:
            print(f"  - {policy['PolicyName']}")
            
        # Check for KB-specific policies
        kb_policies = [p for p in policies['AttachedPolicies'] if 'KB' in p['PolicyName'] or 'Bedrock' in p['PolicyName']]
        
        if kb_policies:
            print(f"\n✅ Found {len(kb_policies)} KB-related policies")
        else:
            print("\n⚠️  No KB-specific policies found (may be in inline policies)")
            
    except Exception as e:
        print(f"Error checking permissions: {e}")

if __name__ == '__main__':
    print("\n🔍 KB EDITOR STAGING DIAGNOSTICS")
    print("=" * 60)
    
    check_api_gateway_resources()
    check_lambda_permissions()
    check_recent_logs()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Visit https://staging.awseuccontent.com")
    print("2. Sign in and click 'Edit Knowledge Base'")
    print("3. Try clicking on a document")
    print("4. Run this script again to see new logs")
