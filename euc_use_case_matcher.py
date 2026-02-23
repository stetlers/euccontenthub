"""
EUC Use Case Matcher
Helps match user requirements to the appropriate WorkSpaces service
"""

import json
from typing import List, Dict, Optional, Set


class EUCUseCaseMatcher:
    """Matches user requirements to appropriate EUC services"""
    
    def __init__(self, matcher_file='euc-use-case-matcher.json'):
        """Initialize with use case data"""
        with open(matcher_file, 'r') as f:
            self.data = json.load(f)
        
        self.services = self.data['services']
        self.decision_tree = self.data['decision_tree']
        self.comparison_matrix = self.data['comparison_matrix']
        
        # Build keyword index
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """Build index for keyword-based matching"""
        self.keyword_to_services = {}
        
        for service in self.services:
            service_name = service['service_name']
            keywords = service.get('keywords', [])
            
            for keyword in keywords:
                if keyword not in self.keyword_to_services:
                    self.keyword_to_services[keyword] = []
                self.keyword_to_services[keyword].append(service_name)
    
    def match_by_keywords(self, query: str) -> List[Dict]:
        """
        Match services based on keywords in user query
        
        Args:
            query: User query or requirements
        
        Returns:
            List of matching services with scores
        
        Example:
            >>> matcher.match_by_keywords("I need persistent desktops for developers")
            [{"service": "Amazon WorkSpaces Personal", "score": 2, "matched_keywords": ["persistent", "desktop"]}]
        """
        query_lower = query.lower()
        matches = {}
        
        for keyword, services in self.keyword_to_services.items():
            if keyword in query_lower:
                for service_name in services:
                    if service_name not in matches:
                        matches[service_name] = {
                            'service': service_name,
                            'score': 0,
                            'matched_keywords': []
                        }
                    matches[service_name]['score'] += 1
                    matches[service_name]['matched_keywords'].append(keyword)
        
        # Sort by score (highest first)
        result = sorted(matches.values(), key=lambda x: x['score'], reverse=True)
        return result
    
    def match_by_requirements(self, requirements: Dict[str, any]) -> List[str]:
        """
        Match services based on specific requirements
        
        Args:
            requirements: Dict of requirements
                - persistence: "persistent" | "non-persistent" | "both"
                - streaming_type: "desktop" | "applications" | "browser" | "both"
                - third_party: bool
                - multiple_use_cases: bool
                - existing_ec2: bool
        
        Returns:
            List of matching service names
        
        Example:
            >>> matcher.match_by_requirements({"persistence": "persistent", "third_party": False})
            ["Amazon WorkSpaces Personal"]
        """
        matching_services = set(s['service_name'] for s in self.services)
        
        # Filter by persistence
        if 'persistence' in requirements:
            persistence = requirements['persistence']
            matching_services = {
                s['service_name'] for s in self.services
                if (persistence == "both" and s['persistence'] in ["both_persistent_and_non_persistent"]) or
                   (persistence == "persistent" and s['persistence'] in ["persistent", "both_persistent_and_non_persistent"]) or
                   (persistence == "non-persistent" and s['persistence'] in ["non-persistent", "both_persistent_and_non_persistent"])
            }
        
        # Filter by third-party requirement
        if requirements.get('third_party'):
            matching_services &= {
                s['service_name'] for s in self.services
                if 'third_party_vendors' in s
            }
        elif 'third_party' in requirements and not requirements['third_party']:
            matching_services &= {
                s['service_name'] for s in self.services
                if 'third_party_vendors' not in s
            }
        
        # Filter by multiple use cases
        if requirements.get('multiple_use_cases'):
            matching_services &= {"Amazon WorkSpaces Core Managed Instances"}
        
        # Filter by existing EC2
        if requirements.get('existing_ec2'):
            matching_services &= {"Amazon WorkSpaces Core Managed Instances"}
        
        # Filter by streaming type
        if 'streaming_type' in requirements:
            streaming_type = requirements['streaming_type']
            if streaming_type == "browser":
                matching_services &= {"Amazon WorkSpaces Secure Browser"}
            elif streaming_type == "applications":
                matching_services &= {"Amazon WorkSpaces Applications", "Amazon WorkSpaces Core Managed Instances"}
        
        return list(matching_services)
    
    def get_service_details(self, service_name: str) -> Optional[Dict]:
        """
        Get detailed information about a service
        
        Args:
            service_name: Name of the service
        
        Returns:
            Service details dict or None
        """
        for service in self.services:
            if service['service_name'].lower() == service_name.lower():
                return service
        return None
    
    def compare_services(self, service_names: List[str]) -> Dict:
        """
        Compare multiple services side-by-side
        
        Args:
            service_names: List of service names to compare
        
        Returns:
            Comparison dict with attributes
        
        Example:
            >>> matcher.compare_services(["Amazon WorkSpaces Personal", "Amazon WorkSpaces Applications"])
            {
                "persistence": {
                    "Amazon WorkSpaces Personal": "Persistent",
                    "Amazon WorkSpaces Applications": "Non-persistent"
                },
                ...
            }
        """
        comparison = {}
        
        for attribute, values in self.comparison_matrix.items():
            comparison[attribute] = {
                service: values.get(service, "N/A")
                for service in service_names
            }
        
        return comparison
    
    def get_recommendation(self, query: str) -> Dict:
        """
        Get service recommendation based on user query
        
        Args:
            query: User query describing their needs
        
        Returns:
            Dict with recommended service and reasoning
        
        Example:
            >>> matcher.get_recommendation("I need persistent desktops for developers")
            {
                "recommended_service": "Amazon WorkSpaces Personal",
                "confidence": "high",
                "reasoning": "Best for persistent desktops...",
                "alternatives": ["Amazon WorkSpaces Core"],
                "matched_keywords": ["persistent", "desktop"]
            }
        """
        # Match by keywords
        keyword_matches = self.match_by_keywords(query)
        
        if not keyword_matches:
            return {
                "recommended_service": None,
                "confidence": "low",
                "reasoning": "Could not determine requirements from query",
                "alternatives": [],
                "matched_keywords": []
            }
        
        # Get top match
        top_match = keyword_matches[0]
        service_name = top_match['service']
        service_details = self.get_service_details(service_name)
        
        # Determine confidence
        confidence = "high" if top_match['score'] >= 3 else "medium" if top_match['score'] >= 2 else "low"
        
        # Get alternatives (other high-scoring matches)
        alternatives = [
            m['service'] for m in keyword_matches[1:3]
            if m['score'] >= top_match['score'] - 1
        ]
        
        # Build reasoning
        reasoning = f"Best for: {', '.join(service_details['best_for'][:2])}"
        
        return {
            "recommended_service": service_name,
            "confidence": confidence,
            "reasoning": reasoning,
            "alternatives": alternatives,
            "matched_keywords": top_match['matched_keywords'],
            "service_details": service_details
        }
    
    def explain_service_choice(self, service_name: str, user_requirements: str) -> str:
        """
        Generate explanation for why a service is recommended
        
        Args:
            service_name: Name of the service
            user_requirements: User's stated requirements
        
        Returns:
            Human-readable explanation
        """
        service = self.get_service_details(service_name)
        if not service:
            return f"Service '{service_name}' not found."
        
        explanation = f"{service_name} is recommended because:\n\n"
        
        # Add best-for reasons
        explanation += "✅ Best for:\n"
        for reason in service['best_for'][:3]:
            explanation += f"   - {reason}\n"
        
        # Add use cases
        explanation += f"\n📋 Use cases:\n"
        for use_case in service['use_cases'][:3]:
            explanation += f"   - {use_case}\n"
        
        # Add important notes if present
        if 'important_notes' in service:
            explanation += f"\n⚠️  Important notes:\n"
            for note in service['important_notes']:
                explanation += f"   - {note}\n"
        
        # Add not suitable for
        if service.get('not_suitable_for'):
            explanation += f"\n❌ Not suitable for:\n"
            for reason in service['not_suitable_for'][:2]:
                explanation += f"   - {reason}\n"
        
        return explanation


# Example usage
if __name__ == '__main__':
    matcher = EUCUseCaseMatcher()
    
    print("=== EUC Use Case Matcher Tests ===\n")
    
    # Test 1: Keyword matching
    print("1. Match by keywords: 'I need persistent desktops for developers'")
    matches = matcher.match_by_keywords("I need persistent desktops for developers")
    for match in matches[:3]:
        print(f"   - {match['service']} (score: {match['score']}, keywords: {match['matched_keywords']})")
    print()
    
    # Test 2: Requirements matching
    print("2. Match by requirements: persistent + no third-party")
    requirements = {"persistence": "persistent", "third_party": False}
    matches = matcher.match_by_requirements(requirements)
    for service in matches:
        print(f"   - {service}")
    print()
    
    # Test 3: Get recommendation
    print("3. Get recommendation: 'We need non-persistent application streaming'")
    recommendation = matcher.get_recommendation("We need non-persistent application streaming")
    print(f"   Recommended: {recommendation['recommended_service']}")
    print(f"   Confidence: {recommendation['confidence']}")
    print(f"   Reasoning: {recommendation['reasoning']}")
    print(f"   Alternatives: {recommendation['alternatives']}")
    print()
    
    # Test 4: Compare services
    print("4. Compare WorkSpaces Personal vs WorkSpaces Applications")
    comparison = matcher.compare_services([
        "Amazon WorkSpaces Personal",
        "Amazon WorkSpaces Applications"
    ])
    for attribute, values in comparison.items():
        print(f"   {attribute}:")
        for service, value in values.items():
            print(f"      - {service}: {value}")
    print()
    
    # Test 5: Explain service choice
    print("5. Explain why WorkSpaces Core Managed Instances is recommended")
    explanation = matcher.explain_service_choice(
        "Amazon WorkSpaces Core Managed Instances",
        "multiple use cases with existing EC2"
    )
    print(explanation)
