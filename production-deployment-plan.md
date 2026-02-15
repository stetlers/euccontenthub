# Production Deployment Plan - EUC Content Hub

## Overview

Deploy staging fixes to production with a clean slate approach: clear existing production data and rebuild with verified staging code.

## Current Production State

### Issues
- ❌ Many posts missing summaries
- ❌ Builder.AWS posts have incorrect authors ("AWS Builder Community")
- ❌ No auto-chaining (old code)
- ❌ No exponential backoff (old code)

### Decision
**Do NOT preserve existing production data**. Staging code is proven and production-ready. Clean slate deployment ensures data quality.

---

## Deployment Strategy

### Phase 1: Pre-Deployment Preparation
### Phase 2: Lambda Deployments
### Phase 3: Production Data Reset
### Phase 4: Live Test & Verification
### Phase 5: Monitoring & Validation

---

## Phase 1: Pre-Deployment Preparation

### 1.1 Backup Current Production State (Optional)
```bash
# Export production data for reference (not for restore)
python export_production_data.py
```

**Note**: This is for historical reference only. We will NOT restore this data.

### 1.2 Verify Staging Success
```bash
# Confirm staging is at 94%+ completion
python diagnose_missing_summaries.py
```

**Expected**:
- 452+ posts with good summaries
- 0 posts with error summaries
- <30 posts without summaries

### 1.3 Document Current Production Metrics
```bash
# Capture baseline for comparison
python check_production_status.py > production_before.txt
```

---

## Phase 2: Lambda Deployments

### 2.1 Deploy Summary Generator Lambda

**File**: `summary_lambda.py`

**Changes**:
- Exponential backoff with retry logic
- Fixed auto-chain variable collision
- Returns None instead of error messages

**Deployment**:
```bash
# Deploy to $LATEST
python deploy_summary_with_autochain.py

# Publish new version
aws lambda publish-version --function-name aws-blog-summary-generator

# Update production alias to new version
aws lambda update-alias \
  --function-name aws-blog-summary-generator \
  --name production \
  --function-version <NEW_VERSION>
```

**Verification**:
```bash
# Check production alias points to new version
aws lambda get-alias \
  --function-name aws-blog-summary-generator \
  --name production
```

### 2.2 Deploy Enhanced Crawler Lambda

**File**: `enhanced_crawler_lambda.py`

**Changes**:
- Deduplication fix (set instead of list)
- Proper ECS task invocation

**Deployment**:
```bash
# Deploy crawler with dependencies
python deploy_crawler_with_deps.py

# Publish new version
aws lambda publish-version --function-name aws-blog-enhanced-crawler

# Update production alias
aws lambda update-alias \
  --function-name aws-blog-enhanced-crawler \
  --name production \
  --function-version <NEW_VERSION>
```

### 2.3 Verify IAM Permissions

**Check**: Summary generator can invoke itself
```bash
# Verify inline policy exists
aws iam get-role-policy \
  --role-name aws-blog-summary-lambda-role \
  --policy-name SummaryGeneratorSelfInvoke
```

**If missing**:
```bash
python add_lambda_self_invoke_permission.py
```

### 2.4 Deploy Classifier Lambda (If Changed)

**File**: `classifier_lambda.py`

**Note**: Only deploy if changes were made. Check git diff.

```bash
# If needed
python deploy_classifier.py
```

### 2.5 Deploy ECS/Fargate Selenium Crawler ⚠️ CRITICAL

**Background**: Previously, Selenium tasks ran in Lambda with high failure rates. Now using ECS/Fargate for reliable execution.

**Current State**:
- ✅ Staging: ECS cluster `selenium-crawler-cluster` and task definition `selenium-crawler-task` configured
- ✅ Production: Uses SAME cluster and task definition, environment passed via container overrides
- ✅ Environment detection: Both enhanced crawler and Selenium crawler detect environment automatically

**Key Insight**: We don't need separate task definitions for staging/production. The enhanced crawler passes the environment via container overrides, and the Selenium crawler reads it to invoke the correct Lambda alias.

#### 2.5.1 Verify ECS Cluster Exists

```bash
# Check if cluster exists
aws ecs describe-clusters --clusters selenium-crawler-cluster
```

**Expected**: Cluster should exist (created during staging setup)

#### 2.5.2 Verify Current Task Definition

```bash
# Check current task definition
aws ecs describe-task-definition --task-definition selenium-crawler-task
```

**Expected**: Task definition should exist with:
- Container name: `selenium-crawler`
- Image: `031421429609.dkr.ecr.us-east-1.amazonaws.com/builder-selenium-crawler:latest`
- Task role: `builder-crawler-task-role`
- Execution role: `ecsTaskExecutionRole`

**Note**: Environment variables are passed via container overrides at runtime, not in task definition.

#### 2.5.3 Verify Task Role Permissions

**Role**: `builder-crawler-task-role`

**Required Permissions**:
1. DynamoDB: Read/Write to `aws-blog-posts` and `aws-blog-posts-staging` tables
2. Lambda: Invoke `aws-blog-summary-generator:production` and `aws-blog-summary-generator:staging` aliases
3. CloudWatch Logs: Write logs

**Check current policy**:
```bash
aws iam get-role-policy \
  --role-name builder-crawler-task-role \
  --policy-name BuilderCrawlerTaskPolicy
```

**Expected Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:031421429609:table/aws-blog-posts",
        "arn:aws:dynamodb:us-east-1:031421429609:table/aws-blog-posts-staging"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": [
        "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-summary-generator:production",
        "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-summary-generator:staging"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:031421429609:log-group:/ecs/builder-selenium-crawler:*"
    }
  ]
}
```

**If policy needs update**, create `update_ecs_task_role_policy.py`:
```python
import boto3

iam = boto3.client('iam')

policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:031421429609:table/aws-blog-posts",
                "arn:aws:dynamodb:us-east-1:031421429609:table/aws-blog-posts-staging"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": [
                "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-summary-generator:production",
                "arn:aws:lambda:us-east-1:031421429609:function:aws-blog-summary-generator:staging"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:us-east-1:031421429609:log-group:/ecs/builder-selenium-crawler:*"
        }
    ]
}

response = iam.put_role_policy(
    RoleName='builder-crawler-task-role',
    PolicyName='BuilderCrawlerTaskPolicy',
    PolicyDocument=json.dumps(policy_document)
)

print("✅ Updated ECS task role policy")
```

#### 2.5.4 Verify Enhanced Crawler Lambda Configuration

**The enhanced crawler automatically detects environment** based on table name and passes it to ECS tasks via container overrides.

**Check Lambda environment variables**:
```bash
aws lambda get-function-configuration \
  --function-name aws-blog-enhanced-crawler:production \
  --query 'Environment.Variables'
```

**Expected**: Should have `ENVIRONMENT=production` (set during deployment)

**Verify ECS invocation logic** in `enhanced_crawler_lambda.py` (lines 752-815):
- ✅ Cluster: `selenium-crawler-cluster` (hardcoded)
- ✅ Task definition: `selenium-crawler-task` (hardcoded)
- ✅ Subnets: `subnet-b2a60bed` (hardcoded)
- ✅ Security groups: `sg-06c921b4472e87b70` (hardcoded)
- ✅ Environment detection: `'staging' if '-staging' in table_name else 'production'`
- ✅ Passes environment via container overrides

**No changes needed** - the code is already production-ready.

#### 2.5.5 Test ECS Task Manually (Optional)

**Before full deployment, optionally test ECS task**:
```bash
# Run single ECS task with test payload
aws ecs run-task \
  --cluster selenium-crawler-cluster \
  --task-definition selenium-crawler-task \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-b2a60bed],securityGroups=[sg-06c921b4472e87b70],assignPublicIp=ENABLED}" \
  --overrides '{
    "containerOverrides": [{
      "name": "selenium-crawler",
      "environment": [
        {"name": "POST_IDS", "value": "test-post-id"},
        {"name": "DYNAMODB_TABLE_NAME", "value": "aws-blog-posts"},
        {"name": "ENVIRONMENT", "value": "production"}
      ]
    }]
  }'
```

**Monitor task**:
```bash
# Get task ARN from previous command output
aws ecs describe-tasks \
  --cluster selenium-crawler-cluster \
  --tasks <TASK_ARN>

# Check logs
aws logs tail /ecs/builder-selenium-crawler --follow
```

**Verify**:
- ✅ Task starts successfully
- ✅ Chrome/Selenium initializes
- ✅ Can fetch Builder.AWS pages
- ✅ Updates DynamoDB correctly
- ✅ Invokes summary Lambda with `:production` alias

**Note**: This step is optional because staging has already validated the ECS task works correctly.

#### 2.5.6 Summary: What's Already Done vs. What's Needed

**✅ Already Configured (No Action Needed)**:
- ECS cluster `selenium-crawler-cluster` exists
- ECS task definition `selenium-crawler-task` exists with correct Docker image
- Task role `builder-crawler-task-role` has permissions for both staging and production
- Enhanced crawler Lambda has hardcoded cluster, task definition, subnet, and security group
- Environment detection works automatically based on table name
- Selenium crawler invokes correct Lambda alias based on environment variable

**⚠️ Action Required**:
1. Verify task role policy includes production Lambda alias (Section 2.5.3)
2. Optionally test ECS task manually with production environment (Section 2.5.5)

**Key Insight**: The ECS infrastructure is environment-agnostic. The same cluster and task definition serve both staging and production. Environment is determined at runtime via container overrides passed by the enhanced crawler Lambda.

#### 2.5.7 Run Verification Script

**Before proceeding to Phase 3, verify ECS is production-ready**:
```bash
python verify_ecs_production_ready.py
```

**Expected Output**:
```
✅ ALL CHECKS PASSED - ECS infrastructure is ready for production
```

**If checks fail**:
```bash
# Update task role policy
python update_ecs_task_role_policy.py

# Re-run verification
python verify_ecs_production_ready.py
```

---

## Phase 3: Production Data Reset

### 3.1 Clear Production DynamoDB Table

**⚠️ CRITICAL**: This deletes all production data. Ensure backups are complete.

```bash
# Clear aws-blog-posts table
python clear_production_table.py
```

**Script** (`clear_production_table.py`):
```python
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('aws-blog-posts')

print("⚠️  WARNING: This will delete ALL production data!")
response = input("Type 'DELETE PRODUCTION DATA' to confirm: ")

if response != 'DELETE PRODUCTION DATA':
    print("Aborted")
    exit(0)

# Scan and delete all items
response = table.scan()
with table.batch_writer() as batch:
    for item in response['Items']:
        batch.delete_item(Key={'post_id': item['post_id']})

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    with table.batch_writer() as batch:
        for item in response['Items']:
            batch.delete_item(Key={'post_id': item['post_id']})

print("✅ Production table cleared")
```

### 3.2 Verify Table is Empty

```bash
# Confirm zero items
aws dynamodb scan \
  --table-name aws-blog-posts \
  --select COUNT
```

**Expected**: `"Count": 0`

---

## Phase 4: Live Test & Verification

### 4.1 Start Monitoring

**Terminal 1**: Real-time progress monitor
```bash
python monitor_production_test.py
```

**Terminal 2**: Log monitoring
```bash
# Watch CloudWatch logs
aws logs tail /aws/lambda/aws-blog-summary-generator --follow
```

### 4.2 Trigger Production Crawler

**Method 1**: From website (recommended)
1. Visit: https://awseuccontent.com
2. Click: "Start Crawling" button
3. Watch monitoring output

**Method 2**: Direct Lambda invocation
```bash
aws lambda invoke \
  --function-name aws-blog-enhanced-crawler:production \
  --invocation-type Event \
  --payload '{}' \
  response.json
```

### 4.3 Monitor Orchestration

**Expected Flow**:
```
1. Enhanced Crawler (2-3 min)
   ↓ Creates ~479 posts
   ↓ Triggers ECS tasks for Builder.AWS
   
2. ECS Tasks (5-10 min)
   ↓ Extracts real authors and content
   ↓ Updates DynamoDB
   ↓ Triggers summary generator
   
3. Summary Generator (30-45 min)
   ↓ Generates AI summaries with exponential backoff
   ↓ Auto-chains through all posts
   ↓ Triggers classifier for each batch
   
4. Classifier (5-10 min)
   ↓ Assigns content type labels
   ✓ Complete!
```

**Total Expected Time**: 45-60 minutes

### 4.4 Check Progress Milestones

**5 minutes**: Posts created
```bash
python check_production_status.py
# Expected: ~479 posts, 0 summaries
```

**15 minutes**: ECS tasks completing
```bash
python check_ecs_task_status.py
# Expected: Builder.AWS posts have real authors
```

**30 minutes**: Summaries generating
```bash
python check_production_status.py
# Expected: 50-70% posts have summaries
```

**60 minutes**: Should be complete
```bash
python check_production_status.py
# Expected: 95%+ posts have summaries
```

---

## Phase 5: Monitoring & Validation

### 5.1 Verify Completion

**Run comprehensive check**:
```bash
python diagnose_missing_summaries.py
```

**Success Criteria**:
- ✅ 95%+ posts have good summaries
- ✅ 0 posts with error summaries
- ✅ <5% posts without summaries (acceptable)
- ✅ All Builder.AWS posts have real authors

### 5.2 Spot Check Data Quality

**Sample AWS Blog posts**:
```bash
python sample_production_posts.py --source aws-blog --count 10
```

**Verify**:
- ✅ Authors present
- ✅ Content present (3000 chars)
- ✅ Summary present (2-3 sentences)
- ✅ Label present (content type)

**Sample Builder.AWS posts**:
```bash
python sample_production_posts.py --source builder.aws.com --count 10
```

**Verify**:
- ✅ Real author names (NOT "AWS Builder Community")
- ✅ Content present
- ✅ Summary present
- ✅ Label present

### 5.3 Check Website

**Visit**: https://awseuccontent.com

**Verify**:
- ✅ Posts display correctly
- ✅ Summaries visible
- ✅ Authors correct
- ✅ Filters work
- ✅ Search works
- ✅ No errors in browser console

### 5.4 Monitor for 24 Hours

**CloudWatch Metrics**:
- Lambda invocations
- Lambda errors
- DynamoDB read/write capacity
- Bedrock API calls

**CloudWatch Logs**:
- Check for errors
- Check for throttling
- Verify auto-chain working

**Set Alerts**:
```bash
# Create CloudWatch alarm for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name production-summary-generator-errors \
  --alarm-description "Alert on summary generator errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=aws-blog-summary-generator
```

---

## Rollback Plan

### If Issues Occur During Deployment

**Scenario 1**: Lambda deployment fails
```bash
# Rollback to previous version
aws lambda update-alias \
  --function-name aws-blog-summary-generator \
  --name production \
  --function-version <PREVIOUS_VERSION>
```

**Scenario 2**: Data issues after crawler runs
```bash
# Clear table and retry
python clear_production_table.py
# Fix issue in code
# Redeploy Lambda
# Trigger crawler again
```

**Scenario 3**: Persistent throttling (>10%)
```bash
# Reduce batch size
aws lambda update-function-configuration \
  --function-name aws-blog-summary-generator \
  --environment Variables={BATCH_SIZE=3}

# Or add rate limiting (Tier 2)
aws lambda update-function-configuration \
  --function-name aws-blog-summary-generator \
  --environment Variables={BEDROCK_DELAY_SECONDS=0.5}
```

---

## Post-Deployment Tasks

### 1. Document Baseline Metrics
```bash
# Capture production metrics
python check_production_status.py > production_after.txt

# Compare before/after
diff production_before.txt production_after.txt
```

### 2. Update Documentation
- Update AGENTS.md with new auto-chain behavior
- Update README.md with deployment notes
- Document any issues encountered

### 3. Schedule Daily Monitoring
```bash
# Add to cron or CloudWatch Events
# Daily check at 9 AM
0 9 * * * python check_production_status.py | mail -s "Daily Production Status" admin@example.com
```

### 4. Plan Next Crawler Run
- Production crawler should run daily
- Monitor for new posts
- Verify auto-chain handles daily volume

---

## Success Criteria

### Deployment Success
- ✅ All Lambdas deployed to production alias
- ✅ IAM permissions configured
- ✅ Production table cleared
- ✅ Crawler completed successfully

### Data Quality Success
- ✅ 95%+ posts have summaries
- ✅ 0 posts with error summaries
- ✅ All Builder.AWS posts have real authors
- ✅ Website displays correctly

### Operational Success
- ✅ Auto-chain working (no manual intervention)
- ✅ Exponential backoff handling throttling
- ✅ No errors in CloudWatch logs
- ✅ Daily crawls processing new posts

---

## Timeline

### Estimated Duration
- **Phase 1** (Preparation): 15 minutes
- **Phase 2** (Lambda Deployments): 15 minutes
- **Phase 3** (Data Reset): 5 minutes
- **Phase 4** (Live Test): 60 minutes
- **Phase 5** (Validation): 30 minutes

**Total**: ~2 hours

### Recommended Schedule
- **Start**: Off-peak hours (evening or weekend)
- **Reason**: Minimize user impact during data reset
- **Team**: Have backup available for troubleshooting

---

## Communication Plan

### Before Deployment
**Notify users**:
- "Scheduled maintenance: [DATE] [TIME]"
- "Site will be unavailable for ~2 hours"
- "All data will be refreshed with improved quality"

### During Deployment
**Status updates**:
- "Maintenance in progress - deploying updates"
- "Data refresh in progress - [X]% complete"

### After Deployment
**Completion notice**:
- "Maintenance complete - site is back online"
- "Improvements: Better summaries, accurate authors, faster updates"
- "Report any issues to [CONTACT]"

---

## Checklist

### Pre-Deployment
- [ ] Staging verified at 94%+ completion
- [ ] Backup production data (optional)
- [ ] Document current production metrics
- [ ] Review deployment plan with team
- [ ] Schedule deployment window
- [ ] Notify users of maintenance

### Deployment
- [ ] Deploy summary generator Lambda
- [ ] Deploy enhanced crawler Lambda
- [ ] Verify IAM permissions
- [ ] Clear production table
- [ ] Start monitoring
- [ ] Trigger production crawler
- [ ] Monitor orchestration progress

### Post-Deployment
- [ ] Verify 95%+ completion
- [ ] Spot check data quality
- [ ] Test website functionality
- [ ] Document baseline metrics
- [ ] Update documentation
- [ ] Notify users of completion
- [ ] Monitor for 24 hours

---

## Contact & Support

### During Deployment
- **Primary**: [Your contact]
- **Backup**: [Backup contact]
- **AWS Support**: [Support case number if needed]

### Post-Deployment Issues
- **CloudWatch Logs**: `/aws/lambda/aws-blog-summary-generator`
- **Monitoring Dashboard**: [CloudWatch dashboard URL]
- **Runbook**: This document

---

## Conclusion

This deployment plan provides a clean slate approach to production, leveraging the proven staging fixes:
- **Auto-chaining** ensures complete processing
- **Exponential backoff** handles Bedrock throttling
- **Clean data** with accurate authors and summaries

The deployment is low-risk because:
- Staging has validated the code (94% success rate)
- Production volume (2-5 posts/day) is well below throttle limits
- Rollback is simple (revert Lambda alias)
- Data can be regenerated if needed

Expected outcome: Production achieves 99%+ success rate with zero manual intervention.
