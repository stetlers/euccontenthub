# Implementation Plan: Chat Service Mapper Integration

## Overview

This implementation plan integrates the EUC Service Name Mapping system into the chat Lambda function. The integration will be implemented incrementally, starting with service mapper initialization, then query expansion, enhanced scoring, rename context, and finally deployment package updates. Each step includes property-based tests to validate correctness.

## Tasks

- [x] 1. Initialize service mapper in chat Lambda
  - Add module-level initialization of EUCServiceMapper
  - Implement error handling with graceful degradation
  - Add logging for initialization success/failure
  - Verify mapper loads all services from JSON file
  - _Requirements: 1.1, 1.2, 1.3_

- [ ]* 1.1 Write property test for service mapper initialization
  - **Property 1: Service Mapper Initialization**
  - **Validates: Requirements 1.1, 1.2**

- [ ]* 1.2 Write unit tests for initialization edge cases
  - Test with missing JSON file
  - Test with invalid JSON format
  - Test with malformed service data
  - _Requirements: 1.2_

- [x] 2. Implement query expansion module
  - [x] 2.1 Create expand_query_with_service_names() function
    - Tokenize query into words
    - Check each word against service mapper
    - Get all service variants for matches
    - Return expansion result with metadata
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [ ]* 2.2 Write property test for query expansion
    - **Property 3: Query Expansion for Service Names**
    - **Property 4: Query Expansion Preserves Non-Service Queries**
    - **Validates: Requirements 2.1, 2.2, 2.3**
  
  - [ ]* 2.3 Write unit tests for query expansion
    - Test with single service name
    - Test with multiple service names
    - Test with no service names
    - Test with mixed service and non-service terms
    - _Requirements: 2.1, 2.2, 2.3_

- [x] 3. Add query expansion logging
  - Add INFO level logging for expansion operations
  - Log original query and expanded terms
  - Log detected services
  - _Requirements: 2.4, 7.2_

- [ ]* 3.1 Write property test for query expansion logging
  - **Property 5: Query Expansion Logging**
  - **Validates: Requirements 2.4, 7.2**

- [x] 4. Enhance relevance scoring with service variants
  - [x] 4.1 Modify filter_and_score_posts() to use expanded terms
    - Call expand_query_with_service_names() at start
    - Pass expanded terms to scoring logic
    - Check both original keywords and expanded terms
    - Implement deduplication to prevent double-counting
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [ ]* 4.2 Write property test for service variant scoring
    - **Property 6: Service Variant Scoring**
    - **Property 7: Score Deduplication**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
  
  - [ ]* 4.3 Write unit tests for enhanced scoring
    - Test scoring with service variants in title
    - Test scoring with service variants in summary
    - Test scoring with service variants in tags
    - Test score deduplication with multiple matches
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 5. Checkpoint - Ensure query expansion and scoring tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement rename context provider
  - [x] 6.1 Create get_rename_context() function
    - Tokenize query into potential service names
    - Check each token for historical service names
    - Call mapper.get_rename_info() for matches
    - Format rename information for AI prompt
    - Return formatted context or None
    - _Requirements: 4.1, 4.2, 4.5_
  
  - [ ]* 6.2 Write property test for rename detection
    - **Property 8: Historical Name Detection**
    - **Property 10: Rename Context Format**
    - **Validates: Requirements 4.1, 4.2, 4.5**
  
  - [ ]* 6.3 Write unit tests for rename context
    - Test with known historical names (AppStream 2.0, WorkSpaces Web, WSP)
    - Test with current service names
    - Test with non-service terms
    - Test context format matches specification
    - _Requirements: 4.1, 4.2, 4.5_

- [x] 7. Add rename detection logging
  - Add INFO level logging for rename detection
  - Log old name, new name, and rename date
  - _Requirements: 7.3_

- [ ]* 7.1 Write property test for rename detection logging
  - **Property 15: Rename Detection Logging**
  - **Validates: Requirements 7.3**

- [x] 8. Enhance AI prompt with rename context
  - [x] 8.1 Modify get_ai_recommendations() to accept rename_context parameter
    - Add optional rename_context parameter
    - Append rename context to system prompt if provided
    - Add rename notice to user prompt if provided
    - _Requirements: 4.3_
  
  - [ ]* 8.2 Write property test for rename context in prompts
    - **Property 9: Rename Context in Prompts**
    - **Validates: Requirements 4.3**
  
  - [ ]* 8.3 Write unit tests for AI prompt enhancement
    - Test system prompt includes rename context
    - Test user prompt includes rename notice
    - Test prompts without rename context (backward compatibility)
    - _Requirements: 4.3_

- [x] 9. Integrate rename context into main Lambda handler
  - Call get_rename_context() in lambda_handler()
  - Pass rename_context to get_ai_recommendations()
  - Ensure integration works with existing flow
  - _Requirements: 4.1, 4.2, 4.3_

- [ ]* 9.1 Write integration test for end-to-end rename flow
  - Test query with historical name triggers rename detection
  - Test rename context flows through to AI response
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 10. Checkpoint - Ensure rename context tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement error handling and graceful degradation
  - [ ] 11.1 Add try-catch blocks for all service mapper operations
    - Wrap initialization in try-catch
    - Wrap query expansion in try-catch
    - Wrap rename detection in try-catch
    - Return safe defaults on errors
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [ ]* 11.2 Write property test for graceful degradation
    - **Property 14: Graceful Degradation on Mapper Unavailability**
    - **Validates: Requirements 6.2, 6.3, 6.4, 6.5**
  
  - [ ]* 11.3 Write unit tests for error handling
    - Test Lambda continues when mapper fails to initialize
    - Test query processing works without mapper
    - Test expansion failures use original query
    - Test rename detection failures don't break responses
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 12. Add comprehensive logging
  - [ ] 12.1 Add initialization logging
    - Log service count on successful initialization
    - Log errors with traceback on failure
    - _Requirements: 7.1, 7.4_
  
  - [ ] 12.2 Implement log level correctness
    - Use INFO for successful operations
    - Use ERROR for failures
    - _Requirements: 7.5_
  
  - [ ]* 12.3 Write property test for log level correctness
    - **Property 16: Log Level Correctness**
    - **Validates: Requirements 7.5**

- [ ] 13. Implement backward compatibility checks
  - [ ] 13.1 Add tests for non-service query processing
    - Verify behavior matches pre-integration for non-service queries
    - Test with mapper enabled and disabled
    - _Requirements: 8.1, 8.2_
  
  - [ ]* 13.2 Write property test for backward compatibility
    - **Property 17: Backward Compatibility for Non-Service Queries**
    - **Validates: Requirements 8.1, 8.2**
  
  - [ ]* 13.3 Write property test for response schema consistency
    - **Property 18: Response Schema Consistency**
    - **Validates: Requirements 8.3, 8.4, 8.5**

- [ ] 14. Checkpoint - Ensure error handling and compatibility tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 15. Update deployment script
  - [ ] 15.1 Modify deploy_chat_with_aws_docs.py
    - Add euc_service_mapper.py to files list
    - Add euc-service-name-mapping.json to files list
    - Implement pre-deployment file validation
    - Verify all files exist before creating zip
    - Add error handling for missing files
    - _Requirements: 5.1, 5.2, 5.3, 5.5_
  
  - [ ] 15.2 Test deployment package creation
    - Verify zip contains all three required files
    - Verify file paths are correct in zip
    - Test with missing files (should fail gracefully)
    - _Requirements: 1.4, 5.1, 5.2, 5.3, 5.5_
  
  - [ ]* 15.3 Write property test for pre-deployment validation
    - **Property 12: Pre-Deployment File Validation**
    - **Validates: Requirements 5.5**

- [ ] 16. Test Lambda deployment package
  - [ ] 16.1 Deploy to staging environment
    - Create deployment package with updated script
    - Deploy to staging Lambda
    - Verify Lambda can load JSON file
    - Check CloudWatch logs for initialization
    - _Requirements: 5.4_
  
  - [ ]* 16.2 Write property test for runtime JSON loading
    - **Property 11: JSON File Loading at Runtime**
    - **Validates: Requirements 5.4**
  
  - [ ] 16.3 Test end-to-end functionality in staging
    - Test query with historical service name (e.g., "AppStream 2.0")
    - Verify query expansion in logs
    - Verify enhanced scoring finds relevant posts
    - Verify AI response includes rename context
    - Test query without service names (backward compatibility)
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 4.3, 8.1_

- [ ] 17. Final checkpoint - Ensure all tests pass
  - Run complete test suite
  - Verify all property tests pass (100+ iterations each)
  - Verify all unit tests pass
  - Verify integration tests pass in staging
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 18. Documentation and deployment
  - [ ] 18.1 Update AGENTS.md with service mapper integration details
    - Document new query expansion behavior
    - Document rename context feature
    - Add troubleshooting section for service mapper
    - _Requirements: All_
  
  - [ ] 18.2 Create deployment checklist
    - Pre-deployment verification steps
    - Post-deployment monitoring steps
    - Rollback procedure if issues occur
    - _Requirements: All_
  
  - [ ] 18.3 Deploy to production
    - Deploy updated Lambda to production
    - Monitor CloudWatch logs for errors
    - Test with production data
    - Verify query expansion and rename context work
    - _Requirements: All_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each property test should run minimum 100 iterations
- All property tests must reference their design document property number
- Integration tests should be run in staging before production deployment
- Monitor CloudWatch logs closely after deployment for any initialization errors
- The service mapper operates as an enhancement - existing functionality must continue to work if it fails
