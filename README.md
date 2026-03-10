# Naturelink GPS Tracker - MQTT Integration

Project untuk monitoring dan parsing data GPS dari device Naturelink via MQTT broker.

---

## Struktur Folder

```
naturelink-gps-tracker/
├── README.md                                      # Dokumentasi utama
├── requirements.txt                               # Python dependencies
├── database_schema.sql                            # SQL schema untuk PostgreSQL
├── .gitignore                                     # Git ignore rules
│
├── docs/                                          # 📚 Dokumentasi
│   ├── MQTT-Subscribe-Guide.md                   # Panduan subscribe MQTT
│   ├── Protokol-Naturelink-Ringkasan.md          # Ringkasan protokol (ID)
│   ├── Developer-Guide-Database-Integration.md   # Guide untuk developer
│   ├── JSON-Republisher-Guide.md                 # Guide untuk JSON republisher
│   └── protocol/
│       ├── protocol.md                            # Protokol lengkap (copy dari docx)
│       └── Communication Protocol_V1.0_2026.docx  # Protokol asli dari vendor
│
├── scripts/                                       # 🔧 Python Scripts
│   ├── naturelink_parser.py                      # Parser data binary GPS
│   ├── mqtt_monitor.py                           # Real-time MQTT monitor
│   ├── mqtt_json_republisher.py                  # Republish raw → JSON ke 1 topic umum
│   └── mqtt_to_database.py                       # MQTT to Database (production)
│
└── data/                                          # 💾 Data & Logs
    ├── sample_parsed.json                         # Contoh hasil parsing
    └── gps_tracking.jsonl                         # Log GPS real-time (auto-generated)
```

---

## Quick Start

### 1. Subscribe ke MQTT Broker (Command Line)

```bash
mosquitto_sub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t "$MQTT_TOPIC" \
  -N | hexdump -C
```

### 2. Parse Data dengan Python Script

```bash
cd scripts
python3 naturelink_parser.py
```

### 3. Monitor Real-time dengan MQTT

```bash
cd scripts
python3 mqtt_monitor.py
```

---

## JSON Republisher (Raw → JSON)

Kalau team developer ingin konsumsi data yang sudah rapi (JSON) tanpa perlu ngerti protokol hex/binary, gunakan script:

- Subscribe raw: `/Naturelink/Send`
- Publish JSON: `/Naturelink/Send/json`

### Konfigurasi `.env`

Pastikan `.env` memiliki variable:

```bash
MQTT_TOPIC=/Naturelink/Send
MQTT_TOPIC_JSON=/Naturelink/Send/json
```

### Menjalankan republisher

```bash
cd scripts
python3 mqtt_json_republisher.py
```

### Subscribe hasil JSON

```bash
mosquitto_sub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t "$MQTT_TOPIC_JSON" \
  -v
```

### Test koneksi publish/subscribe (tanpa ganggu topic device)

Terminal 1 (subscribe):

```bash
mosquitto_sub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t '/test/koneksi' \
  -v
```

Terminal 2 (publish):

```bash
mosquitto_pub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t '/test/koneksi' \
  -m '{"ping":"ok"}'
```

---

## Informasi MQTT Broker

- **Host**: `$MQTT_BROKER`
- **Port**: `$MQTT_PORT`
- **Username**: `$MQTT_USERNAME`
- **Password**: `$MQTT_PASSWORD`
- **Topic**: `$MQTT_TOPIC`

---

## Dokumentasi

### Panduan Lengkap
- [Panduan Subscribe & Baca Data Hex](docs/MQTT-Subscribe-Guide.md)
- [Ringkasan Protokol Naturelink](docs/Protokol-Naturelink-Ringkasan.md) ⭐ **Baca ini dulu!**
- [Developer Guide - Database Integration](docs/Developer-Guide-Database-Integration.md) 🔥 **Untuk Team Developer**
- [JSON Republisher Guide](docs/JSON-Republisher-Guide.md) ✅ **Untuk konsumsi data JSON (1 topic umum)**
- [Dokumentasi Protokol Lengkap](docs/protocol/protocol.md)

### Contoh Data yang Diparsing

Dari data binary GPS, kita dapat extract:

**Lokasi GPS:**
- Latitude: 22.636635°
- Longitude: 114.030401°
- Speed: 0 km/h
- Heading: 196°
- Satellites: 17

**Status Device:**
- Battery: 4.118V
- External Power: 12.282V
- Network: 4G
- Mileage: 99 meter

**Link Google Maps:**
https://www.google.com/maps?q=22.636635,114.030401

---

## Cara Pakai Parser

### Install Dependencies

```bash
pip install paho-mqtt
```

### Parse Data Hex Manual

```python
from scripts.naturelink_parser import parse_hex_string

hex_data = "3e 3e 01 30 08 66 34 40 55 56 71 22 51..."
result = parse_hex_string(hex_data)

print(result['records'][0]['gps']['latitude'])   # 22.636635
print(result['records'][0]['gps']['longitude'])  # 114.030401
```

### Monitor Real-time dari MQTT

Script `mqtt_monitor.py` akan:
- ✅ Subscribe ke topic `/Naturelink/Send`
- ✅ Parse data binary secara otomatis
- ✅ Tampilkan lokasi GPS, speed, battery, dll
- ✅ Simpan ke file `data/gps_tracking.jsonl`

```bash
cd scripts
python3 mqtt_monitor.py
```

Output:
```
================================================================================
📨 MESSAGE #1 - 2026-03-06 14:30:45
================================================================================

📦 Raw Data (97 bytes):
  3e 3e 01 30 08 66 34 40 55 56 71 22 51 00 01 01
  33 00 69 2c 3d 31 5b 68 59 01 41 7b cd 06 33 00
  ...

📡 DEVICE INFO:
  IMEI: 0866344055567122
  Frame ID: 48

📍 LOCATION #1:
  Event: 51
  Time: 2026-03-06T06:10:49
  GPS: ✓ Valid
  Lat/Lon: 22.636635, 114.030401
  Speed: 0 km/h
  Heading: 196°
  Satellites: 17
  Maps: https://www.google.com/maps?q=22.636635,114.030401
  Battery: 4118 mV (4.12V)
  External: 12282 mV (12.28V)
  Network: 4G

💾 Saved to: ../data/gps_tracking.jsonl
```

---

## Format Data

### Binary Protocol Structure

Data yang diterima adalah **binary protocol** dengan struktur:

| Field | Bytes | Contoh | Keterangan |
|-------|-------|--------|------------|
| Preamble | 2 | `3e 3e` | Header tetap (`>>`) |
| Version | 1 | `01` | Versi protokol |
| Frame ID | 1 | `30` | ID frame (1-255) |
| IMEI | 8 | `08 66 34 40...` | IMEI device (BCD) |
| Data Length | 2 | `61 00` | Panjang data (little-endian) |
| Codec ID | 1 | `01` | 0x01 = tracking data |
| Records | Variable | ... | Data GPS + IO elements |
| Checksum | 1 | `4c` | Checksum |
| End | 1 | `0a` | Byte akhir |

### GPS Data Fields

- **Latitude/Longitude**: 4 bytes, little-endian, × 1,000,000
- **Speed**: km/h (0-1023)
- **Timestamp**: Unix time dari 2000-01-01 (bukan 1970!)
- **Satellites**: 0-127
- **Heading**: 0-360°

Lihat [Ringkasan Protokol](docs/Protokol-Naturelink-Ringkasan.md) untuk detail lengkap.

---

## Troubleshooting

### Tidak Ada Data Masuk

1. Cek koneksi MQTT:
```bash
mosquitto_sub -h "$MQTT_BROKER" -p "$MQTT_PORT" -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t '#' -v -C 5
```

2. Pastikan device GPS sudah online dan mengirim data

### Error Parsing

Jika parsing gagal, cek:
- Format data hex benar (dimulai dengan `3e 3e`)
- Data tidak corrupt/incomplete
- Lihat error message untuk detail

### Module Not Found

Install dependencies:
```bash
pip install paho-mqtt
```

---

## Next Steps

1. ✅ Setup MQTT subscription
2. ✅ Dokumentasi protokol lengkap
3. ✅ Parser untuk extract data GPS
4. ✅ Script monitoring real-time
5. ⏳ Simpan data ke database (PostgreSQL/MySQL)
6. ⏳ Buat dashboard web untuk visualisasi
7. ⏳ Alert system untuk geofencing/overspeed

---

**Last Updated**: 6 Maret 2026  
**Protocol Version**: v1.0
