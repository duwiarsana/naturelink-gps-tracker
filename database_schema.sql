-- ============================================================================
-- Naturelink GPS Tracker - Database Schema
-- PostgreSQL Version
-- ============================================================================
-- 
-- Usage:
--   psql -U postgres -d gps_tracking -f database_schema.sql
--
-- Author: GPS Tracking Team
-- Date: 2026-03-06
-- ============================================================================

-- Drop tables if exists (untuk testing)
-- DROP TABLE IF EXISTS io_elements CASCADE;
-- DROP TABLE IF EXISTS device_status CASCADE;
-- DROP TABLE IF EXISTS gps_locations CASCADE;
-- DROP TABLE IF EXISTS devices CASCADE;

-- ============================================================================
-- Table: devices
-- Menyimpan informasi device GPS
-- ============================================================================
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    imei VARCHAR(20) UNIQUE NOT NULL,
    device_name VARCHAR(100),
    device_type VARCHAR(50) DEFAULT 'Naturelink GPS',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index untuk performa
CREATE INDEX IF NOT EXISTS idx_devices_imei ON devices(imei);

-- ============================================================================
-- Table: gps_locations
-- Menyimpan data lokasi GPS dari device
-- ============================================================================
CREATE TABLE IF NOT EXISTS gps_locations (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    imei VARCHAR(20) NOT NULL,
    event_code INTEGER,
    timestamp TIMESTAMP NOT NULL,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    speed INTEGER DEFAULT 0,
    heading INTEGER DEFAULT 0,
    satellites INTEGER DEFAULT 0,
    gps_valid BOOLEAN DEFAULT FALSE,
    signal_quality INTEGER DEFAULT 0,
    altitude INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes untuk performa query
CREATE INDEX IF NOT EXISTS idx_gps_locations_imei ON gps_locations(imei);
CREATE INDEX IF NOT EXISTS idx_gps_locations_timestamp ON gps_locations(timestamp);
CREATE INDEX IF NOT EXISTS idx_gps_locations_device_timestamp ON gps_locations(device_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_gps_locations_coords ON gps_locations(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_gps_locations_speed ON gps_locations(speed);

-- Unique constraint untuk mencegah duplicate data
CREATE UNIQUE INDEX IF NOT EXISTS idx_gps_unique_imei_timestamp 
ON gps_locations(imei, timestamp);

-- ============================================================================
-- Table: device_status
-- Menyimpan status device (battery, voltage, mileage, dll)
-- ============================================================================
CREATE TABLE IF NOT EXISTS device_status (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    imei VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    battery_voltage INTEGER,
    external_voltage INTEGER,
    network_type VARCHAR(10),
    mileage INTEGER DEFAULT 0,
    running_time INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_device_status_imei ON device_status(imei);
CREATE INDEX IF NOT EXISTS idx_device_status_timestamp ON device_status(timestamp);
CREATE INDEX IF NOT EXISTS idx_device_status_imei_timestamp ON device_status(imei, timestamp);

-- ============================================================================
-- Table: io_elements (Optional)
-- Menyimpan IO elements tambahan yang tidak masuk ke tabel utama
-- ============================================================================
CREATE TABLE IF NOT EXISTS io_elements (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES gps_locations(id) ON DELETE CASCADE,
    io_key VARCHAR(50) NOT NULL,
    io_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX IF NOT EXISTS idx_io_elements_location ON io_elements(location_id);
CREATE INDEX IF NOT EXISTS idx_io_elements_key ON io_elements(io_key);

-- ============================================================================
-- Views untuk Query yang Sering Digunakan
-- ============================================================================

-- View: Latest location per device
CREATE OR REPLACE VIEW v_latest_locations AS
SELECT DISTINCT ON (d.imei)
    d.id as device_id,
    d.imei,
    d.device_name,
    g.timestamp,
    g.latitude,
    g.longitude,
    g.speed,
    g.heading,
    g.satellites,
    g.gps_valid,
    g.altitude,
    s.battery_voltage,
    s.external_voltage,
    s.network_type,
    s.mileage
FROM devices d
LEFT JOIN gps_locations g ON d.id = g.device_id
LEFT JOIN device_status s ON d.id = s.device_id AND g.timestamp = s.timestamp
ORDER BY d.imei, g.timestamp DESC;

-- View: Device statistics (last 24 hours)
CREATE OR REPLACE VIEW v_device_stats_24h AS
SELECT 
    d.imei,
    d.device_name,
    COUNT(g.id) as total_records,
    MAX(g.timestamp) as last_update,
    AVG(g.speed) as avg_speed,
    MAX(g.speed) as max_speed,
    MIN(g.speed) as min_speed,
    AVG(s.battery_voltage) as avg_battery,
    MAX(s.mileage) as total_mileage
FROM devices d
LEFT JOIN gps_locations g ON d.id = g.device_id
LEFT JOIN device_status s ON d.id = s.device_id AND g.timestamp = s.timestamp
WHERE g.timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY d.imei, d.device_name;

-- ============================================================================
-- Functions
-- ============================================================================

-- Function: Update device updated_at timestamp
CREATE OR REPLACE FUNCTION update_device_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE devices 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.device_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto update device timestamp when new GPS location inserted
DROP TRIGGER IF EXISTS trigger_update_device_timestamp ON gps_locations;
CREATE TRIGGER trigger_update_device_timestamp
    AFTER INSERT ON gps_locations
    FOR EACH ROW
    EXECUTE FUNCTION update_device_timestamp();

-- ============================================================================
-- Sample Queries (untuk testing)
-- ============================================================================

-- Get latest location for all devices
-- SELECT * FROM v_latest_locations;

-- Get device statistics (24 hours)
-- SELECT * FROM v_device_stats_24h;

-- Get route history for specific device
-- SELECT timestamp, latitude, longitude, speed, heading
-- FROM gps_locations
-- WHERE imei = '0866344055567122'
--   AND timestamp >= NOW() - INTERVAL '24 hours'
-- ORDER BY timestamp ASC;

-- Get devices with low battery
-- SELECT d.imei, d.device_name, s.battery_voltage, s.timestamp
-- FROM devices d
-- JOIN device_status s ON d.id = s.device_id
-- WHERE s.battery_voltage < 3500
--   AND s.timestamp >= NOW() - INTERVAL '1 hour'
-- ORDER BY s.timestamp DESC;

-- Get overspeed events
-- SELECT d.imei, g.timestamp, g.latitude, g.longitude, g.speed
-- FROM gps_locations g
-- JOIN devices d ON g.device_id = d.id
-- WHERE g.speed > 80
--   AND g.timestamp >= NOW() - INTERVAL '24 hours'
-- ORDER BY g.timestamp DESC;

-- ============================================================================
-- Maintenance Queries
-- ============================================================================

-- Delete old data (older than 90 days)
-- DELETE FROM gps_locations WHERE timestamp < NOW() - INTERVAL '90 days';
-- DELETE FROM device_status WHERE timestamp < NOW() - INTERVAL '90 days';

-- Vacuum tables for performance
-- VACUUM ANALYZE devices;
-- VACUUM ANALYZE gps_locations;
-- VACUUM ANALYZE device_status;

-- Check table sizes
-- SELECT 
--     schemaname,
--     tablename,
--     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- ============================================================================
-- Grants (adjust as needed)
-- ============================================================================

-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gps_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gps_user;

-- ============================================================================
-- End of Schema
-- ============================================================================

COMMENT ON TABLE devices IS 'Menyimpan informasi device GPS Naturelink';
COMMENT ON TABLE gps_locations IS 'Menyimpan data lokasi GPS dari device';
COMMENT ON TABLE device_status IS 'Menyimpan status device (battery, voltage, mileage)';
COMMENT ON TABLE io_elements IS 'Menyimpan IO elements tambahan';
