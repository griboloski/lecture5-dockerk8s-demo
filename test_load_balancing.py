#!/usr/bin/env python3
"""
Load Balancing Test Script
Tests that Kubernetes is distributing requests across multiple pods
"""
import requests
import time
from collections import Counter

SERVICE_URL = "http://localhost/info"
NUM_REQUESTS = 20

print(f"🚀 Testing load balancing across pods...")
print(f"📍 Service URL: {SERVICE_URL}")
print(f"🔄 Making {NUM_REQUESTS} requests...\n")

pod_responses = []

for i in range(NUM_REQUESTS):
    try:
        response = requests.get(SERVICE_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            pod_name = data.get('pod_name', 'unknown')
            pod_responses.append(pod_name)
            print(f"Request {i+1:2d}: Served by {pod_name}")
        else:
            print(f"Request {i+1:2d}: Error - Status {response.status_code}")
    except Exception as e:
        print(f"Request {i+1:2d}: Failed - {e}")
    
    time.sleep(0.1)

print("\n" + "="*60)
print("📊 LOAD BALANCING RESULTS")
print("="*60)

if pod_responses:
    counter = Counter(pod_responses)
    total = len(pod_responses)
    
    print(f"\nTotal successful requests: {total}")
    print(f"Number of unique pods serving requests: {len(counter)}\n")
    
    for pod, count in counter.most_common():
        percentage = (count / total) * 100
        bar = "█" * int(percentage / 5)
        print(f"{pod}: {count:2d} requests ({percentage:5.1f}%) {bar}")
    
    print("\n" + "="*60)
    if len(counter) > 1:
        print("✅ SUCCESS: Load balancing is working!")
        print(f"   Traffic distributed across {len(counter)} pods")
    else:
        print("⚠️  WARNING: All requests went to the same pod")
        print("   Load balancing might not be working as expected")
else:
    print("❌ ERROR: No successful requests")

print("="*60)