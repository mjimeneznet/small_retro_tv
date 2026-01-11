#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import random
import subprocess
import shlex
import threading
import time
from flask import Flask, request, jsonify, render_template_string
from PIL import Image, ImageDraw, ImageFont
from RPi import GPIO

app = Flask(__name__)

# Configuration
HOTSPOT_SSID = "RetroTV"
HOTSPOT_PASSWORD = "RetroTV123"
WPA_FILE = "/etc/wpa_supplicant/wpa_supplicant.conf"
IMAGE_SIZE = (480, 640)  # Width x Height
GPIO_PIN = 26  # Same pin as retrotv.py

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def create_hotspot_info_image():
    """Generate simple centered text display"""
    
    def get_hotspot_ip():
        try:
            return subprocess.check_output(['hostname', '-I'], text=True).split()[0]
        except:
            return "169.254.0.21"

    # Create base image with black background
    img = Image.new('RGB', IMAGE_SIZE, color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Add subtle CRT noise effect
    for _ in range(3000):
        x = random.randint(0, IMAGE_SIZE[0]-1)
        y = random.randint(0, IMAGE_SIZE[1]-1)
        img.putpixel((x, y), (0, random.randint(20, 60), 0))

    # Load monospace font
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 40)
    except:
        font = ImageFont.load_default()

    # Create simple text without box decorations
    ip = get_hotspot_ip()
    text = f"""SSID: {HOTSPOT_SSID}
PASS: {HOTSPOT_PASSWORD}
IP: {ip}"""

    # Get text dimensions for centering
    bbox = draw.multiline_textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (IMAGE_SIZE[0] - text_width) // 2
    text_y = (IMAGE_SIZE[1] - text_height) // 2 - 110  # Moved up 2 lines

    # Draw text with subtle shadow for depth
    for dx, dy in [(2, 2)]:
        draw.multiline_text(
            (text_x + dx, text_y + dy),
            text,
            fill=(0, 100, 0),
            font=font,
            align='left',
            spacing=15
        )
    
    # Draw main text in bright green
    draw.multiline_text(
        (text_x, text_y),
        text,
        fill=(0, 255, 0),
        font=font,
        align='left',
        spacing=15
    )

    output_file = "/tmp/retrotv_config.png"
    img.save(output_file)
    return output_file


def display_image():
    """Show image using cvlc in background"""
    image_path = create_hotspot_info_image()
    return subprocess.Popen([
        "cvlc",
        "-q",
        "--fullscreen",
        "--no-osd",
        "--loop",
        "--no-video-title-show",
        image_path
    ])

def create_hotspot():
    """Create configuration hotspot with sudo"""
    subprocess.run([
        "sudo", "nmcli", "dev", "wifi", "hotspot",
        "ifname", "wlan0",
        "ssid", HOTSPOT_SSID,
        "password", HOTSPOT_PASSWORD,
        "band", "bg",
        "channel", "6"
    ], check=True)

def scan_wifi():
    """Scan WiFi networks with sudo"""
    try:
        result = subprocess.check_output(
            ["sudo", "iwlist", "wlan0", "scan"],
            stderr=subprocess.STDOUT,
            text=True
        )
        return list(set(
            line.split('"')[1]
            for line in result.split('\n')
            if "ESSID" in line
        ))
    except subprocess.CalledProcessError:
        return []

def write_wpa_config(ssid, password):
    """Securely write config with sudo privileges"""
    # Sanitize inputs
    safe_ssid = shlex.quote(ssid)
    safe_password = shlex.quote(password)

    config = f"""
network={{
    ssid={safe_ssid}
    psk={safe_password}
    key_mgmt=WPA-PSK
}}"""

    # Write using sudo tee
    subprocess.run(
        f'echo "{config}" | sudo tee -a {WPA_FILE} >/dev/null',
        shell=True,
        check=True
    )

    # Apply changes without full restart
    subprocess.run(
        ["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"],
        check=True
    )

@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<style>
body {
    background: #000;
    margin: 0;
    font-family: 'Courier New', monospace;
    color: #0f0;
    overflow: hidden;
}

.crt {
    background: radial-gradient(circle, transparent 10%, rgba(0,0,0,0.8) 100%);
    position: fixed;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 2;
}

.container {
    position: relative;
    width: 80%;
    margin: 2em auto;
    padding: 20px;
    background: #001100;
    border: 3px solid #0f0;
    box-shadow: 0 0 10px #0f0;
    z-index: 2;
}

h1 {
    color: #0f0;
    text-align: center;
    text-shadow: 0 0 5px #0f0;
    border-bottom: 2px solid #0f0;
    padding-bottom: 10px;
}

button, select, input {
    background: #002200;
    color: #0f0;
    border: 1px solid #0f0;
    padding: 5px 10px;
    margin: 5px;
    font-family: 'Courier New', monospace;
    font-size: 16px;
}

#networks {
    margin: 15px 0;
    position: relative;
    z-index: 4;
}

#networks select {
    width: 100%;
    padding: 8px;
    background: #001100;
    border: 2px solid #0f0;
    box-shadow: 0 0 5px #0f0;
    -webkit-appearance: none;
    -moz-appearance: none;
    appearance: none;
}

.scanlines {
    position: fixed;
    width: 100%;
    height: 100%;
    background: repeating-linear-gradient(
        0deg,
        rgba(0, 0, 0, 0.15) 0px,
        rgba(0, 0, 0, 0.15) 1px,
        transparent 1px,
        transparent 2px
    );
    pointer-events: none;
    z-index: 3;
}

.glow {
    animation: glow 2s infinite alternate;
}

@keyframes glow {
    from { text-shadow: 0 0 5px #0f0; }
    to { text-shadow: 0 0 10px #0f0, 0 0 20px #0f0; }
}

@keyframes dropdown {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
</head>
<body>
    <div class="scanlines"></div>
    <div class="crt"></div>

    <div class="container">
        <h1 class="glow">📺 RetroTV </h1>
        <button onclick="scanNetworks()">📡 BUSCAR WIFI</button>
        <div id="networks"></div>
        <form id="wifiForm" onsubmit="return submitForm(event)">
            <input type="password" id="password" placeholder="🔑 CONTRASEÑA" required>
            <button type="submit">⚡ CONECTAR</button>
        </form>
    </div>

    <script>
    function scanNetworks() {
        fetch('/scan')
            .then(r => r.json())
            .then(nets => {
                const networksDiv = document.getElementById('networks');
                networksDiv.innerHTML = `
                    <select id="ssid" style="animation: dropdown 0.3s ease-out;">
                        ${nets.map(n => `<option>${n}</option>`).join('')}
                    </select>
                `;

                // Force z-index refresh
                networksDiv.style.display = 'none';
                networksDiv.offsetHeight; // Trigger reflow
                networksDiv.style.display = 'block';
            });
    }

    function submitForm(e) {
        e.preventDefault();
        const data = {
            ssid: document.getElementById('ssid').value,
            password: document.getElementById('password').value
        };
        fetch('/configure', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        }).then(() => {
            document.body.innerHTML = `
                <div class="container">
                    <h1 class="glow">⚙️ CONFIGURACION TERMINADA</h1>
                    <p style="text-align: center">Ya puedes salir del modo de configuracion.</p>
                </div>
            `;
        });
    }
    </script>
</body>
</html>
""")

@app.route('/scan')
def handle_scan():
    return jsonify(scan_wifi())

@app.route('/configure', methods=['POST'])
def handle_configure():
    data = request.json
    write_wpa_config(data['ssid'], data['password'])
    #subprocess.run(["sudo", "reboot"])
    return "", 200
def monitor_button_for_reboot(display_proc):
	"""Monitor GPIO button and reboot when released"""
	print("🔘 Monitoring button... Release to reboot")
	
	# Wait while button is pressed
	while GPIO.input(GPIO_PIN) == GPIO.LOW:
		time.sleep(0.1)
	
	print("✅ Button released! Rebooting in 2 seconds...")
	time.sleep(2)
	
	# Cleanup
	if display_proc:
		display_proc.terminate()
	GPIO.cleanup()
	
	# Turn off screen before reboot
	subprocess.call('vcgencmd display_power 0', shell=True)
	
	# Reboot
	subprocess.call(['sudo', 'reboot'])

if __name__ == "__main__":
	display_proc = None
	
	try:
		print("🌐 Creating WiFi hotspot...")
		create_hotspot()
		
		print("📺 Displaying configuration info...")
		display_proc = display_image()
		
		# Run Flask in a separate thread (daemon so it dies when main exits)
		flask_thread = threading.Thread(
			target=lambda: app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False),
			daemon=True
		)
		flask_thread.start()
		
		print("🌍 Web interface available at http://10.42.0.1")
		
		# Main thread monitors button for reboot
		monitor_button_for_reboot(display_proc)
		
	except KeyboardInterrupt:
		print("\n⚠️ Interrupted by user")
	except Exception as e:
		print(f"❌ Error: {e}")
	finally:
		# Cleanup processes
		if display_proc:
			display_proc.terminate()
		GPIO.cleanup()

