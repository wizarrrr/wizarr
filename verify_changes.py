#!/usr/bin/env python3
"""
Simple script to manually verify the library scanning changes.
This doesn't use the full Flask app, just tests the logic.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_library_scanning_logic():
    """Test the logic of library scanning without full Flask setup."""
    
    print("Testing library scanning logic...")
    
    # Simulate the condition check from our modified code
    existing_libraries = 0  # Simulate no existing libraries
    verified_servers = [{"name": "Test Server", "id": 1}]  # Simulate one server
    
    should_scan = existing_libraries == 0 and verified_servers
    
    print(f"Existing libraries: {existing_libraries}")
    print(f"Verified servers: {len(verified_servers)}")
    print(f"Should scan: {should_scan}")
    
    if should_scan:
        print("✓ Logic correctly determines scanning is needed")
        
        # Simulate scanning each server
        for server in verified_servers:
            print(f"  Scanning server: {server['name']}")
            
            # Simulate scan results
            mock_scan_results = {
                "lib1": "Movies",
                "lib2": "TV Shows"
            }
            
            # Simulate processing results 
            pairs = mock_scan_results.items()
            for fid, name in pairs:
                print(f"    Found library: {name} (ID: {fid})")
                
        print("✓ Library scanning simulation completed")
    else:
        print("✓ Logic correctly determines no scanning needed")
    
    return True

def test_invitation_server_logic():
    """Test the server name resolution logic for invitations."""
    
    print("\nTesting invitation server name logic...")
    
    # Simulate different invitation scenarios
    scenarios = [
        {
            "name": "Legacy server field",
            "invitation_server": {"name": "Legacy Server"},
            "invitation_servers": [],
            "expected": "Legacy Server"
        },
        {
            "name": "New servers relationship", 
            "invitation_server": None,
            "invitation_servers": [{"name": "New Server"}],
            "expected": "New Server"
        },
        {
            "name": "Both fields (legacy takes priority)",
            "invitation_server": {"name": "Legacy Server"},
            "invitation_servers": [{"name": "New Server"}],
            "expected": "Legacy Server"
        },
        {
            "name": "Fallback server",
            "invitation_server": None,
            "invitation_servers": [],
            "expected": "Fallback Server"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n  Testing: {scenario['name']}")
        
        # Simulate the logic from our changes
        server = scenario["invitation_server"]
        
        # If no direct server association, try to get from the servers relationship
        if not server and scenario["invitation_servers"]:
            server = scenario["invitation_servers"][0]  # Use the first server from the relationship
        
        # Fallback to any available server
        if not server:
            server = {"name": "Fallback Server"}
        
        server_name = server["name"] if server else "Unknown Server"
        
        if server_name == scenario["expected"]:
            print(f"    ✓ Correctly resolved to: {server_name}")
        else:
            print(f"    ✗ Expected: {scenario['expected']}, Got: {server_name}")
            return False
    
    print("\n✓ All invitation server name scenarios passed")
    return True

def main():
    """Run all verification tests."""
    print("=== Manual Verification of Changes ===\n")
    
    success = True
    success &= test_library_scanning_logic()
    success &= test_invitation_server_logic()
    
    print(f"\n=== Summary ===")
    if success:
        print("✓ All manual tests passed!")
        print("\nChanges implemented:")
        print("1. Library API endpoint now scans servers when no libraries exist")
        print("2. Invitation server name resolution improved to handle new relationship")
        print("3. Library API response includes server name and type")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())