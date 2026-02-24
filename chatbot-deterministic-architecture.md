# Chatbot Deterministic Architecture Design

**Date:** February 24, 2026  
**Status:** Design Proposal  
**Goal:** Make chatbot responses more deterministic and accurate using AWS Bedrock Knowledge Bases

---

## Current Architecture (Problems)

### Current Flow
```
User Query
    ↓
Service Name Mapper (detects renamed services)
    ↓
Use Case Matcher (matches to EUC use cases)
    ↓
AWS Docs MCP (searches official AWS docs)
    ↓
DynamoDB Posts (filters blog posts)
    ↓
Bedrock Claude Sonnet (generates response)
    ↓
Response to User
```

### Current Problems

1. **Non-Deterministic Responses**
   - Claude Sonnet generates different responses for same query
   - No consistent answer format or structure
   - Hallucination risk when combining multiple data sources

2. **Poor Context Integration**
   - Service mapper, use case matcher, AWS docs, and blog posts are loosely coupled
   - No unified knowledge base
   - Hard to maintain consistency across sources

3. **Limited Control**
   - Can't easily update specific Q&A pairs
   - No way to enforce specific answers for common questions
   - Difficult to track which knowledge source influenced response

4. **Scalability Issues**
   - Every query hits multiple APIs (DynamoDB, AWS Docs, Bedrock)
   - No caching of common queries
   - Expensive for high-traffic scenarios

---

## Proposed Architecture: Bedrock Knowledge Bases + RAG

### Overview

Use **AWS Bedrock Knowledge Bases** (Retrieval Augmented Generation) to create a unified, deterministic knowledge layer that combines:
- Curated Q&A pairs (high priority)
- Service name mappings
- Use case recommendations
- AWS documentation summaries
- Blog post summaries

### Architecture Diagram

```
User Query
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Query Preprocessing Layer                                    │
│ - Intent classification                                      │
│ - Entity extraction (service names, use cases)              │
│ - Query expansion (synonyms, renamed services)              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Bedrock Knowledge Base (Vector Search)                      │
│                                                              │
│ Data Sources (S3 Buckets):                                  │
│ 1. curated-qa/           (Priority: HIGH)                   │
│    - common-questions.md                                    │
│    - service-specific-qa.md                                 │
│    - troubleshooting-qa.md                                  │
│                                                              │
│ 2. service-mappings/     (Priority: HIGH)                   │
│    - service-renames.json → converted to markdown          │
│    - service-descriptions.md                                │
│                                                              │
│ 3. use-cases/            (Priority: MEDIUM)                 │
│    - euc-use-cases.json → converted to markdown            │
│    - use-case-examples.md                                   │
│                                                              │
│ 4. aws-docs-summaries/   (Priority: MEDIUM)                 │
│    - service-overviews.md                                   │
│    - best-practices.md                                      │
│                                                              │
│ 5. blog-summaries/       (Priority: LOW)                    │
│    - post-summaries.md (auto-generated from DynamoDB)       │
│                                                              │
│ Vector Store: Amazon OpenSearch Serverless                  │
│ Embedding Model: amazon.titan-embed-text-v2                 │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Response Generation (Bedrock Agent)                         │
│ - Uses retrieved context from Knowledge Base                │
│ - Applies response templates for consistency                │
│ - Cites sources (Q&A, docs, blog posts)                     │
│ - Model: Claude 3.5 Sonnet with strict instructions        │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Response Post-Processing                                    │
│ - Format recommendations with post IDs                      │
│ - Add AWS docs links                                        │
│ - Include service rename warnings                           │
│ - Add use case suggestions                                  │
└─────────────────────────────────────────────────────────────┘
    ↓
Response to User
```

---

## Implementation Details

### 1. Curated Q&A Pairs (Highest Priority)

Create markdown files with common questions and authoritative answers:

**File: `curated-qa/common-questions.md`**
```markdown
# Common Questions About EUC Content Hub

## Q: What is EUC?
**A:** EUC stands for End User Computing. It refers to AWS services that enable 
end users to access applications and desktops, including Amazon WorkSpaces, 
Amazon AppStream 2.0, Amazon WorkSpaces Web, and Amazon Connect.

**Related Services:**
- Amazon WorkSpaces (formerly Amazon WorkSpaces Core)
- Amazon WorkSpaces Personal (formerly Amazon WorkSpaces)
- Amazon AppStream 2.0
- Amazon Connect

**Recommended Posts:**
- [post_id: abc123] "Getting Started with WorkSpaces Personal"
- [post_id: def456] "AppStream 2.0 Best Practices"

---

## Q: How do I set up Amazon WorkSpaces Personal?
**A:** Amazon WorkSpaces Personal (formerly Amazon WorkSpaces) allows you to 
provision cloud-based desktops for your users. Here's a step-by-step guide:

1. Create a directory (AWS Managed Microsoft AD or AD Connector)
2. Configure network settings (VPC, subnets)
3. Launch WorkSpaces bundles
4. Assign users

**AWS Documentation:**
- [Getting Started with WorkSpaces Personal](https://docs.aws.amazon.com/...)

**Recommended Posts:**
- [post_id: xyz789] "WorkSpaces Personal Setup Guide"
- [post_id: uvw012] "WorkSpaces Networking Best Practices"

---

## Q: What's the difference between WorkSpaces and WorkSpaces Personal?
**A:** Amazon WorkSpaces was renamed to Amazon WorkSpaces Personal in 2024. 
They are the same service. WorkSpaces Personal provides persistent, 
user-assigned virtual desktops.

Amazon WorkSpaces (the new service) is a different offering that provides 
pooled, non-persistent desktops for task workers.

**Service Rename Alert:** If you see posts mentioning "Amazon WorkSpaces" 
published before 2024, they likely refer to what is now called 
"WorkSpaces Personal".

**Recommended Posts:**
- [post_id: rename123] "Understanding the WorkSpaces Rename"
```

**File: `curated-qa/troubleshooting-qa.md`**
```markdown
# Troubleshooting Common Issues

## Q: My WorkSpaces users can't connect
**A:** Common causes and solutions:

1. **Network Issues**
   - Check security group rules (ports 4172, 4195)
   - Verify subnet routing
   - Check NAT gateway configuration

2. **Directory Issues**
   - Verify AD Connector health
   - Check user permissions
   - Validate DNS settings

3. **Client Issues**
   - Update WorkSpaces client
   - Check registration code
   - Verify user credentials

**AWS Documentation:**
- [WorkSpaces Troubleshooting Guide](https://docs.aws.amazon.com/...)

**Recommended Posts:**
- [post_id: trouble123] "Debugging WorkSpaces Connectivity"
```

### 2. Service Mappings as Knowledge

Convert `euc-service-name-mapping.json` to markdown:

**File: `service-mappings/service-renames.md`**
```markdown
# AWS Service Name Changes

## Amazon WorkSpaces → Amazon WorkSpaces Personal
**Rename Date:** 2024  
**Reason:** New "Amazon WorkSpaces" service launched for pooled desktops

**What Changed:**
- Old name: Amazon WorkSpaces
- New name: Amazon WorkSpaces Personal
- Service functionality: Unchanged (persistent, user-assigned desktops)

**Impact on Content:**
- Posts before 2024 mentioning "WorkSpaces" refer to WorkSpaces Personal
- Posts after 2024 need to specify "WorkSpaces Personal" vs "WorkSpaces"

**Related Posts:**
- Filter by: service="workspaces" AND date < 2024-01-01

---

## Amazon AppStream → Amazon AppStream 2.0
**Rename Date:** 2016  
**Reason:** Major version upgrade

**What Changed:**
- Old name: Amazon AppStream
- New name: Amazon AppStream 2.0
- Service functionality: Completely redesigned

**Impact on Content:**
- Posts mentioning "AppStream" without "2.0" are likely outdated
- AppStream 1.0 was deprecated in 2016
```

### 3. Use Cases as Knowledge

Convert `euc-use-case-matcher.json` to markdown:

**File: `use-cases/euc-use-cases.md`**
```markdown
# EUC Use Cases and Recommendations

## Use Case: Remote Work / Work From Home
**Keywords:** remote work, work from home, wfh, remote access, telecommute

**Recommended Services:**
- Amazon WorkSpaces Personal (persistent desktops)
- Amazon WorkSpaces (pooled desktops for task workers)
- Amazon WorkSpaces Web (browser-based access)

**Common Questions:**
- "How do I enable remote work for my team?"
- "What's the best AWS service for remote employees?"
- "How to set up secure remote access?"

**Recommended Posts:**
- [post_id: remote123] "Building a Remote Work Solution with WorkSpaces"
- [post_id: remote456] "Securing Remote Access with WorkSpaces Web"

---

## Use Case: Call Center / Contact Center
**Keywords:** call center, contact center, customer service, support agents

**Recommended Services:**
- Amazon Connect (cloud contact center)
- Amazon WorkSpaces (for agent desktops)
- Amazon Chime SDK (for voice/video)

**Common Questions:**
- "How do I build a cloud contact center?"
- "What AWS services do I need for a call center?"
- "How to integrate WorkSpaces with Connect?"

**Recommended Posts:**
- [post_id: contact123] "Building a Contact Center with Amazon Connect"
- [post_id: contact456] "Integrating WorkSpaces with Connect"
```

### 4. AWS Docs Summaries

Instead of real-time API calls, pre-fetch and summarize key AWS docs:

**File: `aws-docs-summaries/workspaces-personal-overview.md`**
```markdown
# Amazon WorkSpaces Personal - Service Overview

**Source:** https://docs.aws.amazon.com/workspaces/latest/userguide/

**Summary:**
Amazon WorkSpaces Personal is a managed Desktop-as-a-Service (DaaS) solution 
that provides persistent, user-assigned cloud desktops. Each user gets their 
own dedicated WorkSpace that persists across sessions.

**Key Features:**
- Persistent desktops (data saved between sessions)
- User-assigned (1:1 user-to-desktop mapping)
- Multiple bundle types (Windows, Linux, various sizes)
- Integration with Active Directory
- Client apps for Windows, Mac, Linux, iOS, Android, web

**Common Use Cases:**
- Remote work / work from home
- Contractor access
- BYOD (Bring Your Own Device)
- Secure access to corporate resources

**Pricing:**
- Monthly or hourly billing
- Costs vary by bundle type and region
- Additional charges for storage and data transfer

**Getting Started:**
1. Set up directory (AWS Managed AD or AD Connector)
2. Configure VPC and subnets
3. Launch WorkSpaces from bundles
4. Assign to users

**Related Services:**
- Amazon WorkSpaces (pooled desktops)
- Amazon WorkSpaces Web (browser-based)
- Amazon AppStream 2.0 (application streaming)
```

### 5. Blog Post Summaries

Auto-generate from DynamoDB posts:

**File: `blog-summaries/posts-2024-01.md`**
```markdown
# Blog Post Summaries - January 2024

## Post: Getting Started with WorkSpaces Personal
**Post ID:** abc123  
**URL:** https://aws.amazon.com/blogs/...  
**Date:** 2024-01-15  
**Authors:** John Doe, Jane Smith  
**Label:** Technical How-To  

**Summary:**
This post provides a step-by-step guide to setting up Amazon WorkSpaces 
Personal for the first time. It covers directory setup, network configuration, 
bundle selection, and user assignment.

**Key Topics:**
- WorkSpaces Personal setup
- Active Directory integration
- VPC configuration
- Bundle selection

**Relevant For:**
- Users asking about WorkSpaces setup
- Remote work solutions
- Getting started guides

---

## Post: AppStream 2.0 Best Practices
**Post ID:** def456  
**URL:** https://aws.amazon.com/blogs/...  
**Date:** 2024-01-20  
**Authors:** Bob Johnson  
**Label:** Best Practices  

**Summary:**
This post outlines best practices for deploying and managing Amazon AppStream 
2.0 fleets. It covers fleet sizing, image management, user authentication, 
and cost optimization.

**Key Topics:**
- AppStream 2.0 fleet management
- Image builder best practices
- User authentication with SAML
- Cost optimization strategies

**Relevant For:**
- Users asking about AppStream setup
- Application streaming use cases
- Cost optimization questions
```

---

## Bedrock Knowledge Base Configuration

### S3 Bucket Structure

```
s3://euc-content-hub-knowledge-base/
├── curated-qa/
│   ├── common-questions.md
│   ├── service-specific-qa.md
│   ├── troubleshooting-qa.md
│   └── metadata.json
├── service-mappings/
│   ├── service-renames.md
│   ├── service-descriptions.md
│   └── metadata.json
├── use-cases/
│   ├── euc-use-cases.md
│   ├── use-case-examples.md
│   └── metadata.json
├── aws-docs-summaries/
│   ├── workspaces-personal-overview.md
│   ├── workspaces-overview.md
│   ├── appstream-overview.md
│   ├── connect-overview.md
│   └── metadata.json
└── blog-summaries/
    ├── posts-2024-01.md
    ├── posts-2024-02.md
    ├── posts-2023-12.md
    └── metadata.json
```

### Metadata Files (for prioritization)

**File: `curated-qa/metadata.json`**
```json
{
  "priority": "HIGH",
  "description": "Curated Q&A pairs with authoritative answers",
  "update_frequency": "manual",
  "last_updated": "2024-02-24",
  "retrieval_weight": 1.0
}
```

**File: `blog-summaries/metadata.json`**
```json
{
  "priority": "LOW",
  "description": "Auto-generated summaries of blog posts",
  "update_frequency": "daily",
  "last_updated": "2024-02-24",
  "retrieval_weight": 0.3
}
```

### Knowledge Base Settings

```python
knowledge_base_config = {
    "name": "euc-content-hub-kb",
    "description": "Knowledge base for EUC Content Hub chatbot",
    "roleArn": "arn:aws:iam::031421429609:role/BedrockKnowledgeBaseRole",
    "knowledgeBaseConfiguration": {
        "type": "VECTOR",
        "vectorKnowledgeBaseConfiguration": {
            "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
        }
    },
    "storageConfiguration": {
        "type": "OPENSEARCH_SERVERLESS",
        "opensearchServerlessConfiguration": {
            "collectionArn": "arn:aws:aoss:us-east-1:031421429609:collection/euc-kb",
            "vectorIndexName": "euc-content-index",
            "fieldMapping": {
                "vectorField": "embedding",
                "textField": "text",
                "metadataField": "metadata"
            }
        }
    }
}
```

---

## Response Generation with Bedrock Agent

### Agent Configuration

```python
agent_config = {
    "agentName": "euc-content-assistant",
    "description": "AI assistant for EUC content discovery",
    "foundationModel": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "instruction": """
You are an AI assistant for the EUC Content Hub, helping users discover 
AWS End User Computing content.

RESPONSE RULES:
1. Always prioritize curated Q&A answers when available
2. Cite sources for all information (Q&A, AWS docs, blog posts)
3. When mentioning renamed services, include a warning
4. Recommend specific blog posts by post_id
5. Keep responses concise (2-3 paragraphs max)
6. Use bullet points for lists
7. Include "Learn More" section with links

RESPONSE FORMAT:
[Answer to question]

**Related Services:**
- [Service names with rename warnings if applicable]

**Recommended Posts:**
- [Post title] (post_id: abc123)
- [Post title] (post_id: def456)

**AWS Documentation:**
- [Doc title and URL]

**Learn More:**
- [Additional resources]
""",
    "knowledgeBases": [
        {
            "knowledgeBaseId": "KB_ID_HERE",
            "description": "EUC content knowledge base",
            "knowledgeBaseState": "ENABLED"
        }
    ]
}
```

### Query Processing Flow

```python
def process_query_with_kb(user_query):
    """
    Process user query using Bedrock Knowledge Base + Agent
    """
    
    # 1. Preprocess query
    expanded_query = expand_query_with_service_names(user_query, service_mapper)
    
    # 2. Retrieve from Knowledge Base
    kb_response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId='KB_ID',
        retrievalQuery={
            'text': expanded_query
        },
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': 10,
                'overrideSearchType': 'HYBRID'  # Vector + keyword search
            }
        }
    )
    
    # 3. Filter and prioritize results
    prioritized_results = prioritize_kb_results(kb_response['retrievalResults'])
    
    # 4. Generate response with Agent
    agent_response = bedrock_agent_runtime.invoke_agent(
        agentId='AGENT_ID',
        agentAliasId='AGENT_ALIAS_ID',
        sessionId=conversation_id,
        inputText=user_query,
        sessionState={
            'knowledgeBaseConfigurations': [
                {
                    'knowledgeBaseId': 'KB_ID',
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'numberOfResults': 10,
                            'overrideSearchType': 'HYBRID'
                        }
                    }
                }
            ]
        }
    )
    
    # 5. Parse response and extract recommendations
    response_text = extract_response_text(agent_response)
    post_ids = extract_post_ids(response_text)
    
    # 6. Fetch full post details from DynamoDB
    recommended_posts = fetch_posts_by_ids(post_ids)
    
    return {
        'response': response_text,
        'recommendations': recommended_posts,
        'sources': extract_sources(agent_response),
        'conversation_id': conversation_id
    }
```

---

## Integration with Existing Components

### Service Name Mapper Integration

```python
# Convert service mapper to markdown for KB
def generate_service_mapping_markdown():
    """
    Convert euc-service-name-mapping.json to markdown for KB
    """
    with open('euc-service-name-mapping.json') as f:
        mappings = json.load(f)
    
    markdown = "# AWS Service Name Changes\n\n"
    
    for old_name, info in mappings.items():
        markdown += f"## {old_name} → {info['new_name']}\n"
        markdown += f"**Rename Date:** {info.get('rename_date', 'Unknown')}\n"
        markdown += f"**Reason:** {info.get('reason', 'Service evolution')}\n\n"
        markdown += "**What Changed:**\n"
        markdown += f"- Old name: {old_name}\n"
        markdown += f"- New name: {info['new_name']}\n"
        markdown += f"- Service functionality: {info.get('functionality_change', 'Unchanged')}\n\n"
        markdown += "**Impact on Content:**\n"
        markdown += f"- {info.get('content_impact', 'Posts may reference old name')}\n\n"
        markdown += "---\n\n"
    
    return markdown

# Upload to S3
def upload_to_kb_bucket(content, key):
    s3.put_object(
        Bucket='euc-content-hub-knowledge-base',
        Key=key,
        Body=content,
        ContentType='text/markdown'
    )

# Sync to KB
upload_to_kb_bucket(
    generate_service_mapping_markdown(),
    'service-mappings/service-renames.md'
)
```

### Use Case Matcher Integration

```python
# Convert use case matcher to markdown for KB
def generate_use_case_markdown():
    """
    Convert euc-use-case-matcher.json to markdown for KB
    """
    with open('euc-use-case-matcher.json') as f:
        use_cases = json.load(f)
    
    markdown = "# EUC Use Cases and Recommendations\n\n"
    
    for use_case_name, info in use_cases.items():
        markdown += f"## Use Case: {use_case_name}\n"
        markdown += f"**Keywords:** {', '.join(info['keywords'])}\n\n"
        markdown += "**Recommended Services:**\n"
        for service in info['services']:
            markdown += f"- {service}\n"
        markdown += "\n**Common Questions:**\n"
        for question in info.get('common_questions', []):
            markdown += f"- \"{question}\"\n"
        markdown += "\n---\n\n"
    
    return markdown

upload_to_kb_bucket(
    generate_use_case_markdown(),
    'use-cases/euc-use-cases.md'
)
```

### AWS Docs Integration

Instead of real-time API calls, periodically fetch and summarize:

```python
# Periodic job (runs daily)
def sync_aws_docs_to_kb():
    """
    Fetch AWS docs and create summaries for KB
    """
    services = [
        'workspaces-personal',
        'workspaces',
        'appstream',
        'connect',
        'chime'
    ]
    
    for service in services:
        # Search AWS docs
        docs = search_aws_documentation(f"{service} overview")
        
        # Fetch full content
        for doc in docs[:5]:  # Top 5 docs per service
            content = fetch_aws_doc_content(doc['url'])
            
            # Summarize with Claude
            summary = summarize_doc_with_claude(content)
            
            # Upload to KB
            upload_to_kb_bucket(
                summary,
                f'aws-docs-summaries/{service}-{doc["id"]}.md'
            )
```

### Blog Post Integration

Auto-sync from DynamoDB:

```python
# Periodic job (runs daily)
def sync_blog_posts_to_kb():
    """
    Sync blog posts from DynamoDB to KB
    """
    # Get all posts
    posts = get_all_posts()
    
    # Group by month
    posts_by_month = {}
    for post in posts:
        month_key = post['date_published'][:7]  # YYYY-MM
        if month_key not in posts_by_month:
            posts_by_month[month_key] = []
        posts_by_month[month_key].append(post)
    
    # Generate markdown for each month
    for month, month_posts in posts_by_month.items():
        markdown = f"# Blog Post Summaries - {month}\n\n"
        
        for post in month_posts:
            markdown += f"## Post: {post['title']}\n"
            markdown += f"**Post ID:** {post['post_id']}\n"
            markdown += f"**URL:** {post['url']}\n"
            markdown += f"**Date:** {post['date_published']}\n"
            markdown += f"**Authors:** {post['authors']}\n"
            markdown += f"**Label:** {post.get('label', 'N/A')}\n\n"
            markdown += f"**Summary:**\n{post.get('summary', 'No summary available')}\n\n"
            markdown += "---\n\n"
        
        # Upload to KB
        upload_to_kb_bucket(
            markdown,
            f'blog-summaries/posts-{month}.md'
        )
```

---

## Benefits of This Approach

### 1. Deterministic Responses
- Curated Q&A ensures consistent answers for common questions
- Knowledge Base retrieval is deterministic (same query → same context)
- Agent instructions enforce response format

### 2. Better Control
- Easy to update Q&A pairs in S3
- Can version control knowledge base content
- Clear prioritization (curated > docs > blogs)

### 3. Improved Accuracy
- RAG reduces hallucination (grounded in knowledge base)
- Citations show source of information
- Service rename warnings built into knowledge

### 4. Scalability
- Knowledge Base handles vector search efficiently
- Caching at OpenSearch level
- Reduced API calls (no real-time AWS docs search)

### 5. Maintainability
- Markdown files are human-readable
- Easy to add new Q&A pairs
- Auto-sync from DynamoDB for blog posts

---

## Implementation Plan

### Phase 1: Setup Infrastructure (Week 1)
1. Create S3 bucket for knowledge base
2. Set up OpenSearch Serverless collection
3. Create Bedrock Knowledge Base
4. Create Bedrock Agent

### Phase 2: Curate Initial Content (Week 2)
1. Write 20-30 common Q&A pairs
2. Convert service mapper to markdown
3. Convert use case matcher to markdown
4. Create initial AWS docs summaries

### Phase 3: Auto-Sync Jobs (Week 3)
1. Build blog post sync Lambda
2. Build AWS docs sync Lambda
3. Set up daily sync schedule
4. Test knowledge base retrieval

### Phase 4: Update Chat Lambda (Week 4)
1. Replace current logic with KB + Agent
2. Update response format
3. Add source citations
4. Deploy to staging

### Phase 5: Testing & Refinement (Week 5)
1. Test with common queries
2. Measure response consistency
3. Refine agent instructions
4. Add more Q&A pairs based on testing

### Phase 6: Production Deployment (Week 6)
1. Deploy to production
2. Monitor response quality
3. Collect user feedback
4. Iterate on Q&A content

---

## Cost Estimate

### Monthly Costs (assuming 10,000 queries/month)

**Bedrock Knowledge Base:**
- Storage: $0.10/GB/month × 1GB = $0.10
- Retrieval: $0.0004/query × 10,000 = $4.00

**OpenSearch Serverless:**
- OCU (compute): $0.24/hour × 2 OCU × 730 hours = $350.40
- Storage: $0.024/GB/month × 10GB = $0.24

**Bedrock Agent (Claude 3.5 Sonnet):**
- Input tokens: $0.003/1K × 500K tokens = $1.50
- Output tokens: $0.015/1K × 200K tokens = $3.00

**S3 Storage:**
- Standard storage: $0.023/GB × 5GB = $0.12

**Lambda (sync jobs):**
- Invocations: $0.20/million × 0.1 million = $0.02
- Duration: $0.0000166667/GB-second × 10,000 = $0.17

**Total: ~$359/month**

**Cost Optimization:**
- Use smaller OpenSearch OCU (1 OCU = $175/month)
- Cache common queries in DynamoDB
- Reduce sync frequency for blog posts

---

## Monitoring & Metrics

### Key Metrics to Track

1. **Response Consistency**
   - Same query → same answer rate
   - Measure with test suite of 100 common queries

2. **Source Attribution**
   - % of responses citing curated Q&A
   - % of responses citing AWS docs
   - % of responses citing blog posts

3. **User Satisfaction**
   - Thumbs up/down on responses
   - Follow-up question rate
   - Conversation abandonment rate

4. **Knowledge Base Health**
   - Number of Q&A pairs
   - Last sync timestamp
   - Retrieval accuracy (manual review)

5. **Cost Metrics**
   - Cost per query
   - OpenSearch OCU utilization
   - Bedrock token usage

---

## Next Steps

1. **Review this design** with stakeholders
2. **Decide on implementation timeline**
3. **Start with Phase 1** (infrastructure setup)
4. **Create initial Q&A pairs** (20-30 common questions)
5. **Test with staging environment**

---

## Questions to Answer

1. **How many curated Q&A pairs do we need?**
   - Start with 20-30, expand based on usage patterns

2. **How often should we sync blog posts?**
   - Daily is sufficient (posts don't change frequently)

3. **Should we keep AWS Docs MCP for real-time queries?**
   - Yes, as fallback for very specific/new topics not in KB

4. **How do we handle conversation history?**
   - Bedrock Agent handles this automatically with session state

5. **What about multi-turn conversations?**
   - Agent maintains context across turns using session ID

---

## Conclusion

This architecture provides a more deterministic, maintainable, and scalable 
chatbot solution by:
- Using curated Q&A for common questions
- Leveraging Bedrock Knowledge Bases for RAG
- Integrating existing components (service mapper, use case matcher)
- Maintaining AWS docs and blog posts as supplementary knowledge

The key insight is to **prioritize curated content** over generated content, 
while still allowing the AI to synthesize information from multiple sources 
when needed.
