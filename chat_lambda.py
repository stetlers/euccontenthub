"""
AWS Blog Chat Assistant Lambda Function - IMPROVED VERSION
Uses AWS Bedrock with enhanced search relevance
"""

import json
import os
import boto3
import uuid
import re
from decimal import Decimal
from collections import Counter

# Initialize clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')
table = dynamodb.Table(TABLE_NAME)

# Bedrock model to use
MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'

# EUC domain keywords for better filtering
EUC_DOMAINS = {
    'workspaces': ['workspaces', 'workspace', 'virtual desktop', 'vdi', 'daas'],
    'appstream': ['appstream', 'app stream', 'application streaming'],
    'workspaces_web': ['workspaces web', 'workspace web', 'web access'],
    'workspaces_thin_client': ['thin client', 'thinclient', 'zero client'],
    'dcv': ['dcv', 'nice dcv', 'streaming protocol'],
    'workdocs': ['workdocs', 'work docs', 'document collaboration'],
    'chime': ['chime', 'video conferencing'],
    'connect': ['connect', 'contact center'],
    'end_user_computing': ['euc', 'end user computing', 'end-user computing', 'remote work', 'hybrid work']
}


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
        all_posts = get_all_posts()
        print(f"Retrieved {len(all_posts)} posts from DynamoDB")
        
        # IMPROVED: Pre-filter and score posts for relevance
        relevant_posts = filter_and_score_posts(user_message, all_posts)
        print(f"Filtered to {len(relevant_posts)} relevant posts")
        
        # Get AI recommendations using only relevant posts
        result = get_ai_recommendations(user_message, relevant_posts, all_posts)
        
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


def filter_and_score_posts(query, posts):
    """
    IMPROVED: Filter and score posts by relevance to query
    
    Scoring algorithm:
    - Title exact match: +10 points
    - Title keyword match: +5 points per keyword
    - Summary keyword match: +3 points per keyword
    - Tags keyword match: +4 points per keyword
    - Content keyword match: +1 point per keyword
    - Domain match (WorkSpaces, AppStream, etc.): +8 points
    - Recent posts (last 6 months): +2 points
    
    Args:
        query: User's search query
        posts: All posts from DynamoDB
    
    Returns:
        List of (score, post) tuples, sorted by score descending
    """
    
    query_lower = query.lower()
    
    # Extract keywords (remove common words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'about', 'how', 'what', 'when', 'where', 
                  'why', 'which', 'who', 'i', 'want', 'need', 'help', 'me', 'my'}
    
    keywords = [w for w in re.findall(r'\b\w+\b', query_lower) if w not in stop_words and len(w) > 2]
    
    print(f"Query keywords: {keywords}")
    
    # Detect domain from query
    detected_domain = detect_domain(query_lower)
    print(f"Detected domain: {detected_domain}")
    
    scored_posts = []
    
    for post in posts:
        score = 0
        
        title = (post.get('title', '') or '').lower()
        summary = (post.get('summary', '') or '').lower()
        tags = (post.get('tags', '') or '').lower()
        content = (post.get('content', '') or '').lower()[:1000]  # First 1000 chars
        
        # Check for exact phrase match in title (highest priority)
        if query_lower in title:
            score += 10
        
        # Score by keyword matches
        for keyword in keywords:
            # Title matches (high weight)
            if keyword in title:
                score += 5
            
            # Summary matches (medium weight)
            if keyword in summary:
                score += 3
            
            # Tags matches (high weight - tags are curated)
            if keyword in tags:
                score += 4
            
            # Content matches (low weight - content is long)
            if keyword in content:
                score += 1
        
        # Domain-specific boost
        if detected_domain:
            domain_keywords = EUC_DOMAINS.get(detected_domain, [])
            for domain_kw in domain_keywords:
                if domain_kw in title:
                    score += 8
                elif domain_kw in summary:
                    score += 6
                elif domain_kw in tags:
                    score += 7
        
        # Boost recent posts (last 6 months)
        date_published = post.get('date_published', '')
        if is_recent_post(date_published):
            score += 2
        
        # Only include posts with some relevance
        if score > 0:
            scored_posts.append((score, post))
    
    # Sort by score descending
    scored_posts.sort(reverse=True, key=lambda x: x[0])
    
    # Log top scores for debugging
    if scored_posts:
        print(f"Top 5 scores: {[(s, p.get('title', '')[:50]) for s, p in scored_posts[:5]]}")
    
    # Return top 50 posts (enough for AI to choose from, but not overwhelming)
    return [post for score, post in scored_posts[:50]]


def detect_domain(query):
    """
    Detect which EUC domain the query is about
    
    Returns:
        Domain key (e.g., 'workspaces', 'appstream') or None
    """
    
    for domain, keywords in EUC_DOMAINS.items():
        for keyword in keywords:
            if keyword in query:
                return domain
    
    return None


def is_recent_post(date_str):
    """Check if post is from last 6 months"""
    try:
        from datetime import datetime, timedelta
        
        if not date_str:
            return False
        
        # Parse date (format: YYYY-MM-DD or similar)
        post_date = datetime.fromisoformat(date_str.split('T')[0])
        six_months_ago = datetime.now() - timedelta(days=180)
        
        return post_date >= six_months_ago
    
    except:
        return False


def get_ai_recommendations(user_message, relevant_posts, all_posts):
    """
    Use AI to find relevant blog posts and generate response
    
    Args:
        user_message: User's query
        relevant_posts: Pre-filtered relevant posts (top 50)
        all_posts: All posts (for fallback)
    
    Returns:
        {
            "response": "conversational response",
            "recommendations": [...]
        }
    """
    
    # If no relevant posts found, use fallback
    if not relevant_posts:
        print("No relevant posts found, using fallback search")
        return fallback_search(user_message, all_posts)
    
    # Prepare post data for AI (use pre-filtered relevant posts)
    post_data = []
    for post in relevant_posts[:30]:  # Limit to top 30 for token efficiency
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
2. Search for the most relevant posts from the provided list (already pre-filtered for relevance)
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

Available Blog Posts (already filtered for relevance - JSON):
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
            post = next((p for p in all_posts if p.get('post_id') == post_id), None)
            
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
        return fallback_search(user_message, relevant_posts if relevant_posts else all_posts)


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
    IMPROVED: Fallback keyword search if AI fails
    Uses the same scoring algorithm as filter_and_score_posts
    
    Args:
        query: User's search query
        posts: List of posts to search
    
    Returns:
        Response with keyword-matched posts
    """
    
    # Use the same scoring algorithm
    scored_posts = []
    query_lower = query.lower()
    
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'about', 'how', 'what', 'when', 'where', 
                  'why', 'which', 'who', 'i', 'want', 'need', 'help', 'me', 'my'}
    
    keywords = [w for w in re.findall(r'\b\w+\b', query_lower) if w not in stop_words and len(w) > 2]
    detected_domain = detect_domain(query_lower)
    
    for post in posts:
        score = 0
        title = (post.get('title', '') or '').lower()
        summary = (post.get('summary', '') or '').lower()
        tags = (post.get('tags', '') or '').lower()
        
        # Exact phrase match
        if query_lower in title:
            score += 10
        
        # Keyword matches
        for keyword in keywords:
            if keyword in title:
                score += 5
            if keyword in summary:
                score += 3
            if keyword in tags:
                score += 4
        
        # Domain boost
        if detected_domain:
            domain_keywords = EUC_DOMAINS.get(detected_domain, [])
            for domain_kw in domain_keywords:
                if domain_kw in title:
                    score += 8
                elif domain_kw in summary:
                    score += 6
        
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
            'relevance_reason': f'Matches your search for "{query}" (relevance score: {score})'
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
