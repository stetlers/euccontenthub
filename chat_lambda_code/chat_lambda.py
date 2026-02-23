"""
AWS Blog Chat Assistant Lambda Function
Uses AWS Bedrock to help users discover relevant blog posts
"""

import json
import os
import boto3
import uuid
from decimal import Decimal

# Initialize clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')
table = dynamodb.Table(TABLE_NAME)

# Bedrock model to use
MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert DynamoDB Decimal types to JSON"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    """
    Main Lambda handler for chat assistant
    
    Input:
    {
        "message": "I want to learn about serverless",
        "conversation_id": "uuid-v4" (optional)
    }
    
    Output:
    {
        "response": "Here are some great posts about serverless...",
        "recommendations": [
            {
                "post_id": "...",
                "title": "...",
                "summary": "...",
                "label": "...",
                "url": "...",
                "relevance_reason": "..."
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
        
        # Get all blog posts from DynamoDB
        posts = get_all_posts()
        print(f"Retrieved {len(posts)} posts from DynamoDB")
        
        # Get AI recommendations
        result = get_ai_recommendations(user_message, posts)
        
        # Add conversation ID
        result['conversation_id'] = conversation_id
        
        return create_response(200, result)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return create_response(500, {
            'error': 'Internal server error',
            'message': str(e)
        })


def get_all_posts():
    """Fetch all blog posts from DynamoDB"""
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        return items
    
    except Exception as e:
        print(f"Error fetching posts: {str(e)}")
        return []


def get_ai_recommendations(user_message, posts):
    """
    Use AI to find relevant blog posts and generate response
    
    Args:
        user_message: User's query
        posts: List of all blog posts
    
    Returns:
        {
            "response": "conversational response",
            "recommendations": [...]
        }
    """
    
    # Prepare post data for AI (limit to essential fields)
    post_data = []
    for post in posts[:350]:  # Limit to avoid token limits
        post_data.append({
            'post_id': post.get('post_id', ''),
            'title': post.get('title', ''),
            'summary': (post.get('summary', '') or '')[:200],  # Truncate long summaries
            'label': post.get('label', 'Unknown'),
            'tags': post.get('tags', ''),
            'authors': post.get('authors', ''),
            'url': post.get('url', '')
        })
    
    # Build AI prompt
    system_prompt = """You are the EUC Content Finder, a helpful assistant for the EUC Content Hub. Your job is to help users discover relevant End User Computing (EUC) articles, blogs, and technical content from AWS.

When a user asks a question:
1. Understand their intent and technical level
2. Search for the most relevant posts from the provided list
3. Recommend 3-5 posts that best match their needs
4. Explain briefly why each post is relevant
5. Be conversational, friendly, and encouraging
6. If no perfect match exists, suggest they propose a community article

Focus on EUC topics: Amazon WorkSpaces, AppStream, virtual desktops, DaaS, end-user computing, remote work solutions.

Categories available:
- Announcement: New releases, features, events
- Best Practices: Patterns, recommendations, architecture
- Curation: Collections, guides, event summaries
- Customer Story: Real-world use cases
- Technical How-To: Step-by-step tutorials with code
- Thought Leadership: Industry trends, future outlook

Always provide specific post recommendations. If you can't find highly relevant posts, suggest the closest matches and mention that users can propose new community articles if they can't find what they need."""

    user_prompt = f"""User Query: {user_message}

Available Blog Posts (JSON):
{json.dumps(post_data, cls=DecimalEncoder)}

Please recommend 3-5 most relevant posts and provide a helpful conversational response.

Respond in JSON format:
{{
    "response": "friendly conversational response to the user (2-3 sentences)",
    "recommendations": [
        {{
            "post_id": "exact post_id from the list",
            "relevance_reason": "1-2 sentences explaining why this post matches their query"
        }}
    ]
}}

Important: Only include post_id and relevance_reason in recommendations. I will fetch the full post details."""

    try:
        # Call Bedrock API
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        }
        
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        ai_text = response_body['content'][0]['text']
        
        print(f"AI Response: {ai_text}")
        
        # Extract JSON from response
        ai_result = extract_json_from_text(ai_text)
        
        if not ai_result:
            raise Exception("Failed to parse AI response")
        
        # Enrich recommendations with full post data
        recommendations = []
        for rec in ai_result.get('recommendations', [])[:5]:  # Limit to 5
            post_id = rec.get('post_id')
            post = next((p for p in posts if p.get('post_id') == post_id), None)
            
            if post:
                recommendations.append({
                    'post_id': post.get('post_id', ''),
                    'title': post.get('title', ''),
                    'summary': post.get('summary', ''),
                    'label': post.get('label', 'Unknown'),
                    'url': post.get('url', ''),
                    'relevance_reason': rec.get('relevance_reason', 'Relevant to your query')
                })
        
        return {
            'response': ai_result.get('response', 'Here are some posts that might help!'),
            'recommendations': recommendations
        }
    
    except Exception as e:
        print(f"Error calling Bedrock: {str(e)}")
        
        # Fallback to keyword search
        return fallback_search(user_message, posts)


def extract_json_from_text(text):
    """Extract JSON object from AI response text"""
    try:
        # Try direct JSON parse
        return json.loads(text)
    except:
        # Try to find JSON in text
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
    
    return None


def fallback_search(query, posts):
    """
    Fallback keyword search if AI fails
    
    Args:
        query: User's search query
        posts: List of all posts
    
    Returns:
        Response with keyword-matched posts
    """
    
    query_lower = query.lower()
    keywords = query_lower.split()
    
    # Score posts by keyword matches
    scored_posts = []
    for post in posts:
        score = 0
        title = (post.get('title', '') or '').lower()
        summary = (post.get('summary', '') or '').lower()
        tags = (post.get('tags', '') or '').lower()
        
        for keyword in keywords:
            if keyword in title:
                score += 3
            if keyword in summary:
                score += 2
            if keyword in tags:
                score += 1
        
        if score > 0:
            scored_posts.append((score, post))
    
    # Sort by score and take top 5
    scored_posts.sort(reverse=True, key=lambda x: x[0])
    top_posts = scored_posts[:5]
    
    recommendations = []
    for score, post in top_posts:
        recommendations.append({
            'post_id': post.get('post_id', ''),
            'title': post.get('title', ''),
            'summary': post.get('summary', ''),
            'label': post.get('label', 'Unknown'),
            'url': post.get('url', ''),
            'relevance_reason': f'Matches your search for "{query}"'
        })
    
    response_text = f"I found {len(recommendations)} posts related to your query about {query}."
    if not recommendations:
        response_text = f"I couldn't find posts specifically about '{query}', but you can browse all posts or try a different search term."
    
    return {
        'response': response_text,
        'recommendations': recommendations
    }


def create_response(status_code, body):
    """Create API Gateway response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }
