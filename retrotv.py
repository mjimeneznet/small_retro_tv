import os
import random
import time
import subprocess
from subprocess import Popen, PIPE
from RPi import GPIO
import signal

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Directory to search for videos
VIDEO_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'videos')
VIDEO_EXTENSIONS = ('.avi', '.mov', '.mp4', '.mkv')

def get_videos(directory):
    """
    Retrieve a list of video files from the specified directory and its subdirectories.
    """
    video_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(VIDEO_EXTENSIONS):
                video_files.append(os.path.join(root, file))
    return video_files

def play_video(video):
    """
    Play a single video using omxplayer.
    """
    try:
        print("Playing video: {}".format(video))
        play_process = Popen(['omxplayer', '--no-osd', '--aspect-mode', 'fill', video], preexec_fn=os.setsid)
        return play_process
    except OSError as e:
        print("Error playing video {}: {}".format(video, e))
        return None

def stop_video(play_process):
    """
    Stop the currently playing video.
    """
    if play_process:
        print("Stopping video...")
        os.killpg(os.getpgid(play_process.pid), signal.SIGTERM)
        play_process.wait()
        print("Video stopped.")

def turn_on_screen():
    """
    Turns on the screen and pauses playback using dbuscontrol.
    """
    try:
        subprocess.call('vcgencmd display_power 1', shell=True)
        print("Screen turned ON.")
    except Exception as e:
        print("Error turning on the screen: {}".format(e))

def turn_off_screen():
    """
    Turns off the screen and pauses playback using dbuscontrol.
    """
    try:
        subprocess.call('vcgencmd display_power 0', shell=True)
        print("Screen turned OFF.")
    except Exception as e:
        print("Error turning off the screen: {}".format(e))

def main():
    """
    Main loop: Waits for a button press and plays videos.
    """
    turn_off_screen()  # Ensure the screen starts off
    screen_on = False
    play_process = None
    videos = get_videos(VIDEO_DIR)

    try:
        while True:
            button_pressed = not GPIO.input(26)
            time.sleep(0.3)  # Debounce delay
            if button_pressed != screen_on:
                screen_on = button_pressed
                if screen_on:
                    print("Button pressed! Playing a random video...")
                    turn_on_screen()
                    if videos:
                        video = random.choice(videos)
                        play_process = play_video(video)
                else:
                    print("Button released! Stopping video...")
                    turn_off_screen()
                    stop_video(play_process)
                    play_process = None
            elif screen_on and play_process and play_process.poll() is not None:
                # Video finished, play another random one
                print("Video finished! Playing another random video...")
                video = random.choice(videos)
                play_process = play_video(video)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        if play_process:
            stop_video(play_process)
        GPIO.cleanup()
        print("GPIO pins cleaned up.")

if __name__ == "__main__":
    main()
