#!/usr/bin/env python3
"""
MQTT JSON Republisher - Naturelink GPS Tracker
Subscribe raw binary dari /Naturelink/Send → Parse → Publish JSON ke /Naturelink/Send/json

Service ini berjalan sebagai daemon/background service yang:
1. Subscribe ke topic raw binary (/Naturelink/Send)
2. Parse data binary menggunakan naturelink_parser
3. Publish hasil parsing dalam format JSON ke topic baru (/Naturelink/Send/json)

Usage:
    python3 mqtt_json_republisher.py

Author: GPS Tracking Team
Date: 2026-03-06
"""

import paho.mqtt.client as mqtt
from naturelink_parser import NaturelinkParser
import json
import os
import logging
from datetime import datetime

from dotenv import load_dotenv


load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
LOG_FILE = os.path.join(PROJECT_DIR, 'data', 'json_republisher.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

MQTT_BROKER = os.getenv('MQTT_BROKER', '127.0.0.1')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')

TOPIC_RAW = os.getenv('MQTT_TOPIC', '/Naturelink/Send')
TOPIC_JSON = os.getenv('MQTT_TOPIC_JSON', '/Naturelink/Send/json')


class JSONRepublisher:
    """Service untuk convert raw binary MQTT ke JSON dan republish"""
    
    def __init__(self):
        self.parser = NaturelinkParser()
        self.client = mqtt.Client(client_id='naturelink_json_republisher')
        
        if MQTT_USERNAME and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        self.message_count = 0
        self.success_count = 0
        self.error_count = 0
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"✓ Connected to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
            client.subscribe(TOPIC_RAW, qos=1)
            logger.info(f"✓ Subscribed to RAW topic: {TOPIC_RAW}")
            logger.info(f"✓ Will publish JSON to: {TOPIC_JSON}")
        else:
            logger.error(f"✗ Connection failed with code: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning(f"⚠ Disconnected from MQTT broker (code: {rc}). Reconnecting...")
    
    def on_message(self, client, userdata, msg):
        """Callback ketika menerima pesan raw binary"""
        self.message_count += 1
        
        try:
            hex_data = msg.payload.hex()
            parsed = self.parser.parse(hex_data)
            
            if not parsed.get('parsed'):
                logger.error(f"Parse error: {parsed.get('error')}")
                self.error_count += 1
                return
            
            json_payload = self.convert_to_json(parsed)
            
            if json_payload:
                result = client.publish(
                    TOPIC_JSON,
                    json.dumps(json_payload, ensure_ascii=False),
                    qos=1,
                    retain=False
                )
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.success_count += 1
                    logger.info(
                        f"✓ [{self.message_count}] Published JSON - "
                        f"IMEI: {json_payload.get('device', {}).get('imei')}, "
                        f"Lat/Lon: {json_payload.get('lokasi', {}).get('latitude'):.6f}, "
                        f"{json_payload.get('lokasi', {}).get('longitude'):.6f}"
                    )
                else:
                    logger.error(f"✗ Failed to publish JSON: {result.rc}")
                    self.error_count += 1
            else:
                logger.warning("⚠ No valid data to publish")
                self.error_count += 1
        
        except Exception as e:
            logger.error(f"✗ Error processing message: {e}")
            self.error_count += 1
    
    def convert_to_json(self, parsed_data):
        """Convert parsed data ke format JSON yang mudah dibaca"""
        header = parsed_data.get('header', {})
        records = parsed_data.get('records', [])
        
        if not records:
            return None
        
        record = records[0]
        gps = record.get('gps', {})
        io = record.get('io_elements', {})
        
        json_payload = {
            "device": {
                "imei": header.get('imei'),
                "frame_id": header.get('frame_id')
            },
            "waktu": record.get('timestamp'),
            "event": {
                "kode": record.get('event_code'),
                "nama": self.get_event_name(record.get('event_code'))
            },
            "lokasi": {
                "latitude": gps.get('latitude'),
                "longitude": gps.get('longitude'),
                "google_maps": f"https://www.google.com/maps?q={gps.get('latitude')},{gps.get('longitude')}",
                "gps_valid": gps.get('valid'),
                "kecepatan_kmh": gps.get('speed_kmh'),
                "arah_derajat": gps.get('heading'),
                "ketinggian_meter": io.get('altitude', {}).get('value', 0),
                "jumlah_satelit": gps.get('satellites'),
                "kualitas_sinyal": gps.get('signal_quality')
            },
            "status_device": {
                "baterai_mv": io.get('battery_voltage', {}).get('value'),
                "baterai_volt": round(io.get('battery_voltage', {}).get('value', 0) / 1000, 2) if io.get('battery_voltage') else None,
                "power_eksternal_mv": io.get('external_voltage', {}).get('value'),
                "power_eksternal_volt": round(io.get('external_voltage', {}).get('value', 0) / 1000, 2) if io.get('external_voltage') else None,
                "jaringan": io.get('network_type'),
                "jarak_tempuh_meter": io.get('mileage', {}).get('value', 0),
                "jarak_tempuh_km": round(io.get('mileage', {}).get('value', 0) / 1000, 2) if io.get('mileage') else 0,
                "waktu_mesin_hidup_detik": io.get('running_time', {}).get('value', 0),
                "waktu_mesin_hidup_menit": round(io.get('running_time', {}).get('value', 0) / 60, 1) if io.get('running_time') else 0
            },
            "metadata": {
                "parsed_at": datetime.now().isoformat(),
                "parser_version": "1.0"
            }
        }
        
        if 'base_station' in io:
            bs = io['base_station']
            json_payload["base_station"] = {
                "mcc": bs.get('mcc'),
                "mnc": bs.get('mnc'),
                "lac": bs.get('lac'),
                "cell_id": bs.get('cell_id')
            }
        
        if 'acceleration' in io:
            acc = io['acceleration']
            json_payload["akselerasi"] = {
                "x_mg": acc.get('x_mg'),
                "y_mg": acc.get('y_mg'),
                "z_mg": acc.get('z_mg')
            }
        
        if 'ibutton_id' in io:
            json_payload["ibutton"] = {
                "id": io.get('ibutton_id'),
                "authorized": io.get('ibutton_authorized', False)
            }
        
        if 'input_status' in io:
            inp = io['input_status']
            json_payload["input_output"] = {
                "din1": inp.get('din1', False),
                "din2": inp.get('din2', False),
                "din3": inp.get('din3', False),
                "din4": inp.get('din4', False),
                "din5": inp.get('din5', False)
            }
            if 'output_status' in io:
                out = io['output_status']
                json_payload["input_output"]["dout1"] = out.get('output1', False)
                json_payload["input_output"]["dout2"] = out.get('output2', False)
        
        return json_payload
    
    def get_event_name(self, event_code):
        """Get event name dari event code"""
        event_names = {
            1: "SOS Alarm",
            2: "Power Cut Alarm",
            3: "Vibration Alarm",
            4: "Enter Geofence",
            5: "Exit Geofence",
            10: "Low Battery",
            11: "Overspeed",
            12: "Harsh Acceleration",
            13: "Harsh Deceleration",
            14: "Sharp Turn",
            15: "Collision",
            20: "Engine On",
            21: "Engine Off",
            30: "GPS Antenna Cut",
            31: "GPS Antenna Short",
            40: "Tow Alarm",
            45: "Heartbeat",
            51: "Tracking Data",
        }
        return event_names.get(event_code, f"Unknown Event ({event_code})")
    
    def start(self):
        """Start republisher service"""
        try:
            print("\n" + "=" * 80)
            print("MQTT JSON REPUBLISHER - NATURELINK GPS TRACKER")
            print("=" * 80)
            print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
            print(f"Subscribe from (RAW): {TOPIC_RAW}")
            print(f"Publish to (JSON): {TOPIC_JSON}")
            print("=" * 80)
            print("\nService running... (Press Ctrl+C to stop)\n")
            
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_forever()
        
        except KeyboardInterrupt:
            print("\n\n⏹ Stopping republisher service...")
            self.cleanup()
        
        except Exception as e:
            logger.error(f"✗ Fatal error: {e}")
            self.cleanup()
    
    def cleanup(self):
        """Cleanup connections"""
        if self.client:
            self.client.disconnect()
        
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)
        print(f"Total messages received: {self.message_count}")
        print(f"Successfully republished: {self.success_count}")
        print(f"Errors: {self.error_count}")
        print(f"Success rate: {(self.success_count/self.message_count*100) if self.message_count > 0 else 0:.1f}%")
        print("=" * 80)
        print("✓ Republisher service stopped")


if __name__ == '__main__':
    republisher = JSONRepublisher()
    republisher.start()
