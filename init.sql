-- init.sql
CREATE TABLE IF NOT EXISTS inventory_master (
    id INT AUTO_INCREMENT PRIMARY KEY,
    STORAGEUNIT VARCHAR(50) NOT NULL,
    GR_Number VARCHAR(50) NOT NULL,
    StorageBin VARCHAR(50),
    MaterialCode VARCHAR(50),
    Quantity DECIMAL(10,2)
);

-- Index for optimizing metrics query by StorageBin prefix
CREATE INDEX idx_storagebin ON inventory_master (StorageBin);
-- Index for optimizing STORAGEUNIT queries
CREATE INDEX idx_storageunit ON inventory_master (STORAGEUNIT);
