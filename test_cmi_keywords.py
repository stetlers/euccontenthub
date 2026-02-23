#!/usr/bin/env python3
"""Quick test for CMI keyword matching"""

from euc_use_case_matcher import EUCUseCaseMatcher

matcher = EUCUseCaseMatcher()

# Test query that was failing
query = "We have existing EC2 deployments and need both persistent desktops and non-persistent applications"

print(f"Query: {query}")
print()

# Get keyword matches
keyword_matches = matcher.match_by_keywords(query)

print("Keyword Matches:")
for match in keyword_matches[:5]:
    print(f"  {match['service']}: score={match['score']}, keywords={match['matched_keywords']}")
print()

# Get recommendation
recommendation = matcher.get_recommendation(query)

print("Recommendation:")
print(f"  Service: {recommendation['recommended_service']}")
print(f"  Confidence: {recommendation['confidence']}")
print(f"  Matched Keywords: {recommendation['matched_keywords']}")
print(f"  Reasoning: {recommendation['reasoning']}")
print()

if recommendation['recommended_service'] == "Amazon WorkSpaces Core Managed Instances":
    print("✅ SUCCESS - CMI correctly detected!")
else:
    print(f"❌ FAIL - Expected CMI, got {recommendation['recommended_service']}")
