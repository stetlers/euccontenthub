# Builder Crawler Triggers Unnecessary Summary Regeneration

## Problem Statement

The Builder.AWS crawler triggers summary and classification regeneration for ALL Builder articles on every crawl run, even when articles haven't changed. This causes:

1. **Wasted Bedrock API calls** - Regenerating summaries that haven't changed
2. **Slow crawl completion** - Processing hundreds of unchanged articles
3. **Potential summary loss** - If summary Lambda fails, all Builder summaries are cleared
4. **Inconsistent behavior** - AWS Blog crawler only regenerates changed articles

## Current Behavior

### AWS Blog Crawler (Working Correctly) ✅
1. Fetches full article content (first 3000 chars)
2. Compares `old_content` vs `new_content`
3. Only regenerates summary if content actually changed
4. **Result**: Efficient, only processes changed articles

### Builder.AWS Crawler (Problem) ❌
1. Uses sitemap metadata only (no content fetching)
2. Generates template string: `f"Learn more about {title}. Visit the full article..."`
3. Template includes title, which may vary slightly each run
4. Comparison: `old_content != new_content` is TRUE every time
5. **Result**: ALL Builder articles marked as changed, ALL summaries regenerated

## Root Cause Analysis

**File**: `enhanced_crawler_lambda.py`  
**Location**: `BuilderAWSCrawler.extract_metadata_from_sitemap()` (line ~507)

```python
def extract_metadata_from_sitemap(self, url, lastmod):
    """Extract metadata from sitemap URL and lastmod"""
    title = self.extract_title_from_slug(url)
    
    return {
        'url': url,
        'title': title,
        'authors': 'AWS Builder Community',
        'date_published': lastmod,
        'date_updated': lastmod,
        'tags': 'End User Computing, Builder.AWS',
        'content': f"Learn more about {title}. Visit the full article on Builder.AWS for detailed information and insights.",  # ← PROBLEM
        'source': 'builder.aws.com'
    }
```

**Why This Causes Issues:**

1. **Title formatting variations** - Title extraction from slug may produce slightly different results
2. **Template string always regenerated** - Even if article unchanged, template is recreated
3. **String comparison fails** - `old_content != new_content` always TRUE
4. **False positive content changes** - Every article appears changed on every crawl

## Impact

### Current State (Production)
- **Builder articles in DB**: ~200+ articles
- **Articles without summaries**: Many (exact count unknown)
- **Crawl frequency**: Manual (triggered by user)
- **Summary Lambda batch size**: 10 posts per invocation
- **Summary Lambda behavior**: Does NOT auto-chain for remaining posts

### What Happens on Each Crawl
1. Builder crawler runs
2. Marks ALL ~200 articles as "content changed"
3. Clears ALL summaries and labels
4. Invokes summary Lambda for 20 batches (200 posts / 10 per batch)
5. Summary Lambda processes 10 posts, then stops
6. **Result**: Only 10 summaries regenerated, 190 articles left without summaries

### User Impact
- Users see Builder articles without summaries
- Summaries disappear after crawl runs
- Inconsistent data quality
- Poor user experience

## Evidence

### Code Analysis

**AWS Blog Crawler** (lines 237-257):
```python
# Check if content changed
old_content = existing_item.get('content', '')
new_content = metadata['content']  # Real content from article
if old_content != new_content:
    content_changed = True
```

**Builder Crawler** (lines 518-537):
```python
# Check if content changed
old_content = existing_item.get('content', '')
new_content = metadata['content']  # Template string with title
if old_content != new_content:
    content_changed = True
```

Both use same logic, but Builder's `new_content` is always a freshly generated template string.

## Proposed Solutions

### Option A: Make Builder Content Static (Quick Fix)

**Approach**: Remove variable data from template string

**Implementation**:
```python
'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.'
```

**Pros**:
- ✅ Quick fix (1 line change)
- ✅ Prevents false content changes
- ✅ No additional API calls needed
- ✅ Can deploy and test in staging immediately

**Cons**:
- ❌ Generic content (no article-specific info)
- ❌ Less useful for summary generation
- ❌ Doesn't solve root issue (no real content)

**Estimated Time**: 15 minutes (change + test + deploy)

---

### Option B: Use lastmod Date for Change Detection (Recommended)

**Approach**: Compare `date_updated` instead of `content` for Builder articles

**Implementation**:
```python
def save_to_dynamodb(self, metadata):
    # Check if item exists
    content_changed = False
    try:
        response = self.table.get_item(Key={'post_id': post_id})
        if 'Item' in response:
            existing_item = response['Item']
            
            # For Builder articles, use lastmod date instead of content
            old_date = existing_item.get('date_updated', '')
            new_date = metadata['date_updated']
            if old_date != new_date:
                content_changed = True
                print(f"  Article updated (lastmod changed)")
        else:
            content_changed = True  # New post
    except:
        content_changed = True  # New post
```

**Pros**:
- ✅ Accurate change detection (uses sitemap lastmod)
- ✅ No additional API calls needed
- ✅ Respects Builder.AWS update timestamps
- ✅ Efficient (only regenerates when article actually updated)
- ✅ Maintains template content for context

**Cons**:
- ❌ Relies on Builder.AWS maintaining accurate lastmod dates
- ❌ Won't detect changes if lastmod not updated

**Estimated Time**: 1 hour (change + test + deploy + validate)

---

### Option C: Fetch Actual Builder Content (Best Long-Term)

**Approach**: Use Selenium crawler to extract real article content

**Implementation**:
1. Modify `builder_selenium_crawler.py` to extract content
2. Store first 3000 chars like AWS Blog crawler
3. Use real content for change detection
4. Generate better summaries from actual content

**Pros**:
- ✅ Most accurate change detection
- ✅ Better summaries (based on real content)
- ✅ Consistent with AWS Blog crawler behavior
- ✅ Future-proof solution

**Cons**:
- ❌ Requires Selenium/ECS infrastructure
- ❌ Slower crawl (must fetch each article)
- ❌ Higher AWS costs (ECS runtime)
- ❌ More complex implementation

**Estimated Time**: 4-6 hours (modify crawler + test + deploy)

**Note**: `builder_selenium_crawler.py` already exists but may not be in use. This would require updating and deploying it.

---

### Option D: Hybrid Approach (Balanced)

**Approach**: Combine Option A + Option B

**Implementation**:
1. Use static content template (Option A)
2. Add lastmod date comparison (Option B)
3. Only regenerate when lastmod changes

**Pros**:
- ✅ Quick to implement
- ✅ Accurate change detection
- ✅ No false positives
- ✅ Efficient processing

**Cons**:
- ❌ Still uses generic content
- ❌ Summaries not as good as real content

**Estimated Time**: 1 hour

---

## Recommendation

**Start with Option B (lastmod date comparison)** because:

1. **Accurate** - Builder.AWS maintains lastmod dates in sitemap
2. **Efficient** - No additional API calls or infrastructure
3. **Quick** - Can implement and test in staging today
4. **Safe** - Can test in staging before production
5. **Reversible** - Easy to rollback if issues occur

**Future Enhancement**: Consider Option C (fetch real content) if:
- Summary quality becomes a priority
- Selenium infrastructure is already available
- Budget allows for additional ECS costs

## Testing Plan

### Phase 1: Staging Testing (Option B)

1. **Modify Code**:
   - Update `BuilderAWSCrawler.save_to_dynamodb()` in `enhanced_crawler_lambda.py`
   - Add lastmod date comparison logic
   - Keep template content as-is

2. **Deploy to Staging**:
   ```bash
   python deploy_lambda.py crawler staging
   ```

3. **Test Scenarios**:
   - Run crawler twice without sitemap changes → Should NOT regenerate summaries
   - Manually update a post's lastmod in staging table → Should regenerate that post only
   - Check CloudWatch logs for "Article updated (lastmod changed)" messages
   - Verify summary count before/after crawl

4. **Validate**:
   - Count posts needing summaries before crawl
   - Run crawler
   - Count posts needing summaries after crawl
   - Should be 0 if no articles changed

### Phase 2: Production Deployment

1. **Deploy to Production** (after staging validation):
   ```bash
   python deploy_lambda.py crawler production
   ```

2. **Monitor**:
   - Run crawler
   - Check CloudWatch logs
   - Verify only changed articles regenerate summaries
   - Monitor Bedrock API usage (should decrease significantly)

## Success Criteria

- [ ] Builder crawler only regenerates summaries for changed articles
- [ ] Unchanged articles keep existing summaries
- [ ] CloudWatch logs show accurate change detection
- [ ] Bedrock API usage decreases (fewer unnecessary calls)
- [ ] Summary count remains stable across crawls
- [ ] User experience improves (consistent summaries)

## Related Issues

- **Related to**: #18 (if it mentions summary issues)
- **Depends on**: #19 (Staging support - COMPLETE)
- **Blocks**: Efficient crawler operations

## Priority

**HIGH** - This issue causes:
- Wasted AWS costs (Bedrock API calls)
- Poor user experience (missing summaries)
- Data inconsistency
- Inefficient crawler operations

## Labels

- bug
- crawler
- enhancement
- high-priority

---

**Status**: Ready for implementation  
**Recommended Solution**: Option B (lastmod date comparison)  
**Estimated Time**: 1 hour (with staging testing)  
**Risk**: Low (can test in staging first)
