# Requirements Document: Chat Service Mapper Integration

## Introduction

This feature integrates the EUC Service Name Mapping system into the chat Lambda function to improve content discovery when users search for AWS EUC services using historical or alternative names. The integration addresses the challenge of AWS service rebranding (e.g., AppStream 2.0 → WorkSpaces Applications) by automatically expanding search queries to include all known service name variants and providing rename context in AI responses.

## Glossary

- **Chat_Lambda**: The AWS Lambda function that powers the AI chat assistant for content discovery
- **Service_Mapper**: The EUCServiceMapper utility class that handles service name mapping and historical name lookups
- **Query_Expansion**: The process of adding historical and alternative service names to a user's search query
- **Relevance_Scoring**: The algorithm that assigns numerical scores to blog posts based on keyword matches
- **Rename_Context**: Information about service name changes that is added to AI responses
- **Deployment_Package**: The Lambda deployment zip file containing Python code and JSON data files
- **Historical_Name**: A previous name for an AWS service (e.g., "AppStream 2.0" for WorkSpaces Applications)
- **Service_Variant**: Any valid name for a service including current name, historical names, and common abbreviations

## Requirements

### Requirement 1: Service Mapper Integration

**User Story:** As a developer, I want to integrate the service mapper utility into the chat Lambda, so that the chat assistant can handle historical service names.

#### Acceptance Criteria

1. WHEN the chat Lambda initializes, THE System SHALL load the service mapper with the mapping JSON file
2. WHEN the service mapper fails to load, THE System SHALL log the error and continue with degraded functionality
3. WHEN the chat Lambda processes a query, THE System SHALL have access to all service mapper methods
4. THE System SHALL include both euc_service_mapper.py and euc-service-name-mapping.json in the Lambda deployment package

### Requirement 2: Query Expansion

**User Story:** As a user searching for content about "AppStream 2.0", I want to find posts that mention "WorkSpaces Applications", so that I can discover all relevant content regardless of which service name is used.

#### Acceptance Criteria

1. WHEN a user submits a search query containing a service name, THE System SHALL expand the query to include all historical and current names for that service
2. WHEN a query contains multiple service names, THE System SHALL expand each service name independently
3. WHEN a query contains no recognized service names, THE System SHALL process the query without modification
4. WHEN query expansion occurs, THE System SHALL log the original and expanded queries for debugging

### Requirement 3: Enhanced Relevance Scoring

**User Story:** As a user, I want search results to include posts that use any variant of a service name, so that I don't miss relevant content due to service rebranding.

#### Acceptance Criteria

1. WHEN scoring posts for relevance, THE System SHALL check for matches against all service name variants
2. WHEN a post title matches any service variant, THE System SHALL apply the same score boost as for the original query term
3. WHEN a post summary matches any service variant, THE System SHALL apply the same score boost as for the original query term
4. WHEN a post tags field matches any service variant, THE System SHALL apply the same score boost as for the original query term
5. WHEN multiple variants match the same post, THE System SHALL accumulate the scores without duplication

### Requirement 4: Rename Context in AI Responses

**User Story:** As a user searching for "AppStream 2.0", I want the AI to inform me that the service is now called "WorkSpaces Applications", so that I understand the current service naming.

#### Acceptance Criteria

1. WHEN a user query contains a historical service name, THE System SHALL detect the rename
2. WHEN a rename is detected, THE System SHALL retrieve rename information including old name, new name, and rename date
3. WHEN generating the AI response, THE System SHALL include rename context in the system prompt
4. WHEN the AI generates a response, THE Response SHALL mention the service rename if applicable
5. THE Rename_Context SHALL include the format: "Note: [old_name] is now called [new_name] (renamed [date])"

### Requirement 5: Deployment Package Configuration

**User Story:** As a developer, I want the deployment script to include all necessary files, so that the Lambda function has access to service mapping data at runtime.

#### Acceptance Criteria

1. WHEN building the Lambda deployment package, THE System SHALL include euc_service_mapper.py
2. WHEN building the Lambda deployment package, THE System SHALL include euc-service-name-mapping.json
3. WHEN building the Lambda deployment package, THE System SHALL include chat_lambda_with_aws_docs.py
4. WHEN the Lambda function starts, THE System SHALL be able to load the JSON file from the deployment package
5. WHEN the deployment script runs, THE System SHALL verify that all required files exist before creating the zip

### Requirement 6: Error Handling and Graceful Degradation

**User Story:** As a system administrator, I want the chat Lambda to continue functioning even if service mapping fails, so that users can still search for content.

#### Acceptance Criteria

1. WHEN the service mapper fails to initialize, THE System SHALL log the error with full traceback
2. WHEN the service mapper is unavailable, THE System SHALL process queries using the existing keyword search
3. WHEN query expansion fails, THE System SHALL use the original query without expansion
4. WHEN rename detection fails, THE System SHALL generate responses without rename context
5. THE System SHALL NOT return error responses to users due to service mapper failures

### Requirement 7: Logging and Observability

**User Story:** As a developer, I want detailed logging of service mapping operations, so that I can debug issues and monitor effectiveness.

#### Acceptance Criteria

1. WHEN the service mapper initializes, THE System SHALL log the number of services loaded
2. WHEN a query is expanded, THE System SHALL log the original query and expanded terms
3. WHEN a rename is detected, THE System SHALL log the old name, new name, and rename date
4. WHEN service mapping operations fail, THE System SHALL log the error with context
5. THE System SHALL log service mapper operations at INFO level for normal operations and ERROR level for failures

### Requirement 8: Backward Compatibility

**User Story:** As a developer, I want the integration to maintain existing chat functionality, so that current users experience no disruption.

#### Acceptance Criteria

1. WHEN a user submits a query without service names, THE System SHALL process it using existing logic
2. WHEN the service mapper is disabled, THE System SHALL function identically to the pre-integration version
3. WHEN processing queries, THE System SHALL maintain the existing response format
4. WHEN generating recommendations, THE System SHALL use the same recommendation structure
5. THE System SHALL NOT modify the API contract or response schema
