# GitHub Issue: Improve Chat Assistant Search Relevance

## Issue Title
Chat assistant returns irrelevant results - needs better search/indexing

## Labels
- `enhancement`
- `ai`
- `chat`
- `search`

## Priority
Medium-High (affects user experience but not blocking)

## Problem Description

The chat assistant is returning irrelevant results when users ask domain-specific questions. 

**Example**:
- Query: "WorkSpaces applications"
- Expected: Posts specifically about Amazon WorkSpaces applications
- Actual: Returns posts from unrelated domains that don't mention WorkSpaces

**Root Cause**: The current implementation likely uses simple keyword matching or basic semantic search without proper filtering/ranking, causing poor relevance in results.

## Current Implementation

Based on AGENTS.md:
- Uses AWS Bedrock (Claude Sonnet)
- "Context-aware responses using post database"
- Implementation in `chat_lambda.py` (not in local repo)

**Suspected Current Approach**:
1. User asks question
2. Lambda scans/queries DynamoDB table
3. Passes all/some posts to Bedrock with user question
4. Bedrock generates response based on provided context

**Problems with Current Approach**:
- No semantic search/vector similarity
- No relevance ranking
- May be passing too many irrelevant posts to Bedrock
- Limited by Bedrock context window (can't pass all posts)
- No domain-specific filtering

## Proposed Solutions

### Option 1: Amazon Bedrock Knowledge Bases (Recommended)
**Best for**: Production-ready, managed solution with minimal code

**How it works**:
1. Create Bedrock Knowledge Base backed by OpenSearch Serverless
2. Sync DynamoDB posts to Knowledge Base (via S3 or direct)
3. Knowledge Base automatically creates vector embeddings
4. Chat queries use Retrieve and Generate (RAG) API
5. Bedrock handles semantic search, ranking, and response generation

**Pros**:
- ✅ Fully managed (no infrastructure to maintain)
- ✅ Built-in vector search with embeddings
- ✅ Automatic relevance ranking
- ✅ Handles chunking and indexing
- ✅ Native Bedrock integration
- ✅ Supports metadata filtering (by source, date, tags)
- ✅ Can update incrementally (add new posts without reindexing all)

**Cons**:
- ❌ Additional AWS cost (OpenSearch Serverless + embeddings)
- ❌ Requires data sync process (DynamoDB → Knowledge Base)
- ❌ Learning curve for Knowledge Base setup

**Implementation Steps**:
1. Create Bedrock Knowledge Base with OpenSearch Serverless
2. Create S3 bucket for post data
3. Create Lambda to sync DynamoDB posts to S3 (JSON/text format)
4. Configure Knowledge Base to use S3 as data source
5. Update chat Lambda to use Knowledge Base Retrieve and Generate API
6. Add sync trigger (EventBridge rule to sync new posts)

**Estimated Effort**: 2-3 days
**Cost**: ~$50-100/month (OpenSearch Serverless + embeddings)

---

### Option 2: Amazon OpenSearch Service with Vector Search
**Best for**: More control over search, existing OpenSearch experience

**How it works**:
1. Set up OpenSearch Service cluster
2. Create index with vector field for embeddings
3. Generate embeddings for posts using Bedrock Embeddings
4. Index posts in OpenSearch with vectors
5. Chat queries use k-NN vector search to find relevant posts
6. Pass top results to Bedrock for response generation

**Pros**:
- ✅ Full control over search logic
- ✅ Advanced filtering and aggregations
- ✅ Can combine vector + keyword search (hybrid)
- ✅ Powerful query DSL
- ✅ Good for complex search requirements

**Cons**:
- ❌ More infrastructure to manage (cluster sizing, updates)
- ❌ Higher cost than Knowledge Bases
- ❌ More complex implementation
- ❌ Need to manage embedding generation
- ❌ Need to handle index updates

**Implementation Steps**:
1. Create OpenSearch Service domain
2. Create index with k-NN vector field
3. Create Lambda to generate embeddings (Bedrock Titan Embeddings)
4. Index all posts with embeddings
5. Update chat Lambda to query OpenSearch
6. Add indexing trigger for new posts

**Estimated Effort**: 3-5 days
**Cost**: ~$100-200/month (OpenSearch cluster)

---

### Option 3: Improved In-Memory Search (Quick Fix)
**Best for**: Immediate improvement without infrastructure changes

**How it works**:
1. Load all posts from DynamoDB
2. Use better keyword matching (fuzzy, stemming)
3. Score posts by relevance (TF-IDF or simple scoring)
4. Filter by metadata (tags, source)
5. Pass top N posts to Bedrock

**Pros**:
- ✅ No new infrastructure
- ✅ Quick to implement (1-2 days)
- ✅ No additional cost
- ✅ Easy to test and iterate

**Cons**:
- ❌ Still limited by keyword matching (no semantic understanding)
- ❌ Doesn't scale well (loads all posts into memory)
- ❌ Less accurate than vector search
- ❌ Limited by Lambda memory/timeout

**Implementation Steps**:
1. Update chat Lambda to load all posts
2. Implement scoring algorithm:
   - Keyword matching in title (high weight)
   - Keyword matching in summary (medium weight)
   - Keyword matching in tags (high weight)
   - Keyword matching in content (low weight)
3. Filter by metadata if query mentions specific services
4. Sort by score, take top 10-20 posts
5. Pass to Bedrock with improved prompt

**Estimated Effort**: 1-2 days
**Cost**: $0 (no new services)

---

### Option 4: Amazon Kendra (Enterprise Search)
**Best for**: Enterprise-grade search with ML-powered relevance

**How it works**:
1. Create Kendra index
2. Configure DynamoDB as data source
3. Kendra automatically indexes and ranks
4. Chat queries use Kendra Query API
5. Pass results to Bedrock for natural language response

**Pros**:
- ✅ Best-in-class relevance (ML-powered)
- ✅ Handles natural language queries
- ✅ Built-in connectors for many data sources
- ✅ Automatic relevance tuning

**Cons**:
- ❌ Most expensive option (~$810/month minimum)
- ❌ Overkill for this use case
- ❌ Complex pricing model

**Not Recommended**: Too expensive for community site

---

## Recommendation

**Phase 1 (Immediate)**: Implement Option 3 (Improved In-Memory Search)
- Quick win to improve relevance
- No infrastructure changes
- Can deploy this week

**Phase 2 (Long-term)**: Migrate to Option 1 (Bedrock Knowledge Bases)
- Best balance of cost, performance, and maintainability
- Fully managed solution
- Proper semantic search with vectors
- Implement after validating Phase 1 improvements

## Success Metrics

After implementation, measure:
1. **Relevance**: User feedback on result quality
2. **Response Time**: Chat response latency
3. **Coverage**: % of queries that return relevant results
4. **User Engagement**: Chat usage frequency

**Target Improvements**:
- 80%+ of queries return relevant results (vs current ~50%?)
- Response time < 3 seconds
- Increased chat usage by 2x

## Testing Plan

1. Create test queries for common domains:
   - "WorkSpaces applications"
   - "AppStream 2.0 setup"
   - "WorkSpaces Web security"
   - "DCV streaming"
2. Compare results before/after implementation
3. Test in staging first
4. Gather user feedback in production

## Related Issues

- Issue #20: Chat agent improvements (if exists)
- Issue #7: Admin portal (could include chat analytics)

## Additional Context

**Current Chat Lambda Location**: `aws-blog-chat-assistant` (AWS Lambda)
**DynamoDB Table**: `aws-blog-posts` (production), `aws-blog-posts-staging` (staging)
**Bedrock Model**: Claude Sonnet

**Data Available for Search**:
- `title` - Post title
- `summary` - AI-generated summary
- `content` - First 3000 chars of post
- `tags` - Comma-separated tags
- `authors` - Post authors
- `source` - aws.amazon.com or builder.aws.com
- `label` - Content type classification
- `date_published` - Publication date

## Next Steps

1. Review and prioritize this issue
2. Decide on implementation approach (Phase 1 vs direct to Phase 2)
3. Create implementation plan
4. Test in staging
5. Deploy to production
6. Monitor metrics and gather feedback
