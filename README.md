# 📺 Small Retro TV

This project is a modern take on the classic CRT TV, inspired by the [Simpsons TV](https://withrow.io/simpsons-tv-build-guide-waveshare) from Brandon Withrow. It plays random TV shows on a 3D-printed old CRT screen, bringing a touch of nostalgia to your living room.

**✨ Features:**
- 🎬 VLC-based video player with random playback
- 📱 Web-based WiFi configurator (no keyboard/monitor needed)
- 🌐 Video management UI (upload, delete, view videos)
- 📏 Automatic video scaling to 480px height
- 🔘 Physical button control (on/off and config mode)

![Retro TV](./images/retro_tv.jpg)

## 🛒 Shopping List
- [Raspberry Pi Zero W](https://www.amazon.es/RASPBERRY-PI-ZERO-Ordenador-Sobremesa/dp/B07BHMRTTY)
- [Waveshare 2.8inch for Raspberry Pi 480×640 dpi](https://www.amazon.es/dp/B08LZG5G19)
- [Adafruit Mono 2.5 W Audio Amplifier](https://www.amazon.es/dp/B07YJLNVVD)
- [1.5" 4ohm 3W Audio Speaker](https://www.amazon.es/dp/B01LN8ONG4)
- [Micro USB DIP Breakout Board](https://www.amazon.es/dp/B07WC8W81F)
- [Micro USB Cable to solder](https://www.amazon.es/dp/B0CWP1MCS9)
- [1K Trim Potentiometer](https://www.amazon.es/dp/B09S3FWWW7)
- [Micro Push Button Switch](https://www.amazon.es/dp/B07BFNKLKG)
- SD Card (enough disk space to store the OS and the videos)
- Cabling

## 🛠️ Steps to Build

### 1. Hardware Assembly
Follow [the original guide](https://withrow.io/simpsons-tv-build-guide-waveshare) to solder all the pieces together.

### 2. Prepare the SD Card
- Download [Raspberry Pi OS Lite (Legacy, Debian 11 Bullseye)](https://www.raspberrypi.com/software/operating-systems/) from the official Raspberry Pi website.
- Burn the image to the SD Card using [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
- Configure WiFi and SSH access before first boot (optional):
  - Enable SSH by creating an empty file named `ssh` in the boot partition
  - Create `wpa_supplicant.conf` in the boot partition with your WiFi credentials (or use the web configurator after first boot)
- Insert the SD Card into the Raspberry Pi and power it on.

### 3. Initial Setup
- SSH into your Raspberry Pi (default credentials):
  ```
  user: pi
  password: raspberry
  ```
- Run `sudo raspi-config` to:
  - Expand filesystem
  - Change default password
  - Set locale/timezone
- Reboot after changes.

### 4. Configure the Display
- Unzip the [28DPI-DTBO.zip](./resources/28DPI-DTBO.zip) into `/etc/overlays`. More info [here](https://www.waveshare.com/wiki/2.8inch_DPI_LCD).
- Edit `/boot/config.txt` and add the following at the end:
  ```
  gpio=0-9=a2
  gpio=12-17=a2
  gpio=20-25=a2
  dtoverlay=dpi24
  enable_dpi_lcd=1
  display_default_lcd=1
  extra_transpose_buffer=2
  dpi_group=2
  dpi_mode=87
  dpi_output_format=0x7F216
  hdmi_timings=480 0 26 16 10 640 0 25 10 15 0 0 0 60 0 32000000 1
  dtoverlay=waveshare-28dpi-3b-4b
  dtoverlay=waveshare-28dpi-3b
  dtoverlay=waveshare-28dpi-4b
  dtoverlay=waveshare-touch-28dpi
  display_rotate=3
  disable_splash=1
  ```

### 5. Software Installation
- Update the system:
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```
- Install dependencies:
  ```bash
  sudo apt install -y vlc python3-flask python3-rpi.gpio python3-pip ffmpeg
  ```
- Clone this repository:
  ```bash
  cd ~
  git clone https://github.com/YOUR_USERNAME/small_retro_tv.git
  cd small_retro_tv
  ```
- Install Python dependencies:
  ```bash
  pip3 install Flask Pillow werkzeug
  ```
- Create the videos directory:
  ```bash
  mkdir -p videos
  ```

### 6. Enable Audio
- Edit `/boot/config.txt` again and add:
  ```
  dtoverlay=audremap,enable_jack,pins_18_19
  ```
- Edit `/boot/cmdline.txt` and add the following (or edit if they exist):
  ```
  console=tty3 consoleblank=0 logo.nologo quiet splash
  ```

### 7. Configure GPIO for Audio
- Create the file `/etc/rc.local` with the following content:
  ```
  #!/bin/sh -e
  # This script is executed at the end of each multiuser runlevel

  raspi-gpio set 19 op a5

  exit 0
  ```

### 8. Create the System Service
- Create the file `/etc/systemd/system/tvplayer.service` with the following [content](./resources/tvplayer.service):
  ```
  [Unit]
  Description=RetroTV Player
  After=network.target

  [Service]
  WorkingDirectory=/home/pi/small_retro_tv/
  ExecStart=/usr/bin/python3 /home/pi/small_retro_tv/retrotv.py
  Restart=always
  User=pi

  [Install]
  WantedBy=multi-user.target
  ```
- Enable and start the service:
  ```bash
  sudo systemctl enable tvplayer.service
  sudo systemctl daemon-reload
  sudo systemctl start tvplayer.service
  ```

## 🎮 How to Use

### Normal Mode (Video Playback)
1. **Press the button** → TV turns on and starts playing random videos
2. **Release the button** → TV turns off
3. **Access web interface** → Open `http://<raspberry-pi-ip>` in your browser to:
   - Upload new videos (automatically scaled to 480px height)
   - Delete videos
   - View video list with size and duration

### Configuration Mode (WiFi Setup)
1. **Hold the button while powering on** the Raspberry Pi
2. The screen will display:
   - SSID: `RetroTV`
   - Password: `RetroTV123`
   - IP address (usually `10.42.0.1`)
3. **Connect to the WiFi hotspot** from your phone/laptop
4. **Open browser** and go to `http://10.42.0.1`
5. **Configure your WiFi** network
6. **Release the button** → Raspberry Pi reboots and connects to your WiFi

## 🎉 Enjoy Your Retro TV!
Your retro TV is now ready to play random TV shows! The videos are automatically detected and reloaded every 5 seconds when changes are made through the web interface.

## 📋 Technical Details

### Video Processing
- **Automatic scaling**: Videos are automatically scaled to maximum 480px height
- **Format conversion**: All videos are converted to MP4 (H.264 baseline, AAC audio)
- **Optimization**: Videos are optimized for Raspberry Pi playback with `libx264` codec
- **Supported formats**: MP4, AVI, MKV, MOV, WebM, FLV, WMV

### System Architecture
- **Python 3** with Flask web framework
- **VLC (cvlc)** for video playback with random loop mode
- **FFmpeg/FFprobe** for video processing and metadata extraction
- **GPIO control** via RPi.GPIO library
- **Background monitoring** for automatic video list updates

### Network Services
- **Port 80** (HTTP) - Web interface for video management (normal mode)
- **Port 80** (HTTP) - WiFi configuration interface (config mode)
- **WiFi Hotspot** - Temporary AP for initial setup (`RetroTV` / `RetroTV123`)

## 🔧 Troubleshooting

### Screen not working
- Verify `/boot/config.txt` has all the display settings
- Check that overlays are properly installed in `/etc/overlays`

### No audio
- Verify audio configuration in `/boot/config.txt`
- Check GPIO 19 is set correctly in `/etc/rc.local`

### Videos not playing
- Ensure videos are in the `videos/` directory
- Check VLC is installed: `which cvlc`
- Check FFmpeg is installed: `which ffmpeg`
- View logs: `sudo journalctl -u tvplayer.service -f`

### Web interface not accessible
- Check service status: `sudo systemctl status tvplayer.service`
- Verify Flask dependencies: `pip3 list | grep -i flask`
- Check network connectivity: `ip addr show`
