#!/usr/bin/env python3
"""
Debug script to check actual API responses
"""

import urllib.request
import json

def test_endpoint(url):
    try:
        req = urllib.request.Request(url, method='GET', headers={'User-Agent': 'AssumptionHunter/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            print(f"URL: {url}")
            print(f"Status: {response.status}")
            print(f"Content-Type: {response.getheader('Content-Type')}")
            
            content = response.read()
            print(f"Content length: {len(content)}")
            
            if 'application/json' in response.getheader('Content-Type', ''):
                try:
                    data = json.loads(content.decode('utf-8'))
                    print("JSON keys:", list(data.keys()) if isinstance(data, dict) else "Not a dict")
                    if isinstance(data, dict) and len(str(data)) < 1000:
                        print("JSON content:", data)
                    else:
                        print("JSON content: (too large to display)")
                except json.JSONDecodeError:
                    print("Not valid JSON")
            else:
                print("Content preview:", content.decode('utf-8')[:200])
                
            print("-" * 50)
            
    except Exception as e:
        print(f"Error: {e}")

# Test the endpoints from our assumptions
endpoints = [
    "https://api.github.com",
    "https://jsonplaceholder.typicode.com/posts/1", 
    "https://httpbin.org/get",
    "https://httpbin.org/user-agent",
    "https://api.publicapis.org/random"
]

for endpoint in endpoints:
    test_endpoint(endpoint)