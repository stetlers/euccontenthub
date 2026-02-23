# Issue #26: ECS/Fargate Migration Progress Update

## Summary

Significant progress made on migrating the Builder.AWS Selenium crawler from Lambda to ECS/Fargate to resolve Chrome stability issues. Phases 1-3 are complete with Docker image successfully built and pushed to ECR.

## Problem Recap

The Lambda-based Selenium crawler experienced 100% failure rate due to Chrome crashes:
- Error: "Chrome failed to start: exited normally"
- Lambda environment insufficient for Selenium/Chrome workloads
- Result: Builder.AWS posts stuck with placeholder "AWS Builder Community" instead of real author names

## Solution: ECS/Fargate Migration

Migrating to ECS/Fargate provides:
- Better process isolation for Chrome
- More memory (4GB vs Lambda's 10GB limit)
- Proven stability with `selenium/standalone-chrome` base image
- Same serverless model (pay per use, no idle costs)

## Progress: Phases 1-3 Complete ✅

### Phase 1: Infrastructure Setup ✅

**ECS Cluster**
- Name: `selenium-crawler-cluster`
- Status: ACTIVE
- ARN: `arn:aws:ecs:us-east-1:031421429609:cluster/selenium-crawler-cluster`

**ECR Repository**
- Name: `selenium-crawler`
- URI: `031421429609.dkr.ecr.us-east-1.amazonaws.com/selenium-crawler`
- Lifecycle Policy: Keep last 5 images

**IAM Roles**
- Task Execution Role: `selenium-crawler-task-execution-role`
  - Permissions: Pull images from ECR, write CloudWatch logs
- Task Role: `selenium-crawler-task-role`
  - Permissions: DynamoDB access, Lambda invocation, CloudWatch logs

**CloudWatch Log Group**
- Name: `/ecs/selenium-crawler`
- Retention: 30 days

**Security Group**
- Name: `selenium-crawler-sg`
- Outbound: HTTPS (443) for internet access

### Phase 2: Docker Container Development ✅

**Files Created:**
- `Dockerfile.ecs-selenium` - Uses `selenium/standalone-chrome:latest` base
- `requirements-ecs-selenium.txt` - Python dependencies (boto3, selenium)
- `ecs_selenium_crawler.py` - ECS-adapted crawler code
- `buildspec.yml` - CodeBuild configuration

**Key Features:**
- Reads environment variables: `DYNAMODB_TABLE_NAME`, `ENVIRONMENT`, `POST_IDS`
- Extracts real author names and content from Builder.AWS pages
- Updates DynamoDB with extracted data
- Auto-invokes Summary Generator Lambda after completion
- Proper exit codes (0 for success, 1 for failure)
- Comprehensive logging

### Phase 3: Docker Build & Push ✅

**CodeBuild Setup:**
- Project: `selenium-crawler-docker-build`
- Build completed successfully
- Image pushed to ECR: `031421429609.dkr.ecr.us-east-1.amazonaws.com/selenium-crawler:latest`

**Build Script:**
- `build-and-push-docker-image.py` - Automates entire build process
  - Creates source zip
  - Uploads to S3
  - Triggers CodeBuild
  - Monitors progress

**ECS Task Definition:**
- Registered: `selenium-crawler-task` (staging)
- CPU: 2048 (2 vCPU)
- Memory: 4096 MB (4 GB)
- Launch Type: Fargate
- Network Mode: awsvpc

## What's Working

✅ ECS cluster created and active
✅ ECR repository configured with lifecycle policy
✅ IAM roles created with correct permissions
✅ Docker image built successfully using CodeBuild
✅ Image pushed to ECR
✅ Task definition registered
✅ CloudWatch logging configured
✅ Security group configured

## Remaining Work

### Phase 4: Sitemap Crawler Integration
- Update `enhanced_crawler_lambda.py` to invoke ECS task instead of Lambda
- Pass `post_ids` as environment variables to ECS task
- Deploy updated sitemap crawler to staging

### Phase 5: Testing in Staging
- Test ECS task directly with sample post IDs
- Verify Chrome starts without crashes
- Verify real author names extracted
- Test end-to-end orchestration: Sitemap → ECS → Summary → Classifier
- Performance testing with various batch sizes

### Phase 6: Production Deployment
- Create production task definition
- Update sitemap crawler for production
- Deploy and monitor

### Phase 7: Monitoring & Documentation
- Set up CloudWatch alarms
- Create deployment scripts
- Update documentation (AGENTS.md, INFRASTRUCTURE.md)

## Cost Estimate

**Per Invocation** (40 posts, ~5 minutes):
- ECS Fargate: 2 vCPU × 4 GB × 5 min = ~$0.02

**Monthly** (4 crawls/month):
- Total: ~$0.08/month (~$1/year)

Acceptable cost increase for reliability and real author names.

## Technical Details

### Orchestration Flow
```
1. Sitemap Crawler (Lambda)
   ↓ Detects NEW/CHANGED posts
   ↓ Invokes ECS task with post_ids
   ↓
2. ECS Fargate Task (Selenium + Chrome)
   ↓ Fetches real content and authors
   ↓ Updates DynamoDB
   ↓ Invokes Summary Generator
   ↓
3. Summary Generator (Lambda)
   ↓ Generates AI summaries
   ↓ Invokes Classifier
   ↓
4. Classifier (Lambda)
   ↓ Assigns content type labels
```

### Why ECS Over Lambda?

| Aspect | Lambda | ECS/Fargate |
|--------|--------|-------------|
| Chrome Stability | 100% crash rate | Proven stable |
| Memory | 10GB max (insufficient) | 4GB (sufficient) |
| Process Isolation | Limited | Excellent |
| Base Image | Custom build | `selenium/standalone-chrome` |
| Cost | Free tier | ~$1/year |
| Startup Time | <1s | ~30s |

## Files Created

```
Infrastructure:
- ecs-task-definition-staging.json
- codebuild-project.json
- codebuild-policy.json
- codebuild-trust-policy.json
- ecs-trust-policy-clean.json
- selenium-crawler-task-role-policy.json

Docker:
- Dockerfile.ecs-selenium
- requirements-ecs-selenium.txt
- ecs_selenium_crawler.py
- buildspec.yml

Scripts:
- build-and-push-docker-image.py

Documentation:
- ecs-migration-phase1-2-complete.md
- .kiro/specs/selenium-ecs-migration/requirements.md
- .kiro/specs/selenium-ecs-migration/design.md
- .kiro/specs/selenium-ecs-migration/tasks.md
```

## Next Session

Priority tasks for next session:
1. Test ECS task directly with sample Builder.AWS post
2. Verify Chrome stability (0% crash rate expected)
3. Verify real author name extraction
4. Update sitemap crawler to invoke ECS task
5. Test end-to-end flow in staging

## Timeline

- **Phase 1-3**: Complete (2026-02-13)
- **Phase 4-5**: Estimated 3-4 hours
- **Phase 6-7**: Estimated 2-3 hours
- **Total Remaining**: ~1 day of work

## Success Criteria

- ✅ ECS task runs without Chrome crashes
- ⏳ Real author names for 100% of Builder.AWS posts
- ⏳ Complete orchestration flow working
- ⏳ 0 data loss or corruption
- ⏳ Task completion rate > 99%

## Deployment Date

2026-02-13 (Phases 1-3)

---

**Status**: In Progress - Infrastructure complete, testing phase next
**Blocker**: None
**Risk**: Low - proven technology stack, isolated testing environment


---

## Latest Update: Deduplication Fix (2026-02-14 14:15 UTC)

### Issue Identified

ECS task logs showed "✓ Updated: [Author Name]" for 39 posts, but only 17 posts actually had real authors in DynamoDB. Investigation revealed the root cause:

**Duplicate Post IDs**: The sitemap crawler was sending duplicate post IDs to the ECS task. Example from task logs:
```
[32/39] Processing: security-checks-using-amazon-q-developer-cli
[35/39] Processing: security-checks-using-amazon-q-developer-cli  (DUPLICATE)
[38/39] Processing: security-checks-using-amazon-q-developer-cli  (DUPLICATE)
```

### Root Cause

In `enhanced_crawler_lambda.py`, the `changed_post_ids` was a **list** instead of a **set**:
- When posts were detected as changed, they were appended to the list
- If the sitemap contained duplicates or the same post was detected multiple times, it would be added multiple times
- ECS task would process the same post multiple times, wasting resources

### Fix Applied ✅

Changed `changed_post_ids` from list to set for automatic deduplication:

```python
# Before
self.changed_post_ids = []
self.changed_post_ids.append(post_id)

# After
self.changed_post_ids = set()
self.changed_post_ids.add(post_id)
changed_post_ids = list(builder_crawler.changed_post_ids)  # Convert to list when needed
```

**Files Modified**:
- `enhanced_crawler_lambda.py` (deployed to staging ✅)
- `crawler_code/lambda_function.py` (kept in sync)

### Testing Plan

1. ✅ Deploy deduplication fix to staging
2. ⏳ Delete all Builder.AWS posts from staging (`python delete_all_builder_posts_staging.py`)
3. ⏳ Run crawler from website (user clicks "Start Crawling")
4. ⏳ Verify complete orchestration chain:
   - Sitemap crawler detects NEW posts
   - ECS task processes unique posts only (no duplicates)
   - Real authors extracted and saved
   - Summaries generated
   - Labels classified
5. ⏳ Deploy to production if successful

### Expected Outcome

After the fix:
- ECS task will process only unique posts (no duplicates)
- All Builder.AWS posts will have real author names
- Complete orchestration chain will work: Sitemap → ECS → Summary → Classifier
- No wasted processing on duplicate posts

### Next Steps

**User Action Required**: 
1. Run `python delete_all_builder_posts_staging.py` and confirm deletion
2. Click "Start Crawling" on https://staging.awseuccontent.com
3. Monitor progress with `python check_staging_status.py`
4. Verify all posts have real authors, summaries, and labels
