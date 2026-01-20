-- SQL Script to initialize the batch_records table for large payload processing
-- This script should be executed once to create the required table structure

CREATE TABLE IF NOT EXISTS batch_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(100) NOT NULL,
    record_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_batch_id (batch_id),
    INDEX idx_record_id (record_id)
);

-- For MySQL, use this alternative syntax:
-- CREATE TABLE IF NOT EXISTS batch_records (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     batch_id VARCHAR(100) NOT NULL,
--     record_id INT NOT NULL,
--     name VARCHAR(255) NOT NULL,
--     email VARCHAR(255) NOT NULL,
--     processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     INDEX idx_batch_id (batch_id),
--     INDEX idx_record_id (record_id)
-- );
