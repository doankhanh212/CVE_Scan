#!/usr/bin/env python3
"""Test NVD API connectivity directly."""

import requests
import json
from colorama import Fore, Style, init

init()

def test_nvd_api(api_key):
    """Test NVD API with different methods."""
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Testing NVD API with key: {api_key[:10]}...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    # Test 1: Original method (header)
    print(f"{Fore.YELLOW}Test 1: Using header 'apiKey'{Style.RESET_ALL}")
    try:
        url = "https://services.nvd.nist.gov/rest/json/cves/1.0"
        headers = {"apiKey": api_key}
        params = {"resultsPerPage": 1}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
    
    # Test 2: Using key parameter
    print(f"\n{Fore.YELLOW}Test 2: Using parameter 'key'{Style.RESET_ALL}")
    try:
        url = "https://services.nvd.nist.gov/rest/json/cves/1.0"
        params = {"key": api_key, "resultsPerPage": 1}
        
        response = requests.get(url, params=params, timeout=10)
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
    
    # Test 3: New NVD API (v2)
    print(f"\n{Fore.YELLOW}Test 3: Using NVD API v2 endpoint{Style.RESET_ALL}")
    try:
        url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        headers = {"apiKey": api_key}
        params = {"resultsPerPage": 1}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
    
    # Test 4: Simple test without API key
    print(f"\n{Fore.YELLOW}Test 4: Without API key (limited results){Style.RESET_ALL}")
    try:
        url = "https://services.nvd.nist.gov/rest/json/cves/1.0"
        params = {"resultsPerPage": 1}
        
        response = requests.get(url, params=params, timeout=10)
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    # Get API key from user
    api_key = input("Enter your NVD API key: ").strip()
    
    if not api_key:
        print(f"{Fore.RED}API key required!{Style.RESET_ALL}")
        exit(1)
    
    test_nvd_api(api_key)
