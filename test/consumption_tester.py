#!/usr/bin/env python3
"""
WSO2 MI Consumption Tester - Comprehensive Performance Testing Tool
Tests REST APIs and RabbitMQ listener with realistic payload sizes and random data
"""

import requests
import json
import time
import statistics
import threading
import argparse
import random
import string
import pika
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import sys

# Configuration
BASE_URL = "http://localhost:8290/restapi"
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USER = "guest"
RABBITMQ_PASSWORD = "guest"
RABBITMQ_QUEUE = "orderQueue"

# Load sample payload files
LARGE_PAYLOAD_TEMPLATE = None
VERY_LARGE_PAYLOAD_TEMPLATE = None

def load_payload_templates():
    """Load large payload templates from files"""
    global LARGE_PAYLOAD_TEMPLATE, VERY_LARGE_PAYLOAD_TEMPLATE
    try:
        with open('sample-large-payload-request.json', 'r') as f:
            LARGE_PAYLOAD_TEMPLATE = json.load(f)
    except:
        LARGE_PAYLOAD_TEMPLATE = None
    
    try:
        with open('sample-very-large-payload-request.json', 'r') as f:
            VERY_LARGE_PAYLOAD_TEMPLATE = json.load(f)
    except:
        VERY_LARGE_PAYLOAD_TEMPLATE = None

# Payload size categories (in KB)
PAYLOAD_SIZES = {
    "small": (1, 10),           # 1-10 KB
    "medium": (10, 100),         # 10-100 KB (most common)
    "large": (100, 1024),        # 100 KB - 1 MB
    "very_large": (1024, 10240)  # 1-10 MB
}

# API endpoints
API_ENDPOINTS = {
    "small": "/small",
    "medium": "/medium",
    "large": "/large",
    "verylarge": "/verylarge"
}


class Stats:
    """Thread-safe statistics collector"""
    def __init__(self):
        self.lock = threading.Lock()
        self.success_count = 0
        self.error_count = 0
        self.response_times = []
        self.status_codes = defaultdict(int)
        self.errors = []
        self.payload_sizes = []

    def add_success(self, response_time, status_code, payload_size):
        with self.lock:
            self.success_count += 1
            self.response_times.append(response_time)
            self.status_codes[status_code] += 1
            self.payload_sizes.append(payload_size)

    def add_error(self, error_msg):
        with self.lock:
            self.error_count += 1
            if len(self.errors) < 100:  # Keep max 100 error samples
                self.errors.append(error_msg)

    def get_stats(self):
        with self.lock:
            total = self.success_count + self.error_count
            if self.response_times:
                return {
                    "success": self.success_count,
                    "errors": self.error_count,
                    "total": total,
                    "success_rate": (self.success_count / total * 100) if total > 0 else 0,
                    "avg_response_time": statistics.mean(self.response_times),
                    "min_response_time": min(self.response_times),
                    "max_response_time": max(self.response_times),
                    "median_response_time": statistics.median(self.response_times),
                    "p95_response_time": self._percentile(self.response_times, 95),
                    "p99_response_time": self._percentile(self.response_times, 99),
                    "avg_payload_size": statistics.mean(self.payload_sizes) if self.payload_sizes else 0,
                    "min_payload_size": min(self.payload_sizes) if self.payload_sizes else 0,
                    "max_payload_size": max(self.payload_sizes) if self.payload_sizes else 0,
                    "status_codes": dict(self.status_codes),
                    "error_samples": self.errors[:20]
                }
            return {
                "success": 0,
                "errors": self.error_count,
                "total": total,
                "success_rate": 0,
                "error_samples": self.errors[:20]
            }

    @staticmethod
    def _percentile(data, percentile):
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]


class PayloadGenerator:
    """Generate random payloads of specified sizes"""
    
    @staticmethod
    def random_string(length):
        """Generate random string"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_email():
        """Generate random email"""
        name = PayloadGenerator.random_string(8)
        return "{}@example.com".format(name)
    
    @staticmethod
    def random_phone():
        """Generate random phone number"""
        num = random.randint(1000, 9999)
        return "+1-555-{}".format(num)
    
    @staticmethod
    def random_address():
        """Generate random address"""
        return {
            "street": "{} {} St".format(random.randint(1, 9999), PayloadGenerator.random_string(8)),
            "city": PayloadGenerator.random_string(10),
            "state": PayloadGenerator.random_string(2).upper(),
            "zipCode": str(random.randint(10000, 99999))
        }
    
    @staticmethod
    def generate_small_payload(request_id):
        """Generate 1-10 KB payload (auth, status checks, simple CRUD)"""
        # Base structure
        payload = {
            "username": f"user_{request_id}",
            "password": PayloadGenerator.random_string(16),
            "email": PayloadGenerator.random_email(),
            "sessionId": PayloadGenerator.random_string(32),
            "timestamp": datetime.now().isoformat(),
            "requestId": f"REQ-{request_id}",
            "metadata": {
                "userAgent": "ConsumptionTester/1.0",
                "ipAddress": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                "deviceId": PayloadGenerator.random_string(24)
            }
        }
        
        # Pad to reach target size (1-10 KB)
        target_size = random.randint(1, 10) * 1024
        current_size = len(json.dumps(payload))
        if current_size < target_size:
            padding_size = target_size - current_size - 100
            payload["padding"] = PayloadGenerator.random_string(padding_size)
        
        return payload
    
    @staticmethod
    def generate_medium_payload(request_id):
        """Generate 10-100 KB payload (business transactions, orders)"""
        payload = {
            "orderId": f"ORD-{request_id}",
            "customer": {
                "id": f"CUST-{random.randint(1000, 9999)}",
                "name": f"{PayloadGenerator.random_string(8)} {PayloadGenerator.random_string(10)}",
                "email": PayloadGenerator.random_email(),
                "phone": PayloadGenerator.random_phone(),
                "address": PayloadGenerator.random_address(),
                "loyaltyPoints": random.randint(0, 10000),
                "accountStatus": random.choice(["active", "premium", "standard"])
            },
            "orderDate": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
            "totalAmount": round(random.uniform(10, 1000), 2),
            "items": [],
            "status": random.choice(["pending", "confirmed", "processing", "shipped", "delivered"]),
            "priority": random.choice(["low", "normal", "high", "urgent"]),
            "shippingAddress": PayloadGenerator.random_address(),
            "billingAddress": PayloadGenerator.random_address(),
            "paymentMethod": {
                "type": random.choice(["credit_card", "debit_card", "paypal", "bank_transfer"]),
                "last4": f"{random.randint(1000, 9999)}",
                "expiryDate": f"{random.randint(1, 12):02d}/{random.randint(25, 30)}"
            },
            "notes": PayloadGenerator.random_string(random.randint(50, 200))
        }
        
        # Add random number of items
        num_items = random.randint(1, 20)
        for i in range(num_items):
            payload["items"].append({
                "productId": f"PROD-{random.randint(100, 999):03d}",
                "name": PayloadGenerator.random_string(random.randint(10, 30)),
                "quantity": random.randint(1, 10),
                "price": round(random.uniform(5, 500), 2),
                "subtotal": round(random.uniform(5, 500), 2),
                "category": PayloadGenerator.random_string(10),
                "sku": PayloadGenerator.random_string(12),
                "description": PayloadGenerator.random_string(random.randint(50, 150))
            })
        
        # Pad to reach target size (10-100 KB)
        target_size = random.randint(10, 100) * 1024
        current_size = len(json.dumps(payload))
        if current_size < target_size:
            padding_size = target_size - current_size - 100
            payload["additionalData"] = PayloadGenerator.random_string(padding_size)
        
        return payload
    
    @staticmethod
    def generate_large_payload(request_id):
        """Generate 100 KB - 1 MB payload (bulk operations, batch sync)"""
        if LARGE_PAYLOAD_TEMPLATE:
            # Use loaded template and just update the batch ID
            payload = LARGE_PAYLOAD_TEMPLATE.copy()
            payload['batchId'] = "BATCH-{}".format(request_id)
            return payload
        
        # Fallback to generation if file not found
        payload = {
            "batchId": "BATCH-{}".format(request_id),
            "timestamp": datetime.now().isoformat(),
            "source": "consumption_tester",
            "batchType": random.choice(["customer_sync", "order_batch", "inventory_update"]),
            "totalRecords": 0,
            "records": []
        }
        
        # Add many records
        num_records = random.randint(50, 200)
        for i in range(num_records):
            payload["records"].append({
                "id": i + 1,
                "recordId": "REC-{}-{:04d}".format(request_id, i),
                "name": "{} {}".format(PayloadGenerator.random_string(10), PayloadGenerator.random_string(12)),
                "email": PayloadGenerator.random_email(),
                "phone": PayloadGenerator.random_phone(),
                "address": PayloadGenerator.random_address(),
                "status": random.choice(["active", "inactive", "pending", "archived"]),
                "createdAt": (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat(),
                "lastModified": datetime.now().isoformat(),
                "description": PayloadGenerator.random_string(random.randint(100, 500)),
                "metadata": {
                    "key{}".format(j): PayloadGenerator.random_string(20) 
                    for j in range(random.randint(5, 15))
                },
                "tags": [PayloadGenerator.random_string(8) for _ in range(random.randint(3, 10))],
                "score": round(random.uniform(0, 100), 2)
            })
        
        payload["totalRecords"] = len(payload["records"])
        
        # Pad to reach target size (100 KB - 1 MB)
        target_size = random.randint(100, 1024) * 1024
        current_size = len(json.dumps(payload))
        if current_size < target_size:
            padding_size = target_size - current_size - 100
            payload["bulkData"] = PayloadGenerator.random_string(padding_size)
        
        return payload
    
    @staticmethod
    def generate_very_large_payload(request_id):
        """Generate 1-10 MB payload (file uploads, EDI batches, large documents)"""
        if VERY_LARGE_PAYLOAD_TEMPLATE:
            # Use loaded template and just update the batch ID
            payload = VERY_LARGE_PAYLOAD_TEMPLATE.copy()
            payload['batchId'] = "MEGA-BATCH-{}".format(request_id)
            return payload
        
        # Fallback to generation if file not found
        payload = {
            "batchId": "MEGA-BATCH-{}".format(request_id),
            "documentType": random.choice(["EDI", "XML_IMPORT", "CSV_BULK", "JSON_EXPORT"]),
            "timestamp": datetime.now().isoformat(),
            "version": "2.0",
            "metadata": {
                "source": "consumption_tester",
                "priority": random.choice(["low", "medium", "high", "critical"]),
                "processingMode": random.choice(["immediate", "scheduled", "batch"]),
                "compression": "none",
                "encryption": "none"
            },
            "records": []
        }
        
        # Add massive number of detailed records
        num_records = random.randint(200, 500)
        for i in range(num_records):
            record = {
                "id": i + 1,
                "recordId": "MEGA-REC-{}-{:05d}".format(request_id, i),
                "entityType": random.choice(["customer", "order", "product", "transaction"]),
                "name": "{} {}".format(PayloadGenerator.random_string(15), PayloadGenerator.random_string(15)),
                "email": PayloadGenerator.random_email(),
                "phone": PayloadGenerator.random_phone(),
                "primaryAddress": PayloadGenerator.random_address(),
                "secondaryAddress": PayloadGenerator.random_address(),
                "status": random.choice(["active", "inactive", "pending", "processing", "completed"]),
                "createdAt": (datetime.now() - timedelta(days=random.randint(0, 1000))).isoformat(),
                "lastModified": datetime.now().isoformat(),
                "lastAccessedAt": (datetime.now() - timedelta(hours=random.randint(0, 720))).isoformat(),
                "description": PayloadGenerator.random_string(random.randint(200, 1000)),
                "longDescription": PayloadGenerator.random_string(random.randint(500, 2000)),
                "notes": PayloadGenerator.random_string(random.randint(100, 500)),
                "comments": [
                    {
                        "commentId": "CMT-{}".format(j),
                        "author": PayloadGenerator.random_string(10),
                        "text": PayloadGenerator.random_string(random.randint(50, 200)),
                        "timestamp": datetime.now().isoformat()
                    }
                    for j in range(random.randint(3, 10))
                ],
                "attributes": {
                    "attr_{}".format(j): PayloadGenerator.random_string(random.randint(20, 100))
                    for j in range(random.randint(10, 30))
                },
                "tags": [PayloadGenerator.random_string(12) for _ in range(random.randint(10, 30))],
                "categories": [PayloadGenerator.random_string(8) for _ in range(random.randint(3, 8))],
                "relatedIds": ["REL-{}".format(random.randint(10000, 99999)) for _ in range(random.randint(5, 15))],
                "numericData": [round(random.uniform(0, 1000), 2) for _ in range(random.randint(10, 50))],
                "booleanFlags": {"flag_{}".format(j): random.choice([True, False]) for j in range(random.randint(5, 20))},
                "score": round(random.uniform(0, 100), 4),
                "rating": round(random.uniform(0, 5), 2),
                "confidence": round(random.uniform(0, 1), 4)
            }
            payload["records"].append(record)
        
        payload["totalRecords"] = len(payload["records"])
        payload["summary"] = {
            "totalRecords": len(payload["records"]),
            "avgRecordSize": len(json.dumps(payload["records"][0])) if payload["records"] else 0,
            "totalSize": len(json.dumps(payload["records"]))
        }
        
        # Pad to reach target size (1-10 MB)
        target_size = random.randint(1024, 10240) * 1024
        current_size = len(json.dumps(payload))
        if current_size < target_size:
            padding_size = target_size - current_size - 100
            # Add large document content
            payload["documentContent"] = PayloadGenerator.random_string(padding_size)
        
        return payload


def test_rest_api(endpoint_name, payload_generator_func, base_url, stats, request_id):
    """Test REST API endpoint"""
    url = base_url + API_ENDPOINTS[endpoint_name]
    
    try:
        payload = payload_generator_func(request_id)
        payload_size = len(json.dumps(payload))
        
        start_time = time.time()
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response_time = time.time() - start_time
        
        stats.add_success(response_time, response.status_code, payload_size)
        return True
    except requests.exceptions.Timeout:
        stats.add_error(f"Timeout on {endpoint_name}")
        return False
    except Exception as e:
        stats.add_error(f"{endpoint_name}: {str(e)[:100]}")
        return False


def test_rabbitmq_listener(payload_generator_func, rabbitmq_config, stats, request_id):
    """Test RabbitMQ listener by publishing messages"""
    try:
        payload = payload_generator_func(request_id)
        payload_size = len(json.dumps(payload))
        
        start_time = time.time()
        
        # Connect and publish
        credentials = pika.PlainCredentials(rabbitmq_config['user'], rabbitmq_config['password'])
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=rabbitmq_config['host'],
                port=rabbitmq_config['port'],
                credentials=credentials
            )
        )
        channel = connection.channel()
        
        channel.basic_publish(
            exchange='',
            routing_key=rabbitmq_config['queue'],
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
                content_type='application/json'
            )
        )
        
        connection.close()
        response_time = time.time() - start_time
        
        stats.add_success(response_time, 200, payload_size)
        return True
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e) if str(e) else 'Connection failed'}"
        stats.add_error(error_msg[:100])
        return False


def run_test(test_name, test_func, duration_seconds, concurrent_users, *args):
    """Run load test for specified duration"""
    stats = Stats()
    start_time = time.time()
    end_time = start_time + duration_seconds
    request_counter = 0
    error_count = 0
    
    def worker():
        nonlocal request_counter, error_count
        while time.time() < end_time:
            try:
                with threading.Lock():
                    request_counter += 1
                    current_id = request_counter
                test_func(*args, stats, current_id)
                time.sleep(0.001)  # Small delay to prevent overwhelming
            except Exception as e:
                with threading.Lock():
                    error_count += 1
                    if error_count <= 3:  # Only show first 3 worker errors
                        print(f"   [!] Worker exception: {type(e).__name__}")
                break
    
    # Start threads
    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [executor.submit(worker) for _ in range(concurrent_users)]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                pass  # Already handled in worker
    
    actual_duration = time.time() - start_time
    results = stats.get_stats()
    
    # Calculate TPS
    tps = results["success"] / actual_duration if actual_duration > 0 else 0
    
    # Print results
    print(f"\n** Results: {test_name}")
    print(f"{'-'*90}")
    print(f"   Requests:  {results['total']:>8,}  |  Success: {results['success']:>8,} ({results['success_rate']:>5.1f}%)  |  Failed: {results['errors']:>6,}")
    print(f"   Duration:  {actual_duration:>7.2f}s  |  TPS: {tps:>11.2f} req/s")
    
    if results['success'] > 0:
        print(f"\n   Payload (KB):  Avg: {results['avg_payload_size']/1024:>7.2f}  |  Min: {results['min_payload_size']/1024:>7.2f}  |  Max: {results['max_payload_size']/1024:>7.2f}")
        print(f"   Latency (ms):  Avg: {results['avg_response_time']*1000:>7.2f}  |  Med: {results['median_response_time']*1000:>7.2f}  |  P95: {results['p95_response_time']*1000:>7.2f}  |  P99: {results['p99_response_time']*1000:>7.2f}")
        
        if results['status_codes']:
            codes_str = "  ".join([f"{code}:{count:,}" for code, count in sorted(results['status_codes'].items())])
            print(f"   Status Codes:  {codes_str}")
    
    if results['errors'] > 0:
        print(f"\n   [X] Top Errors (max 5):")
        error_summary = {}
        for error in results['error_samples']:
            error_type = error.split(':')[0] if ':' in error else error[:50]
            error_summary[error_type] = error_summary.get(error_type, 0) + 1
        
        for i, (error, count) in enumerate(sorted(error_summary.items(), key=lambda x: x[1], reverse=True)[:5], 1):
            print(f"      {i}. [{count:>4}x] {error[:70]}")
    
    print()
    
    return {
        "name": test_name,
        "requests": results['total'],
        "success": results['success'],
        "errors": results['errors'],
        "success_rate": results['success_rate'],
        "tps": tps,
        "avg_response_time": results.get('avg_response_time', 0),
        "avg_payload_size": results.get('avg_payload_size', 0)
    }


def run_comprehensive_test(duration=60, concurrent=20, base_url=BASE_URL, test_rabbitmq=True):
    """Run comprehensive test on all endpoints and listener simultaneously"""
    
    # Load payload templates
    load_payload_templates()
    
    print(f"\n{'#'*90}")
    print(f">> WSO2 MI CONSUMPTION TEST")
    print(f"{'#'*90}")
    print(f"   Duration: {duration}s per test | Workers: {concurrent} per test")
    print(f"   Target: {base_url}")
    if test_rabbitmq:
        print(f"   RabbitMQ: {RABBITMQ_HOST}:{RABBITMQ_PORT} -> Queue: {RABBITMQ_QUEUE}")
    print(f"   Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*90}")
    
    # Prepare all tests
    all_tests = [
        ("REST API - Small Payload (1-10 KB)", test_rest_api, "small", PayloadGenerator.generate_small_payload, base_url),
        ("REST API - Medium Payload (10-100 KB)", test_rest_api, "medium", PayloadGenerator.generate_medium_payload, base_url),
        ("REST API - Large Payload (100KB-1MB)", test_rest_api, "large", PayloadGenerator.generate_large_payload, base_url),
        ("REST API - Very Large Payload (1-10MB)", test_rest_api, "verylarge", PayloadGenerator.generate_very_large_payload, base_url),
    ]
    
    # Add RabbitMQ test if enabled
    rabbitmq_tests = []
    if test_rabbitmq:
        rabbitmq_config = {
            'host': RABBITMQ_HOST,
            'port': RABBITMQ_PORT,
            'user': RABBITMQ_USER,
            'password': RABBITMQ_PASSWORD,
            'queue': RABBITMQ_QUEUE
        }
        rabbitmq_tests = [
            ("RabbitMQ Listener - Medium Payload", test_rabbitmq_listener, PayloadGenerator.generate_medium_payload, rabbitmq_config),
        ]
    
    total_test_count = len(all_tests) + len(rabbitmq_tests)
    print(f"\n\u25b6\ufe0f  Launching {total_test_count} parallel tests...")

    
    # Run all tests simultaneously using ThreadPoolExecutor
    results = [None] * (len(all_tests) + len(rabbitmq_tests))
    
    def run_single_test(index, test_info):
        """Wrapper to run a single test and store result"""
        if len(test_info) == 5:  # REST API test
            test_name, test_func, endpoint, payload_gen, url = test_info
            return index, run_test(test_name, test_func, duration, concurrent, endpoint, payload_gen, url)
        else:  # RabbitMQ test
            test_name, test_func, payload_gen, config = test_info
            return index, run_test(test_name, test_func, duration, concurrent, payload_gen, config)
    
    with ThreadPoolExecutor(max_workers=len(all_tests) + len(rabbitmq_tests)) as executor:
        futures = []
        for idx, test_info in enumerate(all_tests + rabbitmq_tests):
            future = executor.submit(run_single_test, idx, test_info)
            futures.append(future)
        
        # Collect results as they complete
        for future in as_completed(futures):
            idx, result = future.result()
            results[idx] = result
    
    # Summary
    print(f"\n{'#'*90}")
    print(f"** COMPREHENSIVE TEST SUMMARY")
    print(f"{'#'*90}")
    print(f"{'Test Name':<47} {'Reqs':<10} {'Success':<10} {'TPS':<10} {'Latency':<11} {'Size':<10}")
    print(f"{'-'*105}")
    
    total_requests = 0
    total_success = 0
    
    for r in results:
        total_requests += r['requests']
        total_success += r['success']
        size_kb = r['avg_payload_size'] / 1024 if r['avg_payload_size'] > 0 else 0
        
        # Shorten test names for display
        display_name = r['name'].replace('REST API - ', '').replace('RabbitMQ Listener - ', '[MQ] ')
        
        print(f"{display_name:<47} {r['requests']:<10,} {r['success']:<10,} {r['tps']:<10.1f} {r['avg_response_time']*1000:<10.1f}ms {size_kb:<9.1f}KB")
    
    print(f"{'-'*105}")
    print(f"{'TOTAL':<47} {total_requests:<10,} {total_success:<10,} {'':10} {'':11} {'':10}")
    print(f"{'#'*90}")
    
    success_rate = (total_success / total_requests * 100) if total_requests > 0 else 0
    print(f"   Overall Success Rate: {success_rate:.1f}%")
    print(f"   End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*90}\n")


def main():
    parser = argparse.ArgumentParser(
        description="WSO2 MI Consumption Tester - Comprehensive Performance Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run comprehensive test (all APIs + RabbitMQ)
  python consumption_tester.py --duration 60 --concurrent 20
  
  # Test only REST APIs (skip RabbitMQ)
  python consumption_tester.py --duration 30 --concurrent 10 --no-rabbitmq
  
  # High load test
  python consumption_tester.py --duration 120 --concurrent 50
  
  # Quick smoke test
  python consumption_tester.py --duration 10 --concurrent 5
        """
    )
    
    parser.add_argument("--duration", type=int, default=60,
                        help="Test duration per endpoint in seconds (default: 60)")
    parser.add_argument("--concurrent", type=int, default=20,
                        help="Number of concurrent users (default: 20)")
    parser.add_argument("--url", default="http://localhost:8290/restapi",
                        help="Base URL for REST API (default: http://localhost:8290/restapi)")
    parser.add_argument("--rabbitmq-host", default="localhost",
                        help="RabbitMQ host (default: localhost)")
    parser.add_argument("--rabbitmq-port", type=int, default=5672,
                        help="RabbitMQ port (default: 5672)")
    parser.add_argument("--rabbitmq-user", default="guest",
                        help="RabbitMQ username (default: guest)")
    parser.add_argument("--rabbitmq-password", default="guest",
                        help="RabbitMQ password (default: guest)")
    parser.add_argument("--rabbitmq-queue", default="orderQueue",
                        help="RabbitMQ queue name (default: orderQueue)")
    parser.add_argument("--no-rabbitmq", action="store_true",
                        help="Skip RabbitMQ listener tests")
    
    args = parser.parse_args()
    
    # Update global config
    global BASE_URL, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_QUEUE
    BASE_URL = args.url
    RABBITMQ_HOST = args.rabbitmq_host
    RABBITMQ_PORT = args.rabbitmq_port
    RABBITMQ_USER = args.rabbitmq_user
    RABBITMQ_PASSWORD = args.rabbitmq_password
    RABBITMQ_QUEUE = args.rabbitmq_queue
    
    try:
        run_comprehensive_test(
            duration=args.duration,
            concurrent=args.concurrent,
            base_url=BASE_URL,
            test_rabbitmq=not args.no_rabbitmq
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
