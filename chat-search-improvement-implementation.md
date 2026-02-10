# Chat Search Relevance Improvement - Implementation

## Date
2026-02-10

## Problem
Chat assistant returns irrelevant results for domain-specific queries.

**Example**:
- Query: "WorkSpaces applications"
- Current: Returns posts from unrelated domains
- Expected: Returns posts specifically about Amazon WorkSpaces applications

## Solution Implemented
Improved in-memory search with intelligent scoring algorithm (Phase 1 quick fix)

## Changes Made

### File: `chat_lambda_improved.py`

**New Features**:

1. **Pre-filtering with Relevance Scoring**
   - Filters all posts before sending to Bedrock
   - Only sends top 50 most relevant posts to AI
   - Reduces token usage and improves AI focus

2. **Intelligent Scoring Algorithm**
   - Title exact match: +10 points
   - Title keyword match: +5 points per keyword
   - Summary keyword match: +3 points per keyword
   - Tags keyword match: +4 points per keyword (tags are curated)
   - Content keyword match: +1 point per keyword
   - Domain match (WorkSpaces, AppStream, etc.): +8 points
   - Recent posts (last 6 months): +2 points

3. **Domain Detection**
   - Automatically detects EUC domains from query
   - Boosts posts from detected domain
   - Domains: WorkSpaces, AppStream, WorkSpaces Web, Thin Client, DCV, WorkDocs, Chime, Connect

4. **Stop Words Filtering**
   - Removes common words (the, a, and, etc.) from keyword matching
   - Focuses on meaningful terms

5. **Improved Fallback Search**
   - Uses same scoring algorithm if Bedrock fails
   - More accurate than previous simple keyword matching

## Key Improvements

### Before
```python
# Old approach
posts = get_all_posts()  # All posts
post_data = posts[:350]  # Just take first 350
# Send to Bedrock with no filtering
```

### After
```python
# New approach
all_posts = get_all_posts()  # All posts
relevant_posts = filter_and_score_posts(query, all_posts)  # Score and filter
post_data = relevant_posts[:30]  # Top 30 most relevant
# Send pre-filtered posts to Bedrock
```

## Expected Results

**For query "WorkSpaces applications"**:
- ✅ Posts with "WorkSpaces" in title get +5 points per keyword + +8 domain boost
- ✅ Posts with "applications" in title get +5 points
- ✅ Posts with both terms in title get high scores
- ✅ Irrelevant posts get 0 points and are filtered out
- ✅ Only top 30-50 relevant posts sent to Bedrock

**Improvements**:
- 80%+ relevant results (vs ~50% before)
- Faster response (fewer posts to process)
- Lower cost (fewer tokens to Bedrock)
- Better AI responses (focused context)

## Deployment Steps

### 1. Test Locally (Optional)
```bash
# Create test event
python test_chat_lambda.py
```

### 2. Deploy to Staging
```bash
python deploy_lambda.py chat staging
```

### 3. Test in Staging
- Visit https://staging.awseuccontent.com
- Open chat widget
- Test queries:
  - "WorkSpaces applications"
  - "AppStream 2.0 setup"
  - "WorkSpaces Web security"
  - "DCV streaming"

### 4. Deploy to Production
```bash
python deploy_lambda.py chat production
```

### 5. Monitor
- Check CloudWatch logs for scoring output
- Gather user feedback
- Monitor chat usage metrics

## Testing Checklist

- [ ] Deploy to staging
- [ ] Test "WorkSpaces applications" query
- [ ] Test "AppStream" query
- [ ] Test "WorkSpaces Web" query
- [ ] Test generic query like "remote work"
- [ ] Verify results are relevant
- [ ] Check response time (should be < 3 seconds)
- [ ] Deploy to production
- [ ] Monitor for 24 hours
- [ ] Gather user feedback

## Rollback Plan

If issues occur:

**Staging**:
```bash
# Staging uses $LATEST, just redeploy old version
aws lambda update-function-code --function-name aws-blog-chat-assistant \
  --zip-file fileb://chat_lambda_old.zip
```

**Production**:
```bash
# Update alias to previous version
aws lambda update-alias --function-name aws-blog-chat-assistant \
  --name production --function-version <previous-version>
```

## Future Enhancements (Phase 2)

After validating this improvement, consider:

1. **Bedrock Knowledge Bases**
   - Vector search with embeddings
   - Semantic similarity matching
   - Better than keyword matching
   - Cost: ~$50-100/month

2. **Add Internal SA Guide**
   - Once NDA-cleared content is ready
   - Create Knowledge Base with public posts + SA guide
   - Unified search across all content

3. **Analytics**
   - Track query patterns
   - Measure result relevance
   - Identify content gaps

## Success Metrics

Track these metrics after deployment:

1. **Relevance**: User feedback on result quality
2. **Response Time**: Chat response latency
3. **Coverage**: % of queries that return relevant results
4. **Usage**: Chat usage frequency

**Targets**:
- 80%+ relevant results
- < 3 second response time
- 2x increase in chat usage

## Related Files

- `chat_lambda_improved.py` - New implementation
- `chat_lambda_code/chat_lambda.py` - Current production code
- `github-issue-chat-search-relevance.md` - Original issue documentation
- `deploy_lambda.py` - Deployment script

## Notes

- Current Lambda: `aws-blog-chat-assistant`
- Handler: `lambda_function.lambda_handler` (will need to rename file)
- Model: Claude 3 Haiku
- Timeout: 30 seconds (should be sufficient)
- Memory: 512 MB (may need to increase if loading all posts is slow)
