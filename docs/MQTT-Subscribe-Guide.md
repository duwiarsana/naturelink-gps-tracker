# Panduan Subscribe & Baca Data Hex - Naturelink GPS Tracker

Dokumentasi lengkap cara subscribe ke MQTT broker dan membaca data binary dari device Naturelink GPS.

---

## Informasi Koneksi MQTT

### Broker Details
- **Host**: `$MQTT_BROKER`
- **Port**: `$MQTT_PORT`
- **Username**: `$MQTT_USERNAME`
- **Password**: `$MQTT_PASSWORD`
- **Topic**: `$MQTT_TOPIC`

Gunakan file `.env.example` di root project untuk contoh pengisian. Jangan commit file `.env` ke Git.

### Karakteristik Data
- **Format**: Binary protocol (bukan JSON/text)
- **Size**: ~97 bytes per message
- **Header**: Dimulai dengan `3e 3e` (ASCII: `>>`)

---

## Cara Subscribe dan Baca Data

### 1. Subscribe dengan Output Hex (Recommended)

Untuk melihat data dalam format hexadecimal yang mudah dibaca:

```bash
mosquitto_sub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t "$MQTT_TOPIC" \
  -N | hexdump -C
```

**Penjelasan opsi**:
- `-h` : Host MQTT broker
- `-p` : Port MQTT broker
- `-u` : Username untuk autentikasi
- `-P` : Password untuk autentikasi
- `-t` : Topic yang akan di-subscribe
- `-N` : Jangan tambahkan newline di akhir payload (untuk data binary)
- `| hexdump -C` : Pipe output ke hexdump dengan format canonical (hex + ASCII)

**Output contoh**:
```
00000000  3e 3e 01 30 08 66 34 40  55 56 71 22 51 00 01 01  |>>.0.f4@UVq"Q...|
00000010  33 00 69 2c 3d 31 5b 68  59 01 41 7b cd 06 33 00  |3.i,=1[hY.A{..3.|
00000020  11 62 01 1a 02 08 01 16  10 02 fa 2f 03 00 00 04  |.b........./....|
00000030  00 00 0b 09 00 0c 4e 00  0f 00 00 10 00 00 02 0d  |......N.........|
00000040  63 00 00 00 0e 88 06 00  00 00 02 11 0a cc 01 00  |c...............|
00000050  00 a6 27 92 da 3a 03 18  06 0d 00 ef ff 16 fc 4c  |..'..:.........L|
00000060  0a                                                |.|
```

---

### 2. Subscribe dengan Output Text (Untuk Debug)

Untuk melihat data dalam format text (akan ada karakter aneh karena binary):

```bash
mosquitto_sub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t "$MQTT_TOPIC" \
  -v
```

**Opsi tambahan**:
- `-v` : Verbose mode, tampilkan topic + payload

---

### 3. Subscribe dan Simpan ke File Binary

Untuk menyimpan data mentah ke file (untuk analisis offline):

```bash
mosquitto_sub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t "$MQTT_TOPIC" \
  -N > data/naturelink_$(date +%Y%m%d_%H%M%S).bin
```

File akan tersimpan dengan nama seperti: `naturelink_20260306_141530.bin`

---

### 4. Subscribe dengan Debug Mode

Untuk troubleshooting koneksi atau melihat detail protokol MQTT:

```bash
mosquitto_sub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t "$MQTT_TOPIC" \
  -d
```

**Opsi**:
- `-d` : Debug mode, tampilkan detail koneksi dan protokol MQTT

---

### 5. Subscribe Semua Topic Naturelink (Wildcard)

Untuk subscribe semua topic yang dimulai dengan `/Naturelink/`:

```bash
mosquitto_sub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t '/Naturelink/#' \
  -v
```

---

## Opsi Tambahan yang Berguna

### Batasi Jumlah Pesan

Untuk hanya menerima N pesan lalu exit:

```bash
mosquitto_sub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t "$MQTT_TOPIC" \
  -C 10 \
  -N | hexdump -C
```

`-C 10` = exit setelah menerima 10 pesan

### Skip Retained Messages

Untuk tidak menerima retained message (hanya pesan baru):

```bash
mosquitto_sub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t "$MQTT_TOPIC" \
  -R \
  -N | hexdump -C
```

`-R` = skip retained messages

### Set QoS Level

Untuk set Quality of Service level:

```bash
mosquitto_sub \
  -h "$MQTT_BROKER" \
  -p "$MQTT_PORT" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t "$MQTT_TOPIC" \
  -q 1 \
  -N | hexdump -C
```

`-q 1` = QoS level 1 (at least once delivery)

---

## Analisis Data Hex

### Membaca Output Hexdump

Format output hexdump:

```
00000000  3e 3e 01 30 08 66 34 40  55 56 71 22 51 00 01 01  |>>.0.f4@UVq"Q...|
^         ^                                                  ^
offset    hex bytes (16 per baris)                          ASCII representation
```

- **Kolom 1**: Offset byte (dalam hex)
- **Kolom 2-9**: Byte data dalam hex (8 bytes)
- **Kolom 10-17**: Byte data dalam hex (8 bytes lagi)
- **Kolom terakhir**: Representasi ASCII (`.` untuk non-printable)

### Struktur Data Naturelink (Berdasarkan Sample)

```
Offset  Hex                              ASCII    Keterangan
------  -------------------------------  -------  -----------
0x00    3e 3e                            >>       Header/delimiter
0x02    01                               .        Protocol version / message type
0x03    30                               0        Packet type / command
0x04    08                               .        Length / flags
0x05    66 34 40                         f4@      Device ID / koordinat (perlu verifikasi)
0x08    55 56 71 22 51                   UVq"Q    Timestamp / device data
...     (sisanya perlu dokumentasi protokol untuk parsing detail)
```

---

## Troubleshooting

### Tidak Ada Data Masuk

1. **Cek koneksi**:
```bash
mosquitto_sub -h "$MQTT_BROKER" -p "$MQTT_PORT" -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t '#' -v -C 5
```

2. **Cek topic dengan wildcard**:
```bash
mosquitto_sub -h "$MQTT_BROKER" -p "$MQTT_PORT" -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t '/Naturelink/#' -v
```

3. **Coba tanpa leading slash**:
```bash
mosquitto_sub -h "$MQTT_BROKER" -p "$MQTT_PORT" -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t 'Naturelink/Send' -v
```

### Error "Connection Refused"

- Verifikasi username/password
- Cek firewall tidak memblokir port 1883

### Data Terlihat Corrupt

- Pastikan menggunakan opsi `-N` untuk data binary
- Jangan gunakan `-v` kalau pakai hexdump (akan menambah topic di output)

---

## Script Helper (Opsional)

Buat script untuk mempermudah subscribe:

```bash
#!/bin/bash
# File: scripts/subscribe_naturelink.sh

BROKER="$MQTT_BROKER"
PORT="$MQTT_PORT"
USER="$MQTT_USERNAME"
PASS="$MQTT_PASSWORD"
TOPIC="$MQTT_TOPIC"

echo "Subscribing to $TOPIC..."
echo "Press Ctrl+C to stop"
echo ""

mosquitto_sub \
  -h "$BROKER" \
  -p "$PORT" \
  -u "$USER" \
  -P "$PASS" \
  -t "$TOPIC" \
  -N | hexdump -C
```

Cara pakai:
```bash
chmod +x scripts/subscribe_naturelink.sh
./scripts/subscribe_naturelink.sh
```

---

## Next Steps

1. ✅ Subscribe dan lihat data hex
2. ⏳ Tambahkan dokumentasi protokol Naturelink ke `docs/protocol/`
3. ⏳ Parse data binary sesuai protokol
4. ⏳ Extract informasi GPS (lat/lon, speed, timestamp)
5. ⏳ Buat parser script (Python/Node.js)

---

**Last Updated**: 6 Maret 2026
