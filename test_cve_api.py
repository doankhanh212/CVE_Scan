#!/usr/bin/env python3
"""Test CVE analysis endpoint"""

import json
import requests

# Start app and test endpoint
try:
    # Test POST /api/cve/{id}/analysis
    response = requests.post(
        'http://localhost:5000/api/cve/CVE-2023-49441/analysis',
        json={},
        timeout=5
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response:")
    
    data = response.json()
    print(json.dumps(data, indent=2, default=str)[:2000])
    
except Exception as e:
    print(f"Error: {e}")
    print(f"Make sure Flask is running on localhost:5000")
