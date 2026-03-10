# JSON Republisher Service - Naturelink GPS Tracker

Service untuk mengkonversi data binary GPS dari MQTT menjadi JSON dan mempublish ulang ke topic terpisah.

---

## Overview

### Masalah
- Device Naturelink GPS publish data dalam format **binary/hex** ke topic `/Naturelink/Send`
- Developer/aplikasi lain lebih mudah konsumsi data dalam format **JSON**

### Solusi
Service **MQTT JSON Republisher** yang:
1. Subscribe ke topic raw binary: `/Naturelink/Send`
2. Parse data binary menggunakan `naturelink_parser.py`
3. Publish hasil parsing dalam format JSON ke topic baru: `/Naturelink/Send/json`

### Arsitektur

```
┌─────────────────┐
│  GPS Device     │
│  (Naturelink)   │
└────────┬────────┘
         │ Binary data
         ↓
┌─────────────────────────────┐
│   MQTT Broker               │
│   Topic: /Naturelink/Send   │ ← Raw binary
└────────┬────────────────────┘
         │
         ↓ Subscribe
┌─────────────────────────────┐
│  JSON Republisher Service   │
│  (mqtt_json_republisher.py) │
└────────┬────────────────────┘
         │ Parse & Convert
         ↓ Publish JSON
┌─────────────────────────────┐
│   MQTT Broker               │
│   Topic: /Naturelink/       │ ← JSON format
│          Send/json          │
└────────┬────────────────────┘
         │
         ↓ Subscribe
┌─────────────────────────────┐
│  Consumer Apps              │
│  (Web, Mobile, Dashboard)   │
└─────────────────────────────┘
```

---

## Setup & Installation

### 1. Install Dependencies

```bash
pip install paho-mqtt python-dotenv
```

### 2. Konfigurasi Environment

Edit file `.env`:

```bash
# MQTT Configuration
MQTT_BROKER=72.62.126.85
MQTT_PORT=1883
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password
MQTT_TOPIC=/Naturelink/Send
MQTT_TOPIC_JSON=/Naturelink/Send/json
```

### 3. Test Manual

Jalankan service:

```bash
cd scripts
python3 mqtt_json_republisher.py
```

Output:
```
================================================================================
MQTT JSON REPUBLISHER - NATURELINK GPS TRACKER
================================================================================
MQTT Broker: 72.62.126.85:1883
Subscribe from (RAW): /Naturelink/Send
Publish to (JSON): /Naturelink/Send/json
================================================================================

Service running... (Press Ctrl+C to stop)

2026-03-06 17:15:23 - INFO - ✓ Connected to MQTT broker: 72.62.126.85:1883
2026-03-06 17:15:23 - INFO - ✓ Subscribed to RAW topic: /Naturelink/Send
2026-03-06 17:15:23 - INFO - ✓ Will publish JSON to: /Naturelink/Send/json
2026-03-06 17:15:45 - INFO - ✓ [1] Published JSON - IMEI: 0866344055567122, Lat/Lon: 22.636635, 114.030401
```

---

## Format JSON Output

### Contoh JSON yang dipublish ke `/Naturelink/Send/json`:

```json
{
  "device": {
    "imei": "0866344055567122",
    "frame_id": 48
  },
  "waktu": "2026-03-06T06:10:49",
  "event": {
    "kode": 51,
    "nama": "Tracking Data"
  },
  "lokasi": {
    "latitude": 22.636635,
    "longitude": 114.030401,
    "google_maps": "https://www.google.com/maps?q=22.636635,114.030401",
    "gps_valid": true,
    "kecepatan_kmh": 0,
    "arah_derajat": 196,
    "ketinggian_meter": 78,
    "jumlah_satelit": 17,
    "kualitas_sinyal": 25
  },
  "status_device": {
    "baterai_mv": 4118,
    "baterai_volt": 4.12,
    "power_eksternal_mv": 12282,
    "power_eksternal_volt": 12.28,
    "jaringan": "4G",
    "jarak_tempuh_meter": 99,
    "jarak_tempuh_km": 0.1,
    "waktu_mesin_hidup_detik": 1672,
    "waktu_mesin_hidup_menit": 27.9
  },
  "base_station": {
    "mcc": 460,
    "mnc": 0,
    "lac": 10150,
    "cell_id": 54188690
  },
  "akselerasi": {
    "x_mg": 13,
    "y_mg": -17,
    "z_mg": -1002
  },
  "metadata": {
    "parsed_at": "2026-03-06T17:15:45.123456",
    "parser_version": "1.0"
  }
}
```

---

## Subscribe JSON dari Aplikasi Lain

### Command Line (mosquitto_sub)

```bash
mosquitto_sub \
  -h 72.62.126.85 \
  -p 1883 \
  -u your_username \
  -P 'your_password' \
  -t '/Naturelink/Send/json' \
  -v
```

### Python

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    print(f"IMEI: {data['device']['imei']}")
    print(f"Lat/Lon: {data['lokasi']['latitude']}, {data['lokasi']['longitude']}")
    print(f"Speed: {data['lokasi']['kecepatan_kmh']} km/h")

client = mqtt.Client()
client.username_pw_set('your_username', 'your_password')
client.on_message = on_message
client.connect('72.62.126.85', 1883, 60)
client.subscribe('/Naturelink/Send/json')
client.loop_forever()
```

### JavaScript (Node.js)

```javascript
const mqtt = require('mqtt');

const client = mqtt.connect('mqtt://72.62.126.85:1883', {
  username: 'your_username',
  password: 'your_password'
});

client.on('connect', () => {
  client.subscribe('/Naturelink/Send/json');
});

client.on('message', (topic, message) => {
  const data = JSON.parse(message.toString());
  console.log(`IMEI: ${data.device.imei}`);
  console.log(`Lat/Lon: ${data.lokasi.latitude}, ${data.lokasi.longitude}`);
  console.log(`Speed: ${data.lokasi.kecepatan_kmh} km/h`);
});
```

---

## Deploy sebagai Service (Production)

### Systemd Service (Linux)

Buat file `/etc/systemd/system/naturelink-json-republisher.service`:

```ini
[Unit]
Description=Naturelink GPS JSON Republisher Service
After=network.target mosquitto.service

[Service]
Type=simple
User=gps
WorkingDirectory=/opt/naturelink-gps-tracker/scripts
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /opt/naturelink-gps-tracker/scripts/mqtt_json_republisher.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable dan start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable naturelink-json-republisher
sudo systemctl start naturelink-json-republisher
sudo systemctl status naturelink-json-republisher
```

### Docker (Alternative)

Buat `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY .env .env

CMD ["python3", "scripts/mqtt_json_republisher.py"]
```

Build dan run:

```bash
docker build -t naturelink-json-republisher .
docker run -d --name json-republisher --restart always naturelink-json-republisher
```

---

## Monitoring & Logging

### Log File

Service menulis log ke: `data/json_republisher.log`

```bash
tail -f data/json_republisher.log
```

### Statistics

Ketika service di-stop (Ctrl+C), akan muncul statistik:

```
================================================================================
STATISTICS
================================================================================
Total messages received: 1523
Successfully republished: 1520
Errors: 3
Success rate: 99.8%
================================================================================
✓ Republisher service stopped
```

### Health Check

Cek apakah service masih publish JSON:

```bash
mosquitto_sub \
  -h 72.62.126.85 \
  -p 1883 \
  -u your_username \
  -P 'your_password' \
  -t '/Naturelink/Send/json' \
  -C 1
```

---

## ACL Configuration (Opsional)

Untuk keamanan, bisa set ACL agar:
- Device hanya bisa publish ke `/Naturelink/Send` (raw)
- Service republisher bisa subscribe raw + publish JSON
- Developer/aplikasi hanya bisa subscribe JSON

Edit `/etc/mosquitto/acl`:

```
# Device GPS (hanya publish raw)
user gps_device
topic write /Naturelink/Send

# Republisher service (subscribe raw, publish JSON)
user republisher_service
topic read /Naturelink/Send
topic write /Naturelink/Send/json

# Developer/aplikasi (hanya subscribe JSON)
user developer
topic read /Naturelink/Send/json
```

---

## Troubleshooting

### Service tidak connect ke MQTT

1. Cek kredensial di `.env`
2. Cek firewall/network
3. Cek log: `tail -f data/json_republisher.log`

### JSON tidak muncul di topic

1. Cek apakah ada data raw masuk:
   ```bash
   mosquitto_sub -h 72.62.126.85 -u user -P pass -t '/Naturelink/Send' -C 1
   ```

2. Cek log parsing error di `json_republisher.log`

### Format JSON tidak sesuai

Edit function `convert_to_json()` di `mqtt_json_republisher.py` untuk customize format output.

---

## Keuntungan Arsitektur Ini

1. **Separation of Concerns**
   - Device tetap publish raw (tidak perlu ubah firmware)
   - Parser service terpisah (mudah update/maintain)
   - Consumer hanya perlu tahu JSON schema

2. **Backward Compatible**
   - Topic raw (`/Naturelink/Send`) tetap ada
   - Aplikasi lama yang sudah subscribe raw tetap jalan

3. **Scalable**
   - Bisa tambah parser service lain (misal: filter by IMEI, transform lain)
   - Bisa tambah consumer tanpa ganggu device

4. **Easy Integration**
   - Developer baru tinggal subscribe JSON
   - Tidak perlu tahu binary protocol
   - Bisa langsung pakai di web/mobile/dashboard

---

## Next Steps

1. ✅ Deploy service sebagai systemd/docker
2. ✅ Setup monitoring (Grafana/Prometheus)
3. ✅ Tambah alert jika service down
4. ✅ Dokumentasi JSON schema untuk developer
5. ✅ Setup ACL untuk keamanan

---

**Author**: GPS Tracking Team  
**Last Updated**: 6 Maret 2026  
**Version**: 1.0
