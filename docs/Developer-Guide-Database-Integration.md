# Developer Guide - Naturelink GPS Database Integration

Dokumentasi lengkap untuk developer yang ingin mengintegrasikan data GPS Naturelink ke database.

---

## Daftar Isi

1. [Overview](#overview)
2. [Arsitektur Sistem](#arsitektur-sistem)
3. [Setup Environment](#setup-environment)
4. [Database Schema](#database-schema)
5. [Subscribe & Parse Data](#subscribe--parse-data)
6. [Simpan ke Database](#simpan-ke-database)
7. [Contoh Implementasi](#contoh-implementasi)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### Alur Data

```
GPS Device → MQTT Broker → Python Script → Parser → Database
   ↓              ↓              ↓            ↓         ↓
Naturelink   $MQTT_BROKER   mqtt_monitor   Binary    PostgreSQL
  Tracker    /Naturelink/    .py + parser   to JSON   /MySQL/
             Send                                      MongoDB
```

### Teknologi yang Digunakan

- **MQTT Broker**: Mosquitto (`$MQTT_BROKER:$MQTT_PORT`)
- **Parser**: Python 3.x
- **Database**: PostgreSQL / MySQL / MongoDB (pilih salah satu)
- **Library**: `paho-mqtt`, `psycopg2`/`pymysql`/`pymongo`

---

## Arsitektur Sistem

### Komponen Utama

1. **MQTT Subscriber**
   - Subscribe ke topic `/Naturelink/Send`
   - Terima data binary dari GPS device
   - Handle reconnection otomatis

2. **Data Parser**
   - Parse binary protocol Naturelink
   - Extract GPS data (lat/lon, speed, timestamp)
   - Extract device status (battery, network, mileage)
   - Validasi data

3. **Database Writer**
   - Insert data ke database
   - Handle duplicate data
   - Batch insert untuk performa
   - Error handling & retry logic

### Diagram Alur

```
┌─────────────┐
│ GPS Device  │
│ (Naturelink)│
└──────┬──────┘
       │ Binary Data
       ↓
┌─────────────────┐
│  MQTT Broker    │
│ $MQTT_BROKER     │
│ Topic: /Nature  │
│       link/Send │
└──────┬──────────┘
       │ Subscribe
       ↓
┌─────────────────┐
│ Python Script   │
│ mqtt_monitor.py │
└──────┬──────────┘
       │ Raw bytes
       ↓
┌─────────────────┐
│ Parser          │
│ naturelink_     │
│ parser.py       │
└──────┬──────────┘
       │ Parsed JSON
       ↓
┌─────────────────┐
│ Validator       │
│ Check data      │
│ integrity       │
└──────┬──────────┘
       │ Valid data
       ↓
┌─────────────────┐
│ Database        │
│ PostgreSQL/     │
│ MySQL/MongoDB   │
└─────────────────┘
```

---

## Setup Environment

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install paho-mqtt

# PostgreSQL
pip install psycopg2-binary

# MySQL
pip install pymysql

# MongoDB
pip install pymongo

# Optional: untuk async processing
pip install asyncio aiofiles
```

### 2. Environment Variables

Buat file `.env`:

```bash
# MQTT Configuration
MQTT_BROKER=isi_host_mqtt
MQTT_PORT=1883
MQTT_USERNAME=isi_username_mqtt
MQTT_PASSWORD=isi_password_mqtt
MQTT_TOPIC=/Naturelink/Send

# Database Configuration (PostgreSQL)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gps_tracking
DB_USER=postgres
DB_PASSWORD=isi_password_database

# Optional
LOG_LEVEL=INFO
BATCH_SIZE=10
RETRY_ATTEMPTS=3
```

### 3. Load Environment Variables

```python
import os
from dotenv import load_dotenv

load_dotenv()

MQTT_BROKER = os.getenv('MQTT_BROKER')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
```

---

## Database Schema

### PostgreSQL Schema

```sql
-- Table: devices
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    imei VARCHAR(20) UNIQUE NOT NULL,
    device_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: gps_locations
CREATE TABLE gps_locations (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id),
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_imei (imei),
    INDEX idx_timestamp (timestamp),
    INDEX idx_device_timestamp (device_id, timestamp)
);

-- Table: device_status
CREATE TABLE device_status (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id),
    imei VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    battery_voltage INTEGER,
    external_voltage INTEGER,
    network_type VARCHAR(10),
    mileage INTEGER DEFAULT 0,
    running_time INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_imei_timestamp (imei, timestamp)
);

-- Table: io_elements (optional - untuk data IO tambahan)
CREATE TABLE io_elements (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES gps_locations(id),
    io_key VARCHAR(50) NOT NULL,
    io_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_gps_locations_coords ON gps_locations(latitude, longitude);
CREATE INDEX idx_gps_locations_speed ON gps_locations(speed);
```

### MySQL Schema

```sql
-- Sama seperti PostgreSQL, tapi gunakan:
-- AUTO_INCREMENT instead of SERIAL
-- DATETIME instead of TIMESTAMP
-- ENGINE=InnoDB

CREATE TABLE devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    imei VARCHAR(20) UNIQUE NOT NULL,
    device_name VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_imei (imei)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- dst...
```

### MongoDB Schema (Document-based)

```javascript
// Collection: gps_tracking
{
  "_id": ObjectId("..."),
  "imei": "0866344055567122",
  "device_name": "Truck-001",
  "timestamp": ISODate("2026-03-06T06:10:49Z"),
  "event_code": 51,
  "gps": {
    "latitude": 22.636635,
    "longitude": 114.030401,
    "speed_kmh": 0,
    "heading": 196,
    "satellites": 17,
    "valid": true,
    "signal_quality": 25,
    "altitude": 78
  },
  "device_status": {
    "battery_voltage": 4118,
    "external_voltage": 12282,
    "network_type": "4G",
    "mileage": 99,
    "running_time": 1672
  },
  "io_elements": {
    "hdop": 9,
    "input_status": 0,
    "output_status": 0,
    "base_station": {
      "mcc": 460,
      "mnc": 0,
      "lac": 10150,
      "cell_id": 54188690
    },
    "acceleration": {
      "x_mg": 13,
      "y_mg": -17,
      "z_mg": -1002
    }
  },
  "created_at": ISODate("2026-03-06T14:30:45Z")
}

// Indexes
db.gps_tracking.createIndex({ "imei": 1, "timestamp": -1 })
db.gps_tracking.createIndex({ "gps.latitude": 1, "gps.longitude": 1 })
db.gps_tracking.createIndex({ "timestamp": -1 })
```

---

## Subscribe & Parse Data

### Step 1: Import Libraries

```python
import paho.mqtt.client as mqtt
from naturelink_parser import NaturelinkParser
import json
from datetime import datetime
```

### Step 2: Setup MQTT Client

```python
class GPSDataCollector:
    def __init__(self):
        self.parser = NaturelinkParser()
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✓ Connected to MQTT broker")
            client.subscribe(MQTT_TOPIC, qos=1)
        else:
            print(f"✗ Connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        # Convert binary payload to hex
        hex_data = msg.payload.hex()
        
        # Parse data
        parsed = self.parser.parse(hex_data)
        
        if parsed.get('parsed'):
            # Process valid data
            self.save_to_database(parsed)
        else:
            print(f"Parse error: {parsed.get('error')}")
    
    def start(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_forever()
```

### Step 3: Parse Data

```python
def parse_gps_data(hex_data):
    """
    Parse hex data dari MQTT
    
    Returns:
        dict: Parsed data atau None jika gagal
    """
    parser = NaturelinkParser()
    result = parser.parse(hex_data)
    
    if not result.get('parsed'):
        print(f"Error: {result.get('error')}")
        return None
    
    return result
```

### Step 4: Extract Data untuk Database

```python
def extract_database_fields(parsed_data):
    """
    Extract field yang diperlukan untuk database
    
    Returns:
        dict: Data siap insert ke database
    """
    header = parsed_data.get('header', {})
    records = parsed_data.get('records', [])
    
    if not records:
        return None
    
    record = records[0]  # Ambil record pertama
    gps = record.get('gps', {})
    io = record.get('io_elements', {})
    
    data = {
        'imei': header.get('imei'),
        'event_code': record.get('event_code'),
        'timestamp': record.get('timestamp'),
        
        # GPS data
        'latitude': gps.get('latitude'),
        'longitude': gps.get('longitude'),
        'speed': gps.get('speed_kmh'),
        'heading': gps.get('heading'),
        'satellites': gps.get('satellites'),
        'gps_valid': gps.get('valid'),
        'signal_quality': gps.get('signal_quality'),
        
        # Device status
        'battery_voltage': io.get('battery_voltage', {}).get('value'),
        'external_voltage': io.get('external_voltage', {}).get('value'),
        'network_type': io.get('network_type'),
        'mileage': io.get('mileage', {}).get('value'),
        'running_time': io.get('running_time', {}).get('value'),
        'altitude': io.get('altitude', {}).get('value'),
    }
    
    return data
```

---

## Simpan ke Database

### PostgreSQL Implementation

```python
import psycopg2
from psycopg2.extras import execute_values

class PostgreSQLWriter:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        self.cursor = self.conn.cursor()
    
    def insert_device(self, imei, device_name=None):
        """Insert atau update device"""
        query = """
            INSERT INTO devices (imei, device_name)
            VALUES (%s, %s)
            ON CONFLICT (imei) DO UPDATE
            SET updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """
        self.cursor.execute(query, (imei, device_name))
        device_id = self.cursor.fetchone()[0]
        self.conn.commit()
        return device_id
    
    def insert_gps_location(self, data):
        """Insert GPS location data"""
        # Pastikan device ada
        device_id = self.insert_device(data['imei'])
        
        query = """
            INSERT INTO gps_locations (
                device_id, imei, event_code, timestamp,
                latitude, longitude, speed, heading,
                satellites, gps_valid, signal_quality, altitude
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """
        
        values = (
            device_id,
            data['imei'],
            data['event_code'],
            data['timestamp'],
            data['latitude'],
            data['longitude'],
            data['speed'],
            data['heading'],
            data['satellites'],
            data['gps_valid'],
            data['signal_quality'],
            data['altitude']
        )
        
        self.cursor.execute(query, values)
        location_id = self.cursor.fetchone()[0]
        self.conn.commit()
        
        return location_id
    
    def insert_device_status(self, data):
        """Insert device status"""
        device_id = self.insert_device(data['imei'])
        
        query = """
            INSERT INTO device_status (
                device_id, imei, timestamp,
                battery_voltage, external_voltage,
                network_type, mileage, running_time
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            device_id,
            data['imei'],
            data['timestamp'],
            data['battery_voltage'],
            data['external_voltage'],
            data['network_type'],
            data['mileage'],
            data['running_time']
        )
        
        self.cursor.execute(query, values)
        self.conn.commit()
    
    def close(self):
        self.cursor.close()
        self.conn.close()
```

### MySQL Implementation

```python
import pymysql

class MySQLWriter:
    def __init__(self):
        self.conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            charset='utf8mb4'
        )
        self.cursor = self.conn.cursor()
    
    # Sama seperti PostgreSQL, tapi:
    # - Gunakan %s untuk placeholder (sama)
    # - ON DUPLICATE KEY UPDATE untuk MySQL
    
    def insert_device(self, imei, device_name=None):
        query = """
            INSERT INTO devices (imei, device_name)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
            updated_at = CURRENT_TIMESTAMP
        """
        self.cursor.execute(query, (imei, device_name))
        self.conn.commit()
        return self.cursor.lastrowid
```

### MongoDB Implementation

```python
from pymongo import MongoClient
from datetime import datetime

class MongoDBWriter:
    def __init__(self):
        self.client = MongoClient(f"mongodb://{DB_HOST}:{DB_PORT}/")
        self.db = self.client[DB_NAME]
        self.collection = self.db['gps_tracking']
    
    def insert_gps_data(self, parsed_data):
        """Insert complete GPS data as document"""
        header = parsed_data.get('header', {})
        record = parsed_data.get('records', [{}])[0]
        gps = record.get('gps', {})
        io = record.get('io_elements', {})
        
        document = {
            'imei': header.get('imei'),
            'timestamp': datetime.fromisoformat(record.get('timestamp')),
            'event_code': record.get('event_code'),
            'gps': {
                'latitude': gps.get('latitude'),
                'longitude': gps.get('longitude'),
                'speed_kmh': gps.get('speed_kmh'),
                'heading': gps.get('heading'),
                'satellites': gps.get('satellites'),
                'valid': gps.get('valid'),
                'signal_quality': gps.get('signal_quality')
            },
            'device_status': {
                'battery_voltage': io.get('battery_voltage', {}).get('value'),
                'external_voltage': io.get('external_voltage', {}).get('value'),
                'network_type': io.get('network_type'),
                'mileage': io.get('mileage', {}).get('value'),
                'running_time': io.get('running_time', {}).get('value')
            },
            'io_elements': io,
            'created_at': datetime.now()
        }
        
        result = self.collection.insert_one(document)
        return result.inserted_id
    
    def close(self):
        self.client.close()
```

---

## Contoh Implementasi

### Script Lengkap: MQTT to PostgreSQL

```python
#!/usr/bin/env python3
"""
MQTT to PostgreSQL - Complete Implementation
Subscribe MQTT → Parse → Save to Database
"""

import paho.mqtt.client as mqtt
import psycopg2
from naturelink_parser import NaturelinkParser
import os
from datetime import datetime

# Configuration
MQTT_BROKER = os.getenv('MQTT_BROKER')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')
MQTT_TOPIC = os.getenv('MQTT_TOPIC', '/Naturelink/Send')

DB_HOST = 'localhost'
DB_PORT = 5432
DB_NAME = 'gps_tracking'
DB_USER = 'postgres'
DB_PASSWORD = os.getenv('DB_PASSWORD')


class GPSTracker:
    def __init__(self):
        self.parser = NaturelinkParser()
        self.db_conn = None
        self.db_cursor = None
        self.mqtt_client = mqtt.Client()
        self.message_count = 0
        
        # Setup MQTT
        self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        
        # Setup Database
        self.connect_database()
    
    def connect_database(self):
        """Connect to PostgreSQL"""
        try:
            self.db_conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            self.db_cursor = self.db_conn.cursor()
            print("✓ Connected to database")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            raise
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✓ Connected to MQTT broker")
            client.subscribe(MQTT_TOPIC, qos=1)
            print(f"✓ Subscribed to {MQTT_TOPIC}")
        else:
            print(f"✗ MQTT connection failed: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print("⚠ Disconnected from MQTT. Reconnecting...")
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT message"""
        self.message_count += 1
        print(f"\n📨 Message #{self.message_count} - {datetime.now()}")
        
        try:
            # Parse binary data
            hex_data = msg.payload.hex()
            parsed = self.parser.parse(hex_data)
            
            if not parsed.get('parsed'):
                print(f"✗ Parse error: {parsed.get('error')}")
                return
            
            # Extract data
            data = self.extract_data(parsed)
            
            if data:
                # Save to database
                self.save_to_database(data)
                print(f"✓ Saved: IMEI {data['imei']}, Lat/Lon: {data['latitude']:.6f}, {data['longitude']:.6f}")
        
        except Exception as e:
            print(f"✗ Error processing message: {e}")
    
    def extract_data(self, parsed):
        """Extract data from parsed result"""
        header = parsed.get('header', {})
        records = parsed.get('records', [])
        
        if not records:
            return None
        
        record = records[0]
        gps = record.get('gps', {})
        io = record.get('io_elements', {})
        
        return {
            'imei': header.get('imei'),
            'event_code': record.get('event_code'),
            'timestamp': record.get('timestamp'),
            'latitude': gps.get('latitude'),
            'longitude': gps.get('longitude'),
            'speed': gps.get('speed_kmh'),
            'heading': gps.get('heading'),
            'satellites': gps.get('satellites'),
            'gps_valid': gps.get('valid'),
            'signal_quality': gps.get('signal_quality'),
            'altitude': io.get('altitude', {}).get('value', 0),
            'battery_voltage': io.get('battery_voltage', {}).get('value'),
            'external_voltage': io.get('external_voltage', {}).get('value'),
            'network_type': io.get('network_type'),
            'mileage': io.get('mileage', {}).get('value', 0),
            'running_time': io.get('running_time', {}).get('value', 0),
        }
    
    def save_to_database(self, data):
        """Save data to PostgreSQL"""
        try:
            # Insert device
            device_query = """
                INSERT INTO devices (imei)
                VALUES (%s)
                ON CONFLICT (imei) DO UPDATE
                SET updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """
            self.db_cursor.execute(device_query, (data['imei'],))
            device_id = self.db_cursor.fetchone()[0]
            
            # Insert GPS location
            gps_query = """
                INSERT INTO gps_locations (
                    device_id, imei, event_code, timestamp,
                    latitude, longitude, speed, heading,
                    satellites, gps_valid, signal_quality, altitude
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            gps_values = (
                device_id, data['imei'], data['event_code'], data['timestamp'],
                data['latitude'], data['longitude'], data['speed'], data['heading'],
                data['satellites'], data['gps_valid'], data['signal_quality'], data['altitude']
            )
            self.db_cursor.execute(gps_query, gps_values)
            
            # Insert device status
            status_query = """
                INSERT INTO device_status (
                    device_id, imei, timestamp,
                    battery_voltage, external_voltage,
                    network_type, mileage, running_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            status_values = (
                device_id, data['imei'], data['timestamp'],
                data['battery_voltage'], data['external_voltage'],
                data['network_type'], data['mileage'], data['running_time']
            )
            self.db_cursor.execute(status_query, status_values)
            
            # Commit
            self.db_conn.commit()
        
        except Exception as e:
            self.db_conn.rollback()
            print(f"✗ Database error: {e}")
            raise
    
    def start(self):
        """Start tracking"""
        try:
            print("\n" + "="*80)
            print("GPS TRACKER - MQTT TO DATABASE")
            print("="*80)
            print(f"MQTT: {MQTT_BROKER}:{MQTT_PORT}")
            print(f"Database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
            print("="*80 + "\n")
            
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_forever()
        
        except KeyboardInterrupt:
            print("\n\n⏹ Stopping...")
            self.cleanup()
        
        except Exception as e:
            print(f"\n✗ Error: {e}")
            self.cleanup()
    
    def cleanup(self):
        """Cleanup connections"""
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        if self.db_cursor:
            self.db_cursor.close()
        if self.db_conn:
            self.db_conn.close()
        print(f"✓ Total messages processed: {self.message_count}")
        print("✓ Stopped")


if __name__ == '__main__':
    tracker = GPSTracker()
    tracker.start()
```

---

## Best Practices

### 1. Error Handling

```python
def safe_insert(self, data):
    """Insert dengan retry logic"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            self.insert_gps_location(data)
            return True
        except Exception as e:
            retry_count += 1
            print(f"Retry {retry_count}/{max_retries}: {e}")
            time.sleep(1)
    
    return False
```

### 2. Batch Insert

```python
def batch_insert(self, data_list):
    """Insert multiple records sekaligus"""
    query = """
        INSERT INTO gps_locations (...)
        VALUES %s
    """
    values = [(d['imei'], d['latitude'], ...) for d in data_list]
    execute_values(self.cursor, query, values)
    self.conn.commit()
```

### 3. Data Validation

```python
def validate_gps_data(data):
    """Validasi data sebelum insert"""
    if not data.get('imei'):
        return False
    
    lat = data.get('latitude', 0)
    lon = data.get('longitude', 0)
    
    # Validasi koordinat
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return False
    
    # Validasi GPS valid
    if not data.get('gps_valid'):
        print("⚠ GPS not valid, skipping...")
        return False
    
    return True
```

### 4. Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gps_tracker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Usage
logger.info(f"Saved GPS data: {imei}")
logger.error(f"Database error: {e}")
```

### 5. Connection Pooling

```python
from psycopg2 import pool

class DatabasePool:
    def __init__(self):
        self.pool = pool.SimpleConnectionPool(
            1, 20,  # min, max connections
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    
    def get_connection(self):
        return self.pool.getconn()
    
    def return_connection(self, conn):
        self.pool.putconn(conn)
```

---

## Troubleshooting

### Problem: Data tidak masuk ke database

**Solusi:**
1. Cek koneksi database: `psql -h localhost -U postgres -d gps_tracking`
2. Cek error log
3. Validasi data yang diparsing
4. Cek constraint database (unique, foreign key)

### Problem: MQTT disconnect terus

**Solusi:**
1. Cek network connection
2. Implement reconnect logic
3. Gunakan `loop_start()` untuk background thread

### Problem: Duplicate data

**Solusi:**
1. Gunakan unique constraint: `(imei, timestamp)`
2. Atau `ON CONFLICT DO NOTHING`

```sql
ALTER TABLE gps_locations 
ADD CONSTRAINT unique_imei_timestamp 
UNIQUE (imei, timestamp);
```

### Problem: Performa lambat

**Solusi:**
1. Gunakan batch insert
2. Tambah indexes
3. Gunakan connection pooling
4. Async processing

---

## Query Contoh

### Get Latest Location per Device

```sql
SELECT DISTINCT ON (imei)
    imei, timestamp, latitude, longitude, speed
FROM gps_locations
ORDER BY imei, timestamp DESC;
```

### Get Route History

```sql
SELECT 
    timestamp, latitude, longitude, speed, heading
FROM gps_locations
WHERE imei = '0866344055567122'
    AND timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp ASC;
```

### Get Device Statistics

```sql
SELECT 
    imei,
    COUNT(*) as total_records,
    MAX(timestamp) as last_update,
    AVG(speed) as avg_speed,
    MAX(speed) as max_speed
FROM gps_locations
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY imei;
```

---

## Kesimpulan

Dengan dokumentasi ini, developer lain bisa:
1. ✅ Setup environment dengan mudah
2. ✅ Memahami struktur database
3. ✅ Subscribe dan parse data MQTT
4. ✅ Simpan data ke database (PostgreSQL/MySQL/MongoDB)
5. ✅ Implement best practices
6. ✅ Troubleshoot masalah umum

**File yang perlu disiapkan:**
- `mqtt_to_database.py` (script utama)
- `.env` (konfigurasi)
- `requirements.txt` (dependencies)
- SQL schema file

**Next Steps:**
- Deploy ke production server
- Setup monitoring (Grafana, Prometheus)
- Implement alert system
- Buat API untuk akses data

---

**Author**: GPS Tracking Team  
**Last Updated**: 6 Maret 2026  
**Version**: 1.0
