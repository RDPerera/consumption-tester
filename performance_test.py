#!/usr/bin/env python3
"""
Performance Testing Script for WSO2 MI Server
Tests different API endpoints with various payload sizes to measure TPS and capacity
"""

import requests
import json
import time
import statistics
import threading
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import sys

# Configuration
BASE_URL = "http://localhost:8290/restapi"
ENDPOINTS = {
    "small": "/small",
    "medium": "/medium",
    "large": "/large",
    "verylarge": "/verylarge"
}

# Sample payloads
SMALL_PAYLOAD = {
    "username": "testUser",
    "password": "password123",
    "email": "test@example.com"
}

MEDIUM_PAYLOAD = {
    "orderId": "ORD-{id}",
    "customer": {
        "id": "CUST-{id}",
        "name": "Customer {id}",
        "email": "customer{id}@example.com",
        "phone": "+1-555-0100"
    },
    "items": [
        {
            "itemId": "ITEM-001",
            "name": "Product A",
            "quantity": 2,
            "price": 29.99
        },
        {
            "itemId": "ITEM-002",
            "name": "Product B",
            "quantity": 1,
            "price": 49.99
        },
        {
            "itemId": "ITEM-003",
            "name": "Product C",
            "quantity": 3,
            "price": 19.99
        }
    ],
    "total": 129.96,
    "orderDate": "2026-01-20T10:00:00Z",
    "status": "pending"
}

LARGE_PAYLOAD = {
    "batchId": "BATCH-{id}",
    "records": [
        {
            "id": i,
            "name": f"Record {i}",
            "email": f"record{i}@example.com",
            "description": f"Description for record {i}" * 10
        }
        for i in range(1, 51)  # 50 records
    ]
}

VERY_LARGE_PAYLOAD = {
    "batchId": "BATCH-{id}",
    "metadata": {
        "source": "performance-test",
        "timestamp": "2026-01-20T10:00:00Z",
        "version": "1.0"
    },
    "records": [
        {
            "id": i,
            "name": f"Record {i}",
            "email": f"record{i}@example.com",
            "address": {
                "street": f"{i} Main Street",
                "city": "TestCity",
                "state": "TS",
                "zipCode": f"{10000 + i}"
            },
            "description": f"Very detailed description for record {i}" * 20,
            "tags": [f"tag{j}" for j in range(10)],
            "metadata": {f"key{j}": f"value{j}" for j in range(10)}
        }
        for i in range(1, 201)  # 200 records
    ]
}

# Thread-safe counters
class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.success_count = 0
        self.error_count = 0
        self.response_times = []
        self.status_codes = defaultdict(int)
        self.errors = []

    def add_success(self, response_time, status_code):
        with self.lock:
            self.success_count += 1
            self.response_times.append(response_time)
            self.status_codes[status_code] += 1

    def add_error(self, error_msg):
        with self.lock:
            self.error_count += 1
            self.errors.append(error_msg)

    def get_stats(self):
        with self.lock:
            if self.response_times:
                return {
                    "success": self.success_count,
                    "errors": self.error_count,
                    "total": self.success_count + self.error_count,
                    "avg_response_time": statistics.mean(self.response_times),
                    "min_response_time": min(self.response_times),
                    "max_response_time": max(self.response_times),
                    "median_response_time": statistics.median(self.response_times),
                    "p95_response_time": self._percentile(self.response_times, 95),
                    "p99_response_time": self._percentile(self.response_times, 99),
                    "status_codes": dict(self.status_codes),
                    "error_samples": self.errors[:10]  # First 10 errors
                }
            return {
                "success": 0,
                "errors": self.error_count,
                "total": self.error_count,
                "error_samples": self.errors[:10]
            }

    @staticmethod
    def _percentile(data, percentile):
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]


def make_request(endpoint, payload, stats, request_id):
    """Make a single HTTP request"""
    url = BASE_URL + endpoint
    
    # Replace placeholders in payload
    payload_str = json.dumps(payload).replace("{id}", str(request_id))
    payload_dict = json.loads(payload_str)
    
    try:
        start_time = time.time()
        response = requests.post(
            url,
            json=payload_dict,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response_time = time.time() - start_time
        
        stats.add_success(response_time, response.status_code)
        return True
    except requests.exceptions.Timeout:
        stats.add_error("Timeout")
        return False
    except requests.exceptions.RequestException as e:
        stats.add_error(str(e))
        return False


def run_load_test(endpoint_name, payload, duration_seconds, concurrent_users):
    """Run load test for specified duration with given concurrency"""
    print(f"\n{'='*80}")
    print(f"Testing endpoint: {endpoint_name}")
    print(f"Duration: {duration_seconds}s | Concurrent Users: {concurrent_users}")
    print(f"Payload size: ~{len(json.dumps(payload))} bytes")
    print(f"{'='*80}")
    
    stats = Stats()
    start_time = time.time()
    end_time = start_time + duration_seconds
    request_counter = 0
    
    def worker():
        nonlocal request_counter
        while time.time() < end_time:
            request_counter += 1
            make_request(ENDPOINTS[endpoint_name], payload, stats, request_counter)
    
    # Start threads
    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [executor.submit(worker) for _ in range(concurrent_users)]
        
        # Wait for completion
        for future in as_completed(futures):
            future.result()
    
    actual_duration = time.time() - start_time
    results = stats.get_stats()
    
    # Calculate TPS
    tps = results["success"] / actual_duration if actual_duration > 0 else 0
    
    # Print results
    print(f"\n{'='*80}")
    print(f"RESULTS for {endpoint_name}")
    print(f"{'='*80}")
    print(f"Total Requests:      {results['total']}")
    print(f"Successful:          {results['success']} ({results['success']/results['total']*100:.2f}%)")
    print(f"Failed:              {results['errors']}")
    print(f"Actual Duration:     {actual_duration:.2f}s")
    print(f"Transactions/Second: {tps:.2f} TPS")
    
    if results['success'] > 0:
        print(f"\nResponse Times (seconds):")
        print(f"  Average:   {results['avg_response_time']:.4f}s")
        print(f"  Minimum:   {results['min_response_time']:.4f}s")
        print(f"  Maximum:   {results['max_response_time']:.4f}s")
        print(f"  Median:    {results['median_response_time']:.4f}s")
        print(f"  95th %ile: {results['p95_response_time']:.4f}s")
        print(f"  99th %ile: {results['p99_response_time']:.4f}s")
        
        print(f"\nStatus Codes:")
        for code, count in sorted(results['status_codes'].items()):
            print(f"  {code}: {count}")
    
    if results['errors'] > 0:
        print(f"\nError Samples (first 10):")
        for error in results['error_samples']:
            print(f"  - {error}")
    
    print(f"{'='*80}\n")
    
    return {
        "endpoint": endpoint_name,
        "tps": tps,
        "success_rate": results['success']/results['total']*100 if results['total'] > 0 else 0,
        "avg_response_time": results.get('avg_response_time', 0),
        "results": results
    }


def ramp_up_test(endpoint_name, payload, duration_per_level=30, max_concurrent=100, step=10):
    """Gradually increase load to find breaking point"""
    print(f"\n{'#'*80}")
    print(f"RAMP-UP TEST for {endpoint_name}")
    print(f"Duration per level: {duration_per_level}s | Max concurrent: {max_concurrent} | Step: {step}")
    print(f"{'#'*80}")
    
    results = []
    for concurrent in range(step, max_concurrent + 1, step):
        result = run_load_test(endpoint_name, payload, duration_per_level, concurrent)
        results.append({
            "concurrent_users": concurrent,
            "tps": result["tps"],
            "success_rate": result["success_rate"],
            "avg_response_time": result["avg_response_time"]
        })
        
        # Stop if success rate drops below 95%
        if result["success_rate"] < 95:
            print(f"\n⚠️  Success rate dropped below 95% at {concurrent} concurrent users")
            print(f"Maximum sustainable load appears to be around {concurrent - step} concurrent users")
            break
        
        # Brief pause between levels
        time.sleep(2)
    
    # Summary
    print(f"\n{'#'*80}")
    print(f"RAMP-UP TEST SUMMARY for {endpoint_name}")
    print(f"{'#'*80}")
    print(f"{'Concurrent Users':<20} {'TPS':<15} {'Success Rate':<15} {'Avg Response (s)':<20}")
    print(f"{'-'*70}")
    for r in results:
        print(f"{r['concurrent_users']:<20} {r['tps']:<15.2f} {r['success_rate']:<14.2f}% {r['avg_response_time']:<20.4f}")
    print(f"{'#'*80}\n")


def sustained_load_test(endpoint_name, payload, duration=300, concurrent=50):
    """Run sustained load test"""
    print(f"\n{'#'*80}")
    print(f"SUSTAINED LOAD TEST for {endpoint_name}")
    print(f"Duration: {duration}s ({duration/60:.1f} minutes) | Concurrent Users: {concurrent}")
    print(f"{'#'*80}")
    
    result = run_load_test(endpoint_name, payload, duration, concurrent)
    
    print(f"\n✓ Sustained {result['tps']:.2f} TPS over {duration}s with {result['success_rate']:.2f}% success rate")


def all_endpoints_test(duration=60, concurrent=20):
    """Test all endpoints sequentially"""
    print(f"\n{'#'*80}")
    print(f"TESTING ALL ENDPOINTS")
    print(f"Duration per endpoint: {duration}s | Concurrent Users: {concurrent}")
    print(f"{'#'*80}")
    
    payloads = {
        "small": SMALL_PAYLOAD,
        "medium": MEDIUM_PAYLOAD,
        "large": LARGE_PAYLOAD,
        "verylarge": VERY_LARGE_PAYLOAD
    }
    
    results = []
    for endpoint_name, payload in payloads.items():
        result = run_load_test(endpoint_name, payload, duration, concurrent)
        results.append(result)
        time.sleep(2)  # Brief pause between tests
    
    # Summary
    print(f"\n{'#'*80}")
    print(f"ALL ENDPOINTS SUMMARY")
    print(f"{'#'*80}")
    print(f"{'Endpoint':<15} {'TPS':<15} {'Success Rate':<15} {'Avg Response (s)':<20}")
    print(f"{'-'*65}")
    for r in results:
        print(f"{r['endpoint']:<15} {r['tps']:<15.2f} {r['success_rate']:<14.2f}% {r['avg_response_time']:<20.4f}")
    print(f"{'#'*80}\n")


def main():
    parser = argparse.ArgumentParser(description="WSO2 MI Performance Testing Tool")
    parser.add_argument("--mode", choices=["single", "rampup", "sustained", "all"], default="single",
                        help="Test mode (default: single)")
    parser.add_argument("--endpoint", choices=["small", "medium", "large", "verylarge"], default="medium",
                        help="Endpoint to test (default: medium)")
    parser.add_argument("--duration", type=int, default=60,
                        help="Test duration in seconds (default: 60)")
    parser.add_argument("--concurrent", type=int, default=20,
                        help="Number of concurrent users (default: 20)")
    parser.add_argument("--max-concurrent", type=int, default=100,
                        help="Maximum concurrent users for ramp-up test (default: 100)")
    parser.add_argument("--step", type=int, default=10,
                        help="Concurrent user increment for ramp-up test (default: 10)")
    parser.add_argument("--url", default="http://localhost:8290/restapi",
                        help="Base URL (default: http://localhost:8290/restapi)")
    
    args = parser.parse_args()
    
    global BASE_URL
    BASE_URL = args.url
    
    payloads = {
        "small": SMALL_PAYLOAD,
        "medium": MEDIUM_PAYLOAD,
        "large": LARGE_PAYLOAD,
        "verylarge": VERY_LARGE_PAYLOAD
    }
    
    print(f"\n{'='*80}")
    print(f"WSO2 MI PERFORMANCE TESTING TOOL")
    print(f"Target: {BASE_URL}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    try:
        if args.mode == "single":
            run_load_test(args.endpoint, payloads[args.endpoint], args.duration, args.concurrent)
        elif args.mode == "rampup":
            ramp_up_test(args.endpoint, payloads[args.endpoint], args.duration, args.max_concurrent, args.step)
        elif args.mode == "sustained":
            sustained_load_test(args.endpoint, payloads[args.endpoint], args.duration, args.concurrent)
        elif args.mode == "all":
            all_endpoints_test(args.duration, args.concurrent)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
