# Summary Generator Best Practices

## Critical Rule: Small Batches, Many Invocations

**Always use small batch sizes with multiple invocations to avoid timeouts.**

### Recommended Settings

- **Batch Size**: 5 posts per batch
- **Invocation Type**: Event (async)
- **Delay Between Batches**: 2 seconds

### Why Small Batches?

1. **Bedrock API Latency**: Each summary generation takes 2-5 seconds
2. **Content Size**: Posts contain up to 3000 characters that Bedrock must analyze
3. **Lambda Timeout**: 15-minute maximum execution time
4. **Reliability**: Smaller batches are more resilient to transient errors
5. **Progress Tracking**: Easier to monitor and debug

### Calculation

```
Posts Needing Summaries: N
Batch Size: 5
Number of Batches: ceil(N / 5)
Estimated Time: Number of Batches * 1-2 minutes
```

### Example

**Bad (Times Out):**
```python
# 115 posts / 50 per batch = 3 batches
# Each batch takes 4-8 minutes with 3000 chars per post
# Risk of timeout!
lambda_client.invoke(
    FunctionName='aws-blog-summary-generator:production',
    Payload=json.dumps({'batch_size': 50})
)
```

**Also Bad (Still Times Out):**
```python
# 115 posts / 10 per batch = 12 batches
# Each batch takes 2-4 minutes with 3000 chars per post
# Still risks timeout with large content!
lambda_client.invoke(
    FunctionName='aws-blog-summary-generator:production',
    Payload=json.dumps({'batch_size': 10})
)
```

**Good (Completes Successfully):**
```python
# 115 posts / 5 per batch = 23 batches
# Each batch takes 1-2 minutes
# Reliable completion even with 3000 chars per post
for i in range(23):
    lambda_client.invoke(
        FunctionName='aws-blog-summary-generator:production',
        InvocationType='Event',
        Payload=json.dumps({'batch_size': 5})
    )
    time.sleep(2)
```

### Scripts

Use these scripts for summary generation:

- `generate_summaries_small_batches.py` - Production with small batches
- `generate_missing_summaries_prod.py` - OLD (uses batch_size=50, DO NOT USE)

### Monitoring

```bash
# Watch summary generation progress
aws logs tail /aws/lambda/aws-blog-summary-generator --follow

# Check how many posts still need summaries
aws dynamodb scan --table-name aws-blog-posts \
  --filter-expression "attribute_not_exists(summary) OR summary = :empty" \
  --expression-attribute-values '{":empty":{"S":""}}' \
  --select COUNT
```

### Classifier Lambda

The same rule applies to the classifier Lambda:

- **Batch Size**: 5 posts per batch
- **Invocation Type**: Event (async)
- **Delay Between Batches**: 2 seconds

### Auto-Invocation from Crawler

The crawler automatically invokes summary and classifier Lambdas after crawling. Ensure the crawler uses small batch sizes:

```python
# In enhanced_crawler_lambda.py
batch_size = 5  # Small batch size for posts with up to 3000 chars
num_batches = (posts_needing_summaries + batch_size - 1) // batch_size

for i in range(num_batches):
    lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='Event',
        Payload=json.dumps({'batch_size': batch_size})
    )
    time.sleep(2)
```

### Historical Context

**Issue #26 (2026-02-12)**: 
- Summary generation with batch_size=50 timed out, leaving 64 posts without summaries
- Reduced to batch_size=10, but still timed out with posts containing up to 3000 characters
- Final solution: batch_size=5 provides reliable completion
- Key insight: Bedrock must analyze up to 3000 characters per post, requiring smaller batches

**Lesson**: Always prefer reliability over speed. With large content (3000 chars), batch_size=5 ensures completion.
