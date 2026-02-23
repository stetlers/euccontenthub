# Design Document: Chat Service Mapper Integration

## Overview

This design integrates the EUC Service Name Mapping system into the chat Lambda function to improve content discovery for AWS EUC services. The integration enhances the existing keyword-based search by automatically expanding queries to include historical service names, boosting relevance scores for all service name variants, and providing rename context in AI responses.

The solution maintains backward compatibility with existing functionality while adding intelligent service name handling. The service mapper operates as an optional enhancement - if it fails to load or encounters errors, the chat Lambda continues to function using its existing search logic.

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Chat Lambda Function                     │
│                                                              │
│  ┌────────────────┐         ┌──────────────────┐           │
│  │  Lambda Handler│────────▶│  Service Mapper  │           │
│  │                │         │  (EUCServiceMapper)│          │
│  └────────┬───────┘         └────────┬─────────┘           │
│           │                          │                      │
│           │                          │                      │
│           ▼                          ▼                      │
│  ┌────────────────┐         ┌──────────────────┐           │
│  │ Query Processor│◀────────│  Mapping Data    │           │
│  │                │         │  (JSON file)     │           │
│  └────────┬───────┘         └──────────────────┘           │
│           │                                                 │
│           ▼                                                 │
│  ┌────────────────┐                                        │
│  │ Relevance      │                                        │
│  │ Scorer         │                                        │
│  └────────┬───────┘                                        │
│           │                                                 │
│           ▼                                                 │
│  ┌────────────────┐                                        │
│  │ AI Response    │                                        │
│  │ Generator      │                                        │
│  └────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

### Integration Points

1. **Initialization**: Service mapper loads during Lambda cold start
2. **Query Processing**: Queries are expanded before relevance scoring
3. **Relevance Scoring**: Scoring algorithm checks all service variants
4. **AI Prompting**: Rename context is added to system prompts
5. **Deployment**: Mapper files are included in Lambda zip package

### Data Flow

```
User Query
    │
    ▼
Query Expansion (Service Mapper)
    │
    ├─ Detect service names
    ├─ Get all variants (current + historical)
    └─ Expand query terms
    │
    ▼
Relevance Scoring (Enhanced)
    │
    ├─ Score against original terms
    ├─ Score against expanded terms
    └─ Accumulate scores
    │
    ▼
Rename Detection (Service Mapper)
    │
    ├─ Check if query has historical names
    └─ Get rename information
    │
    ▼
AI Response Generation (With Context)
    │
    ├─ Add rename context to prompt
    ├─ Generate response
    └─ Include rename note in response
    │
    ▼
Response to User
```

## Components and Interfaces

### 1. Service Mapper Wrapper

**Purpose**: Initialize and manage the EUCServiceMapper instance

**Interface**:
```python
def initialize_service_mapper() -> Optional[EUCServiceMapper]:
    """
    Initialize the service mapper with error handling
    
    Returns:
        EUCServiceMapper instance or None if initialization fails
    """
    pass

def is_service_mapper_available() -> bool:
    """
    Check if service mapper is available
    
    Returns:
        True if mapper is initialized and ready
    """
    pass
```

**Implementation Notes**:
- Load mapper during Lambda cold start (module-level initialization)
- Catch and log all initialization errors
- Return None on failure to enable graceful degradation
- Log the number of services loaded on success

### 2. Query Expansion Module

**Purpose**: Expand user queries to include all service name variants

**Interface**:
```python
def expand_query_with_service_names(query: str, mapper: Optional[EUCServiceMapper]) -> Dict[str, Any]:
    """
    Expand query to include all service name variants
    
    Args:
        query: Original user query
        mapper: Service mapper instance (or None)
    
    Returns:
        {
            'original_query': str,
            'expanded_terms': Set[str],
            'detected_services': List[str],
            'has_expansion': bool
        }
    """
    pass
```

**Algorithm**:
1. Tokenize query into words
2. For each word, check if it matches a service name (case-insensitive)
3. If match found, get all service variants using `mapper.get_all_names()`
4. Add all variants to expanded terms set
5. Return original query + expanded terms + metadata

**Example**:
```python
Input: "AppStream 2.0 setup guide"
Output: {
    'original_query': 'AppStream 2.0 setup guide',
    'expanded_terms': {
        'appstream', '2.0', 'setup', 'guide',
        'Amazon WorkSpaces Applications',
        'Amazon AppStream 2.0',
        'Amazon AppStream'
    },
    'detected_services': ['Amazon WorkSpaces Applications'],
    'has_expansion': True
}
```

### 3. Enhanced Relevance Scorer

**Purpose**: Score posts using both original and expanded query terms

**Interface**:
```python
def score_post_with_expansion(
    post: Dict,
    original_keywords: List[str],
    expanded_terms: Set[str],
    detected_domain: Optional[str]
) -> int:
    """
    Score a post for relevance using expanded query terms
    
    Args:
        post: Blog post data
        original_keywords: Keywords from original query
        expanded_terms: Expanded terms including service variants
        detected_domain: Detected EUC domain (if any)
    
    Returns:
        Relevance score (integer)
    """
    pass
```

**Scoring Algorithm** (Enhanced):
```
Base scoring (existing):
- Title exact match: +10 points
- Title keyword match: +5 points per keyword
- Summary keyword match: +3 points per keyword
- Tags keyword match: +4 points per keyword
- Content keyword match: +1 point per keyword
- Domain match: +8 points
- Recent posts: +2 points

New scoring (service variants):
- Title service variant match: +5 points per variant
- Summary service variant match: +3 points per variant
- Tags service variant match: +4 points per variant
- Content service variant match: +1 point per variant

Deduplication:
- Track which terms have already scored for each field
- Don't double-count if both original and variant match
```

**Implementation Strategy**:
1. Maintain existing `filter_and_score_posts()` function signature
2. Call `expand_query_with_service_names()` at the start
3. Pass expanded terms to scoring logic
4. Check both original keywords and expanded terms
5. Use a set to track which terms have scored for each field (prevent double-counting)

### 4. Rename Context Provider

**Purpose**: Detect service renames and provide context for AI responses

**Interface**:
```python
def get_rename_context(query: str, mapper: Optional[EUCServiceMapper]) -> Optional[Dict]:
    """
    Get rename context if query contains historical service names
    
    Args:
        query: User query
        mapper: Service mapper instance
    
    Returns:
        {
            'old_name': str,
            'new_name': str,
            'rename_date': str,
            'context_text': str  # Formatted for AI prompt
        }
        or None if no rename detected
    """
    pass
```

**Algorithm**:
1. Tokenize query into potential service names
2. For each token, check if it's a historical service name
3. If historical name found, call `mapper.get_rename_info()`
4. Format rename information for AI prompt
5. Return formatted context or None

**Context Format**:
```
"Note: {old_name} was renamed to {new_name} on {rename_date}. 
When recommending posts, mention this rename to help the user understand 
that content about both names refers to the same service."
```

### 5. AI Prompt Enhancer

**Purpose**: Add rename context to AI system prompts

**Modification to `get_ai_recommendations()`**:
```python
def get_ai_recommendations(
    user_message: str,
    relevant_posts: List[Dict],
    all_posts: List[Dict],
    aws_docs_results: List[Dict],
    rename_context: Optional[Dict] = None  # NEW PARAMETER
) -> Dict:
    """
    Enhanced to include rename context in AI prompts
    """
    pass
```

**System Prompt Enhancement**:
```python
# Existing system prompt
system_prompt = """You are the EUC Content Finder..."""

# Add rename context if available
if rename_context:
    system_prompt += f"\n\n{rename_context['context_text']}"
```

**User Prompt Enhancement**:
```python
# Add rename context to user prompt
if rename_context:
    user_prompt = f"""User Query: {user_message}

SERVICE RENAME NOTICE:
{rename_context['context_text']}

{aws_docs_context}
Available Blog Posts (JSON):
{json.dumps(post_data, cls=DecimalEncoder)}
..."""
```

### 6. Deployment Package Builder

**Purpose**: Include service mapper files in Lambda deployment zip

**Modification to `deploy_chat_with_aws_docs.py`**:
```python
def create_deployment_package():
    """
    Create Lambda deployment package with service mapper
    """
    files_to_include = [
        'chat_lambda_with_aws_docs.py',
        'euc_service_mapper.py',           # NEW
        'euc-service-name-mapping.json'    # NEW
    ]
    
    # Verify all files exist
    for file in files_to_include:
        if not os.path.exists(file):
            raise FileNotFoundError(f"Required file not found: {file}")
    
    # Create zip with all files
    with zipfile.ZipFile('chat_lambda_deployment.zip', 'w') as zipf:
        for file in files_to_include:
            zipf.write(file, arcname=file)
    
    return 'chat_lambda_deployment.zip'
```

## Data Models

### Service Mapping Data Structure

The service mapper uses the existing `euc-service-name-mapping.json` structure:

```json
{
  "services": [
    {
      "current_name": "Amazon WorkSpaces Applications",
      "previous_names": ["Amazon AppStream 2.0", "Amazon AppStream"],
      "service_type": "application_streaming",
      "keywords": ["appstream", "application streaming", "workspaces applications"],
      "related_services": ["Amazon WorkSpaces", "Amazon WorkSpaces Thin Client"],
      "rename_date": "2024-11-18",
      "notes": "Rebranded from AppStream 2.0..."
    }
  ],
  "service_families": {...},
  "metadata": {...}
}
```

### Query Expansion Result

```python
{
    'original_query': str,           # Original user query
    'expanded_terms': Set[str],      # All terms including variants
    'detected_services': List[str],  # Services detected in query
    'has_expansion': bool            # True if expansion occurred
}
```

### Rename Context

```python
{
    'old_name': str,        # Historical service name
    'new_name': str,        # Current service name
    'rename_date': str,     # ISO date of rename
    'context_text': str     # Formatted text for AI prompt
}
```

### Enhanced Post Scoring

```python
{
    'post': Dict,           # Original post data
    'score': int,           # Total relevance score
    'matched_terms': Set[str],  # Terms that matched (for debugging)
    'matched_variants': Set[str]  # Service variants that matched
}
```

## Correctness Properties


*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified several areas where properties can be consolidated:

**Consolidation 1**: Requirements 3.2, 3.3, 3.4 all test score consistency across different post fields (title, summary, tags). These can be combined into a single property that tests score consistency across all fields.

**Consolidation 2**: Requirements 5.1, 5.2, 5.3 all test deployment package file inclusion. These can be combined into a single example test that verifies all required files are present.

**Consolidation 3**: Requirements 7.2, 7.3, 7.4, 7.5 all test logging behavior. These can be consolidated into fewer properties that test logging completeness and correctness.

**Consolidation 4**: Requirements 8.3, 8.4, 8.5 all test API compatibility. These can be combined into a single property that validates the response schema.

### Properties

Property 1: Service Mapper Initialization
*For any* Lambda cold start, initializing the service mapper should either succeed and load all services from the JSON file, or fail gracefully and log the error without preventing Lambda execution.
**Validates: Requirements 1.1, 1.2**

Property 2: Service Mapper Method Availability
*For any* query processed by the Lambda, if the service mapper initialized successfully, all mapper methods (get_current_name, get_all_names, get_rename_info, etc.) should be accessible and callable.
**Validates: Requirements 1.3**

Property 3: Query Expansion for Service Names
*For any* query containing a recognized service name, expanding the query should produce a set of terms that includes the original query terms plus all historical and current names for each detected service.
**Validates: Requirements 2.1, 2.2**

Property 4: Query Expansion Preserves Non-Service Queries
*For any* query containing no recognized service names, expanding the query should return the original query terms unchanged.
**Validates: Requirements 2.3**

Property 5: Query Expansion Logging
*For any* query expansion operation, the system should log both the original query and the expanded terms at INFO level.
**Validates: Requirements 2.4, 7.2**

Property 6: Service Variant Scoring
*For any* blog post and any service name variant, if the variant appears in the post's title, summary, tags, or content, the scoring algorithm should apply the same point boost as it would for the original query term in that field.
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

Property 7: Score Deduplication
*For any* blog post that matches multiple service name variants, the scoring algorithm should accumulate points for each unique field match without double-counting when both the original term and a variant match the same field.
**Validates: Requirements 3.5**

Property 8: Historical Name Detection
*For any* query containing a historical service name (as defined in the mapping JSON), the system should detect the rename and retrieve the complete rename information including old name, new name, and rename date.
**Validates: Requirements 4.1, 4.2**

Property 9: Rename Context in Prompts
*For any* AI response generation where a rename was detected, the system prompt should include the rename context text.
**Validates: Requirements 4.3**

Property 10: Rename Context Format
*For any* detected service rename, the generated rename context text should follow the format "Note: [old_name] is now called [new_name] (renamed [date])" with all three fields populated.
**Validates: Requirements 4.5**

Property 11: JSON File Loading at Runtime
*For any* Lambda function start, the system should be able to load and parse the euc-service-name-mapping.json file from the deployment package without errors.
**Validates: Requirements 5.4**

Property 12: Pre-Deployment File Validation
*For any* deployment script execution, if any required file (euc_service_mapper.py, euc-service-name-mapping.json, chat_lambda_with_aws_docs.py) is missing, the script should fail with a clear error message before creating the zip file.
**Validates: Requirements 5.5**

Property 13: Initialization Failure Logging
*For any* service mapper initialization failure, the system should log the error with a full traceback at ERROR level.
**Validates: Requirements 6.1, 7.4**

Property 14: Graceful Degradation on Mapper Unavailability
*For any* query processed when the service mapper is unavailable (failed to initialize or disabled), the system should process the query using the existing keyword search logic and return a valid response.
**Validates: Requirements 6.2, 6.3, 6.4, 6.5**

Property 15: Rename Detection Logging
*For any* detected service rename, the system should log the old name, new name, and rename date at INFO level.
**Validates: Requirements 7.3**

Property 16: Log Level Correctness
*For any* service mapper operation, the system should log at INFO level for successful operations and ERROR level for failures.
**Validates: Requirements 7.5**

Property 17: Backward Compatibility for Non-Service Queries
*For any* query that does not contain service names, the system's behavior (query processing, scoring, response generation) should be identical to the pre-integration version.
**Validates: Requirements 8.1, 8.2**

Property 18: Response Schema Consistency
*For any* query processed by the system, the response should conform to the existing API schema with fields: response (string), recommendations (array), conversation_id (string), and optionally aws_docs (array).
**Validates: Requirements 8.3, 8.4, 8.5**

## Error Handling

### Error Categories

1. **Initialization Errors**
   - Missing JSON file
   - Invalid JSON format
   - Missing required fields in JSON
   - File permission errors

2. **Runtime Errors**
   - Service mapper method failures
   - Query expansion errors
   - Rename detection errors
   - Logging failures

3. **Deployment Errors**
   - Missing source files
   - Zip creation failures
   - File permission errors

### Error Handling Strategy

**Initialization Errors**:
```python
try:
    service_mapper = EUCServiceMapper('euc-service-name-mapping.json')
    print(f"Service mapper initialized with {len(service_mapper.services)} services")
except FileNotFoundError as e:
    print(f"ERROR: Service mapping file not found: {e}")
    service_mapper = None
except json.JSONDecodeError as e:
    print(f"ERROR: Invalid JSON in service mapping file: {e}")
    service_mapper = None
except Exception as e:
    print(f"ERROR: Failed to initialize service mapper: {e}")
    import traceback
    traceback.print_exc()
    service_mapper = None
```

**Runtime Errors**:
```python
def expand_query_with_service_names(query, mapper):
    try:
        if mapper is None:
            return {'original_query': query, 'expanded_terms': set(query.split()), 
                    'detected_services': [], 'has_expansion': False}
        
        # Perform expansion
        expanded = mapper.expand_query(query)
        # ... rest of logic
        
    except Exception as e:
        print(f"ERROR: Query expansion failed: {e}")
        # Return original query without expansion
        return {'original_query': query, 'expanded_terms': set(query.split()), 
                'detected_services': [], 'has_expansion': False}
```

**Deployment Errors**:
```python
def create_deployment_package():
    required_files = [
        'chat_lambda_with_aws_docs.py',
        'euc_service_mapper.py',
        'euc-service-name-mapping.json'
    ]
    
    # Validate all files exist
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        raise FileNotFoundError(
            f"Required files missing: {', '.join(missing_files)}"
        )
    
    # Create zip
    try:
        with zipfile.ZipFile('chat_lambda_deployment.zip', 'w') as zipf:
            for file in required_files:
                zipf.write(file, arcname=file)
    except Exception as e:
        print(f"ERROR: Failed to create deployment package: {e}")
        raise
```

### Logging Strategy

**Log Levels**:
- INFO: Successful operations (initialization, query expansion, rename detection)
- ERROR: Failures that trigger graceful degradation
- DEBUG: Detailed operation information (disabled in production)

**Log Format**:
```python
# Initialization
print(f"INFO: Service mapper initialized with {count} services")

# Query expansion
print(f"INFO: Query expanded: '{original}' -> {len(expanded)} terms")
print(f"INFO: Detected services: {detected_services}")

# Rename detection
print(f"INFO: Rename detected: {old_name} -> {new_name} ({date})")

# Errors
print(f"ERROR: Service mapper initialization failed: {error}")
print(f"ERROR: Query expansion failed for query '{query}': {error}")
```

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests to ensure comprehensive coverage:

**Unit Tests**: Focus on specific examples, edge cases, and integration points
- Test initialization with valid JSON file
- Test initialization with missing file
- Test initialization with invalid JSON
- Test query expansion with known service names
- Test query expansion with no service names
- Test rename detection with historical names
- Test deployment package creation
- Test graceful degradation scenarios

**Property-Based Tests**: Verify universal properties across all inputs
- Test that query expansion always includes original terms
- Test that scoring is consistent across all service variants
- Test that errors never propagate to user responses
- Test that response schema is always valid
- Test that logging occurs for all operations

### Property-Based Testing Configuration

**Library**: Use `hypothesis` for Python property-based testing

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with feature name and property number
- Tag format: `# Feature: chat-service-mapper-integration, Property N: [property text]`

**Example Property Test**:
```python
from hypothesis import given, strategies as st
import pytest

# Feature: chat-service-mapper-integration, Property 3: Query Expansion for Service Names
@given(st.text(min_size=1))
def test_query_expansion_includes_original_terms(query):
    """
    For any query, expansion should include all original terms
    """
    result = expand_query_with_service_names(query, service_mapper)
    
    original_terms = set(query.split())
    expanded_terms = result['expanded_terms']
    
    # All original terms should be in expanded terms
    assert original_terms.issubset(expanded_terms)
```

### Test Coverage Goals

- Unit test coverage: 90%+ for new code
- Property test coverage: All 18 correctness properties
- Integration test coverage: End-to-end query processing with service mapper
- Error handling coverage: All error paths tested

### Testing Checklist

**Before Deployment**:
- [ ] All unit tests pass
- [ ] All property tests pass (100+ iterations each)
- [ ] Integration tests pass in staging environment
- [ ] Error handling tests pass
- [ ] Deployment package contains all required files
- [ ] Lambda can load JSON file from package
- [ ] Graceful degradation works when mapper is disabled
- [ ] Response schema validation passes
- [ ] Logging output is correct

**After Deployment**:
- [ ] Monitor CloudWatch logs for initialization errors
- [ ] Verify query expansion is working (check logs)
- [ ] Verify rename detection is working (check logs)
- [ ] Test queries with historical service names
- [ ] Verify AI responses include rename context
- [ ] Monitor error rates (should not increase)
- [ ] Verify response times (should not significantly increase)
