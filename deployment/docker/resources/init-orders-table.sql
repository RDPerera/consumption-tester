-- SQL Script to initialize the orders table
-- This script should be executed once to create the required table structure
-- For H2 in-memory database, this needs to be run on application startup

CREATE TABLE IF NOT EXISTS orders (
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

-- For MySQL, use this alternative syntax:
-- CREATE TABLE IF NOT EXISTS orders (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     order_id VARCHAR(100) NOT NULL UNIQUE,
--     customer_id VARCHAR(100) NOT NULL,
--     customer_name VARCHAR(255),
--     item_count INT,
--     total DECIMAL(10,2),
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     INDEX idx_order_id (order_id),
--     INDEX idx_customer_id (customer_id)
-- );
