# Naturelink GPS Tracker - Web Dashboard

Dashboard web real-time untuk monitoring GPS tracker Naturelink dengan visualisasi peta menggunakan OpenStreetMap.

## Features

- 🗺️ **Real-time Map Tracking** - Visualisasi posisi GPS menggunakan OpenStreetMap (Leaflet.js)
- 📊 **Live Data Display** - Menampilkan semua data dari JSON MQTT:
  - Device info (IMEI, Frame ID, Event)
  - GPS location (Lat/Lon, Speed, Heading, Altitude, Satellites)
  - Device status (Battery, External Power, Network, Mileage, Engine Time)
  - Digital I/O (DIN1-DIN5, DOUT1-DOUT2)
  - Acceleration (X, Y, Z axis)
  - iButton/RFID (ID, Authorization status)
  - Base Station info (MCC, MNC, LAC, Cell ID)
- 🔄 **Auto-reconnect** - Otomatis reconnect jika koneksi MQTT terputus
- 📱 **Responsive Design** - Tampilan optimal di desktop dan mobile

## Prerequisites

1. **Mosquitto MQTT Broker** dengan WebSocket support (port 9001)
2. **Web Server** untuk serve static files (Nginx, Apache, atau Python SimpleHTTPServer)

## Setup

### 1. Enable WebSocket di Mosquitto (VPS)

Edit file konfigurasi Mosquitto:

```bash
sudo nano /etc/mosquitto/mosquitto.conf
```

Tambahkan listener WebSocket:

```conf
# MQTT over TCP (existing)
listener 1883
protocol mqtt

# MQTT over WebSocket
listener 9001
protocol websockets

# Authentication
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Restart Mosquitto:

```bash
sudo systemctl restart mosquitto
```

Pastikan port 9001 terbuka di firewall:

```bash
sudo ufw allow 9001/tcp
```

### 2. Serve Dashboard

#### Option A: Python SimpleHTTPServer (Development)

```bash
cd public
python3 -m http.server 8000
```

Akses: `http://localhost:8000`

#### Option B: Nginx (Production)

```bash
sudo apt install nginx
sudo cp -r public /var/www/naturelink-dashboard
```

Edit `/etc/nginx/sites-available/naturelink-dashboard`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /var/www/naturelink-dashboard;
    index index.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/naturelink-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Konfigurasi MQTT Connection

Edit file `js/app.js` jika perlu mengubah konfigurasi MQTT:

```javascript
const MQTT_CONFIG = {
    host: '72.62.126.85',      // MQTT broker IP
    port: 9001,                 // WebSocket port
    username: 'kutaienergy',
    password: 'KutaiEnerg',
    topic: '/Naturelink/Send/json'
};
```

## Usage

1. Buka dashboard di browser
2. Dashboard akan otomatis connect ke MQTT broker
3. Status koneksi ditampilkan di header (hijau = connected, merah = disconnected)
4. Data GPS akan update secara real-time saat device mengirim data
5. Marker di peta akan bergerak mengikuti posisi GPS
6. Klik marker untuk melihat detail lokasi dan link ke Google Maps

## File Structure

```
public/
├── index.html          # Main HTML file
├── css/
│   └── style.css      # Styling
├── js/
│   └── app.js         # MQTT connection & UI logic
└── README.md          # This file
```

## Dependencies

- **Leaflet.js** v1.9.4 - OpenStreetMap library
- **Paho MQTT** v1.0.1 - MQTT client for WebSocket

Semua dependencies di-load via CDN, tidak perlu install manual.

## Troubleshooting

### Dashboard tidak connect ke MQTT

1. Pastikan Mosquitto sudah enable WebSocket (port 9001)
2. Cek firewall: `sudo ufw status`
3. Test WebSocket: `wscat -c ws://72.62.126.85:9001`
4. Cek browser console untuk error messages

### Data tidak muncul

1. Pastikan republisher service berjalan di VPS
2. Cek topic MQTT sudah benar: `/Naturelink/Send/json`
3. Test subscribe manual: `mosquitto_sub -h 72.62.126.85 -p 1883 -u kutaienergy -P 'KutaiEnerg' -t '/Naturelink/Send/json'`

### Map tidak muncul

1. Cek koneksi internet (Leaflet load tiles dari OpenStreetMap)
2. Cek browser console untuk error
3. Pastikan GPS data valid (gps_valid: true)

## Browser Support

- Chrome/Edge (recommended)
- Firefox
- Safari
- Opera

## License

MIT License
