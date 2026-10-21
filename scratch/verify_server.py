import os
import sys
import requests
import json

def test_endpoints():
    base_url = "http://127.0.0.1:8765"
    print("Testing Assistant API endpoints...")
    
    # Check if server is running
    try:
        res = requests.get(f"{base_url}/api/status", timeout=2)
        print("Server status:", res.status_code)
    except Exception as e:
        print("Server is not currently running on port 8765. (Will be launched with main.py)")
        return

    # Check /api/projects
    try:
        res = requests.get(f"{base_url}/api/projects", timeout=5)
        print("\n--- /api/projects Response ---")
        projs = res.json()
        print(f"Total projects returned: {len(projs)}")
        for p in projs:
            print(f" - {p['name']}: exists={p['exists']}, size={p['content_length']} bytes")
    except Exception as e:
        print("Error fetching /api/projects:", e)

    # Check /api/outlook/attention
    try:
        res = requests.get(f"{base_url}/api/outlook/attention", timeout=5)
        print("\n--- /api/outlook/attention Response ---")
        items = res.json()
        print(f"Total active attention items: {len(items)}")
        for it in items[:3]:
            print(f" - From: {it.get('sender')} | Subject: {it.get('subject')} | Urgency: {it.get('urgency')}")
    except Exception as e:
        print("Error fetching /api/outlook/attention:", e)

if __name__ == "__main__":
    test_endpoints()
