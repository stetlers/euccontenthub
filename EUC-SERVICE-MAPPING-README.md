# EUC Service Name Mapping System

## Overview

A comprehensive service name mapping system for AWS End User Computing (EUC) services. Handles historical service names, relationships, and provides utilities for improved search and content discovery.

## Problem Solved

AWS EUC services have undergone several name changes:
- **AppStream 2.0** → **WorkSpaces Applications** (Nov 2024)
- **WorkSpaces Web** → **WorkSpaces Secure Browser** (Nov 2024)
- **WSP/NICE DCV** → **Amazon DCV** (Nov 2024)

This creates challenges:
- Users search using old names
- Content exists under multiple names
- Related services aren't obvious
- Historical context is lost

## Solution

Two-part system:
1. **JSON Data File** (`euc-service-name-mapping.json`) - Service definitions
2. **Python Utility** (`euc_service_mapper.py`) - Mapping logic

## Files

### 1. euc-service-name-mapping.json

Comprehensive service definitions including:
- Current and previous names
- Service relationships
- Keywords for search
- Launch and rename dates
- Documentation URLs
- Service families

### 2. euc_service_mapper.py

Python utility class with methods for:
- Name resolution (current ← historical)
- Related service discovery
- Keyword search
- Query expansion
- Service family lookup

## Usage Examples

### Basic Name Mapping

```python
from euc_service_mapper import EUCServiceMapper

mapper = EUCServiceMapper()

# Get current name from historical name
current = mapper.get_current_name("AppStream 2.0")
# Returns: "Amazon WorkSpaces Applications"

# Get all names (current + historical)
all_names = mapper.get_all_names("WorkSpaces Applications")
# Returns: ["Amazon WorkSpaces Applications", "Amazon AppStream 2.0", "Amazon AppStream"]

# Get previous names only
previous = mapper.get_previous_names("WorkSpaces Secure Browser")
# Returns: ["Amazon WorkSpaces Web"]
```

### Service Relationships

```python
# Get related services
related = mapper.get_related_services("WorkSpaces")
# Returns: ["Amazon WorkSpaces Applications", "Amazon WorkSpaces Thin Client", ...]

# Get service family
family = mapper.get_service_family("WorkSpaces")
# Returns: "Amazon WorkSpaces Family"
```

### Search Enhancement

```python
# Search by keyword
services = mapper.search_by_keyword("streaming")
# Returns: [WorkSpaces Applications, Amazon DCV]

# Expand query with historical names
expanded = mapper.expand_query("AppStream 2.0 setup guide")
# Returns: {"AppStream 2.0", "Amazon WorkSpaces Applications", "Amazon AppStream", "setup", "guide"}
```

### Rename Information

```python
# Get rename details
info = mapper.get_rename_info("WorkSpaces Web")
# Returns: {
#     "old_name": "Amazon WorkSpaces Web",
#     "new_name": "Amazon WorkSpaces Secure Browser",
#     "rename_date": "2024-11-18",
#     "notes": "Rebranded from WorkSpaces Web..."
# }
```

## Integration with Chat Lambda

### Enhanced Search

```python
# In chat_lambda.py
from euc_service_mapper import EUCServiceMapper

mapper = EUCServiceMapper()

def enhance_search_query(user_query):
    """Expand query to include historical service names"""
    # Get all related names
    expanded_terms = mapper.expand_query(user_query)
    
    # Search using all terms
    results = search_posts(expanded_terms)
    
    return results

# Example:
# User searches: "AppStream 2.0 setup"
# System searches: "AppStream 2.0" OR "WorkSpaces Applications" OR "Amazon AppStream"
# Finds content regardless of which name was used
```

### Contextual Responses

```python
def generate_response_with_context(service_name, user_query):
    """Add service context to AI response"""
    # Check if service was renamed
    rename_info = mapper.get_rename_info(service_name)
    
    if rename_info:
        context = f"Note: {rename_info['old_name']} was renamed to {rename_info['new_name']} in {rename_info['rename_date']}."
        # Include in AI prompt
    
    # Get related services
    related = mapper.get_related_services(service_name)
    if related:
        context += f" Related services: {', '.join(related)}"
    
    return context
```

## Use Cases

### 1. Chat Assistant
- Expand user queries with historical names
- Provide context about service renames
- Suggest related services
- Link content across name changes

### 2. Content Crawler
- Tag content with all service names
- Detect service mentions in blog posts
- Create relationships between posts
- Track service evolution

### 3. Search Enhancement
- Search using any service name
- Find related content
- Group by service family
- Filter by service type

### 4. Analytics
- Track service popularity over time
- Identify content gaps
- Measure rename impact
- Analyze service relationships

## Data Structure

### Service Entry

```json
{
  "current_name": "Amazon WorkSpaces Applications",
  "previous_names": ["Amazon AppStream 2.0", "Amazon AppStream"],
  "service_type": "application_streaming",
  "description": "Stream desktop applications to users",
  "keywords": ["appstream", "application streaming", "workspaces applications"],
  "related_services": ["Amazon WorkSpaces", "Amazon WorkSpaces Thin Client"],
  "launch_date": "2013-11-21",
  "rename_date": "2024-11-18",
  "documentation_url": "https://docs.aws.amazon.com/appstream2/",
  "notes": "Rebranded from AppStream 2.0 to WorkSpaces Applications in November 2024"
}
```

### Service Family

```json
{
  "workspaces_family": {
    "name": "Amazon WorkSpaces Family",
    "description": "Suite of end-user computing services",
    "services": [
      "Amazon WorkSpaces",
      "Amazon WorkSpaces Applications",
      "Amazon WorkSpaces Secure Browser",
      "Amazon WorkSpaces Thin Client",
      "Amazon WorkSpaces Core"
    ],
    "keywords": ["workspaces", "euc", "end user computing"]
  }
}
```

## Maintenance

### Adding New Services

1. Add entry to `euc-service-name-mapping.json`:
```json
{
  "current_name": "New Service Name",
  "previous_names": [],
  "service_type": "category",
  "description": "What it does",
  "keywords": ["keyword1", "keyword2"],
  "related_services": ["Related Service 1"],
  "launch_date": "YYYY-MM-DD",
  "rename_date": null,
  "documentation_url": "https://...",
  "notes": "Additional context"
}
```

2. Update service families if needed
3. Test with `python euc_service_mapper.py`

### Updating Service Names

When a service is renamed:

1. Move current name to `previous_names`
2. Update `current_name`
3. Set `rename_date`
4. Update `notes` with rename context
5. Keep `documentation_url` current

## Testing

Run the built-in tests:

```bash
python euc_service_mapper.py
```

Expected output:
```
=== Service Name Mapping Tests ===

1. Current name for 'AppStream 2.0':
   Amazon WorkSpaces Applications

2. All names for 'WorkSpaces Applications':
   ['Amazon WorkSpaces Applications', 'Amazon AppStream 2.0', 'Amazon AppStream']

3. Related services for 'WorkSpaces':
   ['Amazon WorkSpaces Applications', 'Amazon WorkSpaces Thin Client', ...]

...
```

## Benefits

1. **Better Search** - Find content regardless of service name used
2. **Historical Context** - Understand service evolution
3. **Content Linking** - Connect related posts across renames
4. **User Education** - Help users understand service relationships
5. **Future-Proof** - Easy to update as services evolve

## Future Enhancements

1. **API Endpoint** - Expose as REST API for frontend
2. **Caching** - Cache lookups in DynamoDB
3. **Analytics** - Track which names users search for
4. **Auto-Update** - Sync with AWS service catalog
5. **Versioning** - Track mapping changes over time

## Questions?

- How to add a new service? See "Adding New Services" above
- How to handle a rename? See "Updating Service Names" above
- How to integrate with chatbot? See "Integration with Chat Lambda" above
- How to test changes? Run `python euc_service_mapper.py`
