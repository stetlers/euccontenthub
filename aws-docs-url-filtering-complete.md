# AWS Docs URL Filtering Complete

## Date
February 21, 2026

## Summary
Successfully implemented URL filtering in the Chat Lambda to prevent broken AWS documentation links from appearing in chat responses. The Lambda now filters out `.doccarchive` URLs (API reference archives) and non-HTML URLs that don't work in browsers.

## Problem
User reported seeing broken AWS documentation URLs in chat responses, specifically:
- `.doccarchive` URLs (e.g., `https://docs.aws.amazon.com/sdk-for-swift/latest/api/awsappstream.doccarchive/...`)
- These are DocC archive URLs for API references that don't work when opened in a browser

## Solution
Added URL filtering logic to the `search_aws_documentation()` function in `chat_lambda_with_aws_docs.py`:

### Filtering Rules
1. **Skip `.doccarchive` URLs**: These are API reference archives that don't render in browsers
2. **Only include `.html` or `/` URLs**: These are valid documentation pages
3. **Loop through more results**: Changed from `[:limit]` to loop until we have enough valid URLs
4. **Log skipped URLs**: Added logging to track what's being filtered

### Code Changes
```python
# Filter out invalid URLs
if '.doccarchive' in url:
    print(f"INFO: Skipping DocC archive URL: {url}")
    continue

# Only include URLs that end with .html or are root doc pages (end with /)
if not (url.endswith('.html') or url.endswith('/')):
    print(f"INFO: Skipping non-HTML URL: {url}")
    continue
```

## Testing Results

### Direct API Test
Created `test_url_filtering.py` to test the filtering logic:

**Test 1: AppStream 2.0 storage connector**
- ✅ Found 5 valid results
- ✅ Skipped 0 invalid URLs (API returned only valid URLs for this query)

**Test 2: Amazon WorkSpaces configuration**
- ✅ Found 5 valid results
- ✅ All URLs end with `.html`

**Test 3: Lambda function URLs**
- ✅ Found 5 valid results
- ✅ All URLs are valid HTML pages

### Staging Integration Test
Created `test_staging_url_filtering.py` to test the deployed Lambda:

**Test 1: "How do I configure Amazon WorkSpaces?"**
- ✅ AWS docs returned: 3 valid URLs
- ✅ All URLs end with `.html`
- ✅ No `.doccarchive` URLs

**Test 2: "Tell me about AppStream 2.0 storage connector"**
- ✅ AWS docs returned: 3 valid URLs
- ✅ All URLs end with `.html`
- ✅ No `.doccarchive` URLs

**Test 3: "How do I create Lambda function URLs?"**
- ✅ AWS docs returned: 3 valid URLs
- ✅ All URLs end with `.html`
- ✅ No `.doccarchive` URLs

### CloudWatch Logs Verification
Checked CloudWatch logs to confirm filtering is working:

```
INFO: Skipping DocC archive URL: https://docs.aws.amazon.com/sdk-for-swift/latest/api/awsappstream.doccarchive/documentation/awsappstream/appstreamclient/updateapplication(input:)/index.html
INFO: AWS docs search found 5 valid results for query: Tell me about AppStream 2.0
```

```
INFO: Skipping DocC archive URL: https://docs.aws.amazon.com/sdk-for-swift/latest/api/awsappstream.doccarchive/documentation/awsappstream/appstreamclienttypes/stack/storageconnectors/index.html
INFO: AWS docs search found 5 valid results for query: Tell me about AppStream 2.0 storage connector
```

**Confirmation**: The Lambda is actively filtering out `.doccarchive` URLs and only returning valid results.

## Deployment Status

### Staging
- ✅ Deployed to staging Lambda (Feb 21, 2026 at 16:33 UTC)
- ✅ URL filtering working correctly
- ✅ CloudWatch logs show skipped URLs
- ✅ All test queries return valid URLs only
- ✅ No broken links in chat responses

### Production
- ⏳ Ready to deploy
- Waiting for user approval after staging verification

## How It Works

### Before Filtering
1. AWS Docs API returns 100 suggestions
2. Lambda takes first 5 results
3. Some results may be `.doccarchive` URLs (broken in browsers)
4. User sees broken links in chat

### After Filtering
1. AWS Docs API returns 100 suggestions
2. Lambda loops through suggestions
3. Skips `.doccarchive` URLs (logs them)
4. Skips non-HTML URLs
5. Collects 5 valid URLs
6. User only sees working links in chat

## Example Filtered URLs

### Skipped (Invalid)
- `https://docs.aws.amazon.com/sdk-for-swift/latest/api/awsappstream.doccarchive/documentation/awsappstream/appstreamclient/updateapplication(input:)/index.html`
- `https://docs.aws.amazon.com/sdk-for-swift/latest/api/awsappstream.doccarchive/documentation/awsappstream/appstreamclienttypes/stack/storageconnectors/index.html`

### Included (Valid)
- `https://docs.aws.amazon.com/appstream2/latest/developerguide/what-is-appstream.html` ✅
- `https://docs.aws.amazon.com/workspaces/latest/adminguide/amazon-workspaces.html` ✅
- `https://docs.aws.amazon.com/lambda/latest/dg/urls-configuration.html` ✅
- `https://docs.aws.amazon.com/appstream2/` ✅ (root doc page)

## Benefits

1. **No Broken Links**: Users only see working AWS documentation links
2. **Better UX**: All citation links are clickable and functional
3. **Automatic Filtering**: No manual curation needed
4. **Logged for Monitoring**: Skipped URLs are logged for analysis
5. **Flexible**: Can easily adjust filtering rules if needed

## Files Modified

1. `chat_lambda_with_aws_docs.py` - Added URL filtering logic to `search_aws_documentation()`

## Files Created

1. `test_url_filtering.py` - Direct API test with filtering
2. `test_staging_url_filtering.py` - Staging integration test
3. `aws-docs-url-filtering-complete.md` - This summary document

## Verification Steps for User

To verify the fix is working on the staging website:

1. Visit https://staging.awseuccontent.com
2. Open the chat widget (💬 button)
3. Try these queries:
   - "How do I configure Amazon WorkSpaces?"
   - "Tell me about AppStream 2.0 storage connector"
   - "How do I create Lambda function URLs?"
4. Check the AWS Documentation References section
5. Click each [1], [2], [3] link
6. Verify all links open valid AWS documentation pages
7. Verify NO `.doccarchive` URLs appear

## Expected Results

For each query, you should see:
- ✅ AI response with helpful context
- ✅ 📚 AWS Documentation References with [1], [2], [3]
- ✅ All links are clickable and open valid pages
- ✅ No `.doccarchive` URLs
- ✅ All URLs end with `.html` or `/`
- ✅ Blog post recommendations below

## Next Steps

### If Staging Tests Pass
1. Deploy to production:
   ```bash
   python deploy_chat_production.py
   ```

2. Test production endpoint:
   ```bash
   python test_production_chat.py
   ```

3. Verify on production website:
   - Visit https://awseuccontent.com
   - Test same queries in chat widget
   - Verify all links work

### If Issues Found
1. Check CloudWatch logs:
   ```bash
   aws logs tail /aws/lambda/aws-blog-chat-assistant --since 30m --follow
   ```

2. Look for:
   - "Skipping DocC archive URL" messages
   - "AWS docs search found X valid results" messages
   - Any error messages

3. Report specific broken URLs for further filtering

## Monitoring

After production deployment, monitor:
- CloudWatch logs for skipped URLs
- User feedback on link quality
- Any new types of broken URLs
- Response times (should remain <5 seconds)

## Success Criteria

All success criteria met:

1. ✅ URL filtering logic implemented
2. ✅ `.doccarchive` URLs filtered out
3. ✅ Non-HTML URLs filtered out
4. ✅ Deployed to staging Lambda
5. ✅ Direct API tests passing (3/3)
6. ✅ Staging integration tests passing (3/3)
7. ✅ CloudWatch logs show filtering working
8. ✅ All returned URLs are valid
9. ✅ No broken links in test queries
10. ✅ Service mapper still working
11. ✅ Blog recommendations still working

## Conclusion

The URL filtering is working correctly in staging. The Lambda is actively filtering out `.doccarchive` URLs and only returning valid AWS documentation links. All test queries return working links, and CloudWatch logs confirm the filtering is happening.

The user should test on the staging website (https://staging.awseuccontent.com) to verify the fix resolves their issue. If tests pass, the feature is ready for production deployment.
