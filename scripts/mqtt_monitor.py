#!/usr/bin/env python3
"""
Naturelink GPS Tracker - MQTT Real-time Monitor
Subscribe to MQTT broker and parse incoming GPS data in real-time

Author: Auto-generated
Date: 2026-03-06
"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime
from naturelink_parser import NaturelinkParser, format_gps_location
import sys
import os

from dotenv import load_dotenv


load_dotenv()

# MQTT Configuration
MQTT_BROKER = os.getenv('MQTT_BROKER', '127.0.0.1')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_TOPIC = os.getenv('MQTT_TOPIC', '/Naturelink/Send')

# Output configuration
SAVE_TO_FILE = True
OUTPUT_FILE = '../data/gps_tracking.jsonl'


class NaturelinkMonitor:
    """Real-time MQTT monitor for Naturelink GPS data"""
    
    def __init__(self):
        self.parser = NaturelinkParser()
        self.message_count = 0
        self.client = mqtt.Client()
        if MQTT_USERNAME and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print(f"✓ Connected to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
            print(f"✓ Subscribing to topic: {MQTT_TOPIC}")
            client.subscribe(MQTT_TOPIC, qos=1)
            print("\n" + "=" * 80)
            print("Waiting for GPS data... (Press Ctrl+C to stop)")
            print("=" * 80 + "\n")
        else:
            print(f"✗ Connection failed with code: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        if rc != 0:
            print(f"\n⚠ Unexpected disconnection. Reconnecting...")
    
    def on_message(self, client, userdata, msg):
        """Callback when message received"""
        self.message_count += 1
        
        print(f"\n{'=' * 80}")
        print(f"📨 MESSAGE #{self.message_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 80}")
        
        # Convert payload to hex string
        hex_data = msg.payload.hex()
        print(f"\n📦 Raw Data ({len(msg.payload)} bytes):")
        print(self._format_hex(hex_data))
        
        # Parse the data
        try:
            parsed = self.parser.parse(hex_data)
            
            if parsed.get('parsed'):
                self._print_parsed_data(parsed)
                
                # Save to file
                if SAVE_TO_FILE:
                    self._save_to_file(parsed)
            else:
                print(f"\n❌ Parsing failed: {parsed.get('error')}")
        
        except Exception as e:
            print(f"\n❌ Error parsing data: {e}")
        
        print(f"\n{'=' * 80}\n")
    
    def _format_hex(self, hex_str: str, bytes_per_line: int = 16) -> str:
        """Format hex string for display"""
        lines = []
        for i in range(0, len(hex_str), bytes_per_line * 2):
            chunk = hex_str[i:i + bytes_per_line * 2]
            formatted = ' '.join([chunk[j:j+2] for j in range(0, len(chunk), 2)])
            lines.append(f"  {formatted}")
        return '\n'.join(lines)
    
    def _print_parsed_data(self, parsed: dict):
        """Print parsed data in readable format"""
        header = parsed.get('header', {})
        print(f"\n📡 DEVICE INFO:")
        print(f"  IMEI: {header.get('imei')}")
        print(f"  Frame ID: {header.get('frame_id')}")
        
        records = parsed.get('records', [])
        for i, record in enumerate(records, 1):
            print(f"\n📍 LOCATION #{i}:")
            print(f"  Event: {record.get('event_code')}")
            print(f"  Time: {record.get('timestamp')}")
            
            gps = record.get('gps', {})
            status = '✓ Valid' if gps.get('valid') else '✗ Invalid'
            print(f"  GPS: {status}")
            print(f"  Lat/Lon: {gps.get('latitude'):.6f}, {gps.get('longitude'):.6f}")
            print(f"  Speed: {gps.get('speed_kmh')} km/h")
            print(f"  Heading: {gps.get('heading')}°")
            print(f"  Satellites: {gps.get('satellites')}")
            print(f"  Maps: {format_gps_location(record)}")
            
            io = record.get('io_elements', {})
            if 'battery_voltage' in io:
                batt = io['battery_voltage']['value']
                print(f"  Battery: {batt} mV ({batt/1000:.2f}V)")
            
            if 'external_voltage' in io:
                ext = io['external_voltage']['value']
                print(f"  External: {ext} mV ({ext/1000:.2f}V)")
            
            if 'mileage' in io:
                mileage = io['mileage']['value']
                print(f"  Mileage: {mileage} m ({mileage/1000:.2f} km)")
            
            if 'network_type' in io:
                print(f"  Network: {io['network_type']}")
    
    def _save_to_file(self, parsed: dict):
        """Save parsed data to JSONL file"""
        try:
            with open(OUTPUT_FILE, 'a') as f:
                json.dump(parsed, f)
                f.write('\n')
            print(f"\n💾 Saved to: {OUTPUT_FILE}")
        except Exception as e:
            print(f"\n⚠ Failed to save: {e}")
    
    def start(self):
        """Start monitoring"""
        try:
            print("\n" + "=" * 80)
            print("NATURELINK GPS TRACKER - MQTT MONITOR")
            print("=" * 80)
            print(f"\nConnecting to MQTT broker...")
            print(f"  Host: {MQTT_BROKER}")
            print(f"  Port: {MQTT_PORT}")
            print(f"  Topic: {MQTT_TOPIC}")
            
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_forever()
        
        except KeyboardInterrupt:
            print("\n\n⏹ Stopping monitor...")
            self.client.disconnect()
            print(f"✓ Total messages received: {self.message_count}")
            print("✓ Monitor stopped")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)


if __name__ == '__main__':
    monitor = NaturelinkMonitor()
    monitor.start()
