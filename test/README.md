# WSO2 MI Load Testing Tool

Comprehensive performance testing tool for WSO2 Micro Integrator REST APIs and RabbitMQ listeners.

## Features

- **Parallel Testing**: All payload types are tested simultaneously
- **Multiple Payload Sizes**: Small (1-10 KB), Medium (10-100 KB), Large (100KB-1MB), Very Large (1-10MB)
- **RabbitMQ Support**: Tests message queue consumption
- **Realistic Data**: Generates random, realistic payloads for each test
- **Detailed Metrics**: TPS, latency percentiles (P95, P99), payload sizes, error tracking

## Prerequisites

- Python 3.7+
- WSO2 MI running on `http://localhost:8290`
- RabbitMQ running on `localhost:5672` (if testing listeners)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Test
```bash
python consumption_tester.py --duration 10 --concurrent 5
```

### Skip RabbitMQ Tests
```bash
python consumption_tester.py --duration 30 --concurrent 10 --no-rabbitmq
```

### High Load Test
```bash
python consumption_tester.py --duration 120 --concurrent 50
```

### Custom Endpoints
```bash
python consumption_tester.py \
  --url http://your-server:8290/restapi \
  --rabbitmq-host your-rabbitmq-host \
  --duration 60 \
  --concurrent 20
```

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--duration` | 60 | Test duration per endpoint in seconds |
| `--concurrent` | 20 | Number of concurrent workers per test |
| `--url` | http://localhost:8290/restapi | Base URL for REST API |
| `--rabbitmq-host` | localhost | RabbitMQ host |
| `--rabbitmq-port` | 5672 | RabbitMQ port |
| `--rabbitmq-user` | guest | RabbitMQ username |
| `--rabbitmq-password` | guest | RabbitMQ password |
| `--rabbitmq-queue` | orderQueue | RabbitMQ queue name |
| `--no-rabbitmq` | false | Skip RabbitMQ listener tests |

## Output

The tool provides:

### Per-Test Results
- Total requests, success rate, failures
- Throughput (TPS)
- Payload statistics (avg, min, max)
- Latency metrics (avg, median, P95, P99)
- HTTP status code distribution
- Top error types with counts

### Comprehensive Summary
- Aggregated results across all tests
- Overall success rate
- Performance comparison by payload size

## Sample Payloads

The tool uses three sample JSON files for large payloads:
- `sample-large-payload-request.json` - ~100KB
- `sample-medium-payload-request.json` - ~50KB
- `sample-very-large-payload-request.json` - ~7MB

These files must be present in the same directory as the script.

## RabbitMQ Testing

The RabbitMQ test publishes messages directly to the configured queue. Ensure:
1. RabbitMQ is running and accessible
2. The queue exists (will be created if using default settings)
3. WSO2 MI has an inbound endpoint listening to the queue
4. Credentials match your RabbitMQ setup (default: guest/guest)

## Troubleshooting

### RabbitMQ Connection Errors
- Verify RabbitMQ is running: `docker ps | grep rabbitmq`
- Check credentials match your configuration
- Ensure port 5672 is accessible

### REST API Errors
- Confirm WSO2 MI is running on the specified URL
- Check the `/restapi` endpoint is deployed
- Verify the endpoint supports the payload sizes being tested

### Unicode Errors
The script uses ASCII characters only for terminal compatibility. If you still encounter encoding issues, ensure your terminal supports UTF-8.

## Performance Tips

1. **Warm-up**: Run a short test first to warm up the server
2. **Concurrent Users**: Start with 5-10, increase gradually
3. **Duration**: 60-120 seconds gives reliable metrics
4. **System Resources**: Monitor CPU/memory on both client and server
5. **Network**: Consider network latency in distributed setups

## Example Output

```
##########################################################################################
>> WSO2 MI CONSUMPTION TEST
##########################################################################################
   Duration: 10s per test | Workers: 5 per test
   Target: http://localhost:8290/restapi
   RabbitMQ: localhost:5672 -> Queue: orderQueue
   Start: 2026-01-20 10:15:30
##########################################################################################

>> Launching 5 parallel tests...

** Results: REST API - Small Payload (1-10 KB)
------------------------------------------------------------------------------------------
   Requests:     8,317  |  Success:    8,317 (100.0%)  |  Failed:      0
   Duration:     10.00s  |  TPS:       831.33 req/s

   Payload (KB):  Avg:    5.47  |  Min:    1.02  |  Max:    9.98
   Latency (ms):  Avg:    4.01  |  Med:    3.85  |  P95:    6.12  |  P99:    8.45
   Status Codes:  200:8,317

[... more results ...]

##########################################################################################
** COMPREHENSIVE TEST SUMMARY
##########################################################################################
Test Name                                       Reqs       Success    TPS        Latency    Size     
---------------------------------------------------------------------------------------------------------
Small Payload (1-10 KB)                         8,317      8,317      831.3      4.0ms      5.5KB
Medium Payload (10-100 KB)                      1,208      1,208      120.5      34.0ms     54.4KB
Large Payload (100KB-1MB)                       10         10         0.7        7486.8ms   622.9KB
Very Large Payload (1-10MB)                     110        110        10.9       385.2ms    7400.3KB
[MQ] Medium Payload                             341        341        34.1       12.5ms     54.3KB
---------------------------------------------------------------------------------------------------------
TOTAL                                           9,986      9,986                            
##########################################################################################
   Overall Success Rate: 100.0%
   End Time: 2026-01-20 10:15:40
##########################################################################################
```

## Files

- `consumption_tester.py` - Main test script
- `requirements.txt` - Python dependencies
- `sample-large-payload-request.json` - Large payload template
- `sample-medium-payload-request.json` - Medium payload template
- `sample-very-large-payload-request.json` - Very large payload template
- `README.md` - This documentation
