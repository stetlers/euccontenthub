# Selenium Crawler ECS/Fargate Migration - Tasks

## Phase 1: Infrastructure Setup

### 1. Create ECS Cluster
- [x] 1.1 Create ECS cluster named `selenium-crawler-cluster`
- [x] 1.2 Verify cluster is active
- [ ] 1.3 Document cluster ARN

### 2. Create ECR Repository
- [ ] 2.1 Create ECR repository named `selenium-crawler`
- [ ] 2.2 Configure repository lifecycle policy (keep last 5 images)
- [ ] 2.3 Document repository URI

### 3. Create IAM Roles
- [ ] 3.1 Create task execution role (for pulling images, writing logs)
- [ ] 3.2 Create task role with DynamoDB + Lambda permissions
- [ ] 3.3 Attach policies to roles
- [ ] 3.4 Document role ARNs

### 4. Create CloudWatch Log Group
- [ ] 4.1 Create log group `/ecs/selenium-crawler`
- [ ] 4.2 Set retention period (30 days)
- [ ] 4.3 Verify log group exists

## Phase 2: Docker Container Development

### 5. Create Dockerfile
- [ ] 5.1 Write Dockerfile using `selenium/standalone-chrome` base
- [ ] 5.2 Add Python 3 installation
- [ ] 5.3 Add pip dependencies installation
- [ ] 5.4 Copy crawler code
- [ ] 5.5 Set entry point

### 6. Create Crawler Application
- [ ] 6.1 Adapt `builder_selenium_crawler.py` for ECS
- [ ] 6.2 Read environment variables (POST_IDS, DYNAMODB_TABLE_NAME, ENVIRONMENT)
- [ ] 6.3 Implement main() entry point
- [ ] 6.4 Add proper exit codes (0 for success, 1 for failure)
- [ ] 6.5 Add comprehensive logging

### 7. Create requirements.txt
- [ ] 7.1 Add boto3 dependency
- [ ] 7.2 Add selenium dependency
- [ ] 7.3 Pin versions for reproducibility

### 8. Build and Test Docker Image Locally
- [ ] 8.1 Build Docker image
- [ ] 8.2 Run container locally with test environment variables
- [ ] 8.3 Verify Chrome starts without crashes
- [ ] 8.4 Verify crawler can connect to DynamoDB (staging)
- [ ] 8.5 Fix any issues

## Phase 3: ECS Deployment

### 9. Push Docker Image to ECR
- [ ] 9.1 Authenticate Docker to ECR
- [ ] 9.2 Tag image with ECR repository URI
- [ ] 9.3 Push image to ECR
- [ ] 9.4 Verify image in ECR console

### 10. Create Task Definition
- [ ] 10.1 Write task definition JSON file
- [ ] 10.2 Set CPU (2048) and memory (4096)
- [ ] 10.3 Configure container definition
- [ ] 10.4 Set log configuration (CloudWatch)
- [ ] 10.5 Set task and execution role ARNs
- [ ] 10.6 Register task definition
- [ ] 10.7 Document task definition ARN

### 11. Configure Network Resources
- [ ] 11.1 Identify public subnet IDs in default VPC
- [ ] 11.2 Create security group allowing outbound HTTPS
- [ ] 11.3 Document subnet and security group IDs

## Phase 4: Sitemap Crawler Integration

### 12. Update Sitemap Crawler Code
- [ ] 12.1 Add `invoke_selenium_ecs_task()` function
- [ ] 12.2 Replace Lambda invocation with ECS invocation
- [ ] 12.3 Pass post_ids as comma-separated string
- [ ] 12.4 Handle ECS invocation errors gracefully
- [ ] 12.5 Add logging for ECS task ARN

### 13. Deploy Updated Sitemap Crawler to Staging
- [ ] 13.1 Create deployment package
- [ ] 13.2 Update Lambda function code
- [ ] 13.3 Verify deployment successful
- [ ] 13.4 Check Lambda logs for errors

## Phase 5: Testing in Staging

### 14. Test ECS Task Directly
- [ ] 14.1 Run ECS task manually with test post_ids
- [ ] 14.2 Monitor task in ECS console
- [ ] 14.3 Check CloudWatch logs for task execution
- [ ] 14.4 Verify Chrome starts without crashes
- [ ] 14.5 Verify content extraction works
- [ ] 14.6 Verify DynamoDB updates
- [ ] 14.7 Verify Summary Lambda invocation

### 15. Test End-to-End Orchestration
- [ ] 15.1 Modify test post date in staging DynamoDB
- [ ] 15.2 Invoke sitemap crawler
- [ ] 15.3 Verify sitemap crawler invokes ECS task
- [ ] 15.4 Verify ECS task processes posts
- [ ] 15.5 Verify real author names extracted
- [ ] 15.6 Verify Summary → Classifier chain works
- [ ] 15.7 Check all CloudWatch logs

### 16. Verify Data Quality
- [ ] 16.1 Query staging DynamoDB for test posts
- [ ] 16.2 Verify real author names (not "AWS Builder Community")
- [ ] 16.3 Verify content extracted (not placeholder)
- [ ] 16.4 Verify summaries generated
- [ ] 16.5 Verify labels classified

### 17. Performance Testing
- [ ] 17.1 Test with 1 post (baseline)
- [ ] 17.2 Test with 10 posts
- [ ] 17.3 Test with 40 posts (typical batch)
- [ ] 17.4 Measure task duration
- [ ] 17.5 Verify all posts processed successfully

## Phase 6: Production Deployment

### 18. Create Production Task Definition
- [ ] 18.1 Copy staging task definition
- [ ] 18.2 Update environment to "production"
- [ ] 18.3 Update table name to "aws-blog-posts"
- [ ] 18.4 Register production task definition
- [ ] 18.5 Document production task ARN

### 19. Update Sitemap Crawler for Production
- [ ] 19.1 Update sitemap crawler with production task ARN
- [ ] 19.2 Deploy to production Lambda
- [ ] 19.3 Verify deployment successful

### 20. Production Testing
- [ ] 20.1 Test with small batch (3-5 posts)
- [ ] 20.2 Monitor ECS task execution
- [ ] 20.3 Verify real authors extracted
- [ ] 20.4 Verify no data corruption
- [ ] 20.5 Monitor for 24 hours

## Phase 7: Monitoring and Documentation

### 21. Set Up CloudWatch Alarms
- [ ] 21.1 Create alarm for task failure rate > 5%
- [ ] 21.2 Create alarm for task duration > 10 minutes
- [ ] 21.3 Create alarm for no tasks in 7 days
- [ ] 21.4 Test alarms with simulated failures

### 22. Create Deployment Scripts
- [ ] 22.1 Create `build_and_push_image.sh` script
- [ ] 22.2 Create `deploy_ecs_task.sh` script
- [ ] 22.3 Create `test_ecs_task.sh` script
- [ ] 22.4 Document script usage

### 23. Update Documentation
- [ ] 23.1 Update AGENTS.md with ECS architecture
- [ ] 23.2 Update INFRASTRUCTURE.md with ECS setup
- [ ] 23.3 Create ECS-DEPLOYMENT-GUIDE.md
- [ ] 23.4 Update README.md with new architecture diagram

### 24. Clean Up Old Lambda
- [ ] 24.1 Document old Lambda configuration
- [ ] 24.2 Keep old Lambda as backup (don't delete)
- [ ] 24.3 Update Lambda description to "DEPRECATED - Use ECS"
- [ ] 24.4 Remove Lambda from sitemap crawler invocation

## Phase 8: Validation and Closure

### 25. Final Validation
- [ ] 25.1 Run full crawler in production
- [ ] 25.2 Verify 0% Chrome crash rate
- [ ] 25.3 Verify 100% real author names
- [ ] 25.4 Verify all summaries generated
- [ ] 25.5 Verify all labels classified

### 26. Close GitHub Issue #26
- [ ] 26.1 Document resolution in issue
- [ ] 26.2 Link to spec and deployment docs
- [ ] 26.3 Add before/after metrics
- [ ] 26.4 Close issue

## Rollback Plan

If issues occur in production:
- [ ] Revert sitemap crawler to invoke old Lambda
- [ ] Document issues encountered
- [ ] Fix in staging before retrying

## Success Criteria

- ✅ ECS task runs without Chrome crashes
- ✅ Real author names for 100% of Builder.AWS posts
- ✅ Complete orchestration flow working
- ✅ 0 data loss or corruption
- ✅ Task completion rate > 99%
- ✅ All tests passing in staging and production

## Estimated Timeline

- Phase 1 (Infrastructure): 2 hours
- Phase 2 (Docker): 3 hours
- Phase 3 (ECS Deployment): 2 hours
- Phase 4 (Integration): 1 hour
- Phase 5 (Staging Testing): 3 hours
- Phase 6 (Production): 2 hours
- Phase 7 (Monitoring/Docs): 2 hours
- Phase 8 (Validation): 1 hour

**Total: 16 hours (~2 days)**
