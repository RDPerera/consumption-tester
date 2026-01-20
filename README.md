# WSO2 Micro Integrator: Product Consumption Tracker Testing

## Overview

This project provides comprehensive performance and consumption testing for **WSO2 Micro Integrator (MI)**, focusing on real-world integration scenarios commonly used in enterprise environments. The testing framework evaluates resource consumption, throughput, and reliability across different payload sizes and integration patterns.

### What We Are Testing

We are testing various types of **common API integrations** and **event-based integrations** to measure:

- **Resource Consumption**: CPU, memory, and I/O utilization under different load conditions
- **Throughput**: Number of requests/messages processed per second
- **Response Times**: Latency characteristics including average, median, P95, and P99
- **Error Rates**: System reliability and error handling under stress
- **Scalability**: Performance characteristics with concurrent requests

The tests cover:

1. **REST API Integrations** - Three different payload size categories with realistic business scenarios
2. **Event-Based Integrations** - RabbitMQ message queue consumption patterns

---

## Payload Types & Sizes

The testing framework uses three distinct payload categories based on real-world integration patterns:

| Payload Type | Size Range | Use Case | Test API |
|-------------|-----------|----------|----------|
| **Small** | 1-10 KB | Authentication, status checks, simple CRUD operations | `/restapi/small` |
| **Medium** | 10-100 KB | Business transactions, order processing, entity management | `/restapi/medium` |
| **Large** | 100 KB - 1 MB | Batch processing, bulk data imports, report generation | `/restapi/large` |
| **Very Large** | 1-5 MB+ | File uploads, document processing, large data transfers | `/restapi/veryLarge` |

---

## Database Tables

The integration uses MySQL database with the following schema:

### 1. `orders` Table
Stores order data from medium payload API and RabbitMQ listener:

```sql
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(100) NOT NULL UNIQUE,
    customer_id VARCHAR(100) NOT NULL,
    customer_name VARCHAR(255),
    item_count INT,
    total DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order_id (order_id),
    INDEX idx_customer_id (customer_id)
);
```

### 2. `batch_records` Table
Stores individual records from large payload batch processing:

```sql
CREATE TABLE batch_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(100) NOT NULL,
    record_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_batch_id (batch_id),
    INDEX idx_record_id (record_id)
);
```

---

## API Integrations

### 1. Small Payload API - Authentication Service

**Endpoint**: `POST /restapi/small`

**Integration Type**: Simple authentication and validation service

**Payload Size**: 1-10 KB

**What It Does**:
- Receives authentication requests with username/password
- Validates credentials against predefined values
- Returns success/failure response
- No database persistence (in-memory validation)

**Sample Request Structure**:
```json
{
  "username": "user_12345",
  "password": "randompassword123",
  "email": "user@example.com",
  "sessionId": "abc123xyz456",
  "timestamp": "2026-01-20T10:30:00",
  "requestId": "REQ-12345",
  "metadata": {
    "userAgent": "ConsumptionTester/1.0",
    "ipAddress": "192.168.1.100",
    "deviceId": "device123456"
  }
}
```

**Integration Flow**:
1. Request validation
2. Credential extraction (username, password)
3. Authentication logic (username/password match)
4. Response generation (success/failure)

**Architecture Diagram**: See `~/Downloads/MI-resource-diagram/small-payload-integration.png`

---

### 2. Medium Payload API - Order Processing Service

**Endpoint**: `POST /restapi/medium`

**Integration Type**: Business transaction processing with database persistence

**Payload Size**: 10-100 KB

**What It Does**:
- Processes customer orders with multiple line items
- Validates required fields (orderId, customer.id)
- Extracts order details (customer info, items, totals)
- Persists order data to MySQL `orders` table
- Returns confirmation with order details

**Sample Request Structure**:
```json
{
  "orderId": "ORD-12345",
  "customer": {
    "id": "CUST-001",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+1-555-1234",
    "address": {
      "street": "123 Main St",
      "city": "Springfield",
      "state": "IL",
      "zipCode": "62701"
    }
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
    }
  ],
  "total": 109.97,
  "orderDate": "2026-01-20T10:30:00",
  "status": "confirmed"
}
```

**Integration Flow**:
1. Request validation (orderId, customer.id presence check)
2. Data extraction (order fields, customer details, item count)
3. Database insertion to `orders` table
4. Success response with order confirmation

**Architecture Diagram**: See `~/Downloads/MI-resource-diagram/medium-payload-integration.png`

---

### 3. Large Payload API - Batch Processing Service

**Endpoint**: `POST /restapi/large`

**Integration Type**: Batch record processing with memory-optimized iteration

**Payload Size**: 100 KB - 1 MB

**What It Does**:
- Processes batches containing hundreds/thousands of records
- Validates batch metadata (batchId, records array)
- Uses Iterate mediator for memory-efficient processing
- Validates and stores each record individually in `batch_records` table
- Returns processing summary with success/failure counts

**Sample Request Structure**:
```json
{
  "batchId": "BATCH1001",
  "records": [
    {
      "id": 1,
      "name": "Alice Johnson",
      "email": "alice.johnson@example.com"
    },
    {
      "id": 2,
      "name": "Bob Smith",
      "email": "bob.smith@example.com"
    },
    {
      "id": 3,
      "name": "Carol White",
      "email": "carol.white@example.com"
    }
    // ... potentially thousands more records
  ]
}
```

**Integration Flow**:
1. Batch-level validation (batchId, records array presence)
2. Record count extraction
3. Memory-optimized iteration through records array
4. For each record:
   - Validate required fields (id, name, email)
   - Insert into `batch_records` table
   - Track success/failure
5. Return processing summary

**Architecture Diagram**: See `~/Downloads/MI-resource-diagram/large-payload-integration.png`

---

### 4. Very Large Payload API - File Upload Service

**Endpoint**: `POST /restapi/veryLarge`

**Integration Type**: File processing with Base64 decoding and VFS storage

**Payload Size**: 1-5 MB+

**What It Does**:
- Receives Base64-encoded file content
- Validates fileName and content fields
- Decodes Base64 content
- Calculates file size
- Saves file to local file system using VFS (Virtual File System)
- Returns metadata including file path and size

**Sample Request Structure**:
```json
{
  "fileName": "largeData.json",
  "content": "eyJkYXRhIjogIlRoaXMgaXMgYSBsYXJnZSBmaWxlIGNvbnRlbnQgZW5jb2RlZCBpbiBCYXNlNjQifQ=="
}
```

**Integration Flow**:
1. Streaming configuration for large payloads
2. Field validation (fileName, content)
3. File size calculation
4. Base64 decoding
5. File save to `/tmp/wso2mi/uploads/` with timestamp prefix
6. Response with file metadata (name, size, path)

**Architecture Diagram**: See `~/Downloads/MI-resource-diagram/very-large-payload-integration.png`

---

## Event-Based Integration - RabbitMQ Order Queue Listener

### Overview

The event-based integration demonstrates asynchronous message consumption from RabbitMQ, representing a common pattern in enterprise integrations for decoupled, event-driven architectures.

**Integration Type**: RabbitMQ message queue consumer

**Message Broker**: RabbitMQ

**Queue Name**: `orderQueue`

**Protocol**: AMQP (Advanced Message Queuing Protocol)

### What It Does

The RabbitMQ listener (`OrderQueueListener`) continuously monitors the `orderQueue` and processes incoming order messages asynchronously:

1. **Message Consumption**: Listens to `orderQueue` with configurable prefetch count (10 messages)
2. **Message Extraction**: Parses JSON order data from queue messages
3. **Field Extraction**: Extracts orderId, customerId, and full message content
4. **Database Persistence**: Stores order data in `orders` table
5. **Acknowledgment**: Acknowledges message processing (auto.ack=false for reliability)

### Configuration

**Inbound Endpoint**: `OrderQueueListener.xml`

```xml
<inboundEndpoint name="OrderQueueListener"
                 sequence="ProcessOrderSequence"
                 onError="RabbitMQErrorSequence"
                 protocol="rabbitmq">
    <parameters>
        <parameter name="rabbitmq.server.host.name">localhost</parameter>
        <parameter name="rabbitmq.server.port">5672</parameter>
        <parameter name="rabbitmq.queue.name">orderQueue</parameter>
        <parameter name="rabbitmq.prefetch.count">10</parameter>
        <parameter name="rabbitmq.connection.pool.size">25</parameter>
    </parameters>
</inboundEndpoint>
```

### Message Format

The listener expects JSON messages with the following structure:

```json
{
  "orderId": "ORD-67890",
  "customer": {
    "id": "CUST-123",
    "name": "Jane Smith",
    "email": "jane.smith@example.com"
  },
  "items": [
    {
      "itemId": "ITEM-005",
      "name": "Product X",
      "quantity": 3,
      "price": 15.99
    }
  ],
  "total": 47.97
}
```

### Processing Flow

1. **Message Reception**: RabbitMQ delivers message to listener
2. **Logging**: Logs incoming message with queue and listener info
3. **Data Extraction**: 
   - `orderId` from message
   - `customer.id` from customer object
   - Full message content as JSON string
4. **Database Insert**: Stores in `orders` table:
   ```sql
   INSERT INTO orders (order_id, customer_id, order_data, created_at) 
   VALUES (orderId, customerId, messageContent, NOW())
   ```
5. **Success Logging**: Confirms successful processing
6. **Message Acknowledgment**: Acknowledges to RabbitMQ (removes from queue)

### Error Handling

- **Error Sequence**: `RabbitMQErrorSequence` handles processing failures
- **Retry Logic**: Connection retry count: 5, interval: 10 seconds
- **Manual Acknowledgment**: Ensures messages aren't lost on failure

### Performance Features

- **Prefetch Count**: 10 (balances throughput and memory)
- **Connection Pool**: 25 connections for concurrent processing
- **Durable Queue**: Messages persist across broker restarts
- **Sequential Processing**: Ensures message order (sequential=true)

**Architecture Diagram**: See `~/Downloads/MI-resource-diagram/rabbitmq-listener-integration.png`

---

## Testing Script - `consumption_tester.py`

### Overview

The `consumption_tester.py` script is a comprehensive Python-based performance testing tool that simulates realistic load patterns across all integration endpoints. It provides detailed metrics on throughput, latency, error rates, and resource consumption.

### Features

- **Multi-threaded Load Generation**: Configurable concurrent request execution
- **Random Payload Generation**: Creates realistic test data matching production patterns
- **Real-time Metrics Collection**: Tracks response times, success rates, and error details
- **RabbitMQ Testing**: Publishes messages directly to queue for listener testing
- **Statistical Analysis**: Calculates averages, medians, P95, P99 latencies
- **Flexible Configuration**: Command-line arguments for test duration, concurrency, endpoints

### Prerequisites

1. **Python 3.7+** installed
2. **Required Python packages**:
   ```bash
   pip install requests pika
   ```
3. **WSO2 MI running** on `http://localhost:8290`
4. **MySQL database** accessible with `orders` and `batch_records` tables created
5. **RabbitMQ running** on `localhost:5672` (if testing listener)

### Installation

```bash
# Navigate to test directory
cd /Users/dilanperera/wso2mi/Projects/consumption-tester/test

# Install dependencies
pip install -r requirements.txt
```

### Running the Tests

#### Basic Test (Default Configuration)

```bash
python consumption_tester.py --duration 30 --concurrent 10
```

This runs:
- 30 seconds of continuous testing
- 10 concurrent threads
- All API endpoints (small, medium, large, very large)
- RabbitMQ listener testing included

#### Test Specific APIs Only

```bash
# Test only medium and large payload APIs
python consumption_tester.py --duration 60 --concurrent 5 --api-types medium large
```

#### Skip RabbitMQ Tests

```bash
python consumption_tester.py --duration 30 --concurrent 10 --no-rabbitmq
```

#### Custom RabbitMQ Configuration

```bash
python consumption_tester.py \
  --duration 30 \
  --concurrent 10 \
  --rabbitmq-host rabbitmq.example.com \
  --rabbitmq-port 5672 \
  --rabbitmq-user admin \
  --rabbitmq-password secretpass \
  --rabbitmq-queue orderQueue
```

#### High-Throughput Stress Test

```bash
python consumption_tester.py --duration 300 --concurrent 50
```

### Command-Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--duration` | 60 | Test duration in seconds |
| `--concurrent` | 5 | Number of concurrent threads |
| `--api-types` | all | API types to test: small, medium, large, veryLarge (space-separated) |
| `--base-url` | http://localhost:8290/restapi | WSO2 MI base URL |
| `--rabbitmq-host` | localhost | RabbitMQ host |
| `--rabbitmq-port` | 5672 | RabbitMQ port |
| `--rabbitmq-user` | guest | RabbitMQ username |
| `--rabbitmq-password` | guest | RabbitMQ password |
| `--rabbitmq-queue` | orderQueue | RabbitMQ queue name |
| `--no-rabbitmq` | false | Skip RabbitMQ listener tests |

### Test Output

The script provides comprehensive output including:

#### Per-API Metrics
```
Small Payload API Results:
  Success: 1,234 | Errors: 2 | Success Rate: 99.84%
  Avg Response Time: 45.23ms
  Median: 42.10ms | P95: 78.50ms | P99: 95.30ms
  Throughput: 41.13 req/sec
  Payload Sizes: 1.5 KB (avg) | 1.2-9.8 KB (range)
```

#### RabbitMQ Listener Metrics
```
RabbitMQ Listener Results:
  Messages Published: 850
  Publish Success Rate: 100.00%
  Avg Publish Time: 12.34ms
```

#### Overall Summary
```
Total Requests: 5,240
Total Duration: 60.00 seconds
Overall Throughput: 87.33 req/sec
Total Errors: 8 (0.15%)
```

### Interpreting Results

- **Success Rate**: Should be >99% for healthy system
- **P95/P99 Response Times**: Key indicators for user experience
- **Throughput**: Requests per second, measure of system capacity
- **Error Samples**: Shows specific error messages for debugging

### Sample Payload Files

The test directory includes sample payload files for reference:

- `sample-medium-payload-request.json` - Medium payload example
- `sample-large-payload-request.json` - Large payload example
- `sample-very-large-payload-request.json` - Very large payload example

---

## Integration Architecture Diagrams

Detailed integration flow diagrams for each endpoint are available in:

```
~/Downloads/MI-resource-diagram/
```

Files include:
- `small-payload-integration.png` - Small payload authentication flow
- `medium-payload-integration.png` - Medium payload order processing flow
- `large-payload-integration.png` - Large payload batch processing flow
- `very-large-payload-integration.png` - Very large payload file upload flow
- `rabbitmq-listener-integration.png` - Event-based RabbitMQ consumer flow

These diagrams illustrate the complete request/response flow, WSO2 MI mediators used, database interactions, and system component interactions.

---

## Project Structure

```
consumption-tester/
├── README.md                              # This file
├── consumption_tester.py                   # Main testing script
├── requirements.txt                        # Python dependencies
├── pom.xml                                 # Maven project configuration
├── docker-compose-rabbitmq.yml             # RabbitMQ Docker setup
│
├── deployment/                             # Deployment configurations
│   ├── deployment.toml                     # MI deployment config
│   └── docker/
│       ├── Dockerfile                      # MI Docker image
│       └── resources/
│           ├── init-orders-table.sql       # Orders table schema
│           └── init-batch-records-table.sql # Batch records table schema
│
├── src/main/wso2mi/artifacts/              # WSO2 MI integration artifacts
│   ├── apis/
│   │   └── restapi.xml                     # REST API definitions
│   ├── sequences/
│   │   ├── ProcessOrderSequence.xml        # Order processing sequence
│   │   ├── ProcessRecordSequence.xml       # Record processing sequence
│   │   └── RabbitMQErrorSequence.xml       # Error handling sequence
│   ├── inbound-endpoints/
│   │   └── OrderQueueListener.xml          # RabbitMQ listener
│   └── data-sources/
│       └── OrderDatabase.xml               # Database connection config
│
└── test/                                   # Test scripts and samples
    ├── consumption_tester.py               # Testing script
    ├── requirements.txt                    # Python dependencies
    └── sample-*-payload-request.json       # Sample request files
```

---

## Getting Started

### 1. Start RabbitMQ

```bash
docker-compose -f docker-compose-rabbitmq.yml up -d
```

### 2. Start MySQL Database

Ensure MySQL is running and create the required tables using:

```bash
mysql -u root -p < deployment/docker/resources/init-orders-table.sql
mysql -u root -p < deployment/docker/resources/init-batch-records-table.sql
```

### 3. Deploy WSO2 MI

```bash
# Build the project
mvn clean package

# Deploy the CAR file to WSO2 MI
cp target/consumption-tester_1.0.0.car <MI_HOME>/repository/deployment/server/carbonapps/
```

### 4. Run Tests

```bash
cd test
python consumption_tester.py --duration 60 --concurrent 10
```

---

## Support & Documentation

For detailed integration flow documentation, refer to:

- `MEDIUM_PAYLOAD_API.md` - Medium payload integration details
- `LARGE_PAYLOAD_API.md` - Large payload integration details
- `VERY_LARGE_PAYLOAD_API.md` - Very large payload integration details
- `API_FUNCTIONALITY_OVERVIEW.md` - Quick reference guide

---

## License

This project is intended for WSO2 MI performance testing and evaluation purposes.
