import os
import random
import time
import subprocess
import threading
from subprocess import Popen
from RPi import GPIO
from flask import Flask, request, render_template_string, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# GPIO setup
GPIO_PIN = 26
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Configuration
CONFIG_FLAG_FILE = '/tmp/pi_config_mode'  # Temporary control file
VIDEOS_DIR = os.path.join(os.path.dirname(__file__), 'videos')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mkv', 'mov', 'webm', 'flv', 'wmv'}

# Flask app for video management
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

def allowed_file(filename):
	"""Check if file extension is allowed"""
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_video_duration(filepath):
	"""Get video duration using ffprobe"""
	try:
		result = subprocess.check_output([
			'ffprobe', '-v', 'error', 
			'-show_entries', 'format=duration',
			'-of', 'default=noprint_wrappers=1:nokey=1',
			filepath
		], stderr=subprocess.STDOUT, text=True)
		
		duration_seconds = float(result.strip())
		
		# Format duration as HH:MM:SS or MM:SS
		hours = int(duration_seconds // 3600)
		minutes = int((duration_seconds % 3600) // 60)
		seconds = int(duration_seconds % 60)
		
		if hours > 0:
			return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
		else:
			return f"{minutes:02d}:{seconds:02d}"
	except:
		return "N/A"

def get_video_resolution(filepath):
	"""Get video resolution using ffprobe"""
	try:
		result = subprocess.check_output([
			'ffprobe', '-v', 'error',
			'-select_streams', 'v:0',
			'-show_entries', 'stream=width,height',
			'-of', 'csv=s=x:p=0',
			filepath
		], stderr=subprocess.STDOUT, text=True)
		
		width, height = map(int, result.strip().split('x'))
		return width, height
	except:
		return None, None

def scale_video_if_needed(filepath, max_height=480):
	"""Scale video to max height if necessary, always converting to MP4"""
	try:
		width, height = get_video_resolution(filepath)
		
		if height is None:
			print(f"⚠️ Could not detect video resolution for {filepath}")
			return filepath
		
		# Always convert to .mp4 extension for consistency
		base_name = os.path.splitext(filepath)[0]
		output_filepath = base_name + '.mp4'
		
		# If resolution is OK and already MP4, no conversion needed
		if height <= max_height and filepath.endswith('.mp4'):
			print(f"✅ Video resolution OK: {width}x{height}")
			return filepath
		
		print(f"🔄 Converting video from {width}x{height} to max height {max_height}px...")
		
		# Create temporary output file
		temp_output = output_filepath + '.tmp.mp4'
		
		try:
			# Run ffmpeg to scale video with optimal settings for Raspberry Pi
			# scale=-2:480 automatically calculates width and ensures it's divisible by 2
			result = subprocess.run([
				'ffmpeg', '-i', filepath,
				'-vf', f'scale=-2:{max_height}',
				'-c:v', 'libx264',           # H.264 codec
				'-profile:v', 'baseline',     # Maximum compatibility for embedded devices
				'-level', '3.0',              # Compatible with older hardware
				'-preset', 'fast',            # Faster encoding, good for RPi
				'-crf', '23',                 # Quality (18-28, lower is better)
				'-pix_fmt', 'yuv420p',        # Universal pixel format compatibility
				'-c:a', 'aac',                # Audio codec
				'-b:a', '128k',               # Audio bitrate
				'-movflags', '+faststart',    # Optimize for streaming
				'-y',                         # Overwrite output
				temp_output
			], check=True, capture_output=True, text=True)
			
			# Remove original file
			os.remove(filepath)
			
			# Rename temp to final output
			os.rename(temp_output, output_filepath)
			
			# Get new resolution for logging
			new_width, new_height = get_video_resolution(output_filepath)
			print(f"✅ Video converted successfully to {new_width}x{new_height} → {os.path.basename(output_filepath)}")
			return output_filepath
			
		except subprocess.CalledProcessError as e:
			print(f"❌ FFmpeg error: {e.stderr}")
			# Clean up temp file if exists
			if os.path.exists(temp_output):
				os.remove(temp_output)
			# Return original filepath if conversion failed
			return filepath
		
	except Exception as e:
		print(f"❌ Error processing video: {e}")
		return filepath

def get_video_files():
	"""Get list of video files with sizes and durations"""
	videos = []
	if os.path.exists(VIDEOS_DIR):
		for filename in os.listdir(VIDEOS_DIR):
			if allowed_file(filename):
				filepath = os.path.join(VIDEOS_DIR, filename)
				size_mb = os.path.getsize(filepath) / (1024 * 1024)
				duration = get_video_duration(filepath)
				videos.append({
					'name': filename,
					'size': f"{size_mb:.2f} MB",
					'duration': duration
				})
	return sorted(videos, key=lambda x: x['name'])

def count_videos():
	"""Count current video files"""
	if not os.path.exists(VIDEOS_DIR):
		return 0
	return len([f for f in os.listdir(VIDEOS_DIR) if allowed_file(f)])

@app.route('/')
def index():
	"""Main video management interface"""
	videos = get_video_files()
	return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { box-sizing: border-box; }
body {
	background: #000;
	margin: 0;
	font-family: 'Courier New', monospace;
	color: #0f0;
	padding: 20px;
}

.container {
	max-width: 900px;
	margin: 0 auto;
	background: #001100;
	border: 3px solid #0f0;
	box-shadow: 0 0 20px #0f0;
	padding: 30px;
}

h1 {
	color: #0f0;
	text-align: center;
	text-shadow: 0 0 10px #0f0;
	border-bottom: 2px solid #0f0;
	padding-bottom: 15px;
	margin-top: 0;
	font-size: 2em;
}

.upload-section {
	background: #002200;
	border: 2px solid #0f0;
	padding: 20px;
	margin-bottom: 30px;
	border-radius: 5px;
}

input[type="file"] {
	background: #001100;
	color: #0f0;
	border: 1px solid #0f0;
	padding: 10px;
	width: 100%;
	margin: 10px 0;
	font-family: 'Courier New', monospace;
}

button {
	background: #003300;
	color: #0f0;
	border: 2px solid #0f0;
	padding: 12px 25px;
	font-family: 'Courier New', monospace;
	font-size: 16px;
	cursor: pointer;
	transition: all 0.3s;
	border-radius: 3px;
}

button:hover {
	background: #0f0;
	color: #000;
	box-shadow: 0 0 15px #0f0;
}

.delete-btn {
	background: #330000;
	border-color: #f00;
	color: #f00;
	padding: 8px 15px;
	font-size: 14px;
}

.delete-btn:hover {
	background: #f00;
	color: #000;
	box-shadow: 0 0 15px #f00;
}

.video-list {
	margin-top: 20px;
}

.video-item {
	background: #002200;
	border: 1px solid #0f0;
	padding: 15px;
	margin-bottom: 10px;
	display: flex;
	justify-content: space-between;
	align-items: center;
	border-radius: 3px;
}

.video-info {
	flex-grow: 1;
}

.video-name {
	font-weight: bold;
	color: #0f0;
	margin-bottom: 5px;
}

.video-size {
	color: #0a0;
	font-size: 0.9em;
}

.video-meta {
	display: flex;
	gap: 15px;
	flex-wrap: wrap;
}

.video-meta span {
	display: inline-block;
}

.progress {
	display: none;
	background: #002200;
	border: 2px solid #0f0;
	height: 30px;
	margin: 15px 0;
	border-radius: 3px;
	overflow: hidden;
}

.progress-bar {
	background: #0f0;
	height: 100%;
	width: 0%;
	transition: width 0.3s;
	box-shadow: 0 0 10px #0f0;
}

.status {
	text-align: center;
	padding: 10px;
	display: none;
	margin: 10px 0;
	border-radius: 3px;
}

.success { 
	background: #003300; 
	border: 1px solid #0f0; 
	color: #0f0; 
}

.error { 
	background: #330000; 
	border: 1px solid #f00; 
	color: #f00; 
}

.empty-state {
	text-align: center;
	padding: 40px;
	color: #0a0;
	font-style: italic;
}

@media (max-width: 600px) {
	.video-item {
		flex-direction: column;
		align-items: flex-start;
	}
	.delete-btn {
		margin-top: 10px;
		width: 100%;
	}
}
</style>
</head>
<body>
	<div class="container">
		<h1>📺 RetroTV - Gestión de Videos</h1>
		
		<div class="upload-section">
			<h2 style="margin-top:0; color:#0f0;">📤 Subir Nuevo Video</h2>
			<p style="color:#0a0; font-size:0.9em; margin:10px 0;">
				📏 Los videos se escalarán automáticamente a máximo 480px de altura
			</p>
			<form id="uploadForm" enctype="multipart/form-data">
				<input type="file" id="fileInput" name="file" accept="video/*" required>
				<button type="submit">⬆️ Subir Video</button>
			</form>
			<div class="progress" id="progressBar">
				<div class="progress-bar" id="progressBarFill"></div>
			</div>
			<div class="status" id="status"></div>
		</div>

		<div class="video-list">
			<h2 style="color:#0f0;">🎬 Videos Disponibles ({{ videos|length }})</h2>
			{% if videos %}
				{% for video in videos %}
				<div class="video-item">
					<div class="video-info">
						<div class="video-name">{{ video.name }}</div>
						<div class="video-meta video-size">
							<span>📦 {{ video.size }}</span>
							<span>⏱️ {{ video.duration }}</span>
						</div>
					</div>
					<button class="delete-btn" onclick="deleteVideo('{{ video.name }}')">🗑️ Borrar</button>
				</div>
				{% endfor %}
			{% else %}
				<div class="empty-state">
					No hay videos. ¡Sube tu primer video!
				</div>
			{% endif %}
		</div>
	</div>

	<script>
	const uploadForm = document.getElementById('uploadForm');
	const fileInput = document.getElementById('fileInput');
	const progressBar = document.getElementById('progressBar');
	const progressBarFill = document.getElementById('progressBarFill');
	const status = document.getElementById('status');

	uploadForm.addEventListener('submit', async (e) => {
		e.preventDefault();
		
		const file = fileInput.files[0];
		if (!file) return;

		const formData = new FormData();
		formData.append('file', file);

		progressBar.style.display = 'block';
		status.style.display = 'none';

		try {
			const xhr = new XMLHttpRequest();
			
			xhr.upload.addEventListener('progress', (e) => {
				if (e.lengthComputable) {
					const percent = (e.loaded / e.total) * 100;
					progressBarFill.style.width = percent + '%';
				}
			});

			xhr.upload.addEventListener('load', () => {
				// Upload complete, now processing
				showStatus('⏳ Procesando video (escalando si es necesario)...', 'success');
			});

			xhr.addEventListener('load', () => {
				if (xhr.status === 200) {
					showStatus('✅ Video subido y procesado correctamente!', 'success');
					setTimeout(() => location.reload(), 1500);
				} else {
					showStatus('❌ Error al subir: ' + xhr.responseText, 'error');
				}
				progressBar.style.display = 'none';
				progressBarFill.style.width = '0%';
			});

			xhr.addEventListener('error', () => {
				showStatus('❌ Error de red al subir el archivo', 'error');
				progressBar.style.display = 'none';
			});

			xhr.open('POST', '/upload');
			xhr.send(formData);

		} catch (err) {
			showStatus('❌ Error: ' + err.message, 'error');
			progressBar.style.display = 'none';
		}
	});

	async function deleteVideo(filename) {
		if (!confirm('¿Seguro que quieres borrar "' + filename + '"?')) return;

		try {
			const response = await fetch('/delete/' + encodeURIComponent(filename), {
				method: 'DELETE'
			});

			if (response.ok) {
				showStatus('✅ Video borrado correctamente', 'success');
				setTimeout(() => location.reload(), 1000);
			} else {
				showStatus('❌ Error al borrar el video', 'error');
			}
		} catch (err) {
			showStatus('❌ Error: ' + err.message, 'error');
		}
	}

	function showStatus(message, type) {
		status.textContent = message;
		status.className = 'status ' + type;
		status.style.display = 'block';
	}
	</script>
</body>
</html>
""", videos=videos)

@app.route('/upload', methods=['POST'])
def upload_file():
	"""Handle video upload with automatic scaling and MP4 conversion"""
	try:
		if 'file' not in request.files:
			return 'No file provided', 400
		
		file = request.files['file']
		if file.filename == '':
			return 'No file selected', 400
		
		if not allowed_file(file.filename):
			return f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}', 400
		
		# Ensure videos directory exists
		os.makedirs(VIDEOS_DIR, exist_ok=True)
		
		# Save file
		filename = secure_filename(file.filename)
		filepath = os.path.join(VIDEOS_DIR, filename)
		
		print(f"📤 Uploading: {filename}")
		file.save(filepath)
		print(f"✅ File saved: {filepath}")
		
		# Scale/convert video (max height 480px, always to MP4)
		# Returns the final filepath (may change extension to .mp4)
		final_filepath = scale_video_if_needed(filepath, max_height=480)
		
		final_filename = os.path.basename(final_filepath)
		print(f"✅ Final video: {final_filename}")
		
		return 'Upload successful', 200
	except Exception as e:
		print(f"❌ Upload error: {e}")
		return f'Upload failed: {str(e)}', 500

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
	"""Delete a video file"""
	try:
		filepath = os.path.join(VIDEOS_DIR, secure_filename(filename))
		if os.path.exists(filepath) and allowed_file(filename):
			os.remove(filepath)
			return 'Deleted successfully', 200
		return 'File not found', 404
	except Exception as e:
		return f'Delete failed: {str(e)}', 500

def check_config_mode():
    """Check if button is pressed at startup"""
    return GPIO.input(GPIO_PIN) == GPIO.LOW

def run_config_mode():
    """Handle configuration mode and reboot"""
    print("CONFIGURATION MODE ACTIVE")

    # Turn on screen for configuration
    screen_power(True)
    time.sleep(1)  # Give screen time to wake up

    # Run the configuration script
    config_script = os.path.join(os.path.dirname(__file__), 'configuration.py')
    subprocess.call(['python3', config_script])

    print("Configuration complete. Release button to reboot...")

    # Wait for button release
    while GPIO.input(GPIO_PIN) == GPIO.LOW:
        time.sleep(0.1)

    print("Button released, rebooting...")
    time.sleep(1)  # Brief pause before reboot

    # Turn off screen before reboot
    screen_power(False)
    subprocess.call(['sudo', 'reboot'])

def play_video():
    try:
        cmd = ['cvlc', '-q', '--gain', '0.75', '--audio-filter=downmix',
               '--fullscreen', '--no-osd', '--aspect-ratio=fill',
               '--random', '--loop', 'videos/']
        return Popen(cmd)
    except Exception as e:
        print(f"Playback error: {e}")
        return None

def stop_video(process):
    if process:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()

def screen_power(state):
    subprocess.call(f'vcgencmd display_power {"1" if state else "0"}', shell=True)

def start_web_interface():
	"""Start Flask web server in background thread"""
	print("🌐 Starting web interface on http://<your-pi-ip>")
	app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)

def normal_operation():
    """Main video playback logic with auto-reload on video changes"""
    current_process = None
    screen_state = False
    video_count = count_videos()
    last_check_time = time.time()
    CHECK_INTERVAL = 5  # Check for new videos every 5 seconds

    # Ensure screen is off at startup
    screen_power(False)

    # Start web interface in background thread
    web_thread = threading.Thread(target=start_web_interface, daemon=True)
    web_thread.start()
    print("✅ Web interface started - You can manage videos from any browser")
    print(f"📹 Initial video count: {video_count}")

    try:
        while True:
            btn_state = GPIO.input(GPIO_PIN) == GPIO.LOW
            current_time = time.time()

            # Check if video list has changed
            if current_time - last_check_time >= CHECK_INTERVAL:
                new_count = count_videos()
                if new_count != video_count:
                    print(f"🔄 Video list changed ({video_count} -> {new_count})")
                    video_count = new_count
                    
                    # If playing, restart VLC to reload video list
                    if screen_state and current_process:
                        print("🔄 Reloading VLC with new video list...")
                        stop_video(current_process)
                        current_process = play_video()
                        print("✅ VLC reloaded")
                
                last_check_time = current_time

            if btn_state and not screen_state:
                # Start playback
                screen_state = True
                video_count = count_videos()  # Update count when starting
                current_process = play_video()
                time.sleep(1.5)
                screen_power(True)
                print(f"▶️ Playback started ({video_count} videos)")

            elif not btn_state and screen_state:
                # Stop playback
                screen_state = False
                screen_power(False)
                stop_video(current_process)
                current_process = None
                print("⏹️ Playback stopped")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        stop_video(current_process)
        screen_power(False)
        GPIO.cleanup()

if __name__ == "__main__":
    # Check for existing config flag
    if os.path.exists(CONFIG_FLAG_FILE):
        os.remove(CONFIG_FLAG_FILE)
        normal_operation()
    elif check_config_mode():
        run_config_mode()
    else:
        normal_operation()

