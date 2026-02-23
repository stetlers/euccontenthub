"""
AWS Blog Chat Assistant Lambda Function - WITH AWS DOCS INTEGRATION + SERVICE MAPPER
Uses AWS Bedrock with enhanced search relevance + AWS Documentation API + EUC Service Name Mapping
"""

import json
import os
import boto3
import uuid
import re
import urllib.request
import urllib.parse
from decimal import Decimal
from collections import Counter
from typing import Optional

# Import service mapper and use case matcher
try:
    from euc_service_mapper import EUCServiceMapper
except ImportError as e:
    print(f"WARNING: Failed to import EUCServiceMapper: {e}")
    EUCServiceMapper = None

try:
    from euc_use_case_matcher import EUCUseCaseMatcher
except ImportError as e:
    print(f"WARNING: Failed to import EUCUseCaseMatcher: {e}")
    EUCUseCaseMatcher = None

# Initialize clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-blog-posts')
table = dynamodb.Table(TABLE_NAME)

# Initialize service mapper (module-level, runs during cold start)
service_mapper: Optional['EUCServiceMapper'] = None
try:
    if EUCServiceMapper is not None:
        service_mapper = EUCServiceMapper('euc-service-name-mapping.json')
        service_count = len(service_mapper.services) if hasattr(service_mapper, 'services') else 0
        print(f"INFO: Service mapper initialized successfully with {service_count} services")
    else:
        print("INFO: EUCServiceMapper class not available, service mapping disabled")
except FileNotFoundError as e:
    print(f"ERROR: Service mapping file not found: {e}")
    print("INFO: Service mapping disabled, chat will function with degraded search capabilities")
    service_mapper = None
except json.JSONDecodeError as e:
    print(f"ERROR: Invalid JSON in service mapping file: {e}")
    print("INFO: Service mapping disabled, chat will function with degraded search capabilities")
    service_mapper = None
except Exception as e:
    print(f"ERROR: Failed to initialize service mapper: {e}")
    import traceback
    traceback.print_exc()
    print("INFO: Service mapping disabled, chat will function with degraded search capabilities")
    service_mapper = None

# Initialize use case matcher (module-level, runs during cold start)
use_case_matcher: Optional['EUCUseCaseMatcher'] = None
try:
    if EUCUseCaseMatcher is not None:
        use_case_matcher = EUCUseCaseMatcher('euc-use-case-matcher.json')
        service_count = len(use_case_matcher.services) if hasattr(use_case_matcher, 'services') else 0
        print(f"INFO: Use case matcher initialized successfully with {service_count} services")
    else:
        print("INFO: EUCUseCaseMatcher class not available, use case matching disabled")
except FileNotFoundError as e:
    print(f"ERROR: Use case matcher file not found: {e}")
    print("INFO: Use case matching disabled, chat will function with basic recommendations")
    use_case_matcher = None
except json.JSONDecodeError as e:
    print(f"ERROR: Invalid JSON in use case matcher file: {e}")
    print("INFO: Use case matching disabled, chat will function with basic recommendations")
    use_case_matcher = None
except Exception as e:
    print(f"ERROR: Failed to initialize use case matcher: {e}")
    import traceback
    traceback.print_exc()
    print("INFO: Use case matching disabled, chat will function with basic recommendations")
    use_case_matcher = None

# Bedrock model to use
MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'

# AWS Documentation Search API (official endpoint used by AWS MCP server)
AWS_DOCS_SEARCH_API = 'https://proxy.search.docs.aws.com/search'

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
    Main Lambda handler for chat assistant with AWS docs integration
    
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
        "aws_docs": [
            {
                "title": "...",
                "url": "...",
                "snippet": "..."
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
        
        # Check if query is AWS service-specific
        aws_docs_results = []
        if is_aws_service_query(user_message):
            print("Detected AWS service query, searching AWS docs...")
            aws_docs_results = search_aws_documentation(user_message)
            print(f"Found {len(aws_docs_results)} AWS docs results")
        
        # Get all blog posts from DynamoDB
        all_posts = get_all_posts()
        print(f"Retrieved {len(all_posts)} posts from DynamoDB")
        
        # Pre-filter and score posts for relevance
        relevant_posts = filter_and_score_posts(user_message, all_posts)
        print(f"Filtered to {len(relevant_posts)} relevant posts")
        
        # Detect service renames in query
        rename_context = get_rename_context(user_message, service_mapper)
        
        # Get use case recommendation
        use_case_recommendation = get_use_case_recommendation(user_message, use_case_matcher)
        
        # Get AI recommendations with AWS docs context, rename context, and use case recommendation
        result = get_ai_recommendations(user_message, relevant_posts, all_posts, aws_docs_results, rename_context, use_case_recommendation)
        
        # Add AWS docs to response
        if aws_docs_results:
            result['aws_docs'] = aws_docs_results[:3]  # Top 3 docs
        
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


def is_aws_service_query(query):
    """
    Detect if query is asking about specific AWS services
    
    Returns:
        True if query mentions AWS services or technical concepts
    """
    query_lower = query.lower()
    
    # AWS service indicators
    aws_indicators = [
        'lambda', 's3', 'ec2', 'dynamodb', 'rds', 'cloudformation', 'cloudwatch',
        'iam', 'vpc', 'api gateway', 'cognito', 'bedrock', 'sagemaker',
        'workspaces', 'appstream', 'connect', 'chime',
        'how to', 'configure', 'setup', 'deploy', 'create', 'manage',
        'best practice', 'architecture', 'security', 'cost', 'pricing'
    ]
    
    return any(indicator in query_lower for indicator in aws_indicators)


def search_aws_documentation(query, limit=5):
    """
    Search AWS official documentation using the AWS docs search API
    
    This uses the same API endpoint as the official AWS Documentation MCP server:
    https://github.com/awslabs/mcp/blob/main/src/aws-documentation-mcp-server/awslabs/aws_documentation_mcp_server/server_aws.py
    
    Args:
        query: Search query
        limit: Maximum number of results (default 5)
    
    Returns:
        List of doc results with title, url, snippet
    """
    try:
        # Build request body (matches AWS MCP server format)
        request_body = {
            'textQuery': {
                'input': query,
            },
            'contextAttributes': [
                {'key': 'domain', 'value': 'docs.aws.amazon.com'}
            ],
            'acceptSuggestionBody': 'RawText',
            'locales': ['en_us'],
        }
        
        # Convert request body to JSON
        json_data = json.dumps(request_body).encode('utf-8')
        
        # Make POST request with proper headers
        req = urllib.request.Request(
            AWS_DOCS_SEARCH_API,
            data=json_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Parse results (matches AWS MCP server response format)
        results = []
        suggestions = data.get('suggestions', [])
        
        # EUC service identifiers for relevance filtering
        # Use specific URL patterns to avoid false positives
        euc_url_patterns = [
            '/workspaces/', '/workspaces-', 
            '/appstream', 
            '/workdocs/', '/workdocs-',
            '/chime/', '/chime-',
            '/connect/', '/connect-',
            '/dcv/', '/nice-dcv/',
            '/workspaces-thin-client/'
        ]
        
        # Title keywords (more flexible)
        euc_title_keywords = [
            'workspaces', 'appstream', 'workdocs', 'chime', 'connect',
            'dcv', 'nice dcv', 'thin client'
        ]
        
        for i, suggestion in enumerate(suggestions):
            # Stop if we have enough valid results
            if len(results) >= limit:
                break
                
            if 'textExcerptSuggestion' in suggestion:
                text_suggestion = suggestion['textExcerptSuggestion']
                url = text_suggestion.get('link', '')
                title = text_suggestion.get('title', '')
                
                # Filter out invalid URLs
                # Skip DocC archive URLs (API reference archives that don't work in browsers)
                if '.doccarchive' in url:
                    print(f"INFO: Skipping DocC archive URL: {url}")
                    continue
                
                # Only include URLs that end with .html or are root doc pages (end with /)
                if not (url.endswith('.html') or url.endswith('/')):
                    print(f"INFO: Skipping non-HTML URL: {url}")
                    continue
                
                # RELEVANCE FILTER: Only include docs about EUC services
                # Check URL patterns (strict) or title keywords (flexible)
                url_lower = url.lower()
                title_lower = title.lower()
                
                # Check if URL matches EUC service patterns
                url_matches = any(pattern in url_lower for pattern in euc_url_patterns)
                
                # Check if title contains EUC keywords (with word boundaries to avoid false positives)
                title_matches = False
                for keyword in euc_title_keywords:
                    # Use word boundaries to avoid matching "connect" in "connector"
                    if f' {keyword} ' in f' {title_lower} ' or title_lower.startswith(keyword + ' ') or title_lower.endswith(' ' + keyword):
                        title_matches = True
                        break
                
                is_euc_relevant = url_matches or title_matches
                
                if not is_euc_relevant:
                    print(f"INFO: Skipping non-EUC doc: {title} ({url})")
                    continue
                
                # Extract context (snippet) - prioritize seo_abstract, then abstract, then summary
                context = None
                metadata = text_suggestion.get('metadata', {})
                if 'seo_abstract' in metadata:
                    context = metadata['seo_abstract']
                elif 'abstract' in metadata:
                    context = metadata['abstract']
                elif 'summary' in text_suggestion:
                    context = text_suggestion['summary']
                elif 'suggestionBody' in text_suggestion:
                    context = text_suggestion['suggestionBody']
                
                # Truncate long snippets
                if context and len(context) > 200:
                    context = context[:200] + '...'
                
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': context or ''
                })
        
        print(f"INFO: AWS docs search found {len(results)} EUC-relevant results for query: {query}")
        return results
    
    except Exception as e:
        print(f"ERROR: Failed to search AWS docs: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def expand_query_with_service_names(query, mapper):
    """
    Expand query to include all service name variants
    
    Args:
        query: Original user query
        mapper: Service mapper instance (or None)
    
    Returns:
        {
            'original_query': str,
            'expanded_terms': set,
            'detected_services': list,
            'has_expansion': bool
        }
    """
    query_lower = query.lower()
    original_terms = set(re.findall(r'\b\w+\b', query_lower))
    expanded_terms = set(original_terms)
    detected_services = []
    
    # If mapper not available, return original query
    if mapper is None:
        return {
            'original_query': query,
            'expanded_terms': expanded_terms,
            'detected_services': [],
            'has_expansion': False
        }
    
    try:
        # Check for multi-word service names first (e.g., "WorkSpaces Applications")
        # Try common patterns
        multi_word_patterns = [
            r'workspaces\s+applications?',
            r'appstream\s+2\.0',
            r'workspaces\s+web',
            r'workspaces\s+secure\s+browser',
            r'workspaces\s+thin\s+client',
            r'workspaces\s+core',
            r'nice\s+dcv',
            r'amazon\s+dcv'
        ]
        
        for pattern in multi_word_patterns:
            match = re.search(pattern, query_lower)
            if match:
                service_phrase = match.group()
                # Try to find this service
                all_names = mapper.get_all_names(service_phrase)
                if all_names:
                    current_name = all_names[0]
                    detected_services.append(current_name)
                    # Add all variants
                    for name in all_names:
                        # Add full name
                        expanded_terms.add(name.lower())
                        # Add individual words from name
                        expanded_terms.update(re.findall(r'\b\w+\b', name.lower()))
                    
                    print(f"INFO: Detected service '{service_phrase}' -> expanded to {len(all_names)} variants")
        
        # Check each word individually
        for term in original_terms:
            if len(term) > 2:  # Skip very short words
                all_names = mapper.get_all_names(term)
                if all_names:
                    current_name = all_names[0]
                    if current_name not in detected_services:
                        detected_services.append(current_name)
                        # Add all variants
                        for name in all_names:
                            expanded_terms.add(name.lower())
                            expanded_terms.update(re.findall(r'\b\w+\b', name.lower()))
                        
                        print(f"INFO: Detected service '{term}' -> expanded to {len(all_names)} variants")
        
        has_expansion = len(detected_services) > 0
        
        if has_expansion:
            print(f"INFO: Query expansion: '{query}' -> {len(expanded_terms)} total terms")
            print(f"INFO: Detected services: {detected_services}")
        
        return {
            'original_query': query,
            'expanded_terms': expanded_terms,
            'detected_services': detected_services,
            'has_expansion': has_expansion
        }
    
    except Exception as e:
        print(f"ERROR: Query expansion failed: {e}")
        # Return original query without expansion
        return {
            'original_query': query,
            'expanded_terms': original_terms,
            'detected_services': [],
            'has_expansion': False
        }


def get_rename_context(query, mapper):
    """
    Get rename context if query contains historical service names
    
    Args:
        query: User query
        mapper: Service mapper instance (or None)
    
    Returns:
        {
            'old_name': str,
            'new_name': str,
            'rename_date': str,
            'context_text': str  # Formatted for AI prompt
        }
        or None if no rename detected
    """
    # If mapper not available, return None
    if mapper is None:
        return None
    
    try:
        query_lower = query.lower()
        
        # Check for multi-word service names first (e.g., "AppStream 2.0", "WorkSpaces Web")
        multi_word_patterns = [
            r'appstream\s+2\.0',
            r'appstream\s+2',
            r'workspaces\s+web',
            r'nice\s+dcv',
            r'wsp'
        ]
        
        for pattern in multi_word_patterns:
            match = re.search(pattern, query_lower)
            if match:
                service_phrase = match.group()
                rename_info = mapper.get_rename_info(service_phrase)
                if rename_info:
                    old_name = rename_info['old_name']
                    new_name = rename_info['new_name']
                    rename_date = rename_info['rename_date']
                    
                    print(f"INFO: Rename detected: {old_name} -> {new_name} (renamed {rename_date})")
                    
                    # Format context text for AI prompt
                    context_text = (
                        f"IMPORTANT SERVICE RENAME: {old_name} is now called {new_name} "
                        f"(renamed on {rename_date}). When recommending posts, please mention "
                        f"this rename to help users understand that content about both names "
                        f"refers to the same service."
                    )
                    
                    return {
                        'old_name': old_name,
                        'new_name': new_name,
                        'rename_date': rename_date,
                        'context_text': context_text
                    }
        
        # Check individual words for historical service names
        words = re.findall(r'\b\w+\b', query_lower)
        for word in words:
            if len(word) > 2:  # Skip very short words
                rename_info = mapper.get_rename_info(word)
                if rename_info:
                    old_name = rename_info['old_name']
                    new_name = rename_info['new_name']
                    rename_date = rename_info['rename_date']
                    
                    print(f"INFO: Rename detected: {old_name} -> {new_name} (renamed {rename_date})")
                    
                    # Format context text for AI prompt
                    context_text = (
                        f"IMPORTANT SERVICE RENAME: {old_name} is now called {new_name} "
                        f"(renamed on {rename_date}). When recommending posts, please mention "
                        f"this rename to help users understand that content about both names "
                        f"refers to the same service."
                    )
                    
                    return {
                        'old_name': old_name,
                        'new_name': new_name,
                        'rename_date': rename_date,
                        'context_text': context_text
                    }
        
        # No rename detected
        return None
    
    except Exception as e:
        print(f"ERROR: Rename detection failed: {e}")
        import traceback
        traceback.print_exc()
        return None


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
    Filter and score posts by relevance to query
    NOW WITH SERVICE NAME EXPANSION
    
    Scoring algorithm:
    - Title exact match: +10 points
    - Title keyword match: +5 points per keyword
    - Summary keyword match: +3 points per keyword
    - Tags keyword match: +4 points per keyword
    - Content keyword match: +1 point per keyword
    - Service variant match: Same points as keyword match
    - Domain match (WorkSpaces, AppStream, etc.): +8 points
    - Recent posts (last 6 months): +2 points
    """
    
    query_lower = query.lower()
    
    # Expand query with service names
    expansion_result = expand_query_with_service_names(query, service_mapper)
    expanded_terms = expansion_result['expanded_terms']
    detected_services = expansion_result['detected_services']
    
    # Extract keywords (remove common words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'about', 'how', 'what', 'when', 'where', 
                  'why', 'which', 'who', 'i', 'want', 'need', 'help', 'me', 'my'}
    
    keywords = [w for w in re.findall(r'\b\w+\b', query_lower) if w not in stop_words and len(w) > 2]
    
    print(f"Query keywords: {keywords}")
    print(f"Expanded terms: {len(expanded_terms)} terms (including service variants)")
    
    # Detect domain from query
    detected_domain = detect_domain(query_lower)
    print(f"Detected domain: {detected_domain}")
    
    scored_posts = []
    
    for post in posts:
        score = 0
        
        title = (post.get('title', '') or '').lower()
        summary = (post.get('summary', '') or '').lower()
        tags = (post.get('tags', '') or '').lower()
        content = (post.get('content', '') or '').lower()[:1000]
        
        # Check for exact phrase match in title
        if query_lower in title:
            score += 10
        
        # Score by keyword matches
        for keyword in keywords:
            if keyword in title:
                score += 5
            if keyword in summary:
                score += 3
            if keyword in tags:
                score += 4
            if keyword in content:
                score += 1
        
        # Score by expanded service name variants
        for expanded_term in expanded_terms:
            # Skip if already counted as keyword
            if expanded_term not in keywords:
                if expanded_term in title:
                    score += 5
                if expanded_term in summary:
                    score += 3
                if expanded_term in tags:
                    score += 4
                if expanded_term in content:
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
        
        # Boost recent posts
        date_published = post.get('date_published', '')
        if is_recent_post(date_published):
            score += 2
        
        if score > 0:
            scored_posts.append((score, post))
    
    # Sort by score descending
    scored_posts.sort(reverse=True, key=lambda x: x[0])
    
    # Log top scores
    if scored_posts:
        print(f"Top 5 scores: {[(s, p.get('title', '')[:50]) for s, p in scored_posts[:5]]}")
    
    return [post for score, post in scored_posts[:50]]


def detect_domain(query):
    """Detect which EUC domain the query is about"""
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
        
        post_date = datetime.fromisoformat(date_str.split('T')[0])
        six_months_ago = datetime.now() - timedelta(days=180)
        
        return post_date >= six_months_ago
    except:
        return False


def get_use_case_recommendation(query, matcher):
    """
    Get use case-based service recommendation
    
    Args:
        query: User query
        matcher: Use case matcher instance (or None)
    
    Returns:
        {
            'recommended_service': str,
            'confidence': str,
            'reasoning': str,
            'context_text': str  # Formatted for AI prompt
        }
        or None if no recommendation
    """
    # If matcher not available, return None
    if matcher is None:
        return None
    
    try:
        # Get recommendation
        recommendation = matcher.get_recommendation(query)
        
        if not recommendation or not recommendation.get('recommended_service'):
            return None
        
        service_name = recommendation['recommended_service']
        confidence = recommendation['confidence']
        reasoning = recommendation['reasoning']
        service_details = recommendation.get('service_details', {})
        
        # Only provide recommendation if confidence is medium or high
        if confidence == 'low':
            print(f"INFO: Use case match confidence too low, skipping recommendation")
            return None
        
        print(f"INFO: Use case recommendation: {service_name} (confidence: {confidence})")
        
        # Build context text for AI prompt
        context_text = f"""
USE CASE RECOMMENDATION:
Based on the user's requirements, {service_name} appears to be the most suitable service.

Reasoning: {reasoning}

Best for:
{chr(10).join(f'- {reason}' for reason in service_details.get('best_for', [])[:3])}

When recommending blog posts, prioritize content about {service_name} and explain why this service matches their needs.
"""
        
        # Add important notes if present
        if service_details.get('important_notes'):
            context_text += f"""
Important notes:
{chr(10).join(f'- {note}' for note in service_details['important_notes'])}
"""
        
        return {
            'recommended_service': service_name,
            'confidence': confidence,
            'reasoning': reasoning,
            'context_text': context_text,
            'service_details': service_details
        }
    
    except Exception as e:
        print(f"ERROR: Use case recommendation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_ai_recommendations(user_message, relevant_posts, all_posts, aws_docs_results, rename_context=None, use_case_recommendation=None):
    """
    Use AI to find relevant blog posts and generate response
    NOW WITH AWS DOCS CONTEXT + RENAME CONTEXT
    
    Args:
        user_message: User's query
        relevant_posts: Pre-filtered relevant posts
        all_posts: All posts (for fallback)
        aws_docs_results: AWS documentation search results
        rename_context: Service rename context (optional)
    
    Returns:
        {
            "response": "conversational response",
            "recommendations": [...]
        }
    """
    
    # If no relevant posts found, use fallback
    if not relevant_posts:
        print("No relevant posts found, using fallback search")
        return fallback_search(user_message, all_posts, aws_docs_results)
    
    # Prepare post data for AI
    post_data = []
    for post in relevant_posts[:30]:
        post_data.append({
            'post_id': post.get('post_id', ''),
            'title': post.get('title', ''),
            'summary': (post.get('summary', '') or '')[:200],
            'label': post.get('label', 'Unknown'),
            'tags': post.get('tags', ''),
            'authors': post.get('authors', ''),
            'url': post.get('url', '')
        })
    
    # Build AI prompt with AWS docs context
    system_prompt = """You are the EUC Content Finder, a helpful assistant for the EUC Content Hub. Your job is to help users discover relevant End User Computing (EUC) articles, blogs, and technical content from AWS.

When a user asks a question:
1. If AWS documentation is provided, use it to give accurate technical context
2. Understand their intent and technical level
3. Search for the most relevant posts from the provided list
4. Recommend 3-5 posts that best match their needs
5. Explain briefly why each post is relevant
6. Be conversational, friendly, and encouraging

Focus on EUC topics: Amazon WorkSpaces, AppStream, virtual desktops, DaaS, end-user computing, remote work solutions.

If AWS documentation is provided, reference it to provide authoritative technical context, then recommend blog posts for practical examples and community insights."""

    # Add rename context to system prompt if available
    if rename_context:
        system_prompt += f"\n\n{rename_context['context_text']}"
    
    # Add use case recommendation context if available
    if use_case_recommendation:
        system_prompt += f"\n\n{use_case_recommendation['context_text']}"

    # Add AWS docs context if available
    aws_docs_context = ""
    if aws_docs_results:
        aws_docs_context = f"\n\nAWS Official Documentation (for technical context):\n{json.dumps(aws_docs_results, indent=2)}\n"

    # Add rename notice to user prompt if available
    rename_notice = ""
    if rename_context:
        rename_notice = f"""
SERVICE RENAME ALERT - CRITICAL INFORMATION:
{rename_context['old_name']} was renamed to {rename_context['new_name']} on {rename_context['rename_date']}.

IMPORTANT RESPONSE STRUCTURE:
1. If the user asks a direct question (e.g., "Is X the same as Y?", "What is X?"), answer the question FIRST
2. THEN mention the rename: "{rename_context['old_name']} is now called {rename_context['new_name']}"
3. If it's not a direct question, you can mention the rename naturally in context

Example for "Is WorkSpaces Secure Browser the same as AppStream 2.0?":
GOOD: "No, WorkSpaces Secure Browser and AppStream 2.0 are different services. Note that AppStream 2.0 was recently renamed to WorkSpaces Applications..."
BAD: "AppStream 2.0 was recently renamed to WorkSpaces Applications, so the two services are not the same..."

The user expects the direct answer first, then the context.
"""

    user_prompt = f"""User Query: {user_message}
{rename_notice}{aws_docs_context}
Available Blog Posts (JSON):
{json.dumps(post_data, cls=DecimalEncoder)}

Please recommend 3-5 most relevant posts and provide a helpful conversational response.
If AWS docs were provided, briefly mention the official guidance, then recommend blog posts for practical examples.
IMPORTANT: If a service rename was noted above, follow the response structure guidance (answer direct questions first, then provide rename context).

Respond in JSON format:
{{
    "response": "friendly conversational response (2-3 sentences, follow rename response structure if applicable)",
    "recommendations": [
        {{
            "post_id": "exact post_id from the list",
            "relevance_reason": "1-2 sentences explaining why this post matches their query"
        }}
    ]
}}"""

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
        for rec in ai_result.get('recommendations', [])[:5]:
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
        return fallback_search(user_message, relevant_posts if relevant_posts else all_posts, aws_docs_results)


def extract_json_from_text(text):
    """Extract JSON object from AI response text"""
    try:
        return json.loads(text)
    except:
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
    return None


def fallback_search(query, posts, aws_docs_results=None):
    """Fallback keyword search if AI fails"""
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
        
        if query_lower in title:
            score += 10
        
        for keyword in keywords:
            if keyword in title:
                score += 5
            if keyword in summary:
                score += 3
            if keyword in tags:
                score += 4
        
        if detected_domain:
            domain_keywords = EUC_DOMAINS.get(detected_domain, [])
            for domain_kw in domain_keywords:
                if domain_kw in title:
                    score += 8
                elif domain_kw in summary:
                    score += 6
        
        if score > 0:
            scored_posts.append((score, post))
    
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
    
    response_text = f"I found {len(recommendations)} posts related to your query."
    if aws_docs_results:
        response_text = f"Based on AWS documentation and our content hub, here are {len(recommendations)} relevant posts."
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
