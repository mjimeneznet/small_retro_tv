import os
import random
import time
import subprocess
from subprocess import Popen
from RPi import GPIO
import signal

# GPIO setup
GPIO_PIN = 26
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Configuration
VIDEO_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'videos')
VIDEO_EXTENSIONS = ('.avi', '.mov', '.mp4', '.mkv')
CONFIG_FLAG_FILE = '/tmp/pi_config_mode'  # Temporary control file

def get_videos(directory):
    # Return the video directory with wildcard for all supported video types
    wildcards = [f"{directory}/**/*{ext}" for ext in VIDEO_EXTENSIONS]
    return wildcards

def check_config_mode():
    """Check if button is pressed at startup"""
    return GPIO.input(GPIO_PIN) == GPIO.LOW

def run_config_mode():
    """Handle configuration mode and reboot"""
    print("CONFIGURATION MODE ACTIVE")
    
    # Create control file
    with open(CONFIG_FLAG_FILE, 'w') as f:
        f.write('1')
    
    try:
        # Wait for button release
        while GPIO.input(GPIO_PIN) == GPIO.LOW:
            time.sleep(0.1)
        
        # Configuration logic here
        print("Configuration complete. Rebooting...")
        
    finally:
        # Cleanup and reboot
        if os.path.exists(CONFIG_FLAG_FILE):
            os.remove(CONFIG_FLAG_FILE)
        GPIO.cleanup()
        subprocess.call('sudo reboot', shell=True)

def play_video(video_paths):
    try:
        cmd = ['cvlc', '-q', '--gain', '0.75', '--audio-filter=downmix', 
               '--fullscreen', '--no-osd', '--aspect-ratio=fill',
               '--random', '--loop'] + video_paths
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

def normal_operation():
    """Main video playback logic"""
    videos = get_videos(VIDEO_DIR)
    current_process = None
    screen_state = False
    
    # Ensure screen is off at startup
    screen_power(False)

    try:
        while True:
            btn_state = GPIO.input(GPIO_PIN) == GPIO.LOW
            
            if btn_state and not screen_state:
                # Start playback
                screen_state = True
                current_process = play_video(videos)
                time.sleep(1.5)
                screen_power(True)
                
            elif not btn_state and screen_state:
                # Stop playback
                screen_state = False
                screen_power(False)
                stop_video(current_process)
                current_process = None

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

