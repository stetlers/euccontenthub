# Builder.AWS Crawler Fix - Tasks

## Task List

- [x] 1. Update BuilderAWSCrawler.save_to_dynamodb() method
  - [x] 1.1 Modify `else` branch to use `if_not_exists()` for authors
  - [x] 1.2 Modify `else` branch to use `if_not_exists()` for content
  - [x] 1.3 Remove summary/label fields from `else` branch
  - [x] 1.4 Verify `if content_changed` branch is unchanged

- [x] 2. Test changes locally
  - [x] 2.1 Review code changes for correctness
  - [x] 2.2 Verify DynamoDB UpdateExpression syntax
  - [x] 2.3 Check for any syntax errors

- [x] 3. Deploy to staging
  - [x] 3.1 Copy enhanced_crawler_lambda.py to crawler_code/lambda_function.py
  - [x] 3.2 Create deployment zip
  - [x] 3.3 Deploy to aws-blog-crawler Lambda
  - [x] 3.4 Verify deployment successful

- [x] 4. Test in staging
  - [x] 4.1 Check current staging data (authors, summaries)
  - [x] 4.2 Run crawler in staging
  - [x] 4.3 Verify 0 authors changed to "AWS Builder Community"
  - [x] 4.4 Verify 0 summaries lost for unchanged posts
  - [x] 4.5 Verify 0 real content replaced with template
  - [x] 4.6 Check crawler logs for errors

- [x] 5. Implement orchestration fix
  - [x] 5.1 Add `changed_post_ids` list to BuilderAWSCrawler.__init__()
  - [x] 5.2 Track changed post IDs in save_to_dynamodb()
  - [x] 5.3 Invoke Selenium crawler with post_ids in lambda_handler()
  - [x] 5.4 Update Summary/Classifier invocation to only run for AWS Blog posts
  - [x] 5.5 Copy changes to crawler_code/lambda_function.py

- [ ] 6. Update Selenium crawler
  - [ ] 6.1 Add `post_ids` parameter to lambda_handler()
  - [ ] 6.2 Query DynamoDB for URLs if post_ids provided
  - [ ] 6.3 Crawl only specified posts if post_ids provided
  - [ ] 6.4 Otherwise use current behavior (crawl all EUC posts)
  - [ ] 6.5 Deploy to staging ECS task

- [ ] 7. Test complete orchestration in staging
  - [ ] 7.1 Deploy both crawlers to staging
  - [ ] 7.2 Run sitemap crawler
  - [ ] 7.3 Verify Selenium crawler invoked with correct post_ids
  - [ ] 7.4 Verify real authors fetched
  - [ ] 7.5 Verify summaries generated from real content
  - [ ] 7.6 Verify 0% data loss

- [ ] 8. Deploy to production
  - [ ] 8.1 Review staging test results
  - [ ] 8.2 Deploy sitemap crawler to production Lambda
  - [ ] 8.3 Deploy Selenium crawler to production ECS
  - [ ] 8.4 Run crawler in production
  - [ ] 8.5 Monitor for regressions

- [ ] 9. Update documentation
  - [x] 9.1 Update AGENTS.md with Builder crawler rules
  - [x] 9.2 Update README.md with architecture diagrams
  - [x] 9.3 Create completion document
  - [ ] 9.4 Update Issue #26 with final resolution
  - [ ] 9.5 Close Issue #26

## Task Details

### Task 1.1-1.3: Modify else branch

**File**: `enhanced_crawler_lambda.py`  
**Lines**: ~595-610  
**Current Code**:
```python
else:
    update_expression = '''
        SET #url = :url,
            title = :title,
            authors = :authors,
            date_published = :date_published,
            date_updated = :date_updated,
            tags = :tags,
            content = :content,
            last_crawled = :last_crawled,
            #source = :source
    '''
```

**New Code**:
```python
else:
    # Post unchanged - preserve existing authors, content, and summary
    update_expression = '''
        SET #url = :url,
            title = :title,
            date_published = if_not_exists(date_published, :date_published),
            date_updated = :date_updated,
            tags = :tags,
            last_crawled = :last_crawled,
            #source = :source,
            authors = if_not_exists(authors, :authors),
            content = if_not_exists(content, :content)
    '''
    # Note: Does NOT touch summary, label, or other AI-generated fields
```

### Task 4: Staging Test Procedure

**Pre-test Check**:
```bash
python check_staging_builder_posts.py
# Record: number of posts with real authors, number with summaries
```

**Run Crawler**:
```bash
aws lambda invoke \
  --function-name aws-blog-crawler \
  --invocation-type Event \
  --payload '{"source": "builder"}' \
  response.json
```

**Post-test Check**:
```bash
python check_staging_builder_posts.py
# Verify: same number of real authors, same number of summaries
```

**Success Criteria**:
- Authors with real names: UNCHANGED
- Posts with summaries: UNCHANGED or INCREASED (never decreased)
- No errors in CloudWatch logs

### Task 5: Production Deployment

**Only proceed if**:
- All staging tests pass
- No regressions observed
- Code review complete

**Deployment**:
```bash
# Deploy to production Lambda
aws lambda update-function-code \
  --function-name aws-blog-crawler \
  --zip-file fileb://crawler_production_deploy.zip
```

**Monitor**:
- Check CloudWatch logs for errors
- Verify post counts
- Check for user reports of missing data

## Estimated Time

- Task 1: 30 minutes (code changes)
- Task 2: 15 minutes (local testing)
- Task 3: 15 minutes (staging deployment)
- Task 4: 30 minutes (staging testing)
- Task 5: 30 minutes (production deployment)
- Task 6: 30 minutes (documentation)

**Total**: ~2.5 hours

## Dependencies

- AWS credentials configured
- Access to staging and production Lambdas
- Staging environment with test data

## Risks

- **Low Risk**: Changes are minimal and well-tested
- **Mitigation**: Staging environment catches issues before production
- **Rollback**: Can revert Lambda code instantly if needed

## Notes

- This fix addresses the root cause of Issue #26 (summary loss)
- Staging environment proved its value by catching this regression
- The fix uses DynamoDB's built-in `if_not_exists()` function, no custom logic needed
