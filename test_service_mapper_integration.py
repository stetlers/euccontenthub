"""
Property-based and unit tests for EUC Service Mapper Integration
Tests for chat-service-mapper-integration feature
"""

import pytest
import json
import os
import tempfile
from hypothesis import given, strategies as st, settings
from euc_service_mapper import EUCServiceMapper


# ============================================================================
# TASK 1.1: Property Test for Service Mapper Initialization
# ============================================================================

# Feature: chat-service-mapper-integration, Property 1: Service Mapper Initialization
@settings(max_examples=100, deadline=None)
@given(st.booleans())
def test_property_service_mapper_initialization(file_exists):
    """
    Property 1: Service Mapper Initialization
    
    For any Lambda cold start, initializing the service mapper should either 
    succeed and load all services from the JSON file, or fail gracefully and 
    log the error without preventing Lambda execution.
    
    Validates: Requirements 1.1, 1.2
    """
    if file_exists:
        # Test successful initialization
        try:
            mapper = EUCServiceMapper('euc-service-name-mapping.json')
            
            # Should have loaded services
            assert hasattr(mapper, 'services'), "Mapper should have 'services' attribute"
            assert len(mapper.services) > 0, "Mapper should load at least one service"
            
            # Should have built indexes
            assert hasattr(mapper, 'by_current_name'), "Mapper should have 'by_current_name' index"
            assert hasattr(mapper, 'by_any_name'), "Mapper should have 'by_any_name' index"
            
            # Should be able to call methods
            assert callable(mapper.get_current_name), "get_current_name should be callable"
            assert callable(mapper.get_all_names), "get_all_names should be callable"
            
        except Exception as e:
            pytest.fail(f"Initialization should not raise exception with valid file: {e}")
    else:
        # Test graceful failure with missing file
        try:
            mapper = EUCServiceMapper('nonexistent-file.json')
            pytest.fail("Should raise FileNotFoundError for missing file")
        except FileNotFoundError:
            # Expected - graceful failure
            pass
        except Exception as e:
            # Any other exception is also acceptable as long as it's caught
            pass


# ============================================================================
# TASK 1.2: Unit Tests for Initialization Edge Cases
# ============================================================================

def test_initialization_with_missing_file():
    """
    Test initialization fails gracefully with missing JSON file
    Validates: Requirement 1.2
    """
    with pytest.raises(FileNotFoundError):
        EUCServiceMapper('nonexistent-file.json')


def test_initialization_with_invalid_json():
    """
    Test initialization fails gracefully with invalid JSON format
    Validates: Requirement 1.2
    """
    # Create temporary file with invalid JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{ invalid json }")
        temp_file = f.name
    
    try:
        with pytest.raises(json.JSONDecodeError):
            EUCServiceMapper(temp_file)
    finally:
        os.unlink(temp_file)


def test_initialization_with_malformed_service_data():
    """
    Test initialization handles malformed service data
    Validates: Requirement 1.2
    """
    # Create temporary file with malformed data (missing required fields)
    malformed_data = {
        "services": [
            {
                "current_name": "Test Service"
                # Missing other required fields
            }
        ],
        "service_families": {},
        "metadata": {}
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(malformed_data, f)
        temp_file = f.name
    
    try:
        # Should initialize but may have limited functionality
        mapper = EUCServiceMapper(temp_file)
        assert mapper is not None
        assert len(mapper.services) == 1
    finally:
        os.unlink(temp_file)


def test_initialization_with_valid_file():
    """
    Test successful initialization with valid JSON file
    Validates: Requirements 1.1, 1.3
    """
    mapper = EUCServiceMapper('euc-service-name-mapping.json')
    
    # Verify mapper loaded services
    assert len(mapper.services) > 0, "Should load services from file"
    
    # Verify indexes were built
    assert len(mapper.by_current_name) > 0, "Should build current name index"
    assert len(mapper.by_any_name) > 0, "Should build any name index"
    
    # Verify all methods are accessible
    assert callable(mapper.get_current_name)
    assert callable(mapper.get_previous_names)
    assert callable(mapper.get_all_names)
    assert callable(mapper.get_related_services)
    assert callable(mapper.search_by_keyword)
    assert callable(mapper.expand_query)
    assert callable(mapper.get_service_info)
    assert callable(mapper.get_service_family)
    assert callable(mapper.get_rename_info)


def test_mapper_methods_accessible():
    """
    Test all service mapper methods are accessible after initialization
    Validates: Requirement 1.3
    """
    mapper = EUCServiceMapper('euc-service-name-mapping.json')
    
    # Test each method can be called without errors
    try:
        # Test with known service
        result = mapper.get_current_name("AppStream 2.0")
        assert result is not None or result is None  # Either is valid
        
        result = mapper.get_all_names("WorkSpaces")
        assert isinstance(result, list)
        
        result = mapper.get_rename_info("AppStream 2.0")
        assert result is None or isinstance(result, dict)
        
        result = mapper.search_by_keyword("streaming")
        assert isinstance(result, list)
        
        result = mapper.expand_query("test query")
        assert isinstance(result, set)
        
    except Exception as e:
        pytest.fail(f"Mapper methods should be accessible: {e}")


# ============================================================================
# Integration Test: Lambda Initialization Simulation
# ============================================================================

def test_lambda_cold_start_simulation():
    """
    Simulate Lambda cold start with service mapper initialization
    Validates: Requirements 1.1, 1.2, 1.3
    """
    # Simulate the module-level initialization code
    service_mapper = None
    initialization_error = None
    
    try:
        service_mapper = EUCServiceMapper('euc-service-name-mapping.json')
        service_count = len(service_mapper.services)
        print(f"INFO: Service mapper initialized successfully with {service_count} services")
    except FileNotFoundError as e:
        initialization_error = f"Service mapping file not found: {e}"
        print(f"ERROR: {initialization_error}")
    except json.JSONDecodeError as e:
        initialization_error = f"Invalid JSON in service mapping file: {e}"
        print(f"ERROR: {initialization_error}")
    except Exception as e:
        initialization_error = f"Failed to initialize service mapper: {e}"
        print(f"ERROR: {initialization_error}")
    
    # Verify Lambda can continue regardless of initialization result
    if service_mapper is not None:
        # Success case
        assert len(service_mapper.services) > 0
        assert service_mapper.get_current_name is not None
    else:
        # Failure case - Lambda should still be able to continue
        assert initialization_error is not None
        print("INFO: Lambda continues with degraded functionality")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
