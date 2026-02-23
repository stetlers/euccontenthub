#!/usr/bin/env python3
"""
Test WorkSpaces Personal Mapping
Verify that the service mapper correctly handles WorkSpaces vs WorkSpaces Personal
"""

from euc_service_mapper import EUCServiceMapper

def test_workspaces_personal():
    """Test WorkSpaces Personal mapping"""
    print("=" * 70)
    print("Test: WorkSpaces Personal Mapping")
    print("=" * 70)
    
    mapper = EUCServiceMapper()
    
    # Test 1: "WorkSpaces" should map to "WorkSpaces Personal"
    print("\n1. Current name for 'WorkSpaces':")
    current = mapper.get_current_name('WorkSpaces')
    print(f"   Result: {current}")
    print(f"   Expected: Amazon WorkSpaces Personal")
    print(f"   ✅ PASS" if current == "Amazon WorkSpaces Personal" else f"   ❌ FAIL")
    
    # Test 2: "Amazon WorkSpaces" should map to "WorkSpaces Personal"
    print("\n2. Current name for 'Amazon WorkSpaces':")
    current = mapper.get_current_name('Amazon WorkSpaces')
    print(f"   Result: {current}")
    print(f"   Expected: Amazon WorkSpaces Personal")
    print(f"   ✅ PASS" if current == "Amazon WorkSpaces Personal" else f"   ❌ FAIL")
    
    # Test 3: Get all names for WorkSpaces Personal
    print("\n3. All names for 'WorkSpaces Personal':")
    all_names = mapper.get_all_names('WorkSpaces Personal')
    print(f"   Result: {all_names}")
    print(f"   Expected: ['Amazon WorkSpaces Personal', 'Amazon WorkSpaces']")
    expected = ['Amazon WorkSpaces Personal', 'Amazon WorkSpaces']
    print(f"   ✅ PASS" if all_names == expected else f"   ❌ FAIL")
    
    # Test 4: Get rename info for WorkSpaces
    print("\n4. Rename info for 'WorkSpaces':")
    rename_info = mapper.get_rename_info('WorkSpaces')
    if rename_info:
        print(f"   Old name: {rename_info['old_name']}")
        print(f"   New name: {rename_info['new_name']}")
        print(f"   Rename date: {rename_info['rename_date']}")
        print(f"   ✅ PASS" if rename_info['new_name'] == "Amazon WorkSpaces Personal" else f"   ❌ FAIL")
    else:
        print(f"   ❌ FAIL - No rename info found")
    
    # Test 5: Verify AppStream 2.0 still maps correctly
    print("\n5. Current name for 'AppStream 2.0':")
    current = mapper.get_current_name('AppStream 2.0')
    print(f"   Result: {current}")
    print(f"   Expected: Amazon WorkSpaces Applications")
    print(f"   ✅ PASS" if current == "Amazon WorkSpaces Applications" else f"   ❌ FAIL")
    
    # Test 6: Verify they are different services
    print("\n6. Verify WorkSpaces Personal != WorkSpaces Applications:")
    ws_personal = mapper.get_current_name('WorkSpaces')
    ws_apps = mapper.get_current_name('AppStream 2.0')
    print(f"   WorkSpaces Personal: {ws_personal}")
    print(f"   WorkSpaces Applications: {ws_apps}")
    print(f"   Are different: {ws_personal != ws_apps}")
    print(f"   ✅ PASS" if ws_personal != ws_apps else f"   ❌ FAIL")
    
    # Test 7: Query expansion for "WorkSpaces"
    print("\n7. Query expansion for 'WorkSpaces setup':")
    expanded = mapper.expand_query('WorkSpaces setup')
    print(f"   Result: {expanded}")
    has_personal = 'Amazon WorkSpaces Personal' in expanded
    has_old_name = 'Amazon WorkSpaces' in expanded
    print(f"   Has 'Amazon WorkSpaces Personal': {has_personal}")
    print(f"   Has 'Amazon WorkSpaces': {has_old_name}")
    print(f"   ✅ PASS" if has_personal and has_old_name else f"   ❌ FAIL")
    
    # Test 8: Query expansion for "AppStream 2.0"
    print("\n8. Query expansion for 'AppStream 2.0 deployment':")
    expanded = mapper.expand_query('AppStream 2.0 deployment')
    print(f"   Result: {expanded}")
    has_apps = 'Amazon WorkSpaces Applications' in expanded
    has_appstream = 'Amazon AppStream 2.0' in expanded
    print(f"   Has 'Amazon WorkSpaces Applications': {has_apps}")
    print(f"   Has 'Amazon AppStream 2.0': {has_appstream}")
    print(f"   ✅ PASS" if has_apps and has_appstream else f"   ❌ FAIL")
    
    # Test 9: Service family
    print("\n9. Service family for 'WorkSpaces Personal':")
    family = mapper.get_service_family('WorkSpaces Personal')
    print(f"   Result: {family}")
    print(f"   Expected: Amazon WorkSpaces Family")
    print(f"   ✅ PASS" if family == "Amazon WorkSpaces Family" else f"   ❌ FAIL")
    
    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70)

if __name__ == '__main__':
    test_workspaces_personal()
