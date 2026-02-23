# Chat Lambda AWS Docs Integration

## Overview

Enhanced the EUC Content Hub chat assistant to integrate with AWS official documentation. When users ask AWS service-specific questions, the assistant now:

1. Searches AWS official documentation for authoritative technical context
2. Searches the blog post database for community content and tutorials
3. Combines both sources to provide comprehensive answers

## Architecture

```
User Query: "How to configure WorkSpaces MFA?"
    ↓
┌─────────────────────────────────────────┐
│  Chat Lambda (Enhanced)                 │
│                                         │
│  1. Detect AWS Service Query            │
│     ✓ Contains: "WorkSpaces", "configure"│
│                                         │
│  2. Search AWS Docs API                 │
│     → GET docs.aws.amazon.com/search    │
│     ← Official MFA documentation        │
│                                         │
│  3. Search Blog Posts (DynamoDB)        │
│     → Scan aws-blog-posts table         │
│     ← Community tutorials               │
│                                         │
│  4. AI Processing (Bedrock)             │
│     → Combine AWS docs + blog posts     │
│     ← Generate response                 │
└─────────────────────────────────────────┘
    ↓
Response:
{
  "response": "According to AWS docs, WorkSpaces supports MFA...",
  "aws_docs": [
    {
      "title": "WorkSpaces MFA Configuration",
      "url": "https://docs.aws.amazon.com/...",
      "snippet": "..."
    }
  ],
  "recommendations": [
    {
      "title": "Step-by-step MFA Setup Guide",
      "url": "https://aws.amazon.com/blogs/...",
      "relevance_reason": "Practical tutorial with screenshots"
    }
  ]
}
```

## Key Features

### 1. AWS Service Detection

Automatically detects queries about AWS services:
- Service names: Lambda, S3, WorkSpaces, AppStream, etc.
- Action keywords: configure, setup, deploy, create, manage
- Technical terms: architecture, best practice, security, cost

### 2. AWS Documentation Search

Uses the official AWS documentation search API:
- Endpoint: `https://docs.aws.amazon.com/search/doc-search.html`
- Returns: Title, URL, snippet
- Limit: Top 5 results (configurable)

### 3. Enhanced AI Context

The AI now receives:
- AWS official documentation (authoritative technical context)
- Blog posts from content hub (practical examples)
- User query and intent

This allows for responses like:
> "According to AWS documentation, WorkSpaces supports MFA through AWS Directory Service. Here are some community posts with step-by-step setup guides..."

## Files

### Core Implementation
- `chat_lambda_with_aws_docs.py` - Enhanced Lambda function
- `deploy_chat_with_aws_docs.py` - Deployment script
- `test_chat_with_aws_docs.py` - Test suite

### Key Functions

**`is_aws_service_query(query)`**
- Detects if query is about AWS services
- Returns: `True` if AWS-related, `False` otherwise

**`search_aws_documentation(query, limit=5)`**
- Searches AWS docs API
- Returns: List of `{title, url, snippet}`

**`get_ai_recommendations(user_message, relevant_posts, all_posts, aws_docs_results)`**
- Enhanced to include AWS docs context
- Generates response combining official docs + blog posts

## Deployment

### To Staging

```bash
python deploy_chat_with_aws_docs.py
```

This will:
1. Create deployment package (zip)
2. Update Lambda function code
3. Update staging alias to $LATEST
4. Verify deployment

### Testing

Run automated tests:
```bash
python test_chat_with_aws_docs.py
```

Test single query:
```bash
python test_chat_with_aws_docs.py --single
```

### To Production

After testing in staging:
```bash
# 1. Publish new version
aws lambda publish-version --function-name aws-blog-chat-assistant

# 2. Update production alias
aws lambda update-alias \
  --function-name aws-blog-chat-assistant \
  --name production \
  --function-version <version-number>
```

## Frontend Integration

The response now includes an `aws_docs` field:

```javascript
// Example response
{
  "response": "Here's what I found...",
  "aws_docs": [
    {
      "title": "Amazon WorkSpaces MFA",
      "url": "https://docs.aws.amazon.com/...",
      "snippet": "Configure multi-factor authentication..."
    }
  ],
  "recommendations": [
    // Blog posts as before
  ]
}
```

### Display AWS Docs Separately

Update `chat-widget.js` to display AWS docs:

```javascript
// Add AWS docs section
if (data.aws_docs && data.aws_docs.length > 0) {
  responseHtml += '<div class="aws-docs-section">';
  responseHtml += '<h4>📚 AWS Official Documentation</h4>';
  
  data.aws_docs.forEach(doc => {
    responseHtml += `
      <div class="aws-doc-item">
        <a href="${doc.url}" target="_blank">${doc.title}</a>
        <p>${doc.snippet}</p>
      </div>
    `;
  });
  
  responseHtml += '</div>';
}
```

## Test Scenarios

### Scenario 1: AWS Service Query
**Input:** "How do I configure Amazon WorkSpaces for multi-factor authentication?"

**Expected:**
- ✓ AWS docs results (3-5 official docs)
- ✓ Blog post recommendations (3-5 community posts)
- ✓ Response mentions both official docs and community content

### Scenario 2: General EUC Query
**Input:** "What are the best practices for virtual desktop deployment?"

**Expected:**
- ✗ No AWS docs (too general)
- ✓ Blog post recommendations
- ✓ Response focuses on community content

### Scenario 3: Specific Technical Query
**Input:** "How to setup AppStream 2.0 image builder?"

**Expected:**
- ✓ AWS docs results (official setup guide)
- ✓ Blog post recommendations (tutorials)
- ✓ Response combines both sources

## Benefits

1. **Authoritative Context** - Users get official AWS guidance
2. **Practical Examples** - Community posts provide real-world tutorials
3. **Better Answers** - AI has more context to work with
4. **Reduced Hallucination** - Official docs ground the AI's responses
5. **Comprehensive Coverage** - Both official and community perspectives

## Limitations

1. **API Rate Limits** - AWS docs API may have rate limits (not documented)
2. **Network Latency** - Additional HTTP request adds ~200-500ms
3. **Relevance** - AWS docs search may return generic results for specific queries
4. **No Caching** - Each query hits the API (could add caching later)

## Future Enhancements

1. **Caching** - Cache AWS docs results in DynamoDB (TTL: 24 hours)
2. **Fallback** - If AWS docs API fails, continue with blog posts only
3. **Filtering** - Filter AWS docs by service (WorkSpaces, AppStream, etc.)
4. **Recommendations** - Use AWS docs recommendation API for related content
5. **Analytics** - Track which queries trigger AWS docs vs blog-only

## Monitoring

Check CloudWatch logs for:
- AWS docs API errors
- Query detection accuracy
- Response times
- User satisfaction (via feedback)

## Rollback

If issues occur:

```bash
# Revert staging to previous version
aws lambda update-alias \
  --function-name aws-blog-chat-assistant \
  --name staging \
  --function-version <previous-version>
```

## Questions?

- AWS docs API endpoint correct? (Test manually)
- Rate limits on AWS docs API? (Monitor CloudWatch)
- Should we cache results? (Depends on usage patterns)
- Frontend changes needed? (Yes, to display AWS docs separately)
