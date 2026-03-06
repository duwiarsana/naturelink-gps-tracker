#!/usr/bin/env python3
"""
MQTT to Database - Production Ready Script
Subscribe to Naturelink GPS MQTT → Parse → Save to PostgreSQL/MySQL/MongoDB

Usage:
    python3 mqtt_to_database.py --db postgresql
    python3 mqtt_to_database.py --db mysql
    python3 mqtt_to_database.py --db mongodb

Author: GPS Tracking Team
Date: 2026-03-06
"""

import paho.mqtt.client as mqtt
import psycopg2
import pymysql
from pymongo import MongoClient
from naturelink_parser import NaturelinkParser
import argparse
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import time
import os

from dotenv import load_dotenv


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../data/gps_tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


load_dotenv()

MQTT_BROKER = os.getenv('MQTT_BROKER', '127.0.0.1')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_TOPIC = os.getenv('MQTT_TOPIC', '/Naturelink/Send')

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT_POSTGRES = int(os.getenv('DB_PORT_POSTGRES', '5432'))
DB_PORT_MYSQL = int(os.getenv('DB_PORT_MYSQL', '3306'))
DB_PORT_MONGO = int(os.getenv('DB_PORT_MONGO', '27017'))
DB_NAME = os.getenv('DB_NAME', 'gps_tracking')
DB_USER = os.getenv('DB_USER', '')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')


class DatabaseWriter:
    """Base class for database writers"""
    
    def insert_gps_data(self, data: Dict[str, Any]) -> bool:
        raise NotImplementedError
    
    def close(self):
        raise NotImplementedError


class PostgreSQLWriter(DatabaseWriter):
    """PostgreSQL database writer"""
    
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT_POSTGRES,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            self.cursor = self.conn.cursor()
            logger.info("✓ Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"✗ PostgreSQL connection failed: {e}")
            raise
    
    def insert_gps_data(self, data: Dict[str, Any]) -> bool:
        try:
            device_query = """
                INSERT INTO devices (imei)
                VALUES (%s)
                ON CONFLICT (imei) DO UPDATE
                SET updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """
            self.cursor.execute(device_query, (data['imei'],))
            device_id = self.cursor.fetchone()[0]
            
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
            self.cursor.execute(gps_query, gps_values)
            
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
            self.cursor.execute(status_query, status_values)
            
            self.conn.commit()
            return True
        
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ PostgreSQL insert error: {e}")
            return False
    
    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("✓ PostgreSQL connection closed")


class MySQLWriter(DatabaseWriter):
    """MySQL database writer"""
    
    def __init__(self):
        try:
            self.conn = pymysql.connect(
                host=DB_HOST,
                port=DB_PORT_MYSQL,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                charset='utf8mb4'
            )
            self.cursor = self.conn.cursor()
            logger.info("✓ Connected to MySQL")
        except Exception as e:
            logger.error(f"✗ MySQL connection failed: {e}")
            raise
    
    def insert_gps_data(self, data: Dict[str, Any]) -> bool:
        try:
            device_query = """
                INSERT INTO devices (imei)
                VALUES (%s)
                ON DUPLICATE KEY UPDATE
                updated_at = CURRENT_TIMESTAMP
            """
            self.cursor.execute(device_query, (data['imei'],))
            device_id = self.cursor.lastrowid or self._get_device_id(data['imei'])
            
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
            self.cursor.execute(gps_query, gps_values)
            
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
            self.cursor.execute(status_query, status_values)
            
            self.conn.commit()
            return True
        
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ MySQL insert error: {e}")
            return False
    
    def _get_device_id(self, imei: str) -> int:
        query = "SELECT id FROM devices WHERE imei = %s"
        self.cursor.execute(query, (imei,))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("✓ MySQL connection closed")


class MongoDBWriter(DatabaseWriter):
    """MongoDB database writer"""
    
    def __init__(self):
        try:
            self.client = MongoClient(f"mongodb://{DB_HOST}:{DB_PORT_MONGO}/")
            self.db = self.client[DB_NAME]
            self.collection = self.db['gps_tracking']
            logger.info("✓ Connected to MongoDB")
        except Exception as e:
            logger.error(f"✗ MongoDB connection failed: {e}")
            raise
    
    def insert_gps_data(self, data: Dict[str, Any]) -> bool:
        try:
            document = {
                'imei': data['imei'],
                'timestamp': datetime.fromisoformat(data['timestamp']),
                'event_code': data['event_code'],
                'gps': {
                    'latitude': data['latitude'],
                    'longitude': data['longitude'],
                    'speed_kmh': data['speed'],
                    'heading': data['heading'],
                    'satellites': data['satellites'],
                    'valid': data['gps_valid'],
                    'signal_quality': data['signal_quality'],
                    'altitude': data['altitude']
                },
                'device_status': {
                    'battery_voltage': data['battery_voltage'],
                    'external_voltage': data['external_voltage'],
                    'network_type': data['network_type'],
                    'mileage': data['mileage'],
                    'running_time': data['running_time']
                },
                'created_at': datetime.now()
            }
            
            self.collection.insert_one(document)
            return True
        
        except Exception as e:
            logger.error(f"✗ MongoDB insert error: {e}")
            return False
    
    def close(self):
        if self.client:
            self.client.close()
        logger.info("✓ MongoDB connection closed")


class GPSTracker:
    """Main GPS tracker class"""
    
    def __init__(self, db_type: str = 'postgresql'):
        self.parser = NaturelinkParser()
        self.db_writer = self._create_db_writer(db_type)
        self.mqtt_client = mqtt.Client()
        self.message_count = 0
        self.success_count = 0
        self.error_count = 0
        
        if MQTT_USERNAME and MQTT_PASSWORD:
            self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
    
    def _create_db_writer(self, db_type: str) -> DatabaseWriter:
        """Create database writer based on type"""
        if db_type == 'postgresql':
            return PostgreSQLWriter()
        elif db_type == 'mysql':
            return MySQLWriter()
        elif db_type == 'mongodb':
            return MongoDBWriter()
        else:
            raise ValueError(f"Unknown database type: {db_type}")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"✓ Connected to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
            client.subscribe(MQTT_TOPIC, qos=1)
            logger.info(f"✓ Subscribed to topic: {MQTT_TOPIC}")
        else:
            logger.error(f"✗ MQTT connection failed with code: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning("⚠ Disconnected from MQTT broker. Reconnecting...")
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT message"""
        self.message_count += 1
        
        try:
            hex_data = msg.payload.hex()
            parsed = self.parser.parse(hex_data)
            
            if not parsed.get('parsed'):
                logger.error(f"Parse error: {parsed.get('error')}")
                self.error_count += 1
                return
            
            data = self._extract_data(parsed)
            
            if data and self._validate_data(data):
                if self.db_writer.insert_gps_data(data):
                    self.success_count += 1
                    logger.info(
                        f"✓ [{self.message_count}] IMEI: {data['imei']}, "
                        f"Lat/Lon: {data['latitude']:.6f}, {data['longitude']:.6f}, "
                        f"Speed: {data['speed']} km/h"
                    )
                else:
                    self.error_count += 1
            else:
                logger.warning("⚠ Invalid data, skipped")
                self.error_count += 1
        
        except Exception as e:
            logger.error(f"✗ Error processing message: {e}")
            self.error_count += 1
    
    def _extract_data(self, parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
            'speed': gps.get('speed_kmh', 0),
            'heading': gps.get('heading', 0),
            'satellites': gps.get('satellites', 0),
            'gps_valid': gps.get('valid', False),
            'signal_quality': gps.get('signal_quality', 0),
            'altitude': io.get('altitude', {}).get('value', 0),
            'battery_voltage': io.get('battery_voltage', {}).get('value'),
            'external_voltage': io.get('external_voltage', {}).get('value'),
            'network_type': io.get('network_type'),
            'mileage': io.get('mileage', {}).get('value', 0),
            'running_time': io.get('running_time', {}).get('value', 0),
        }
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate GPS data"""
        if not data.get('imei'):
            logger.warning("⚠ Missing IMEI")
            return False
        
        lat = data.get('latitude', 0)
        lon = data.get('longitude', 0)
        
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            logger.warning(f"⚠ Invalid coordinates: {lat}, {lon}")
            return False
        
        if not data.get('gps_valid'):
            logger.warning("⚠ GPS not valid")
            return False
        
        return True
    
    def start(self):
        """Start GPS tracking"""
        try:
            print("\n" + "=" * 80)
            print("NATURELINK GPS TRACKER - MQTT TO DATABASE")
            print("=" * 80)
            print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
            print(f"MQTT Topic: {MQTT_TOPIC}")
            print(f"Database: {self.db_writer.__class__.__name__}")
            print("=" * 80)
            print("\nWaiting for GPS data... (Press Ctrl+C to stop)\n")
            
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_forever()
        
        except KeyboardInterrupt:
            print("\n\n⏹ Stopping GPS tracker...")
            self.cleanup()
        
        except Exception as e:
            logger.error(f"✗ Fatal error: {e}")
            self.cleanup()
            sys.exit(1)
    
    def cleanup(self):
        """Cleanup connections"""
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        if self.db_writer:
            self.db_writer.close()
        
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)
        print(f"Total messages: {self.message_count}")
        print(f"Successfully saved: {self.success_count}")
        print(f"Errors: {self.error_count}")
        print(f"Success rate: {(self.success_count/self.message_count*100) if self.message_count > 0 else 0:.1f}%")
        print("=" * 80)
        print("✓ GPS tracker stopped")


def main():
    parser = argparse.ArgumentParser(
        description='Naturelink GPS Tracker - MQTT to Database'
    )
    parser.add_argument(
        '--db',
        choices=['postgresql', 'mysql', 'mongodb'],
        default='postgresql',
        help='Database type (default: postgresql)'
    )
    
    args = parser.parse_args()
    
    tracker = GPSTracker(db_type=args.db)
    tracker.start()


if __name__ == '__main__':
    main()
