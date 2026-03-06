#!/usr/bin/env python3
"""
Simple GPS Monitor - Naturelink GPS Tracker
Subscribe ke MQTT dan tampilkan data GPS dalam format JSON yang mudah dibaca

Usage:
    python3 simple_gps_monitor.py

Author: GPS Tracking Team
Date: 2026-03-06
"""

import paho.mqtt.client as mqtt
from naturelink_parser import NaturelinkParser
import json
from datetime import datetime
import os

from dotenv import load_dotenv


load_dotenv()

MQTT_BROKER = os.getenv('MQTT_BROKER', '127.0.0.1')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_TOPIC = os.getenv('MQTT_TOPIC', '/Naturelink/Send')


class SimpleGPSMonitor:
    """Simple GPS monitor dengan output JSON yang mudah dibaca"""
    
    def __init__(self):
        self.parser = NaturelinkParser()
        self.client = mqtt.Client()
        if MQTT_USERNAME and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.message_count = 0
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✓ Terhubung ke MQTT broker")
            print(f"✓ Subscribe ke topic: {MQTT_TOPIC}")
            client.subscribe(MQTT_TOPIC, qos=1)
            print("\n" + "="*80)
            print("Menunggu data GPS... (Tekan Ctrl+C untuk stop)")
            print("="*80 + "\n")
        else:
            print(f"✗ Koneksi gagal dengan kode: {rc}")
    
    def on_message(self, client, userdata, msg):
        """Callback ketika menerima pesan MQTT"""
        self.message_count += 1
        
        # Parse data binary
        hex_data = msg.payload.hex()
        parsed = self.parser.parse(hex_data)
        
        if not parsed.get('parsed'):
            print(f"❌ Error parsing: {parsed.get('error')}")
            return
        
        # Convert ke format JSON yang mudah dibaca
        readable_data = self.convert_to_readable_json(parsed)
        
        # Print JSON dengan format indented
        print(f"\n{'='*80}")
        print(f"📍 DATA GPS #{self.message_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        print(json.dumps(readable_data, indent=2, ensure_ascii=False))
        print(f"\n{'='*80}\n")
    
    def convert_to_readable_json(self, parsed_data):
        """Convert parsed data ke format JSON yang mudah dibaca"""
        header = parsed_data.get('header', {})
        records = parsed_data.get('records', [])
        
        if not records:
            return {"error": "Tidak ada data GPS"}
        
        record = records[0]
        gps = record.get('gps', {})
        io = record.get('io_elements', {})
        
        # Format data yang mudah dibaca
        readable = {
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
                "gps_valid": "✓ Valid" if gps.get('valid') else "✗ Invalid",
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
            }
        }
        
        # Tambahkan base station info jika ada
        if 'base_station' in io:
            bs = io['base_station']
            readable["base_station"] = {
                "mcc": bs.get('mcc'),
                "mnc": bs.get('mnc'),
                "lac": bs.get('lac'),
                "cell_id": bs.get('cell_id')
            }
        
        # Tambahkan acceleration info jika ada
        if 'acceleration' in io:
            acc = io['acceleration']
            readable["akselerasi"] = {
                "x_mg": acc.get('x_mg'),
                "y_mg": acc.get('y_mg'),
                "z_mg": acc.get('z_mg')
            }
        
        return readable
    
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
            # Tambahkan event code lainnya sesuai kebutuhan
        }
        return event_names.get(event_code, f"Unknown Event ({event_code})")
    
    def start(self):
        """Mulai monitoring GPS"""
        try:
            print("\n" + "="*80)
            print("SIMPLE GPS MONITOR - NATURELINK GPS TRACKER")
            print("="*80)
            print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
            print(f"Topic: {MQTT_TOPIC}")
            print("="*80)
            
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_forever()
        
        except KeyboardInterrupt:
            print("\n\n⏹ Menghentikan monitor...")
            self.client.disconnect()
            print(f"✓ Total pesan diterima: {self.message_count}")
            print("✓ Monitor dihentikan")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            self.client.disconnect()


if __name__ == '__main__':
    monitor = SimpleGPSMonitor()
    monitor.start()
