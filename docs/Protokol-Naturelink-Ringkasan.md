# Ringkasan Protokol Naturelink GPS Tracker

Dokumentasi ringkas untuk memahami format data binary dari Naturelink GPS Tracker.

---

## Struktur Paket GPRS (Tracking Data)

### Format Umum

| Field | Bytes | Contoh Hex | Keterangan |
|-------|-------|------------|------------|
| **Preamble** | 2 | `3E 3E` | Header tetap (tanda awal paket) |
| **Version** | 1 | `01` | Versi protokol |
| **Frame ID** | 1 | `30` | ID frame (1-255, berulang) |
| **IMEI** | 8 | `08 66 34 40 55 56 71 22 51` | IMEI device (BCD code) |
| **Data Length** | 2 | `61 00` | Panjang data (little-endian) |
| **Codec ID** | 1 | `01` | ID parsing data (0x01 = tracking data) |
| **Number of Records** | 1 | `01` | Jumlah record dalam paket |
| **Record Data** | Variable | ... | Data GPS dan IO elements |
| **Checksum** | 1 | `0A` | Checksum semua data |
| **End** | 1 | `0A` | Byte akhir tetap |

---

## Struktur Record Data (Codec ID = 0x01)

### Base Info

| Field | Bytes | Format | Keterangan |
|-------|-------|--------|------------|
| **Event Code** | 2 | Little-endian | Kode event/alarm |
| **Timestamp** | 4 | Little-endian | Unix timestamp dari 2000-01-01 00:00:00 |
| **Latitude** | 4 | Little-endian | Latitude × 1,000,000 |
| **Longitude** | 4 | Little-endian | Longitude × 1,000,000 |
| **Status & Signal & Speed** | 2 | Bit field | bit0: GPS valid, bit1-5: CSQ, bit6-15: Speed |
| **Satellites & Angle** | 2 | Bit field | bit0-6: Satellites, bit7-15: Heading (0-360°) |

### Penjelasan Field Penting

#### 1. **Timestamp**
- Format: Unix timestamp dari **2000-01-01 00:00:00** (bukan 1970!)
- Little-endian 4 bytes
- Contoh: `2D FB 44 2B` = 0x2B44FB2D = 727,827,245 detik dari 2000-01-01
- Konversi ke tanggal: Tambahkan ke epoch 2000-01-01

#### 2. **Latitude & Longitude**
- Format: Integer × 1,000,000 (little-endian)
- Contoh Latitude: `CF FE 58 01` = 0x0158FECF = 22,609,615 → **22.609615°**
- Contoh Longitude: `B1 E8 CB 06` = 0x06CBE8B1 = 114,026,673 → **114.026673°**

#### 3. **Status & Signal & Speed** (2 bytes)
Format bit: `0000 0000 0010 1110` (contoh: `2E 00`)

- **bit 0**: GPS positioning status
  - `0` = Invalid (GPS tidak fix)
  - `1` = Valid (GPS fix)
- **bit 1-5**: Signal Quality (CSQ)
  - Range: 0-31
  - Contoh: `10111` = 23
- **bit 6-15**: Speed over ground (km/h)
  - Range: 0-1023 km/h
  - Contoh: `0000 0000 00` = 0 km/h

#### 4. **Satellites & Angle** (2 bytes)
Format bit: `0000 0000 0000 0000` (contoh: `00 00`)

- **bit 0-6**: Number of satellites
  - Range: 0-127
- **bit 7-15**: Heading/Angle
  - Range: 0-360°

---

## IO Elements

Setelah Base Info, ada IO Elements yang berisi data tambahan (voltage, mileage, dll).

### Struktur IO Elements

| Field | Bytes | Keterangan |
|-------|-------|------------|
| **No. of IO data 1Byte** | 1 | Jumlah IO data dengan value 1 byte |
| **IO Data ID** | 1 | ID data (lihat tabel IO Element) |
| **IO Data Value** | 1 | Nilai data |
| ... | ... | (repeat untuk semua IO 1-byte) |
| **No. of IO data 2Byte** | 1 | Jumlah IO data dengan value 2 byte |
| **IO Data ID** | 1 | ID data |
| **IO Data Value** | 2 | Nilai data (little-endian) |
| ... | ... | (repeat) |
| **No. of IO data 4Byte** | 1 | Jumlah IO data dengan value 4 byte |
| ... | ... | (dst untuk 8-byte dan variable length) |

### Tabel IO Element ID (Yang Penting)

| ID (Hex) | Nama | Bytes | Format | Keterangan |
|----------|------|-------|--------|------------|
| `01` | Battery Voltage | 2 | Little-endian | Tegangan baterai internal (mV) |
| `02` | External Voltage | 2 | Little-endian | Tegangan eksternal/power (mV) |
| `03` | AD1 | 2 | Little-endian | Analog input 1 (mV) |
| `04` | AD2 | 2 | Little-endian | Analog input 2 (mV) |
| `0B` | HDOP | 2 | Little-endian | Horizontal Dilution of Precision |
| `0C` | Altitude | 2 | Little-endian | Ketinggian (meter) |
| `0D` | Mileage | 4 | Little-endian | Jarak tempuh (meter) |
| `0E` | Running Time | 4 | Little-endian | Waktu mesin hidup (detik) |
| `0F` | Input Port Status | 2 | Bit field | Status input port |
| `10` | Output Port Status | 2 | Bit field | Status output port |
| `11` | Base Station Info | 10 | Variable | MCC, MNC, LAC, Cell ID |
| `12` | Fuel Percentage | 2 | Little-endian | Persentase bahan bakar |
| `18` | XYZ Acceleration | 6 | 3×2 bytes | Akselerasi X, Y, Z (mg) |
| `1A` | Network Type | 1 | Byte | 1=2G, 2=4G, dll |

---

## Contoh Parsing Data Real

### Data Hex yang Ditangkap:
```
3e 3e 01 30 08 66 34 40 55 56 71 22 51 00 01 01
33 00 69 2c 3d 31 5b 68 59 01 41 7b cd 06 33 00
11 62 01 1a 02 08 01 16 10 02 fa 2f 03 00 00 04
00 00 0b 09 00 0c 4e 00 0f 00 00 10 00 00 02 0d
63 00 00 00 0e 88 06 00 00 00 02 11 0a cc 01 00
00 a6 27 92 da 3a 03 18 06 0d 00 ef ff 16 fc 4c
0a
```

### Parsing Step-by-Step:

#### Header
- `3e 3e` = Preamble ✓
- `01` = Version 1
- `30` = Frame ID 48
- `08 66 34 40 55 56 71 22 51` = IMEI: **866344055567225**

#### Data Length & Codec
- `61 00` = 0x0061 = **97 bytes** data length
- `01` = Codec ID 0x01 (tracking data)
- `01` = **1 record**

#### Record 1 - Base Info
- **Event Code**: `33 00` = 0x0033 = Event **51**
- **Timestamp**: `69 2c 3d 31` = 0x313D2C69 = 827,827,305 detik
  - Dari 2000-01-01 → **2026-03-31 (sekitar)**
- **Latitude**: `5b 68 59 01` = 0x0159685B = 22,609,499 → **22.609499°**
- **Longitude**: `41 7b cd 06` = 0x06CD7B41 = 114,030,401 → **114.030401°**
- **Status**: `33 00` = 0x0033 = `0000 0000 0011 0011`
  - bit0 = 1 → GPS **Valid** ✓
  - bit1-5 = 11001 = 25 → CSQ **25**
  - bit6-15 = 0 → Speed **0 km/h**
- **Satellites**: `11 62` = 0x6211
  - bit0-6 = 0010001 = **17 satellites**
  - bit7-15 = 110001 = **49°** heading

#### IO Elements
- `01` = 1 IO data (1-byte)
  - ID `1a` = Network Type, Value `02` = **4G**
  
- `08` = 8 IO data (2-byte)
  - ID `01` = Battery, Value `16 10` = 0x1016 = **4118 mV**
  - ID `02` = External, Value `fa 2f` = 0x2FFA = **12,282 mV**
  - ID `03` = AD1, Value `00 00` = **0 mV**
  - ID `04` = AD2, Value `00 00` = **0 mV**
  - ID `0b` = HDOP, Value `09 00` = **9**
  - ID `0c` = Altitude, Value `4e 00` = **78 meter**
  - ID `0f` = Input, Value `00 00` = **0**
  - ID `10` = Output, Value `00 00` = **0**

- `02` = 2 IO data (4-byte)
  - ID `0d` = Mileage, Value `63 00 00 00` = **99 meter**
  - ID `0e` = Runtime, Value `88 06 00 00` = **1,672 detik** (27 menit)

- `00` = 0 IO data (8-byte)

- `02` = 2 IO data (variable length)
  - ID `11`, Length `0a` = Base Station (10 bytes)
    - `cc 01 00 00 a6 27 92 da 3a 03`
    - MCC: 0x01CC = **460** (China)
    - MNC: 0x0000 = **0**
    - LAC: 0x27A6
    - Cell ID: 0x033ADA92
  
  - ID `18`, Length `06` = XYZ Acceleration (6 bytes)
    - `0d 00 ef ff 16 fc`
    - X: 0x000D = **13 mg**
    - Y: 0xFFEF = **-17 mg**
    - Z: 0xFC16 = **-1002 mg**

#### Checksum & End
- `4c` = Checksum
- `0a` = End byte ✓

---

## Kesimpulan Data yang Diparsing

Dari data hex di atas, kita dapat informasi:

### **Lokasi GPS**
- **Latitude**: 22.609499°
- **Longitude**: 114.030401°
- **GPS Status**: Valid (fix)
- **Satellites**: 17
- **Heading**: 49°
- **Speed**: 0 km/h
- **Altitude**: 78 meter

### **Waktu**
- **Timestamp**: 2026-03-31 (perkiraan)

### **Status Device**
- **Battery**: 4.118V
- **External Power**: 12.282V
- **Network**: 4G
- **Mileage**: 99 meter
- **Engine Runtime**: 27 menit

### **Lokasi di Google Maps**
[22.609499, 114.030401](https://www.google.com/maps?q=22.609499,114.030401)

---

## Tips Parsing

1. **Selalu gunakan little-endian** untuk multi-byte values
2. **Timestamp dimulai dari 2000-01-01**, bukan 1970-01-01
3. **Latitude/Longitude dibagi 1,000,000** untuk dapat nilai desimal
4. **Speed dalam km/h** sudah langsung, tidak perlu konversi
5. **IO Elements bisa berbeda** tergantung konfigurasi device

---

## Next Steps

1. ✅ Pahami struktur protokol
2. ⏳ Buat Python parser script
3. ⏳ Test dengan data real dari MQTT
4. ⏳ Simpan hasil parsing ke database/file

---

**Referensi**: Communication Protocol_V1.0_2026.docx
