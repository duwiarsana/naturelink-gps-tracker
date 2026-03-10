#!/usr/bin/env python3
"""
Naturelink GPS Tracker - Binary Data Parser
Parses binary MQTT data from Naturelink GPS devices according to protocol v1.0

Author: Auto-generated
Date: 2026-03-06
"""

import struct
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json


class NaturelinkParser:
    """Parser for Naturelink GPS binary protocol"""
    
    # Epoch start: 2000-01-01 00:00:00
    EPOCH_2000 = datetime(2000, 1, 1, 0, 0, 0)
    
    # IO Element IDs
    IO_ELEMENTS = {
        0x01: {'name': 'battery_voltage', 'unit': 'mV', 'bytes': 2},
        0x02: {'name': 'external_voltage', 'unit': 'mV', 'bytes': 2},
        0x03: {'name': 'ad1', 'unit': 'mV', 'bytes': 2},
        0x04: {'name': 'ad2', 'unit': 'mV', 'bytes': 2},
        0x0B: {'name': 'hdop', 'unit': '', 'bytes': 2},
        0x0C: {'name': 'altitude', 'unit': 'm', 'bytes': 2},
        0x0D: {'name': 'mileage', 'unit': 'm', 'bytes': 4},
        0x0E: {'name': 'running_time', 'unit': 's', 'bytes': 4},
        0x0F: {'name': 'input_status', 'unit': '', 'bytes': 2},
        0x10: {'name': 'output_status', 'unit': '', 'bytes': 2},
        0x11: {'name': 'base_station', 'unit': '', 'bytes': 10},
        0x12: {'name': 'fuel_percentage', 'unit': '%', 'bytes': 2},
        0x18: {'name': 'acceleration_xyz', 'unit': 'mg', 'bytes': 6},
        0x1A: {'name': 'network_type', 'unit': '', 'bytes': 1},
    }
    
    def __init__(self):
        self.data = None
        self.offset = 0
    
    def parse(self, hex_data: str) -> Dict[str, Any]:
        """
        Parse hex string data from Naturelink GPS device
        
        Args:
            hex_data: Hex string (with or without spaces)
            
        Returns:
            Dictionary containing parsed data
        """
        # Remove spaces and convert to bytes
        hex_clean = hex_data.replace(' ', '').replace('\n', '')
        self.data = bytes.fromhex(hex_clean)
        self.offset = 0
        
        result = {
            'raw_hex': hex_data,
            'parsed': True,
            'error': None
        }
        
        try:
            # Parse header
            header = self._parse_header()
            result['header'] = header
            
            # Parse data based on codec ID
            if header['codec_id'] == 0x01:
                records = self._parse_tracking_data(header['num_records'])
                result['records'] = records
            elif header['codec_id'] == 0x80:
                result['command'] = self._parse_command_data(header['data_length'])
            else:
                result['error'] = f"Unknown codec ID: 0x{header['codec_id']:02X}"
                result['parsed'] = False
            
            # Parse footer
            footer = self._parse_footer()
            result['footer'] = footer
            
        except Exception as e:
            result['parsed'] = False
            result['error'] = str(e)
        
        return result
    
    def _read_bytes(self, n: int) -> bytes:
        """Read n bytes from data"""
        if self.offset + n > len(self.data):
            raise ValueError(f"Not enough data: need {n} bytes at offset {self.offset}")
        chunk = self.data[self.offset:self.offset + n]
        self.offset += n
        return chunk
    
    def _read_uint8(self) -> int:
        """Read 1 byte unsigned integer"""
        return struct.unpack('<B', self._read_bytes(1))[0]
    
    def _read_uint16_le(self) -> int:
        """Read 2 bytes unsigned integer (little-endian)"""
        return struct.unpack('<H', self._read_bytes(2))[0]
    
    def _read_uint32_le(self) -> int:
        """Read 4 bytes unsigned integer (little-endian)"""
        return struct.unpack('<I', self._read_bytes(4))[0]

    def _read_int32_le(self) -> int:
        """Read 4 bytes signed integer (little-endian)"""
        return struct.unpack('<i', self._read_bytes(4))[0]
    
    def _read_int16_le(self) -> int:
        """Read 2 bytes signed integer (little-endian)"""
        return struct.unpack('<h', self._read_bytes(2))[0]
    
    def _parse_header(self) -> Dict[str, Any]:
        """Parse packet header"""
        preamble = self._read_bytes(2)
        if preamble != b'\x3e\x3e':
            raise ValueError(f"Invalid preamble: {preamble.hex()}")
        
        version = self._read_uint8()
        frame_id = self._read_uint8()
        
        # IMEI (8 bytes BCD)
        imei_bytes = self._read_bytes(8)
        imei = ''.join([f"{b:02x}" for b in imei_bytes])
        
        data_length = self._read_uint16_le()
        codec_id = self._read_uint8()
        
        # For tracking data, read number of records
        num_records = 0
        if codec_id == 0x01:
            num_records = self._read_uint8()
        
        return {
            'preamble': preamble.hex(),
            'version': version,
            'frame_id': frame_id,
            'imei': imei,
            'data_length': data_length,
            'codec_id': codec_id,
            'num_records': num_records
        }
    
    def _parse_tracking_data(self, num_records: int) -> List[Dict[str, Any]]:
        """Parse tracking data records"""
        records = []
        
        for i in range(num_records):
            record = self._parse_single_record()
            records.append(record)
        
        return records
    
    def _parse_single_record(self) -> Dict[str, Any]:
        """Parse a single tracking record"""
        # Base info
        event_code = self._read_uint16_le()
        timestamp_raw = self._read_uint32_le()
        latitude_raw = self._read_int32_le()
        longitude_raw = self._read_int32_le()
        status_speed = self._read_uint16_le()
        sat_angle = self._read_uint16_le()
        
        # Parse timestamp (from 2000-01-01)
        timestamp = self.EPOCH_2000 + timedelta(seconds=timestamp_raw)
        
        # Parse latitude/longitude
        latitude = latitude_raw / 1000000.0
        longitude = longitude_raw / 1000000.0
        
        # Parse status & speed
        gps_valid = (status_speed & 0x01) == 1
        signal_quality = (status_speed >> 1) & 0x1F
        speed = (status_speed >> 6) & 0x3FF
        
        # Parse satellites & angle
        satellites = sat_angle & 0x7F
        heading = (sat_angle >> 7) & 0x1FF
        
        record = {
            'event_code': event_code,
            'timestamp': timestamp.isoformat(),
            'timestamp_unix': int(timestamp.timestamp()),
            'gps': {
                'latitude': latitude,
                'longitude': longitude,
                'valid': gps_valid,
                'satellites': satellites,
                'heading': heading,
                'speed_kmh': speed,
                'signal_quality': signal_quality,
            },
            'io_elements': {}
        }
        
        # Parse IO elements
        io_data = self._parse_io_elements()
        record['io_elements'] = io_data
        
        return record
    
    def _parse_io_elements(self) -> Dict[str, Any]:
        """Parse IO elements"""
        io_data = {}
        
        # 1-byte IO elements
        num_1byte = self._read_uint8()
        for _ in range(num_1byte):
            io_id = self._read_uint8()
            value = self._read_uint8()
            self._add_io_element(io_data, io_id, value, 1)
        
        # 2-byte IO elements
        num_2byte = self._read_uint8()
        for _ in range(num_2byte):
            io_id = self._read_uint8()
            value = self._read_uint16_le()
            self._add_io_element(io_data, io_id, value, 2)
        
        # 4-byte IO elements
        num_4byte = self._read_uint8()
        for _ in range(num_4byte):
            io_id = self._read_uint8()
            value = self._read_uint32_le()
            self._add_io_element(io_data, io_id, value, 4)
        
        # 8-byte IO elements
        num_8byte = self._read_uint8()
        for _ in range(num_8byte):
            io_id = self._read_uint8()
            value_bytes = self._read_bytes(8)
            self._add_io_element(io_data, io_id, value_bytes.hex(), 8)
        
        # Variable length IO elements
        num_var = self._read_uint8()
        for _ in range(num_var):
            io_id = self._read_uint8()
            length = self._read_uint8()
            value_bytes = self._read_bytes(length)
            
            # Special parsing for known variable-length IOs
            if io_id == 0x11:  # Base station
                io_data['base_station'] = self._parse_base_station(value_bytes)
            elif io_id == 0x18:  # XYZ acceleration
                io_data['acceleration'] = self._parse_acceleration(value_bytes)
            else:
                io_data[f'io_{io_id:02x}'] = value_bytes.hex()
        
        return io_data
    
    def _add_io_element(self, io_data: Dict, io_id: int, value: Any, size: int):
        """Add IO element to data dict"""
        if io_id in self.IO_ELEMENTS:
            info = self.IO_ELEMENTS[io_id]
            name = info['name']
            unit = info['unit']
            
            # Special handling for network type
            if io_id == 0x1A:
                network_types = {1: '2G', 2: '4G', 3: '5G'}
                io_data[name] = network_types.get(value, f'Unknown({value})')
            else:
                io_data[name] = {
                    'value': value,
                    'unit': unit
                }
        else:
            io_data[f'io_{io_id:02x}'] = value
    
    def _parse_base_station(self, data: bytes) -> Dict[str, Any]:
        """Parse base station info (10 bytes)"""
        mcc = struct.unpack('<H', data[0:2])[0]
        mnc = struct.unpack('<H', data[2:4])[0]
        lac = struct.unpack('<H', data[4:6])[0]
        cell_id = struct.unpack('<I', data[6:10])[0]
        
        return {
            'mcc': mcc,
            'mnc': mnc,
            'lac': lac,
            'cell_id': cell_id
        }
    
    def _parse_acceleration(self, data: bytes) -> Dict[str, Any]:
        """Parse XYZ acceleration (6 bytes)"""
        x = struct.unpack('<h', data[0:2])[0]
        y = struct.unpack('<h', data[2:4])[0]
        z = struct.unpack('<h', data[4:6])[0]
        
        return {
            'x_mg': x,
            'y_mg': y,
            'z_mg': z
        }
    
    def _parse_command_data(self, length: int) -> str:
        """Parse command protocol data"""
        cmd_bytes = self._read_bytes(length - 1)  # -1 for codec ID
        return cmd_bytes.decode('ascii', errors='ignore')
    
    def _parse_footer(self) -> Dict[str, Any]:
        """Parse packet footer"""
        checksum = self._read_uint8()
        end_byte = self._read_uint8()
        
        if end_byte != 0x0A:
            raise ValueError(f"Invalid end byte: 0x{end_byte:02X}")
        
        return {
            'checksum': checksum,
            'end_byte': end_byte
        }


def parse_hex_string(hex_data: str) -> Dict[str, Any]:
    """
    Convenience function to parse hex string
    
    Args:
        hex_data: Hex string (with or without spaces)
        
    Returns:
        Parsed data dictionary
    """
    parser = NaturelinkParser()
    return parser.parse(hex_data)


def format_gps_location(record: Dict[str, Any]) -> str:
    """Format GPS location as Google Maps link"""
    gps = record.get('gps', {})
    lat = gps.get('latitude', 0)
    lon = gps.get('longitude', 0)
    return f"https://www.google.com/maps?q={lat},{lon}"


def print_parsed_data(parsed: Dict[str, Any]):
    """Pretty print parsed data"""
    if not parsed.get('parsed'):
        print(f"❌ Parsing failed: {parsed.get('error')}")
        return
    
    print("=" * 80)
    print("NATURELINK GPS DATA")
    print("=" * 80)
    
    # Header
    header = parsed.get('header', {})
    print(f"\n📡 DEVICE INFO")
    print(f"  IMEI: {header.get('imei')}")
    print(f"  Frame ID: {header.get('frame_id')}")
    print(f"  Codec: 0x{header.get('codec_id', 0):02X}")
    
    # Records
    records = parsed.get('records', [])
    for i, record in enumerate(records, 1):
        print(f"\n📍 RECORD #{i}")
        print(f"  Event Code: {record.get('event_code')}")
        print(f"  Timestamp: {record.get('timestamp')}")
        
        gps = record.get('gps', {})
        print(f"\n  🌍 GPS:")
        print(f"    Latitude: {gps.get('latitude'):.6f}°")
        print(f"    Longitude: {gps.get('longitude'):.6f}°")
        print(f"    Valid: {'✓' if gps.get('valid') else '✗'}")
        print(f"    Speed: {gps.get('speed_kmh')} km/h")
        print(f"    Heading: {gps.get('heading')}°")
        print(f"    Satellites: {gps.get('satellites')}")
        print(f"    Signal Quality: {gps.get('signal_quality')}")
        print(f"    Maps: {format_gps_location(record)}")
        
        io = record.get('io_elements', {})
        if io:
            print(f"\n  🔌 IO ELEMENTS:")
            for key, value in io.items():
                if isinstance(value, dict) and 'value' in value:
                    unit = value.get('unit', '')
                    val = value.get('value')
                    print(f"    {key}: {val} {unit}")
                else:
                    print(f"    {key}: {value}")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    # Example: Parse sample data
    sample_hex = """
    3e 3e 01 30 08 66 34 40 55 56 71 22 51 00 01 01
    33 00 69 2c 3d 31 5b 68 59 01 41 7b cd 06 33 00
    11 62 01 1a 02 08 01 16 10 02 fa 2f 03 00 00 04
    00 00 0b 09 00 0c 4e 00 0f 00 00 10 00 00 02 0d
    63 00 00 00 0e 88 06 00 00 00 02 11 0a cc 01 00
    00 a6 27 92 da 3a 03 18 06 0d 00 ef ff 16 fc 4c
    0a
    """
    
    print("Parsing sample Naturelink GPS data...\n")
    result = parse_hex_string(sample_hex)
    print_parsed_data(result)
    
    # Also save as JSON
    print("\n📄 Saving to JSON...")
    with open('/Users/duwiarsana/CascadeProjects/naturelink-gps-tracker/data/sample_parsed.json', 'w') as f:
        json.dump(result, f, indent=2)
    print("✓ Saved to data/sample_parsed.json")
