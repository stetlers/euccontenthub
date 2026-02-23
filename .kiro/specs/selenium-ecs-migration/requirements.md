# Selenium Crawler ECS/Fargate Migration - Requirements

## Overview

Migrate the Builder.AWS Selenium crawler from Lambda to ECS/Fargate to resolve Chrome stability issues and enable reliable author name extraction.

## Problem Statement

The current Selenium crawler running in Lambda experiences 100% failure rate due to Chrome crashes:
- Error: "Chrome failed to start: exited normally"
- Error: "disconnected: not connected to DevTools"
- 10GB Lambda memory insufficient for Chrome
- Lambda environment unstable for Selenium workloads

**Impact**: Builder.AWS posts have placeholder "AWS Builder Community" author instead of real author names, which is critical for the app's value proposition of acknowledging contributors.

## User Stories

### 1. As a content contributor
I want my real name displayed on my Builder.AWS articles so that I receive proper acknowledgment for my work.

**Acceptance Criteria**:
- Real author names extracted from Builder.AWS pages
- Author names stored in DynamoDB
- Author names displayed on frontend
- No placeholder "AWS Builder Community" for posts with real authors

### 2. As a system administrator
I want the Selenium crawler to run reliably without crashes so that author extraction works consistently.

**Acceptance Criteria**:
- Chrome runs without crashes
- 0% failure rate for content extraction
- Crawler completes successfully for all posts
- Logs show successful page loads and extractions

### 3. As a developer
I want the crawler to be invoked by the sitemap crawler so that the orchestration flow works correctly.

**Acceptance Criteria**:
- Sitemap crawler can invoke ECS task
- ECS task receives `post_ids` parameter
- ECS task processes only specified posts
- ECS task auto-invokes Summary → Classifier chain

### 4. As a cost-conscious operator
I want the crawler to only run when needed so that we minimize infrastructure costs.

**Acceptance Criteria**:
- Crawler only runs for NEW or CHANGED posts
- No unnecessary crawls for unchanged posts
- ECS tasks terminate after completion
- No idle containers consuming resources

## Functional Requirements

### 1. ECS Task Definition
- **FR-1.1**: Task must run on Fargate (serverless)
- **FR-1.2**: Task must use Docker container with Chrome + Selenium
- **FR-1.3**: Task must have sufficient memory (4GB minimum)
- **FR-1.4**: Task must have sufficient CPU (2 vCPU minimum)
- **FR-1.5**: Task must have IAM role for DynamoDB and Lambda access

### 2. Crawler Functionality
- **FR-2.1**: Accept `post_ids` parameter from sitemap crawler
- **FR-2.2**: Query DynamoDB for post URLs
- **FR-2.3**: Extract real author names from Builder.AWS pages
- **FR-2.4**: Extract content (first 3000 chars)
- **FR-2.5**: Update DynamoDB with extracted data
- **FR-2.6**: Invoke Summary Generator Lambda after completion
- **FR-2.7**: Handle errors gracefully (retry, skip, log)

### 3. Invocation Method
- **FR-3.1**: Sitemap crawler invokes ECS task via AWS SDK
- **FR-3.2**: Pass `post_ids` as environment variables or task overrides
- **FR-3.3**: Task runs asynchronously (fire-and-forget)
- **FR-3.4**: Task logs to CloudWatch for monitoring

### 4. Chrome Configuration
- **FR-4.1**: Chrome runs in headless mode
- **FR-4.2**: Chrome uses optimized flags for stability
- **FR-4.3**: Selenium WebDriver configured for Fargate environment
- **FR-4.4**: Proper cleanup of Chrome processes

## Non-Functional Requirements

### Performance
- **NFR-1**: Task startup time < 30 seconds
- **NFR-2**: Page load time < 10 seconds per post
- **NFR-3**: Total execution time < 5 minutes for 40 posts

### Reliability
- **NFR-4**: Chrome crash rate < 5%
- **NFR-5**: Content extraction success rate > 95%
- **NFR-6**: Task completion rate > 99%

### Scalability
- **NFR-7**: Support processing up to 100 posts per invocation
- **NFR-8**: Support concurrent task execution if needed

### Cost
- **NFR-9**: Task only runs when invoked (no idle costs)
- **NFR-10**: Task terminates immediately after completion

### Monitoring
- **NFR-11**: All logs sent to CloudWatch
- **NFR-12**: Task success/failure metrics available
- **NFR-13**: Alerts for task failures

## Technical Constraints

1. **Docker Required**: Must build and push Docker image to ECR
2. **ECS Cluster**: Must create or use existing ECS cluster
3. **VPC Configuration**: Task must run in VPC with internet access
4. **IAM Permissions**: Task role needs DynamoDB, Lambda, CloudWatch access
5. **Backward Compatibility**: Must work with existing sitemap crawler

## Success Criteria

1. ✅ ECS task runs without Chrome crashes
2. ✅ Real author names extracted for Builder.AWS posts
3. ✅ Sitemap crawler successfully invokes ECS task
4. ✅ Complete orchestration flow works: Sitemap → ECS → Summary → Classifier
5. ✅ 0 posts with placeholder "AWS Builder Community" after crawl
6. ✅ All tests pass in staging environment

## Out of Scope

- Migrating other crawlers to ECS (only Selenium crawler)
- Changing sitemap crawler logic (already deployed)
- Modifying Summary or Classifier Lambdas
- Frontend changes

## Dependencies

- Existing `builder_selenium_crawler.py` code
- Docker installed for building images
- AWS ECR repository for Docker images
- ECS cluster (can be created as part of this work)
- Sitemap crawler already deployed with orchestration logic

## Risks

1. **Docker Build Complexity**: Building Selenium + Chrome image can be tricky
   - Mitigation: Use proven base images (selenium/standalone-chrome)

2. **ECS Learning Curve**: Team may be unfamiliar with ECS
   - Mitigation: Use Fargate (simpler than EC2-based ECS)

3. **Invocation Latency**: ECS task startup slower than Lambda
   - Mitigation: Acceptable trade-off for reliability

4. **Cost Increase**: ECS may be more expensive than Lambda
   - Mitigation: Only runs when needed, no idle costs

## Timeline Estimate

- Requirements: 1 hour (this document)
- Design: 2 hours
- Implementation: 4-6 hours
- Testing: 2-3 hours
- Total: 1-2 days

## Approval

This spec requires approval before implementation begins.
