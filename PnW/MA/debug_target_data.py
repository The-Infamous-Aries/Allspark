#!/usr/bin/env python3
"""
Debug script to check what fields are actually available in target nation data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Mock the nation data structure that would be returned by the API
# This simulates what the actual API returns based on the query we saw
mock_target_nation = {
    'id': '12345',
    'nation_name': 'Test Nation',
    'leader_name': 'Test Leader',
    'color': 'blue',
    'flag': 'https://example.com/flag.png',
    'discord': 'testuser#1234',
    'discord_id': '123456789',
    'beige_turns': 0,
    'num_cities': 5,
    'score': 3402.21,
    'espionage_available': True,
    'date': '2024-01-01',
    'last_active': '2024-01-01',
    'soldiers': 210000,
    'tanks': 16739,
    'aircraft': 632,
    'ships': 110,
    'missiles': 5,
    'nukes': 0,
    'spies': 50,
    'money': 1000000,
    'coal': 8000,
    'oil': 6000,
    'uranium': 500,
    'iron': 4000,
    'bauxite': 3000,
    'lead': 2500,
    'gasoline': 5000,
    'munitions': 3000,
    'steel': 2000,
    'aluminum': 1500,
    'food': 10000,
    'cities': [
        {'id': 1, 'name': 'City 1', 'infrastructure': 1000, 'stadium': 1, 'barracks': 5, 'factory': 5, 'airforcebase': 5, 'drydock': 3},
        {'id': 2, 'name': 'City 2', 'infrastructure': 1200, 'stadium': 1, 'barracks': 5, 'factory': 5, 'airforcebase': 5, 'drydock': 3},
        {'id': 3, 'name': 'City 3', 'infrastructure': 800, 'stadium': 0, 'barracks': 5, 'factory': 5, 'airforcebase': 5, 'drydock': 3},
        {'id': 4, 'name': 'City 4', 'infrastructure': 1500, 'stadium': 1, 'barracks': 5, 'factory': 5, 'airforcebase': 5, 'drydock': 3},
        {'id': 5, 'name': 'City 5', 'infrastructure': 900, 'stadium': 0, 'barracks': 5, 'factory': 5, 'airforcebase': 5, 'drydock': 3}
    ]
}

def debug_nation_data():
    print("=== Debug Target Nation Data ===")
    print(f"Available keys: {list(mock_target_nation.keys())}")
    print()
    
    # Test resource extraction with detailed debugging
    print("=== Resource Extraction Debug ===")
    resource_fields = ['money', 'coal', 'oil', 'uranium', 'iron', 'bauxite', 'lead', 'gasoline', 'munitions', 'steel', 'aluminum', 'food']
    
    for field in resource_fields:
        value = mock_target_nation.get(field)
        safe_value = mock_target_nation.get(field, 0) or 0
        print(f"{field}: {value} (type: {type(value)}) -> safe: {safe_value}")
    
    print()
    
    # Test military extraction
    print("=== Military Extraction Debug ===")
    military_fields = ['soldiers', 'tanks', 'aircraft', 'ships', 'missiles', 'nukes']
    
    for field in military_fields:
        value = mock_target_nation.get(field)
        safe_value = mock_target_nation.get(field, 0) or 0
        print(f"{field}: {value} (type: {type(value)}) -> safe: {safe_value}")
    
    print()
    
    # Test cities and infrastructure
    print("=== Cities Debug ===")
    cities = mock_target_nation.get('cities', [])
    print(f"Number of cities: {len(cities)}")
    
    if cities:
        print(f"First city keys: {list(cities[0].keys()) if isinstance(cities[0], dict) else 'Not a dict'}")
        
        total_infra = 0
        for i, city in enumerate(cities):
            if isinstance(city, dict):
                infra = city.get('infrastructure', 0) or 0
                total_infra += infra
                print(f"City {i+1}: {city.get('name', 'Unknown')} - Infrastructure: {infra}")
        
        print(f"Total infrastructure calculated: {total_infra}")
    
    print()
    
    # Test what might cause zero values
    print("=== Zero Value Analysis ===")
    for field in resource_fields:
        value = mock_target_nation.get(field)
        safe_value = mock_target_nation.get(field, 0) or 0
        if safe_value == 0:
            print(f"{field} is zero: original value = {value}, type = {type(value)}")

if __name__ == "__main__":
    debug_nation_data()