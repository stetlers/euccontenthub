"""
Chat Lambda with Bedrock Knowledge Base Integration - Staging

This Lambda function replaces the current chat implementation with a
deterministic approach using Bedrock Agent + Knowledge Base.

Key improvements:
- Deterministic responses from curated Q&A
- Automatic citations from knowledge base
- Structured response format
- Better handling of service renames
"""

import json
import boto3
import uuid
import os
from decimal import Decimal

# AWS Configuration
REGION = os.environ.get('AWS_REGION')  # Lambda provides this automatically
AGENT_ID = os.environ.get('AGENT_ID', 'VEHCRYBNQ7')
AGENT_ALIAS_ID = os.environ.get('AGENT_ALIAS_ID', '46GCEU7LNT')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'aws-blog-posts-staging')

# Initialize AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal to int/float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def cors_headers():
    """Return CORS headers for API Gateway"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }

def create_response(status_code, body):
    """Create API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': cors_headers(),
        'body': json.dumps(body, cls=DecimalEncoder)
    }

def extract_post_ids_from_response(response_text):
    """
    Extract post IDs mentioned in the agent's response.
    
    The agent might mention posts in various formats:
    - "post_id: abc123"
    - "[post_id: abc123]"
    - Search for posts matching keywords
    """
    import re
    
    # Look for explicit post_id mentions
    post_id_pattern = r'post_id[:\s]+([a-zA-Z0-9-]+)'
    matches = re.findall(post_id_pattern, response_text, re.IGNORECASE)
    
    return list(set(matches))  # Remove duplicates

def get_posts_by_ids(post_ids):
    """Fetch full post details from DynamoDB by post IDs"""
    if not post_ids:
        return []
    
    posts = []
    for post_id in post_ids[:5]:  # Limit to 5 posts
        try:
            response = table.get_item(Key={'post_id': post_id})
            if 'Item' in response:
                posts.append(response['Item'])
        except Exception as e:
            print(f"Error fetching post {post_id}: {str(e)}")
    
    return posts

def search_posts_by_keywords(response_text, limit=3):
    """
    Search for relevant posts based on keywords in the agent's response.
    
    This is a fallback when no explicit post IDs are mentioned.
    """
    # Extract key terms from response (simple approach)
    keywords = []
    
    # Look for service names
    services = [
        'workspaces', 'appstream', 'connect', 'chime', 
        'workdocs', 'workspaces personal', 'workspaces applications',
        'workspaces secure browser', 'workspaces web'
    ]
    
    response_lower = response_text.lower()
    for service in services:
        if service in response_lower:
            keywords.append(service)
    
    if not keywords:
        return []
    
    # Search DynamoDB for posts matching keywords
    try:
        # Scan table for posts (in production, use better indexing)
        scan_response = table.scan(Limit=50)
        posts = scan_response.get('Items', [])
        
        # Score posts by keyword matches
        scored_posts = []
        for post in posts:
            score = 0
            title_lower = post.get('title', '').lower()
            content_lower = post.get('content', '').lower()
            tags_lower = post.get('tags', '').lower()
            
            for keyword in keywords:
                if keyword in title_lower:
                    score += 3
                if keyword in tags_lower:
                    score += 2
                if keyword in content_lower:
                    score += 1
            
            if score > 0:
                scored_posts.append((score, post))
        
        # Sort by score and return top posts
        scored_posts.sort(reverse=True, key=lambda x: x[0])
        return [post for score, post in scored_posts[:limit]]
        
    except Exception as e:
        print(f"Error searching posts: {str(e)}")
        return []

def format_post_recommendation(post):
    """Format a post for the recommendations array"""
    return {
        'post_id': post.get('post_id'),
        'title': post.get('title'),
        'url': post.get('url'),
        'summary': post.get('summary', 'No summary available'),
        'label': post.get('label', 'N/A'),
        'authors': post.get('authors', 'Unknown'),
        'date_published': post.get('date_published', 'Unknown'),
        'source': post.get('source', 'aws.amazon.com')
    }

def invoke_bedrock_agent(user_message, session_id):
    """
    Invoke Bedrock Agent with user message.
    
    Returns:
        dict: {
            'response': str,
            'citations': list,
            'trace': dict (optional)
        }
    """
    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=user_message,
            enableTrace=True  # Enable trace for debugging
        )
        
        # Collect response chunks
        full_response = ""
        citations = []
        trace_data = {}
        
        for event in response['completion']:
            # Collect response text
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
            
            # Collect trace information (for debugging)
            if 'trace' in event:
                trace = event['trace']
                if 'trace' in trace:
                    trace_info = trace['trace']
                    # Store trace data for logging
                    if 'orchestrationTrace' in trace_info:
                        trace_data = trace_info['orchestrationTrace']
        
        return {
            'response': full_response,
            'citations': citations,
            'trace': trace_data
        }
        
    except Exception as e:
        print(f"Error invoking Bedrock Agent: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def lambda_handler(event, context):
    """
    Main Lambda handler for chat with Bedrock Agent integration
    
    Input:
    {
        "message": "What is EUC?",
        "conversation_id": "uuid-v4" (optional)
    }
    
    Output:
    {
        "response": "EUC stands for End User Computing...",
        "recommendations": [
            {
                "post_id": "...",
                "title": "...",
                "summary": "...",
                "url": "...",
                "label": "...",
                "relevance_reason": "..."
            }
        ],
        "citations": [
            {
                "source": "curated-qa/common-questions.md",
                "content": "..."
            }
        ],
        "conversation_id": "uuid-v4"
    }
    """
    
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        user_message = body.get('message', '').strip()
        conversation_id = body.get('conversation_id') or str(uuid.uuid4())
        
        # Validate input
        if not user_message:
            return create_response(400, {
                'error': 'Message is required'
            })
        
        if len(user_message) > 500:
            return create_response(400, {
                'error': 'Message too long (max 500 characters)'
            })
        
        print(f"Processing message: {user_message}")
        print(f"Conversation ID: {conversation_id}")
        
        # Invoke Bedrock Agent
        agent_result = invoke_bedrock_agent(user_message, conversation_id)
        
        response_text = agent_result['response']
        citations = agent_result['citations']
        
        print(f"Agent response length: {len(response_text)}")
        print(f"Citations count: {len(citations)}")
        
        # Extract post IDs from response
        post_ids = extract_post_ids_from_response(response_text)
        print(f"Extracted post IDs: {post_ids}")
        
        # Get posts by IDs
        recommended_posts = get_posts_by_ids(post_ids)
        
        # If no explicit post IDs, search by keywords
        if not recommended_posts:
            print("No explicit post IDs found, searching by keywords...")
            recommended_posts = search_posts_by_keywords(response_text, limit=3)
            print(f"Found {len(recommended_posts)} posts by keyword search")
        
        # Format recommendations
        recommendations = [format_post_recommendation(post) for post in recommended_posts]
        
        # Format citations
        formatted_citations = []
        for citation in citations:
            if 'retrievedReferences' in citation:
                for ref in citation['retrievedReferences']:
                    location = ref.get('location', {})
                    content = ref.get('content', {}).get('text', '')
                    
                    citation_obj = {
                        'content': content[:200] + '...' if len(content) > 200 else content
                    }
                    
                    # Add source information
                    if 's3Location' in location:
                        s3_uri = location['s3Location'].get('uri', '')
                        # Extract filename from S3 URI
                        if '/' in s3_uri:
                            source_file = s3_uri.split('/')[-1]
                            citation_obj['source'] = source_file
                        else:
                            citation_obj['source'] = 'knowledge-base'
                    else:
                        citation_obj['source'] = 'knowledge-base'
                    
                    formatted_citations.append(citation_obj)
        
        # Build response
        result = {
            'response': response_text,
            'recommendations': recommendations,
            'citations': formatted_citations[:5],  # Limit to 5 citations
            'conversation_id': conversation_id
        }
        
        print(f"Returning response with {len(recommendations)} recommendations and {len(formatted_citations)} citations")
        
        return create_response(200, result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return create_response(500, {
            'error': 'Internal server error',
            'message': str(e)
        })

# For local testing
if __name__ == '__main__':
    # Test event
    test_event = {
        'body': json.dumps({
            'message': 'What is EUC?'
        })
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
