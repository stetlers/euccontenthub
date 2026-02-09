# Design Document: Builder.AWS Crawler Change Detection Fix

## Overview

This design addresses the issue where the Builder.AWS crawler unnecessarily regenerates summaries for all ~200 articles on every crawl run. The root cause is that the crawler generates a content template string during metadata extraction, which varies slightly on each run, causing the content comparison to always detect changes.

The solution implements proper change detection using lastmod dates from the sitemap XML, ensuring summaries are only regenerated when articles actually update. This approach is consistent with how the AWS Blog crawler handles change detection and will significantly reduce Bedrock API usage while preserving existing summaries.

## Architecture

### Current Architecture (Problem)

```
BuilderAWSCrawler.crawl_all_posts()
  ↓
extract_metadata_from_sitemap(url, lastmod)
  ↓ Generates: "Builder.AWS article. Visit the full article..."
  ↓ (Static template, but stored as content)
  ↓
save_to_dynamodb(metadata)
  ↓
Compare old content vs new content
  ↓ ALWAYS DIFFERENT (template regenerated)
  ↓
Clear summary field → Trigger regeneration
```

**Problem**: The content template is static text, but it's regenerated on every crawl, causing string comparison to fail.

### Proposed Architecture (Solution)

```
BuilderAWSCrawler.crawl_all_posts()
  ↓
extract_metadata_from_sitemap(url, lastmod)
  ↓ Generates static template (no variables)
  ↓ Extracts lastmod date
  ↓
save_to_dynamodb(metadata)
  ↓
Compare old lastmod vs new lastmod
  ↓ ONLY DIFFERENT if article updated
  ↓
If changed: Clear summary → Trigger regeneration
If unchanged: Preserve summary → Skip regeneration
```

**Solution**: Use lastmod date comparison instead of content comparison for change detection.

## Components and Interfaces

### Modified Components

#### 1. BuilderAWSCrawler.extract_metadata_from_sitemap()

**Current Implementation**:
```python
def extract_metadata_from_sitemap(self, url, lastmod):
    title = self.extract_title_from_slug(url)
    
    return {
        'url': url,
        'title': title,
        'authors': 'AWS Builder Community',
        'date_published': lastmod,
        'date_updated': lastmod,
        'tags': 'End User Computing, Builder.AWS',
        'content': 'Builder.AWS article. Visit the full article on Builder.AWS for detailed information and insights.',
        'source': 'builder.aws.com'
    }
```

**Proposed Changes**:
- Content template remains static (no changes needed - already static)
- Ensure lastmod is properly passed through to save_to_dynamodb()
- No functional changes to this method

#### 2. BuilderAWSCrawler.save_to_dynamodb()

**Current Implementation** (lines 625-700):
```python
def save_to_dynamodb(self, metadata):
    # ... existing code ...
    
    # Check if item exists
    content_changed = False
    try:
        response = self.table.get_item(Key={'post_id': post_id})
        if 'Item' in response:
            self.posts_updated += 1
            existing_item = response['Item']
            
            # PROBLEM: Compares content strings (always different)
            old_content = existing_item.get('content', '')
            new_content = metadata['content']
            if old_content != new_content:
                content_changed = True
                print(f"  Content changed - will regenerate summary")
            else:
                print(f"  Article unchanged")
```

**Proposed Changes**:
```python
def save_to_dynamodb(self, metadata):
    # ... existing code ...
    
    # Check if item exists
    content_changed = False
    try:
        response = self.table.get_item(Key={'post_id': post_id})
        if 'Item' in response:
            self.posts_updated += 1
            existing_item = response['Item']
            
            # SOLUTION: Compare lastmod dates instead of content
            old_lastmod = existing_item.get('date_updated', '')
            new_lastmod = metadata['date_updated']
            if old_lastmod != new_lastmod:
                content_changed = True
                print(f"  Article updated (lastmod changed: {old_lastmod} → {new_lastmod})")
            else:
                content_changed = False
                print(f"  Article unchanged (lastmod: {new_lastmod})")
```

**Key Changes**:
1. Replace `old_content` comparison with `old_lastmod` comparison
2. Replace `new_content` comparison with `new_lastmod` comparison
3. Update log messages to show lastmod dates instead of generic "content changed"
4. Preserve all other logic (summary clearing, counter increments, etc.)

### Unchanged Components

#### 1. AWSBlogCrawler
- No changes needed
- Already uses proper content comparison
- Serves as reference implementation

#### 2. DynamoDB Schema
- No schema changes required
- `date_updated` field already exists and stores lastmod
- No new fields needed

#### 3. Summary Generator Lambda
- No changes needed
- Already triggered correctly by crawler
- Processes posts with empty summary field

#### 4. Classifier Lambda
- No changes needed
- Already triggered correctly by summary generator

## Data Models

### DynamoDB Post Record (Builder.AWS)

**Existing Fields** (no changes):
```python
{
    'post_id': 'builder-{slug}',           # Primary key
    'url': 'https://builder.aws.com/...',
    'title': 'Article Title',
    'authors': 'AWS Builder Community',
    'date_published': '2024-01-15',        # ISO 8601 from sitemap lastmod
    'date_updated': '2024-01-15',          # ISO 8601 from sitemap lastmod
    'tags': 'End User Computing, Builder.AWS',
    'content': 'Builder.AWS article. Visit the full article...',  # Static template
    'summary': 'AI-generated summary',     # Empty if needs regeneration
    'label': 'Technical How-To',           # Classification
    'label_confidence': 0.95,
    'source': 'builder.aws.com',
    'last_crawled': '2024-01-20T10:30:00'
}
```

**Change Detection Logic**:
- **Before Fix**: Compare `content` field (always different due to template regeneration)
- **After Fix**: Compare `date_updated` field (only different if article updated)

### Sitemap XML Structure

```xml
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://builder.aws.com/articles/article-slug</loc>
    <lastmod>2024-01-15</lastmod>
  </url>
</urlset>
```

**Extraction**:
- `loc` → `metadata['url']`
- `lastmod` → `metadata['date_updated']` and `metadata['date_published']`

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Static Content Template Consistency

*For any* Builder.AWS article URL, calling extract_metadata_from_sitemap() multiple times should produce identical content template strings.

**Validates: Requirements 1.1, 1.2**

### Property 2: Lastmod Date Extraction and Storage

*For any* Builder.AWS article in the sitemap with a lastmod date, the crawler should extract that date and store it in both the `date_published` and `date_updated` fields in DynamoDB.

**Validates: Requirements 2.1, 2.2, 2.4**

### Property 3: Change Detection Based on Lastmod Comparison

*For any* existing Builder.AWS article with a stored date_updated value, when the crawler processes it:
- If the new lastmod date differs from the stored date_updated, the article should be marked as changed (content_changed = True)
- If the new lastmod date equals the stored date_updated, the article should be marked as unchanged (content_changed = False)

**Validates: Requirements 3.1, 3.2, 3.3**

### Property 4: Summary Field Preservation for Unchanged Articles

*For any* Builder.AWS article where content_changed is False, the DynamoDB update should not modify the summary field, and the posts_needing_summaries counter should not increment.

**Validates: Requirements 3.4, 4.1, 4.2**

### Property 5: Summary Field Clearing for Changed Articles

*For any* Builder.AWS article where content_changed is True, the DynamoDB update should set the summary field to empty string, and the posts_needing_summaries counter should increment by one.

**Validates: Requirements 3.5, 4.3, 4.4**

### Property 6: Accurate Counter Reporting

*For any* crawl run, the following invariants should hold:
- posts_processed = posts_created + posts_updated
- posts_needing_summaries = posts_created + (number of changed articles)
- All counters should be non-negative integers

**Validates: Requirements 5.2, 5.3, 5.4, 5.5**

### Property 7: Backward Compatibility with Legacy Data

*For any* existing Builder.AWS article without a date_updated field, the crawler should:
- Successfully process the article without errors
- Mark it as changed (content_changed = True)
- Add the date_updated field from the sitemap to the DynamoDB record
- Clear the summary field and increment posts_needing_summaries

**Validates: Requirements 6.1, 6.2, 6.3**

## Error Handling

### Sitemap Parsing Errors

**Scenario**: Sitemap XML is malformed or inaccessible

**Handling**:
- Catch XML parsing exceptions in `get_article_sitemaps()` and `crawl_all_posts()`
- Log error with sitemap URL
- Continue processing other sitemaps
- Return partial results with error count

**Code Pattern**:
```python
try:
    root = ET.fromstring(response.text)
    # ... process sitemap ...
except Exception as e:
    print(f"Error processing sitemap {sitemap_url}: {e}")
    continue  # Skip to next sitemap
```

### Missing Lastmod Date

**Scenario**: Sitemap entry lacks lastmod element

**Handling**:
- Use current timestamp as fallback
- Log warning about missing lastmod
- Continue processing article
- Mark as changed (conservative approach)

**Code Pattern**:
```python
lastmod = url_elem.find('ns:lastmod', namespace)
if lastmod is not None:
    date = lastmod.text
else:
    date = datetime.utcnow().isoformat()
    print(f"  Warning: No lastmod for {url}, using current time")
```

### DynamoDB Access Errors

**Scenario**: DynamoDB table unavailable or permission denied

**Handling**:
- Catch boto3 exceptions in `save_to_dynamodb()`
- Log error with post_id and exception details
- Return False to indicate save failure
- Continue processing other articles
- Include error count in final results

**Code Pattern**:
```python
try:
    self.table.update_item(...)
    return True
except Exception as e:
    print(f"Error saving to DynamoDB: {e}")
    return False
```

### Legacy Data Without date_updated

**Scenario**: Existing post lacks date_updated field

**Handling**:
- Treat missing field as empty string in comparison
- Empty string != new lastmod → marks as changed
- Update adds date_updated field
- Summary regenerated (safe conservative approach)

**Code Pattern**:
```python
old_lastmod = existing_item.get('date_updated', '')  # Returns '' if missing
new_lastmod = metadata['date_updated']
if old_lastmod != new_lastmod:  # '' != '2024-01-15' → True
    content_changed = True
```

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests**: Focus on specific examples, edge cases, and error conditions
- Test specific date comparison scenarios
- Test missing lastmod handling
- Test legacy data migration
- Test error conditions (malformed XML, missing fields)

**Property Tests**: Verify universal properties across all inputs
- Test change detection logic with random dates
- Test summary preservation across multiple crawl runs
- Test backward compatibility with various data states

### Property-Based Testing Configuration

**Library**: Use `hypothesis` for Python property-based testing

**Configuration**:
- Minimum 100 iterations per property test
- Each test references its design document property
- Tag format: **Feature: builder-crawler-change-detection, Property {number}: {property_text}**

### Test Scenarios

#### Unit Test Scenarios

1. **First Crawl (New Article)**
   - Article doesn't exist in DynamoDB
   - Should create new record with lastmod
   - Should mark as needing summary
   - Should increment posts_created counter

2. **Second Crawl (Unchanged Article)**
   - Article exists with lastmod='2024-01-15'
   - Sitemap has lastmod='2024-01-15'
   - Should mark as unchanged
   - Should preserve existing summary
   - Should NOT increment posts_needing_summaries

3. **Third Crawl (Changed Article)**
   - Article exists with lastmod='2024-01-15'
   - Sitemap has lastmod='2024-01-20'
   - Should mark as changed
   - Should clear summary field
   - Should increment posts_needing_summaries

4. **Legacy Data (Missing date_updated)**
   - Article exists without date_updated field
   - Should treat as changed
   - Should add date_updated field
   - Should regenerate summary

5. **Missing Lastmod in Sitemap**
   - Sitemap entry lacks lastmod element
   - Should use current timestamp
   - Should log warning
   - Should continue processing

#### Property Test Scenarios

1. **Property 1: Static Content Template**
   - Generate random article URLs
   - Extract metadata twice
   - Assert content templates are identical

2. **Property 3: Change Detection**
   - Generate random pairs of (old_date, new_date)
   - Test change detection logic
   - Assert: changed = (old_date != new_date)

3. **Property 4: Summary Preservation**
   - Generate random articles with summaries
   - Simulate unchanged crawl (same lastmod)
   - Assert: summary field unchanged

4. **Property 7: Backward Compatibility**
   - Generate random articles without date_updated
   - Simulate crawl with new lastmod
   - Assert: date_updated field added, marked as changed

### Staging Environment Testing

**Test Plan** (from issue-20-testing-plan.md):

1. **Deploy to Staging**
   ```bash
   python deploy_lambda.py crawler staging
   ```

2. **First Crawl Run**
   - Trigger crawler in staging
   - Verify posts created/updated
   - Record posts_needing_summaries count
   - Verify summaries generated

3. **Second Crawl Run (Critical Test)**
   - Trigger crawler again immediately
   - **Expected**: posts_needing_summaries = 0
   - **Expected**: All articles show "Article unchanged"
   - **Expected**: Existing summaries preserved
   - **Expected**: CloudWatch logs show lastmod comparisons

4. **Verify Results**
   - Check DynamoDB staging table
   - Verify summary fields not empty
   - Verify date_updated fields populated
   - Check CloudWatch logs for accurate reporting

5. **Production Deployment**
   - Only deploy if all staging tests pass
   - Monitor first production crawl closely
   - Verify Bedrock API usage decreases

### Success Criteria

- ✅ Second crawl run shows "Article unchanged" for unchanged posts
- ✅ Existing summaries preserved across crawl runs
- ✅ `posts_needing_summaries` is 0 when no articles changed
- ✅ CloudWatch logs show accurate change detection
- ✅ Bedrock API usage decreases significantly
- ✅ All property tests pass with 100+ iterations
- ✅ All unit tests pass
- ✅ Staging tests pass before production deployment
