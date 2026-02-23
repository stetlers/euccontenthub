"""
EUC Service Name Mapper
Utility for mapping service names, handling historical names, and finding related services
"""

import json
from typing import List, Dict, Optional, Set


class EUCServiceMapper:
    """Maps EUC service names including historical names and relationships"""
    
    def __init__(self, mapping_file='euc-service-name-mapping.json'):
        """Initialize with service mapping data"""
        with open(mapping_file, 'r') as f:
            self.data = json.load(f)
        
        self.services = self.data['services']
        self.service_families = self.data['service_families']
        
        # Build lookup indexes
        self._build_indexes()
    
    def _build_indexes(self):
        """Build indexes for fast lookups"""
        # Index by current name
        self.by_current_name = {
            s['current_name'].lower(): s for s in self.services
        }
        
        # Index by any name (current or previous)
        self.by_any_name = {}
        for service in self.services:
            # Add current name
            current_lower = service['current_name'].lower()
            self.by_any_name[current_lower] = service
            
            # Add current name without "Amazon" prefix
            if current_lower.startswith('amazon '):
                short_name = current_lower.replace('amazon ', '', 1)
                if short_name not in self.by_any_name:  # Don't overwrite if already exists
                    self.by_any_name[short_name] = service
            
            # Add previous names
            for prev_name in service.get('previous_names', []):
                prev_lower = prev_name.lower()
                self.by_any_name[prev_lower] = service
                
                # Add previous name without "Amazon" prefix
                if prev_lower.startswith('amazon '):
                    short_prev = prev_lower.replace('amazon ', '', 1)
                    if short_prev not in self.by_any_name:
                        self.by_any_name[short_prev] = service
        
        # Index by keyword
        self.by_keyword = {}
        for service in self.services:
            for keyword in service.get('keywords', []):
                if keyword not in self.by_keyword:
                    self.by_keyword[keyword] = []
                self.by_keyword[keyword].append(service)
    
    def _find_service_fuzzy(self, name: str) -> Optional[Dict]:
        """Find service with fuzzy matching"""
        name_lower = name.lower()
        
        # Try exact match first (highest priority)
        if name_lower in self.by_any_name:
            return self.by_any_name[name_lower]
        
        # Try exact match with "amazon" prefix
        amazon_name = f"amazon {name_lower}"
        if amazon_name in self.by_any_name:
            return self.by_any_name[amazon_name]
        
        # Try partial match - but prefer shorter matches (more specific)
        # This prevents "WorkSpaces" from matching "WorkSpaces Applications"
        matches = []
        for service in self.services:
            current_name_lower = service['current_name'].lower()
            
            # Check if name is in current name
            if name_lower in current_name_lower:
                # Calculate match quality (prefer exact or closer matches)
                match_quality = len(current_name_lower) - len(name_lower)
                matches.append((match_quality, service))
            
            # Try previous names
            for prev_name in service.get('previous_names', []):
                prev_name_lower = prev_name.lower()
                if name_lower in prev_name_lower:
                    match_quality = len(prev_name_lower) - len(name_lower)
                    matches.append((match_quality, service))
        
        # Return best match (lowest quality score = closest match)
        if matches:
            matches.sort(key=lambda x: x[0])
            return matches[0][1]
        
        return None
    
    def get_current_name(self, service_name: str) -> Optional[str]:
        """
        Get current name for a service (handles historical names)
        
        Args:
            service_name: Any name (current or historical)
        
        Returns:
            Current service name or None if not found
        
        Example:
            >>> mapper.get_current_name("AppStream 2.0")
            "Amazon WorkSpaces Applications"
        """
        service = self._find_service_fuzzy(service_name)
        return service['current_name'] if service else None
    
    def get_previous_names(self, service_name: str) -> List[str]:
        """
        Get all previous names for a service
        
        Args:
            service_name: Current or historical service name
        
        Returns:
            List of previous names
        
        Example:
            >>> mapper.get_previous_names("Amazon WorkSpaces Applications")
            ["Amazon AppStream 2.0", "Amazon AppStream"]
        """
        service = self._find_service_fuzzy(service_name)
        return service.get('previous_names', []) if service else []
    
    def get_all_names(self, service_name: str) -> List[str]:
        """
        Get all names (current + previous) for a service
        
        Args:
            service_name: Any service name
        
        Returns:
            List of all names (current first, then previous)
        
        Example:
            >>> mapper.get_all_names("AppStream")
            ["Amazon WorkSpaces Applications", "Amazon AppStream 2.0", "Amazon AppStream"]
        """
        service = self._find_service_fuzzy(service_name)
        if not service:
            return []
        
        return [service['current_name']] + service.get('previous_names', [])
    
    def get_related_services(self, service_name: str) -> List[str]:
        """
        Get related services
        
        Args:
            service_name: Any service name
        
        Returns:
            List of related service names
        
        Example:
            >>> mapper.get_related_services("WorkSpaces Applications")
            ["Amazon WorkSpaces", "Amazon WorkSpaces Thin Client"]
        """
        service = self._find_service_fuzzy(service_name)
        return service.get('related_services', []) if service else []
    
    def search_by_keyword(self, keyword: str) -> List[Dict]:
        """
        Search services by keyword
        
        Args:
            keyword: Search keyword
        
        Returns:
            List of matching services
        
        Example:
            >>> mapper.search_by_keyword("streaming")
            [{"current_name": "Amazon WorkSpaces Applications", ...}, ...]
        """
        keyword_lower = keyword.lower()
        
        # Exact keyword match
        if keyword_lower in self.by_keyword:
            return self.by_keyword[keyword_lower]
        
        # Partial keyword match
        matches = []
        for service in self.services:
            for kw in service.get('keywords', []):
                if keyword_lower in kw.lower():
                    matches.append(service)
                    break
        
        return matches
    
    def expand_query(self, query: str) -> Set[str]:
        """
        Expand a query to include all related service names
        
        Args:
            query: User query
        
        Returns:
            Set of search terms including historical names
        
        Example:
            >>> mapper.expand_query("AppStream 2.0 setup")
            {"AppStream 2.0", "Amazon WorkSpaces Applications", "Amazon AppStream", "setup"}
        """
        query_lower = query.lower()
        terms = set(query.split())
        expanded = set(terms)
        
        # Check for multi-word service names first (more specific)
        for service in self.services:
            # Check current name
            current_lower = service['current_name'].lower()
            if current_lower in query_lower:
                expanded.add(service['current_name'])
                expanded.update(service.get('previous_names', []))
            
            # Check previous names
            for prev_name in service.get('previous_names', []):
                if prev_name.lower() in query_lower:
                    expanded.add(service['current_name'])
                    expanded.update(service.get('previous_names', []))
        
        # Check each term against service names (single words)
        for term in terms:
            # Try to find matching service
            service = self.by_any_name.get(term.lower())
            if service:
                # Add all names for this service
                expanded.add(service['current_name'])
                expanded.update(service.get('previous_names', []))
        
        return expanded
    
    def get_service_info(self, service_name: str) -> Optional[Dict]:
        """
        Get complete service information
        
        Args:
            service_name: Any service name
        
        Returns:
            Service info dict or None
        """
        return self._find_service_fuzzy(service_name)
    
    def get_service_family(self, service_name: str) -> Optional[str]:
        """
        Get the service family for a service
        
        Args:
            service_name: Any service name
        
        Returns:
            Family name or None
        
        Example:
            >>> mapper.get_service_family("WorkSpaces")
            "Amazon WorkSpaces Family"
        """
        current_name = self.get_current_name(service_name)
        if not current_name:
            return None
        
        for family_id, family in self.service_families.items():
            if current_name in family['services']:
                return family['name']
        
        return None
    
    def get_rename_info(self, service_name: str) -> Optional[Dict]:
        """
        Get rename information for a service
        
        Args:
            service_name: Any service name
        
        Returns:
            Dict with rename info or None
        
        Example:
            >>> mapper.get_rename_info("AppStream 2.0")
            {
                "old_name": "Amazon AppStream 2.0",
                "new_name": "Amazon WorkSpaces Applications",
                "rename_date": "2024-11-18",
                "notes": "Rebranded from AppStream 2.0..."
            }
        """
        service = self._find_service_fuzzy(service_name)
        if not service or not service.get('rename_date'):
            return None
        
        previous_names = service.get('previous_names', [])
        if not previous_names:
            return None
        
        return {
            'old_name': previous_names[0],  # Most recent previous name
            'new_name': service['current_name'],
            'rename_date': service['rename_date'],
            'notes': service.get('notes', '')
        }


# Example usage
if __name__ == '__main__':
    mapper = EUCServiceMapper()
    
    # Test cases
    print("=== Service Name Mapping Tests ===\n")
    
    # Test 1: Get current name from historical name
    print("1. Current name for 'AppStream 2.0':")
    print(f"   {mapper.get_current_name('AppStream 2.0')}\n")
    
    # Test 2: Get all names
    print("2. All names for 'WorkSpaces Applications':")
    print(f"   {mapper.get_all_names('WorkSpaces Applications')}\n")
    
    # Test 3: Get related services
    print("3. Related services for 'WorkSpaces':")
    print(f"   {mapper.get_related_services('WorkSpaces')}\n")
    
    # Test 4: Search by keyword
    print("4. Services matching 'streaming':")
    for service in mapper.search_by_keyword('streaming'):
        print(f"   - {service['current_name']}")
    print()
    
    # Test 5: Expand query
    print("5. Expand query 'AppStream 2.0 setup':")
    print(f"   {mapper.expand_query('AppStream 2.0 setup')}\n")
    
    # Test 6: Get rename info
    print("6. Rename info for 'WorkSpaces Web':")
    info = mapper.get_rename_info('WorkSpaces Web')
    if info:
        print(f"   {info['old_name']} → {info['new_name']}")
        print(f"   Date: {info['rename_date']}")
    print()
    
    # Test 7: Get service family
    print("7. Service family for 'WorkSpaces':")
    print(f"   {mapper.get_service_family('WorkSpaces')}\n")
