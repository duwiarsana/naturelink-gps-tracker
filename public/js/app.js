let map;
let marker;
let client;
let currentPosition = [-6.390071, 106.994909];

const MQTT_CONFIG = {
    host: window.location.hostname || '72.62.126.85',
    port: 9001,
    clientId: 'web_dashboard_' + Math.random().toString(16).substr(2, 8),
    username: 'kutaienergy',
    password: 'KutaiEnerg',
    topic: '/Naturelink/Send/json'
};

function initMap() {
    map = L.map('map', {
        zoomControl: false
    }).setView(currentPosition, 15);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);
    
    const carIcon = L.divIcon({
        className: 'custom-car-icon',
        html: '<div style="font-size: 24px;">🚗</div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
    
    marker = L.marker(currentPosition, { icon: carIcon }).addTo(map);
    marker.bindPopup('Waiting for GPS data...').openPopup();
}

function connectMQTT() {
    updateStatus('Connecting...', false);
    
    console.log('Attempting MQTT connection to:', MQTT_CONFIG.host + ':' + MQTT_CONFIG.port);
    console.log('Client ID:', MQTT_CONFIG.clientId);
    
    client = new Paho.MQTT.Client(
        MQTT_CONFIG.host,
        MQTT_CONFIG.port,
        MQTT_CONFIG.clientId
    );
    
    client.onConnectionLost = onConnectionLost;
    client.onMessageArrived = onMessageArrived;
    
    const connectOptions = {
        userName: MQTT_CONFIG.username,
        password: MQTT_CONFIG.password,
        onSuccess: onConnect,
        onFailure: onFailure,
        useSSL: false,
        timeout: 10,
        keepAliveInterval: 60,
        cleanSession: true
    };
    
    try {
        client.connect(connectOptions);
    } catch (error) {
        console.error('MQTT connection error:', error);
        updateStatus('Connection Error: ' + error.message, false);
    }
}

function onConnect() {
    console.log('Connected to MQTT broker');
    updateStatus('Connected', true);
    client.subscribe(MQTT_CONFIG.topic);
    console.log('Subscribed to:', MQTT_CONFIG.topic);
}

function onFailure(error) {
    console.error('Connection failed:', error);
    const errorMsg = error.errorMessage || 'Unknown error';
    updateStatus('Connection Failed: ' + errorMsg, false);
    console.log('Retrying in 5 seconds...');
    setTimeout(connectMQTT, 5000);
}

function onConnectionLost(responseObject) {
    if (responseObject.errorCode !== 0) {
        console.log('Connection lost:', responseObject.errorMessage);
        updateStatus('Disconnected', false);
        setTimeout(connectMQTT, 5000);
    }
}

function onMessageArrived(message) {
    try {
        const data = JSON.parse(message.payloadString);
        console.log('Received data:', data);
        updateDashboard(data);
    } catch (error) {
        console.error('Error parsing message:', error);
    }
}

function updateStatus(text, connected) {
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    statusText.textContent = text;
    
    if (connected) {
        statusIndicator.classList.add('connected');
        statusIndicator.classList.remove('disconnected');
    } else {
        statusIndicator.classList.add('disconnected');
        statusIndicator.classList.remove('connected');
    }
}

function updateDashboard(data) {
    if (!data) return;
    
    document.getElementById('imei').textContent = data.device?.imei || '-';
    document.getElementById('frameId').textContent = data.device?.frame_id || '-';
    document.getElementById('event').textContent = 
        `${data.event?.kode || '-'} - ${data.event?.nama || '-'}`;
    document.getElementById('lastUpdate').textContent = 
        data.waktu ? new Date(data.waktu).toLocaleString('id-ID') : '-';
    
    if (data.lokasi) {
        const loc = data.lokasi;
        document.getElementById('latitude').textContent = 
            loc.latitude?.toFixed(6) || '-';
        document.getElementById('longitude').textContent = 
            loc.longitude?.toFixed(6) || '-';
        document.getElementById('speed').textContent = 
            loc.kecepatan_kmh !== undefined ? `${loc.kecepatan_kmh} km/h` : '-';
        document.getElementById('heading').textContent = 
            loc.arah_derajat !== undefined ? `${loc.arah_derajat}°` : '-';
        document.getElementById('altitude').textContent = 
            loc.ketinggian_meter !== undefined ? `${loc.ketinggian_meter} m` : '-';
        document.getElementById('satellites').textContent = 
            loc.jumlah_satelit !== undefined ? loc.jumlah_satelit : '-';
        
        const gpsValidEl = document.getElementById('gpsValid');
        if (loc.gps_valid) {
            gpsValidEl.textContent = '✓ Valid';
            gpsValidEl.className = 'value gps-valid';
        } else {
            gpsValidEl.textContent = '✗ Invalid';
            gpsValidEl.className = 'value gps-invalid';
        }
        
        document.getElementById('signalQuality').textContent = 
            loc.kualitas_sinyal !== undefined ? loc.kualitas_sinyal : '-';
        
        if (loc.latitude && loc.longitude) {
            updateMap(loc.latitude, loc.longitude, data);
        }
    }
    
    if (data.status_device) {
        const status = data.status_device;
        document.getElementById('battery').textContent = 
            status.baterai_volt !== undefined ? `${status.baterai_volt} V` : '-';
        document.getElementById('externalPower').textContent = 
            status.power_eksternal_volt !== undefined ? `${status.power_eksternal_volt} V` : '-';
        document.getElementById('network').textContent = status.jaringan || '-';
        document.getElementById('mileage').textContent = 
            status.jarak_tempuh_km !== undefined ? `${status.jarak_tempuh_km} km` : '-';
        document.getElementById('engineTime').textContent = 
            status.waktu_mesin_hidup_menit !== undefined ? 
            `${status.waktu_mesin_hidup_menit} min` : '-';
    }
    
    if (data.input_output) {
        const io = data.input_output;
        updateIOStatus('din1', io.din1);
        updateIOStatus('din2', io.din2);
        updateIOStatus('din3', io.din3);
        updateIOStatus('din4', io.din4);
        updateIOStatus('din5', io.din5);
        updateIOStatus('dout1', io.dout1);
        updateIOStatus('dout2', io.dout2);
    }
    
    if (data.akselerasi) {
        const accel = data.akselerasi;
        document.getElementById('accelX').textContent = 
            accel.x_mg !== undefined ? `${accel.x_mg} mg` : '-';
        document.getElementById('accelY').textContent = 
            accel.y_mg !== undefined ? `${accel.y_mg} mg` : '-';
        document.getElementById('accelZ').textContent = 
            accel.z_mg !== undefined ? `${accel.z_mg} mg` : '-';
    }
    
    if (data.ibutton) {
        const ibuttonCard = document.getElementById('ibuttonCard');
        ibuttonCard.style.display = 'block';
        document.getElementById('ibuttonId').textContent = data.ibutton.id || '-';
        const authEl = document.getElementById('ibuttonAuth');
        if (data.ibutton.authorized) {
            authEl.textContent = '✓ Authorized';
            authEl.className = 'value gps-valid';
        } else {
            authEl.textContent = '✗ Not Authorized';
            authEl.className = 'value gps-invalid';
        }
    }
    
    if (data.base_station) {
        const bs = data.base_station;
        document.getElementById('mcc').textContent = bs.mcc || '-';
        document.getElementById('mnc').textContent = bs.mnc || '-';
        document.getElementById('lac').textContent = bs.lac || '-';
        document.getElementById('cellId').textContent = bs.cell_id || '-';
    }
}

function updateIOStatus(elementId, status) {
    const element = document.getElementById(elementId);
    if (element) {
        if (status) {
            element.textContent = 'ON';
            element.className = 'io-status on';
        } else {
            element.textContent = 'OFF';
            element.className = 'io-status off';
        }
    }
}

function updateMap(lat, lon, data) {
    const newPosition = [lat, lon];
    currentPosition = newPosition;
    
    marker.setLatLng(newPosition);
    map.setView(newPosition, map.getZoom());
    
    const popupContent = `
        <div style="min-width: 200px;">
            <strong>📍 GPS Location</strong><br>
            <strong>IMEI:</strong> ${data.device?.imei || '-'}<br>
            <strong>Speed:</strong> ${data.lokasi?.kecepatan_kmh || 0} km/h<br>
            <strong>Heading:</strong> ${data.lokasi?.arah_derajat || 0}°<br>
            <strong>Time:</strong> ${data.waktu ? new Date(data.waktu).toLocaleString('id-ID') : '-'}<br>
            <a href="${data.lokasi?.google_maps}" target="_blank">Open in Google Maps</a>
        </div>
    `;
    
    marker.bindPopup(popupContent);
}

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    connectMQTT();
});
