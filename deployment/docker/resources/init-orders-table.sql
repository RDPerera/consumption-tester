-- SQL Script to initialize the orders table
-- This script should be executed once to create the required table structure
-- Supports both REST API (parsed fields) and RabbitMQ (full JSON) approaches

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(100) NOT NULL UNIQUE,
    customer_id VARCHAR(100) NOT NULL,
    customer_name VARCHAR(255),
    item_count INT,
    total DOUBLE,
    order_data MEDIUMTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order_id (order_id),
    INDEX idx_customer_id (customer_id)
);

-- MEDIUMTEXT supports up to 16MB of data for order_data column
-- Other columns support parsed/structured data from REST API
