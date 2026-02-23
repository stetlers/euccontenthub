# EUC Use Case Matcher

## Overview

The EUC Use Case Matcher helps users choose the right Amazon WorkSpaces service based on their specific requirements and use cases. It goes beyond simple service name mapping to provide intelligent recommendations based on:

- **Persistence requirements** (persistent vs non-persistent)
- **Streaming type** (desktop, applications, browser)
- **Third-party integration** needs
- **Use case complexity** (single vs multiple use cases)
- **Existing infrastructure** (EC2 deployments)

## Problem It Solves

The WorkSpaces service family has become complex with 6 different services:

1. **Amazon WorkSpaces Personal** - Persistent desktops
2. **Amazon WorkSpaces Applications** - Non-persistent desktops/apps
3. **Amazon WorkSpaces Secure Browser** - Browser-only access
4. **Amazon WorkSpaces Core** - Third-party VDI infrastructure
5. **Amazon WorkSpaces Core Managed Instances (CMI)** - EC2-based with third-party tooling
6. **Amazon WorkSpaces Pool** - Non-persistent desktops (edge cases only)

Users often don't know which service to use, leading to:
- Wrong service selection
- Suboptimal architectures
- Confusion about service capabilities
- Missed opportunities for better solutions

## How It Works

### 1. Keyword-Based Matching

Matches user queries against service keywords:

```python
matcher = EUCUseCaseMatcher()
matches = matcher.match_by_keywords("I need persistent desktops for developers")

# Returns:
# [
#   {
#     "service": "Amazon WorkSpaces Personal",
#     "score": 2,
#     "matched_keywords": ["persistent", "desktop"]
#   }
# ]
```

### 2. Requirements-Based Matching

Matches based on specific requirements:

```python
requirements = {
    "persistence": "persistent",
    "third_party": False,
    "streaming_type": "desktop"
}

matches = matcher.match_by_requirements(requirements)
# Returns: ["Amazon WorkSpaces Personal"]
```

### 3. Smart Recommendations

Provides recommendations with confidence scores and reasoning:

```python
recommendation = matcher.get_recommendation("We need non-persistent application streaming")

# Returns:
# {
#   "recommended_service": "Amazon WorkSpaces Applications",
#   "confidence": "high",
#   "reasoning": "Best for task workers needing temporary desktops...",
#   "alternatives": ["Amazon WorkSpaces Pool"],
#   "matched_keywords": ["non-persistent", "application"],
#   "service_details": {...}
# }
```

### 4. Service Comparison

Compare services side-by-side:

```python
comparison = matcher.compare_services([
    "Amazon WorkSpaces Personal",
    "Amazon WorkSpaces Applications"
])

# Returns comparison matrix with:
# - Persistence (persistent vs non-persistent)
# - Streaming type (desktop vs applications)
# - Management (AWS-native vs third-party)
# - Best use cases
```

### 5. Detailed Explanations

Generate human-readable explanations:

```python
explanation = matcher.explain_service_choice(
    "Amazon WorkSpaces Core Managed Instances",
    "multiple use cases with existing EC2"
)

# Returns formatted explanation with:
# - Best-for reasons
# - Use cases
# - Important notes
# - Not suitable for
```

## Integration with Chatbot

### Current Flow (Service Name Mapping Only)

```
User: "Tell me about WorkSpaces"
  ↓
Service Mapper: "WorkSpaces" → "WorkSpaces Personal"
  ↓
Chatbot: Returns blog posts about WorkSpaces Personal
```

### Enhanced Flow (With Use Case Matching)

```
User: "I need non-persistent desktops for task workers"
  ↓
Use Case Matcher: Analyzes requirements
  - Keywords: "non-persistent", "task workers"
  - Recommendation: WorkSpaces Applications
  - Confidence: High
  - Reasoning: "Best for task workers needing temporary desktops"
  ↓
Service Mapper: Expands to include historical names
  - "WorkSpaces Applications"
  - "AppStream 2.0"
  ↓
Chatbot: Returns relevant posts + explains why WorkSpaces Applications is recommended
```

## Use Case Decision Tree

The matcher includes a decision tree to help guide users:

1. **Do users need persistent desktops?**
   - Yes → WorkSpaces Personal, Core, or CMI
   - No → WorkSpaces Applications, Secure Browser, Pool, Core, or CMI

2. **Are you using third-party VDI vendors?**
   - Yes → WorkSpaces Core or CMI
   - No → WorkSpaces Personal, Applications, Secure Browser, or Pool

3. **Do you have multiple use cases?**
   - Yes → WorkSpaces Core Managed Instances (PREFERRED)
   - No → Other services

4. **Do you have existing EC2 deployments?**
   - Yes → WorkSpaces Core Managed Instances
   - No → Other services

5. **Do users only need web browser access?**
   - Yes → WorkSpaces Secure Browser
   - No → Other services

6. **Do users only need specific applications?**
   - Yes → WorkSpaces Applications
   - No → WorkSpaces Personal, Pool, Core, or CMI

7. **Do you need same desktop client as WorkSpaces Personal?**
   - Yes → WorkSpaces Pool
   - No → WorkSpaces Applications

8. **Do you need to share images between persistent and non-persistent?**
   - Yes → WorkSpaces Pool
   - No → WorkSpaces Applications

## Service Comparison Matrix

| Service | Persistence | Streaming Type | Management | Best Use Case |
|---------|-------------|----------------|------------|---------------|
| **WorkSpaces Personal** | Persistent | Full desktop | AWS-native | Traditional VDI, persistent desktops |
| **WorkSpaces Applications** | Non-persistent | Desktop and applications | AWS-native | Non-persistent desktops/apps, task workers |
| **WorkSpaces Secure Browser** | Non-persistent | Browser only | AWS-native | Secure web access only |
| **WorkSpaces Core** | Both (via third-party) | Infrastructure | Third-party VDI vendors | Third-party VDI infrastructure |
| **WorkSpaces Core Managed Instances** | Both (via third-party) | Desktops and applications | Third-party VDI vendors | Multiple use cases with third-party tooling (PREFERRED) |
| **WorkSpaces Pool** | Non-persistent | Full desktop | AWS-native | Edge cases requiring client/image compatibility |

## Example Scenarios

### Scenario 1: Traditional VDI Replacement

**User Query**: "We're migrating from on-premises VDI. Users need persistent Windows desktops."

**Matcher Analysis**:
- Keywords: "persistent", "desktop"
- Recommendation: Amazon WorkSpaces Personal
- Confidence: High
- Reasoning: "Best for traditional VDI replacement with persistent desktops"

### Scenario 2: Task Workers

**User Query**: "We have 500 task workers who need temporary access to applications for a few hours per day."

**Matcher Analysis**:
- Keywords: "task workers", "temporary", "applications"
- Recommendation: Amazon WorkSpaces Applications
- Confidence: High
- Reasoning: "Best for task workers needing temporary desktops, cost-optimized for high user density"

### Scenario 3: Citrix Customer

**User Query**: "We're using Citrix DaaS and want to migrate to AWS."

**Matcher Analysis**:
- Keywords: "citrix", "third-party"
- Recommendation: Amazon WorkSpaces Core
- Confidence: High
- Reasoning: "Best for customers using Citrix DaaS with existing third-party VDI investments"

### Scenario 4: Complex Deployment

**User Query**: "We have existing EC2 instances and need both persistent desktops for developers and non-persistent apps for task workers."

**Matcher Analysis**:
- Keywords: "ec2", "multiple use cases", "persistent", "non-persistent"
- Recommendation: Amazon WorkSpaces Core Managed Instances
- Confidence: High
- Reasoning: "Preferred option for customers with multiple use cases and existing EC2 deployments"

### Scenario 5: Secure Web Access

**User Query**: "Contractors need secure access to our internal web applications only."

**Matcher Analysis**:
- Keywords: "browser", "web access", "secure"
- Recommendation: Amazon WorkSpaces Secure Browser
- Confidence: High
- Reasoning: "Best for secure access to internal web apps without full desktop"

### Scenario 6: Edge Case

**User Query**: "We have WorkSpaces Personal users and need to add non-persistent desktops using the same client and images."

**Matcher Analysis**:
- Keywords: "client compatibility", "image sharing", "non-persistent"
- Recommendation: Amazon WorkSpaces Pool
- Confidence: High
- Reasoning: "Best for image sharing between persistent and non-persistent users"
- Important Note: "Only use in edge cases. WorkSpaces Applications is preferred for most non-persistent desktop scenarios."

## Chatbot Integration Example

```python
from euc_use_case_matcher import EUCUseCaseMatcher
from euc_service_mapper import EUCServiceMapper

# Initialize both helpers
use_case_matcher = EUCUseCaseMatcher()
service_mapper = EUCServiceMapper()

# User query
user_query = "I need non-persistent desktops for task workers"

# Step 1: Get use case recommendation
recommendation = use_case_matcher.get_recommendation(user_query)

# Step 2: Get service details
service_name = recommendation['recommended_service']
service_details = use_case_matcher.get_service_details(service_name)

# Step 3: Expand to include historical names for search
all_names = service_mapper.get_all_names(service_name)

# Step 4: Build AI response
ai_response = f"""
Based on your requirements, I recommend {service_name}.

{recommendation['reasoning']}

This service is best for:
{chr(10).join(f'- {reason}' for reason in service_details['best_for'][:3])}

I've found some relevant blog posts about {service_name} and its previous name ({all_names[1] if len(all_names) > 1 else 'N/A'}).
"""

# Step 5: Search for blog posts using expanded names
search_terms = all_names  # Includes current and historical names
```

## Files

- **euc-use-case-matcher.json**: Service use case data
- **euc_use_case_matcher.py**: Python helper class
- **EUC-USE-CASE-MATCHER-README.md**: This documentation

## Benefits

1. **Better Service Selection**: Users get the right service for their needs
2. **Reduced Confusion**: Clear explanations of service differences
3. **Improved Recommendations**: Context-aware suggestions
4. **Comprehensive Coverage**: Handles all 6 WorkSpaces services
5. **Edge Case Handling**: Identifies when WorkSpaces Pool is appropriate
6. **Third-Party Integration**: Recognizes when Core or CMI is needed
7. **Cost Optimization**: Recommends cost-effective solutions

## Future Enhancements

1. **Machine Learning**: Learn from user feedback to improve recommendations
2. **Cost Estimation**: Include cost comparisons in recommendations
3. **Migration Paths**: Suggest migration strategies between services
4. **Capacity Planning**: Help estimate required capacity
5. **Integration Patterns**: Recommend integration with other AWS services
6. **Regional Availability**: Consider service availability by region
7. **Compliance Requirements**: Factor in compliance needs (HIPAA, PCI, etc.)

## Testing

Run the test suite:

```bash
python euc_use_case_matcher.py
```

Expected output:
- Keyword matching tests
- Requirements matching tests
- Recommendation tests
- Service comparison tests
- Explanation generation tests

## Deployment

To integrate into the chatbot Lambda:

1. Add `euc-use-case-matcher.json` to Lambda deployment package
2. Add `euc_use_case_matcher.py` to Lambda deployment package
3. Update `chat_lambda_with_aws_docs.py` to import and use the matcher
4. Test in staging before production deployment

## Support

For questions or issues:
- Check CloudWatch logs for matcher errors
- Verify JSON file is valid
- Test locally with `python euc_use_case_matcher.py`
- Review service details in `euc-use-case-matcher.json`

---

**Version**: 1.0  
**Last Updated**: February 21, 2026  
**Status**: Ready for integration
