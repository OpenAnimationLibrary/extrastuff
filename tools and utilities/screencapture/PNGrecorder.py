#This script authored by Rodney Baker and licensed CC-0.  For more information please see: <http://creativecommons.org/publicdomain/zero/1.0/>
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import time
import os
import sys
from datetime import datetime
import mss
import mss.tools
import queue
import configparser
from pynput import mouse

class PNGRecorder:
    MAX_FRAMES = 9999  # Maximum number of frames per sequence

    def __init__(self, root):
        self.root = root
        self.root.title("PNG Screen Recorder")
        self.is_recording = False
        self.is_paused = False
        self.recording_thread = None
        self.frame_count = 0
        self.current_prefix = ""
        self.script_dir = self.get_script_directory()

        # Initialize the message queue
        self.queue = queue.Queue()

        # Initialize the list to track recorded files
        self.recorded_files = []

        # Load settings
        self.load_settings()

        # Create GUI elements
        self.create_widgets()

        # Start the queue processing loop
        self.process_queue()

        # Initialize mouse listener
        self.mouse_listener = None

    def get_script_directory(self):
        """
        Returns the directory where the script is located.
        """
        if getattr(sys, 'frozen', False):
            # If the application is frozen (e.g., packaged with PyInstaller)
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        return script_dir

    def load_settings(self):
        """
        Loads settings from recordingsettings.ini. If the file doesn't exist, creates it with default settings.
        """
        self.config = configparser.ConfigParser()
        self.settings_file = os.path.join(self.script_dir, 'recordingsettings.ini')
        
        if os.path.exists(self.settings_file):
            self.config.read(self.settings_file)
            self.output_directory = self.config.get('Settings', 'output_directory', fallback=self.script_dir)
            self.frame_interval = self.config.getint('Settings', 'frame_interval', fallback=100)
            self.output_prefix = self.config.get('Settings', 'output_prefix', fallback='recording')
            self.event_driven = self.config.getboolean('Settings', 'event_driven', fallback=False)
            self.frames_to_remove = self.config.getint('Settings', 'frames_to_remove', fallback=5)
        else:
            # Create default settings
            self.output_directory = self.script_dir
            self.frame_interval = 100  # Default 100 ms
            self.output_prefix = 'recording'
            self.event_driven = False
            self.frames_to_remove = 5
            self.save_settings()

    def save_settings(self):
        """
        Saves current settings to recordingsettings.ini.
        """
        if not self.config.has_section('Settings'):
            self.config.add_section('Settings')
        self.config.set('Settings', 'output_directory', self.output_directory)
        self.config.set('Settings', 'frame_interval', str(self.frame_interval))
        self.config.set('Settings', 'output_prefix', self.output_prefix)
        self.config.set('Settings', 'event_driven', str(self.event_driven))
        self.config.set('Settings', 'frames_to_remove', str(self.frames_to_remove))
        
        with open(self.settings_file, 'w') as configfile:
            self.config.write(configfile)

    def create_widgets(self):
        padding_options = {'padx': 10, 'pady': 5}

        # Frame Interval Label and Entry
        interval_frame = tk.Frame(self.root)
        interval_frame.pack(fill=tk.X, **padding_options)

        interval_label = tk.Label(interval_frame, text="Frame Interval (ms):")
        interval_label.pack(side=tk.LEFT)

        self.interval_entry = tk.Entry(interval_frame)
        self.interval_entry.insert(0, str(self.frame_interval))
        self.interval_entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        self.interval_entry.bind("<FocusOut>", self.update_frame_interval)

        # Output Filename Prefix Label and Entry
        output_frame = tk.Frame(self.root)
        output_frame.pack(fill=tk.X, **padding_options)

        output_label = tk.Label(output_frame, text="Output Filename Prefix:")
        output_label.pack(side=tk.LEFT)

        self.output_entry = tk.Entry(output_frame)
        self.output_entry.insert(0, self.output_prefix)
        self.output_entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        self.output_entry.bind("<FocusOut>", self.update_output_prefix)

        # Output Directory Label and Entry with Browse Button
        directory_frame = tk.Frame(self.root)
        directory_frame.pack(fill=tk.X, **padding_options)

        directory_label = tk.Label(directory_frame, text="Output Directory:")
        directory_label.pack(side=tk.LEFT)

        self.directory_entry = tk.Entry(directory_frame, width=50)
        self.directory_entry.insert(0, self.output_directory)
        self.directory_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        browse_button = tk.Button(directory_frame, text="Browse", command=self.browse_output_directory)
        browse_button.pack(side=tk.RIGHT)

        # Frames to Remove Label and Entry
        remove_frame = tk.Frame(self.root)
        remove_frame.pack(fill=tk.X, **padding_options)

        remove_label = tk.Label(remove_frame, text="Frames to Remove at End:")
        remove_label.pack(side=tk.LEFT)

        self.remove_entry = tk.Entry(remove_frame)
        self.remove_entry.insert(0, str(self.frames_to_remove))
        self.remove_entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        self.remove_entry.bind("<FocusOut>", self.update_frames_to_remove)

        # Event-Driven Capture Checkbox
        event_frame = tk.Frame(self.root)
        event_frame.pack(fill=tk.X, **padding_options)

        self.event_var = tk.BooleanVar(value=self.event_driven)
        event_checkbox = tk.Checkbutton(event_frame, text="Event-Driven Capture (Mouse Down)", variable=self.event_var, command=self.toggle_event_driven)
        event_checkbox.pack(side=tk.LEFT)

        # Start/Resume and Pause Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, **padding_options)

        self.start_button = tk.Button(
            button_frame, 
            text="Start Recording", 
            command=self.start_or_resume_recording, 
            bg="green", 
            fg="white",
            width=20,
            height=2
        )
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.pause_button = tk.Button(
            button_frame, 
            text="Pause Recording", 
            command=self.pause_recording, 
            bg="orange", 
            fg="white", 
            state=tk.DISABLED,
            width=20,
            height=2
        )
        self.pause_button.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5)

        # Stop Button
        stop_button_frame = tk.Frame(self.root)
        stop_button_frame.pack(fill=tk.X, **padding_options)

        self.stop_button = tk.Button(
            stop_button_frame, 
            text="Stop Recording", 
            command=self.stop_recording, 
            bg="red", 
            fg="white", 
            state=tk.DISABLED,
            width=42,  # Span both Start and Pause buttons
            height=2
        )
        self.stop_button.pack(fill=tk.X, padx=5)

        # Status Labels
        status_frame = tk.Frame(self.root)
        status_frame.pack(fill=tk.X, **padding_options)

        self.status_label = tk.Label(status_frame, text="Status: Not Recording", fg="blue")
        self.status_label.pack(anchor='w')

        self.frame_label = tk.Label(status_frame, text="Frames Captured: 0", fg="black")
        self.frame_label.pack(anchor='w')

    def update_frame_interval(self, event):
        """
        Updates the frame interval based on user input and saves the setting.
        """
        try:
            interval = int(self.interval_entry.get())
            if interval <= 0:
                raise ValueError
            self.frame_interval = interval
            self.save_settings()
        except ValueError:
            messagebox.showerror("Invalid Interval", "Please enter a valid positive integer for frame interval.")
            self.interval_entry.delete(0, tk.END)
            self.interval_entry.insert(0, str(self.frame_interval))

    def update_output_prefix(self, event):
        """
        Updates the output filename prefix based on user input and saves the setting.
        """
        prefix = self.output_entry.get().strip()
        if prefix:
            self.output_prefix = prefix
            self.save_settings()
        else:
            messagebox.showerror("Invalid Prefix", "Output filename prefix cannot be empty.")
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, self.output_prefix)

    def update_frames_to_remove(self, event):
        """
        Updates the number of frames to remove at the end based on user input and saves the setting.
        """
        try:
            frames = int(self.remove_entry.get())
            if frames < 0:
                raise ValueError
            self.frames_to_remove = frames
            self.save_settings()
        except ValueError:
            messagebox.showerror("Invalid Number", "Please enter a valid non-negative integer for frames to remove.")
            self.remove_entry.delete(0, tk.END)
            self.remove_entry.insert(0, str(self.frames_to_remove))

    def browse_output_directory(self):
        """
        Opens a dialog for the user to select the output directory.
        """
        selected_directory = filedialog.askdirectory(initialdir=self.output_directory, title="Select Output Directory")
        if selected_directory:
            self.output_directory = selected_directory
            self.directory_entry.delete(0, tk.END)
            self.directory_entry.insert(0, self.output_directory)
            self.save_settings()

    def toggle_event_driven(self):
        """
        Toggles event-driven capture mode based on the checkbox state.
        """
        self.event_driven = self.event_var.get()
        self.save_settings()

    def start_or_resume_recording(self):
        if not self.is_recording and not self.is_paused:
            # Start a new recording with countdown
            self.start_countdown()
        elif self.is_recording and self.is_paused:
            # Resume the paused recording
            self.resume_recording()

    def start_countdown(self, count=10):
        """
        Starts a countdown before beginning the recording.
        """
        if count > 0:
            self.queue.put(("status", f"Recording starts in: {count}", "blue"))
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.DISABLED)
            self.root.after(1000, self.start_countdown, count - 1)
        else:
            self.start_recording()

    def start_recording(self):
        # Validate and get frame interval
        try:
            interval = int(self.interval_entry.get())
            if interval <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Interval", "Please enter a valid positive integer for frame interval.")
            self.queue.put(("status", "Not Recording", "blue"))
            self.queue.put(("start_button_text", "Start Recording"))
            self.start_button.config(state=tk.NORMAL)
            return

        # Get output filename prefix
        output_prefix = self.output_entry.get().strip()
        if not output_prefix:
            output_prefix = self.output_prefix

        # Initialize the first prefix with timestamp
        self.current_prefix = self.generate_prefix(output_prefix)
        
        # Initialize recording parameters
        self.is_recording = True
        self.is_paused = False
        self.frame_count = 0
        self.recorded_files = []  # Reset recorded files list
        self.queue.put(("status", "Recording...", "red"))
        self.queue.put(("frame_count", self.frame_count))

        # Update button states
        self.queue.put(("start_button_text", "Resume Recording"))
        self.queue.put(("pause_button_text", "Pause Recording"))
        self.queue.put(("start_button_state", "disabled"))
        self.queue.put(("pause_button_state", "normal"))
        self.queue.put(("stop_button_state", "normal"))

        # Start the recording thread
        if self.event_driven:
            self.start_mouse_listener()
        else:
            self.recording_thread = threading.Thread(
                target=self.record_screen, 
                args=(self.frame_interval,),
                daemon=True  # Ensure thread exits when main program does
            )
            self.recording_thread.start()

    def pause_recording(self):
        if self.is_recording and not self.is_paused:
            self.is_paused = True
            self.queue.put(("status", "Paused", "orange"))
            self.queue.put(("pause_button_text", "Resume Recording"))
            self.queue.put(("start_button_state", "normal"))

            # Stop mouse listener if event-driven
            if self.event_driven and self.mouse_listener is not None:
                self.mouse_listener.stop()
                self.mouse_listener = None

    def resume_recording(self):
        if self.is_recording and self.is_paused:
            self.is_paused = False
            self.queue.put(("status", "Recording...", "red"))
            self.queue.put(("pause_button_text", "Pause Recording"))
            self.queue.put(("start_button_state", "disabled"))

            # Restart mouse listener if event-driven
            if self.event_driven:
                self.start_mouse_listener()
            else:
                if self.recording_thread is None or not self.recording_thread.is_alive():
                    self.recording_thread = threading.Thread(
                        target=self.record_screen, 
                        args=(self.frame_interval,),
                        daemon=True  # Ensure thread exits when main program does
                    )
                    self.recording_thread.start()

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.is_paused = False
        self.queue.put(("status", "Stopping Recording...", "orange"))
        self.queue.put(("pause_button_state", "disabled"))
        self.queue.put(("start_button_state", "disabled"))

        # Stop mouse listener if event-driven
        if self.event_driven and self.mouse_listener is not None:
            self.mouse_listener.stop()
            self.mouse_listener = None

        # Wait for the recording thread to finish
        if self.recording_thread is not None:
            self.recording_thread.join()
            self.recording_thread = None

        # Remove the last X frames to avoid unwanted end frames
        self.remove_last_x_frames(self.frames_to_remove)

        # Inform the user of completion
        self.queue.put(("messagebox", "Recording Complete", f"Screen recording saved in:\n{self.output_directory}"))
        self.queue.put(("status", "Not Recording", "blue"))
        self.queue.put(("frame_count", 0))

        # Re-enable start button and reset its text
        self.queue.put(("start_button_text", "Start Recording"))
        self.queue.put(("start_button_state", "normal"))

    def remove_last_x_frames(self, x):
        """
        Removes the last x frames from the recorded_files list and deletes the corresponding PNG files.
        """
        if len(self.recorded_files) >= x:
            frames_to_remove = self.recorded_files[-x:]
            self.recorded_files = self.recorded_files[:-x]
        else:
            frames_to_remove = self.recorded_files
            self.recorded_files = []

        for file in frames_to_remove:
            try:
                os.remove(file)
                print(f"Removed unwanted frame: {file}")
            except Exception as e:
                print(f"Error removing file {file}: {e}")

    def record_screen(self, interval):
        """
        Recording loop for timed capture.
        """
        with mss.mss() as sct:
            # Define the monitor to capture (primary monitor)
            monitor = sct.monitors[1]
            monitor_area = {
                "top": monitor["top"],
                "left": monitor["left"],
                "width": monitor["width"],
                "height": monitor["height"]
            }

            while self.is_recording:
                if self.is_paused:
                    time.sleep(0.1)  # Sleep briefly to reduce CPU usage while paused
                    continue

                # If event-driven, skip timed capture
                if self.event_driven:
                    time.sleep(0.1)
                    continue

                filename = os.path.join(self.output_directory, f"{self.current_prefix}.{self.frame_count:04d}.png")

                # Capture the screen
                try:
                    print(f"Capturing frame {self.frame_count} to {filename}")
                    sct_img = sct.grab(monitor_area)
                    mss.tools.to_png(sct_img.rgb, sct_img.size, output=filename)
                    self.frame_count += 1
                    self.recorded_files.append(filename)
                    self.queue.put(("frame_count", self.frame_count))

                    # Check if frame_count exceeds MAX_FRAMES
                    if self.frame_count > self.MAX_FRAMES:
                        # Reset frame_count and generate a new prefix
                        self.frame_count = 0
                        self.current_prefix = self.generate_prefix(self.output_prefix)
                        print(f"Sequence limit reached. New prefix: {self.current_prefix}")

                except Exception as e:
                    print(f"Error capturing screen: {e}")
                    self.queue.put(("status", "Error during recording", "red"))
                    self.queue.put(("messagebox_error", "Recording Error", f"An error occurred while capturing the screen:\n{e}"))
                    self.is_recording = False
                    self.is_paused = False
                    break

                # Wait for the specified interval
                time.sleep(interval / 1000.0)

    def generate_prefix(self, base_prefix):
        """
        Generates a unique prefix by appending the current date and time.
        Format: base_prefix_YYYYMMDD_HHMMSS
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_prefix = f"{base_prefix}_{timestamp}"
        return unique_prefix

    def update_status(self, text, color=None):
        if color:
            self.status_label.config(text=f"Status: {text}", fg=color)
        else:
            self.status_label.config(text=f"Status: {text}")

    def update_frame_count_label(self, count):
        self.frame_label.config(text=f"Frames Captured: {count}")

    def process_queue(self):
        """
        Processes messages from the recording thread to update the GUI.
        """
        try:
            while True:
                message = self.queue.get_nowait()
                if message[0] == "status":
                    self.update_status(message[1], message[2] if len(message) > 2 else None)
                elif message[0] == "frame_count":
                    self.update_frame_count_label(message[1])
                elif message[0] == "pause_button_text":
                    self.pause_button.config(text=message[1])
                elif message[0] == "start_button_text":
                    self.start_button.config(text=message[1])
                elif message[0] == "pause_button_state":
                    self.pause_button.config(state=message[1])
                elif message[0] == "start_button_state":
                    self.start_button.config(state=message[1])
                elif message[0] == "stop_button_state":
                    self.stop_button.config(state=message[1])
                elif message[0] == "messagebox":
                    messagebox.showinfo(message[1], message[2])
                elif message[0] == "messagebox_error":
                    messagebox.showerror(message[1], message[2])
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)  # Check the queue every 100 ms

    def cleanup(self):
        """
        Cleans up resources when closing the application.
        """
        if self.is_recording:
            self.is_recording = False
            self.is_paused = False
            if self.recording_thread is not None:
                self.recording_thread.join()
            # Stop mouse listener if event-driven
            if self.event_driven and self.mouse_listener is not None:
                self.mouse_listener.stop()
                self.mouse_listener = None

    def on_closing(self):
        if self.is_recording:
            if messagebox.askokcancel("Quit", "Recording is in progress. Do you want to quit?"):
                self.cleanup()
                self.root.destroy()
        else:
            self.root.destroy()

    # Event-Driven Capture Methods
    def start_mouse_listener(self):
        """
        Starts the mouse listener to capture frames on mouse down events.
        """
        self.mouse_listener = mouse.Listener(
            on_click=self.on_mouse_event
        )
        self.mouse_listener.start()

    def on_mouse_event(self, x, y, button, pressed):
        """
        Callback function for mouse click events to trigger screen capture on mouse down.
        """
        if pressed and self.is_recording and not self.is_paused:
            self.capture_frame()

    def capture_frame(self):
        """
        Captures a single frame and updates the frame count.
        """
        with mss.mss() as sct:
            try:
                # Define the monitor to capture (primary monitor)
                monitor = sct.monitors[1]
                monitor_area = {
                    "top": monitor["top"],
                    "left": monitor["left"],
                    "width": monitor["width"],
                    "height": monitor["height"]
                }

                filename = os.path.join(self.output_directory, f"{self.current_prefix}.{self.frame_count:04d}.png")
                print(f"Capturing frame {self.frame_count} to {filename}")
                sct_img = sct.grab(monitor_area)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=filename)
                self.frame_count += 1
                self.recorded_files.append(filename)
                self.queue.put(("frame_count", self.frame_count))

                # Check if frame_count exceeds MAX_FRAMES
                if self.frame_count > self.MAX_FRAMES:
                    # Reset frame_count and generate a new prefix
                    self.frame_count = 0
                    self.current_prefix = self.generate_prefix(self.output_prefix)
                    print(f"Sequence limit reached. New prefix: {self.current_prefix}")

            except Exception as e:
                print(f"Error capturing screen: {e}")
                self.queue.put(("status", "Error during recording", "red"))
                self.queue.put(("messagebox_error", "Recording Error", f"An error occurred while capturing the screen:\n{e}"))
                self.is_recording = False
                self.is_paused = False
                if self.event_driven and self.mouse_listener is not None:
                    self.mouse_listener.stop()
                    self.mouse_listener = None

def main():
    root = tk.Tk()
    app = PNGRecorder(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
