#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import random
import subprocess
import shlex
from flask import Flask, request, jsonify, render_template_string
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# Configuration
HOTSPOT_SSID = "RetroTV"
HOTSPOT_PASSWORD = "RetroTV123"
WPA_FILE = "/etc/wpa_supplicant/wpa_supplicant.conf"
IMAGE_SIZE = (480, 640)  # Width x Height


def create_hotspot_info_image():
    """Generate retro TV-style PNG with precise formatting"""
    BORDER_WIDTH = 15

    def get_hotspot_ip():
        try:
            return subprocess.check_output(['hostname', '-I'], text=True).split()[0]
        except:
            return "169.254.0.21"

    # Create base image with dark green background
    img = Image.new('RGB', IMAGE_SIZE, color=(0, 30, 0))
    draw = ImageDraw.Draw(img)

    # Add CRT noise within borders
    for _ in range(4000):
        x = random.randint(BORDER_WIDTH, IMAGE_SIZE[0]-BORDER_WIDTH-1)
        y = random.randint(BORDER_WIDTH, IMAGE_SIZE[1]-BORDER_WIDTH-1)
        img.putpixel((x, y), (0, random.randint(50, 100), 0))

    # Load monospace font with size validation
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 34)  # Reduced from 36
        char_width = font.getlength("M")  # Get exact monospace width
    except:
        font = ImageFont.load_default()
        char_width = 12  # Fallback approximation

    # Calculate box width based on available space
    available_width = IMAGE_SIZE[0] - 2*BORDER_WIDTH - 20  # 20px padding
    box_chars = min(int(available_width / char_width), 34)
    box_width = box_chars

    # Format ASCII box with exact spacing
    def format_ascii_box():
        ip = get_hotspot_ip()
        return f"""╔{'═'*(box_width-2)}╗
║ SSID: {HOTSPOT_SSID.ljust(box_width-10)} ║
║ PASS: {HOTSPOT_PASSWORD.ljust(box_width-10)} ║
║ IP: {ip.ljust(box_width-8)} ║
╚{'═'*(box_width-2)}╝"""

    text = format_ascii_box()

    # Get precise text dimensions
    bbox = draw.multiline_textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (IMAGE_SIZE[0] - text_width) // 2
    text_y = (IMAGE_SIZE[1] - text_height) // 2 - 50

    # Draw green border
    draw.rectangle(
        [(BORDER_WIDTH, BORDER_WIDTH), 
         (IMAGE_SIZE[0]-BORDER_WIDTH, IMAGE_SIZE[1]-BORDER_WIDTH)],
        outline=(0, 255, 0),
        width=BORDER_WIDTH
    )

    # Draw text with shadow
    for dx, dy in [(-1,-1), (1,1), (-1,1), (1,-1)]:
        draw.multiline_text(
            (text_x + dx, text_y + dy),
            text,
            fill=(0, 80, 0),
            font=font,
            align='center',
            spacing=10
        )
    
    draw.multiline_text(
        (text_x, text_y),
        text,
        fill=(0, 255, 0),
        font=font,
        align='center',
        spacing=10
    )

    # Draw scanlines avoiding text area
    scanline_start = BORDER_WIDTH
    scanline_end = IMAGE_SIZE[0] - BORDER_WIDTH 
    text_bottom = text_y + text_height + BORDER_WIDTH + 15 
    
    for y in range(BORDER_WIDTH, IMAGE_SIZE[1]-BORDER_WIDTH, 20):
        if y < text_y - BORDER_WIDTH or y > text_bottom:
            draw.line(
                [(scanline_start, y+75), (scanline_end, y-75)],
                fill=(0, 60, 0)
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
if __name__ == "__main__":
    # Grant temporary sudo for port 80
    #subprocess.run(["sudo", "setcap", "cap_net_bind_service=+ep", "/usr/bin/python3"])

    try:
        create_hotspot()
        display_proc = display_image()  # Start image display
        app.run(host='0.0.0.0', port=80)
    finally:
        # Cleanup processes
        if 'display_proc' in locals():
            display_proc.terminate()
        #subprocess.run(["sudo", "setcap", "cap_net_bind_service=-ep", "/usr/bin/python3"])

