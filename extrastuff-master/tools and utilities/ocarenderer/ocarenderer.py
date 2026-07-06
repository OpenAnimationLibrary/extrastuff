#OCA (Open Cel Animation) file render demonstration
import json
import os
import shutil
import sys
from PIL import Image, ImageChops, ImageTk
import imageio
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import threading
import gc
import logging
import numpy as np
import subprocess
import platform
import queue

# Configure logging to output to both console and a log file
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("oca_processor.log"),
        logging.StreamHandler()
    ]
)

def load_oca_file(filepath):
    """
    Load and parse the OCA JSON file.

    Args:
        filepath (str): Path to the OCA JSON file.

    Returns:
        dict: Parsed OCA data.

    Raises:
        ValueError: If the JSON is invalid or cannot be loaded.
    """
    try:
        with open(filepath, 'r') as file:
            oca_data = json.load(file)
        return oca_data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    except Exception as e:
        raise ValueError(f"Error loading OCA file: {e}")

def calculate_total_frames(end_time, frame_rate):
    """
    Calculate the total number of frames based on end time and frame rate.

    Args:
        end_time (float): The end time of the animation in seconds.
        frame_rate (float): The frame rate (frames per second).

    Returns:
        int: Total number of frames.

    Raises:
        ValueError: If end_time or frame_rate is invalid.
    """
    try:
        total_frames = int(end_time * frame_rate)
        if total_frames <= 0:
            raise ValueError("Total frames calculated is zero or negative.")
        return total_frames
    except TypeError:
        raise ValueError("Invalid endTime or frameRate in OCA file.")

def map_layer_frames(oca_data, total_frames):
    """
    Map each layer to its corresponding frames for the entire animation duration.

    Args:
        oca_data (dict): Parsed OCA data.
        total_frames (int): Total number of frames in the animation.

    Returns:
        list: Mappings of layers to their frames.

    Raises:
        ValueError: If no valid layers are found.
    """
    layer_mappings = []
    for layer in oca_data.get('layers', []):
        try:
            frames = layer.get('frames', [])
            if not frames:
                logging.warning(f"Layer '{layer.get('name', 'Unnamed')}' has no frames. Skipping.")
                continue

            mapping = []
            current_frame_index = 0
            frame_duration_counter = 0

            for frame_number in range(total_frames):
                if current_frame_index >= len(frames):
                    # Repeat the last frame if out of frames
                    mapping.append(frames[-1])
                else:
                    current_frame = frames[current_frame_index]
                    mapping.append(current_frame)
                    frame_duration_counter += 1

                    if frame_duration_counter >= current_frame.get('duration', 1):
                        current_frame_index += 1
                        frame_duration_counter = 0

            layer_mappings.append({
                'layer': layer,
                'frames': mapping
            })
        except Exception as e:
            logging.warning(f"Error mapping frames for layer '{layer.get('name', 'Unnamed')}': {e}")
            continue

    if not layer_mappings:
        raise ValueError("No valid layers found in OCA file.")

    return layer_mappings

def apply_opacity(image, opacity):
    """
    Apply opacity to an image.

    Args:
        image (PIL.Image.Image): The image to modify.
        opacity (float): Opacity level between 0 and 1.

    Returns:
        PIL.Image.Image: The image with adjusted opacity.
    """
    try:
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        alpha = image.split()[3]
        alpha = alpha.point(lambda p: p * opacity)
        image.putalpha(alpha)
        return image
    except Exception as e:
        logging.warning(f"Error applying opacity: {e}")
        return image

def paste_image_onto_canvas(canvas, image, position, opacity, blending_mode='normal'):
    """
    Paste an image onto the canvas with specified opacity and blending mode.

    Args:
        canvas (PIL.Image.Image): The base canvas image.
        image (PIL.Image.Image): The image to paste.
        position (list): [x_center, y_center] position on the canvas.
        opacity (float): Opacity level between 0 and 1.
        blending_mode (str): Blending mode to apply.

    Returns:
        None
    """
    try:
        image = apply_opacity(image, opacity)
        img_width, img_height = image.size
        x_center, y_center = position
        top_left = (int(x_center - img_width / 2), int(y_center - img_height / 2))

        if blending_mode == 'normal':
            canvas.paste(image, top_left, image)
        elif blending_mode == 'multiply':
            # Extract the region from the canvas
            region = canvas.crop((top_left[0], top_left[1], top_left[0] + img_width, top_left[1] + img_height))
            blended = ImageChops.multiply(region, image)
            canvas.paste(blended, top_left)
        elif blending_mode == 'screen':
            region = canvas.crop((top_left[0], top_left[1], top_left[0] + img_width, top_left[1] + img_height))
            blended = ImageChops.screen(region, image)
            canvas.paste(blended, top_left)
        else:
            logging.warning(f"Unsupported blending mode '{blending_mode}'. Using 'normal' mode.")
            canvas.paste(image, top_left, image)
    except Exception as e:
        logging.warning(f"Error pasting image onto canvas: {e}")

def composite_frames(oca_data, layer_mappings, total_frames, background_color, oca_dir, progress_callback=None, thumbnail=False):
    """
    Composite all frames based on the OCA data and layer mappings.

    Args:
        oca_data (dict): Parsed OCA data.
        layer_mappings (list): Mappings of layers to their frames.
        total_frames (int): Total number of frames in the animation.
        background_color (list): Background color in [R, G, B, A] format.
        oca_dir (str): Directory of the OCA file for relative paths.
        progress_callback (function, optional): Callback to update progress.
        thumbnail (bool): Flag to indicate if generating thumbnail.

    Returns:
        list: List of composited frames as PIL.Image.Image objects.

    Raises:
        ValueError: If no frames are successfully processed.
    """
    width = oca_data.get('width', 1920)
    height = oca_data.get('height', 1080)
    frames = []

    # Convert background color from [0-1] to [0-255]
    try:
        bg_color = tuple([int(max(0, min(c, 1)) * 255) for c in background_color[:3]] + [int(max(0, min(background_color[3], 1)) * 255)])
    except Exception as e:
        logging.warning(f"Invalid backgroundColor format. Using white background. Error: {e}")
        bg_color = (255, 255, 255, 255)

    frame_step = 1  # Default: process every frame
    max_thumbnail_frames = 10  # Limit number of frames for thumbnail

    if thumbnail:
        # Reduce the number of frames and resolution for thumbnail
        frame_step = max(1, total_frames // max_thumbnail_frames)
        thumbnail_size = (320, 180)  # Reduced resolution
    else:
        thumbnail_size = (width, height)

    # Determine resampling filter
    if hasattr(Image, 'Resampling'):
        resample_filter = Image.Resampling.LANCZOS
    else:
        resample_filter = Image.LANCZOS  # For older Pillow versions

    for frame_number in range(total_frames):
        if thumbnail and (frame_number % frame_step != 0):
            continue  # Skip frames for thumbnail

        try:
            # Create a new transparent canvas with reduced size if thumbnail
            if thumbnail:
                canvas = Image.new('RGBA', thumbnail_size, bg_color)
            else:
                canvas = Image.new('RGBA', (width, height), bg_color)

            for layer_mapping in layer_mappings:
                layer = layer_mapping['layer']
                frame_info = layer_mapping['frames'][frame_number]

                if not layer.get('visible', True):
                    continue  # Skip invisible layers

                file_path = frame_info.get('fileName')
                if not file_path:
                    logging.warning(f"Frame {frame_number} in layer '{layer.get('name', 'Unnamed')}' has no fileName. Skipping.")
                    continue

                # Resolve the file path relative to the OCA file's directory
                if not os.path.isabs(file_path):
                    file_path = os.path.join(oca_dir, file_path)

                layer_opacity = layer.get('opacity', 1.0) * frame_info.get('opacity', 1.0)
                layer_opacity = max(0.0, min(layer_opacity, 1.0))  # Clamp between 0 and 1

                # Load the image
                if not os.path.isfile(file_path):
                    logging.warning(f"File '{file_path}' not found. Please verify the file path. Skipping this frame.")
                    continue

                try:
                    image = Image.open(file_path).convert('RGBA')
                except Exception as e:
                    logging.warning(f"Error loading image '{file_path}': {e}. Skipping this frame.")
                    continue

                # Get position
                position = frame_info.get('position', layer.get('position', [width // 2, height // 2]))
                if not isinstance(position, list) or len(position) != 2:
                    logging.warning(f"Invalid position format in frame {frame_number} of layer '{layer.get('name', 'Unnamed')}'. Using center.")
                    position = [width // 2, height // 2]

                # Get blending mode
                blending_mode = layer.get('blendingMode', 'normal')

                # Resize image if generating thumbnail
                if thumbnail:
                    image = image.resize(thumbnail_size, resample=resample_filter)

                # Paste onto canvas with blending mode
                paste_image_onto_canvas(canvas, image, position, layer_opacity, blending_mode=blending_mode)

            # Convert canvas to RGBA
            final_frame = canvas.convert('RGBA')
            frames.append(final_frame)

            # Update progress
            if progress_callback and not thumbnail:
                progress_callback(frame_number + 1, total_frames)

            # Clean up
            del canvas
            del image
            gc.collect()

        except Exception as e:
            logging.warning(f"Error processing frame {frame_number}: {e}")
            continue

    if not frames:
        raise ValueError("No frames were successfully processed.")

    return frames

def save_as_gif(frames, output_path, frame_rate):
    """
    Save the composited frames as a GIF.

    Args:
        frames (list): List of PIL.Image.Image objects.
        output_path (str): Path to save the GIF.
        frame_rate (float): Frames per second.

    Raises:
        ValueError: If saving fails.
    """
    try:
        frame_duration = max(1, int(1000 / frame_rate))  # Duration per frame in milliseconds
        frames_rgb = [frame.convert('P', palette=Image.ADAPTIVE) for frame in frames]  # Convert to palette mode for GIF
        frames_rgb[0].save(
            output_path,
            save_all=True,
            append_images=frames_rgb[1:],
            duration=frame_duration,
            loop=0
        )
        logging.info(f"GIF saved to {output_path}")
    except Exception as e:
        raise ValueError(f"Error saving GIF: {e}")

def save_as_video(frames, output_path, frame_rate):
    """
    Save the composited frames as an MP4 video.

    Args:
        frames (list): List of PIL.Image.Image objects.
        output_path (str): Path to save the MP4 video.
        frame_rate (float): Frames per second.

    Raises:
        ValueError: If saving fails.
    """
    try:
        # Convert PIL Images to NumPy arrays
        frames_np = []
        for idx, frame in enumerate(frames):
            try:
                frame_rgb = frame.convert('RGB')  # Ensure RGB mode
                frame_np = np.array(frame_rgb)
                logging.info(f"Frame {idx} shape: {frame_np.shape}")
                frames_np.append(frame_np)
            except Exception as e:
                logging.warning(f"Error converting frame {idx} to NumPy array: {e}. Skipping.")
                continue

        if not frames_np:
            raise ValueError("No frames were converted to NumPy arrays.")

        # Verify all frames have the same shape
        first_shape = frames_np[0].shape
        for idx, frame_np in enumerate(frames_np):
            if frame_np.shape != first_shape:
                raise ValueError(f"Frame {idx} has shape {frame_np.shape}, which does not match the first frame's shape {first_shape}.")

        # Save the video using imageio
        imageio.mimsave(output_path, frames_np, fps=frame_rate)
        logging.info(f"Video saved to {output_path}")
    except Exception as e:
        raise ValueError(f"Error saving video: {e}")

def create_backup(original_filepath):
    """
    Create a backup of the original OCA file by appending an incremental number.

    Args:
        original_filepath (str): Path to the original OCA file.

    Returns:
        str: Path to the created backup file.
    """
    directory, filename = os.path.split(original_filepath)
    name, ext = os.path.splitext(filename)
    backup_index = 1
    while True:
        backup_filename = f"{name}_backup{backup_index}{ext}"
        backup_filepath = os.path.join(directory, backup_filename)
        if not os.path.exists(backup_filepath):
            shutil.copy(original_filepath, backup_filepath)
            logging.info(f"Backup created: {backup_filepath}")
            return backup_filepath
        backup_index += 1

def open_file(file_path):
    """
    Open a file with the default application based on the operating system.

    Args:
        file_path (str): Path to the file to open.

    Returns:
        None

    Raises:
        None: Errors are handled internally and logged.
    """
    try:
        if platform.system() == 'Darwin':       # macOS
            subprocess.call(['open', file_path])
        elif platform.system() == 'Windows':    # Windows
            os.startfile(file_path)
        else:                                   # Linux and others
            subprocess.call(['xdg-open', file_path])
        logging.info(f"Opened file: {file_path}")
    except Exception as e:
        logging.error(f"Failed to open file '{file_path}': {e}")
        messagebox.showerror("Error", f"Failed to open the output file:\n{e}")

class OCAProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OCA Processor")
        self.fullscreen = True  # Track full-screen state
        self.root.attributes('-fullscreen', True)  # Set to full screen
        self.root.bind("<Escape>", self.exit_fullscreen)  # Bind Escape key to exit full screen

        # Initialize variables
        self.oca_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.output_format = tk.StringVar(value='gif')
        self.processing = False

        # Thumbnail related variables
        self.thumbnail_frames_queue = queue.Queue()
        self.thumbnail_photoimages = []
        self.current_thumbnail_frame = 0
        self.thumbnail_running = False

        # Create Menu
        self.create_menu()

        # Create Main Paned Window
        self.create_main_paned_window()

        # Start the periodic check for thumbnail frames
        self.root.after(100, self.check_thumbnail_queue)

    def create_menu(self):
        """
        Create the application menu bar with File options.
        """
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open OCA File", command=self.open_oca_file)
        file_menu.add_command(label="Save OCA File", command=self.save_oca_file)
        file_menu.add_command(label="Save As", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Toggle Full Screen", command=self.toggle_fullscreen)
        file_menu.add_command(label="Restart", command=self.restart_program)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

    def create_main_paned_window(self):
        """
        Create the main paned window dividing the text editor and control panels.
        """
        paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # Left Pane: Text Editor
        editor_frame = ttk.Frame(paned_window, padding=10)
        paned_window.add(editor_frame, weight=3)

        editor_label = ttk.Label(editor_frame, text="OCA JSON Editor:")
        editor_label.pack(anchor=tk.W)

        # Add Scrollbars to Text Widget
        text_scroll_y = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL)
        text_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        text_scroll_x = ttk.Scrollbar(editor_frame, orient=tk.HORIZONTAL)
        text_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.text_editor = tk.Text(editor_frame, wrap=tk.NONE, undo=True,
                                   yscrollcommand=text_scroll_y.set,
                                   xscrollcommand=text_scroll_x.set)
        self.text_editor.pack(fill=tk.BOTH, expand=True)

        text_scroll_y.config(command=self.text_editor.yview)
        text_scroll_x.config(command=self.text_editor.xview)

        # Right Pane: Controls and Thumbnail
        controls_frame = ttk.Frame(paned_window, padding=10)
        paned_window.add(controls_frame, weight=1)

        # Output File Selection
        output_label = ttk.Label(controls_frame, text="Output File:")
        output_label.pack(anchor=tk.W, pady=(0, 5))
        self.output_entry = ttk.Entry(controls_frame, textvariable=self.output_file_path, width=50, state='readonly')
        self.output_entry.pack(fill=tk.X, pady=(0, 10))

        output_button = ttk.Button(controls_frame, text="Browse...", command=self.save_as)
        output_button.pack(anchor=tk.E, pady=(0, 10))

        # Output Format Selection
        format_label = ttk.Label(controls_frame, text="Output Format:")
        format_label.pack(anchor=tk.W, pady=(0, 5))
        format_frame = ttk.Frame(controls_frame)
        format_frame.pack(anchor=tk.W, pady=(0, 10))

        ttk.Radiobutton(format_frame, text='GIF', variable=self.output_format, value='gif').pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(format_frame, text='MP4', variable=self.output_format, value='mp4').pack(side=tk.LEFT)

        # Process Button
        self.process_button = ttk.Button(controls_frame, text="Process OCA", command=self.process_oca)
        self.process_button.pack(anchor=tk.E, pady=(10, 10))

        # Progress Bar
        self.progress = ttk.Progressbar(controls_frame, orient='horizontal', mode='determinate', length=200)
        self.progress.pack(fill=tk.X, pady=(10, 10))

        # Status Message
        self.status_message = tk.StringVar()
        self.status_label = ttk.Label(controls_frame, textvariable=self.status_message, foreground="blue")
        self.status_label.pack(anchor=tk.W, pady=(5, 0))

        # Separator
        separator = ttk.Separator(controls_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=10)

        # Thumbnail Preview
        thumbnail_label = ttk.Label(controls_frame, text="Thumbnail Preview:")
        thumbnail_label.pack(anchor=tk.W, pady=(0, 5))

        self.thumbnail_canvas = tk.Canvas(controls_frame, width=320, height=180, bg='black')
        self.thumbnail_canvas.pack()

        # Generate Thumbnail Button
        generate_thumbnail_button = ttk.Button(controls_frame, text="Generate Thumbnail", command=self.generate_thumbnail_manual)
        generate_thumbnail_button.pack(anchor=tk.E, pady=(5, 0))

    def open_oca_file(self):
        """
        Open an OCA or JSON file and load its content into the text editor.
        """
        file_path = filedialog.askopenfilename(
            title="Select OCA File",
            filetypes=[("OCA and JSON Files", "*.oca;*.json"), ("JSON Files", "*.json"), ("OCA Files", "*.oca"), ("All Files", "*.*")]
        )
        if file_path:
            self.oca_file_path.set(file_path)
            self.status_message.set("OCA file selected.")
            logging.info(f"Selected OCA file: {file_path}")
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                self.text_editor.delete(1.0, tk.END)
                self.text_editor.insert(tk.END, content)
                # Generate thumbnail after loading the file
                threading.Thread(target=self.generate_thumbnail_preview, daemon=True).start()
            except Exception as e:
                logging.error(f"Error reading OCA file: {e}")
                messagebox.showerror("Error", f"Failed to read OCA file:\n{e}")

    def save_oca_file(self):
        """
        Save the current content of the text editor back to the original OCA file.
        """
        if not self.oca_file_path.get():
            messagebox.showerror("Error", "No OCA file is currently loaded.")
            return
        try:
            content = self.text_editor.get(1.0, tk.END)
            with open(self.oca_file_path.get(), 'w') as file:
                file.write(content)
            self.status_message.set("OCA file saved.")
            logging.info(f"OCA file saved: {self.oca_file_path.get()}")
            # Refresh thumbnail after saving the file
            threading.Thread(target=self.generate_thumbnail_preview, daemon=True).start()
        except Exception as e:
            logging.error(f"Error saving OCA file: {e}")
            messagebox.showerror("Error", f"Failed to save OCA file:\n{e}")

    def save_as(self):
        """
        Open a dialog to save the output animation as GIF or MP4.
        """
        file_types = [
            ("GIF", "*.gif"),
            ("MP4 Video", "*.mp4"),
            ("All Files", "*.*")
        ]
        default_extension = "*.gif" if self.output_format.get() == 'gif' else "*.mp4"
        initial_dir = os.path.dirname(self.oca_file_path.get()) if self.oca_file_path.get() else "."
        file_path = filedialog.asksaveasfilename(
            title="Save Output",
            defaultextension=default_extension,
            filetypes=file_types,
            initialdir=initial_dir
        )
        if file_path:
            self.output_file_path.set(file_path)
            self.status_message.set("Output file selected.")
            logging.info(f"Selected output file: {file_path}")

    def process_oca(self):
        """
        Process the OCA file: create backup, save edits, composite frames, and save animation.
        """
        if self.processing:
            messagebox.showinfo("Processing", "Processing is already in progress.")
            return

        oca_path = self.oca_file_path.get()
        output_path = self.output_file_path.get()
        output_format = self.output_format.get()

        if not oca_path:
            messagebox.showerror("Error", "Please select an OCA file to process.")
            return
        if not output_path:
            messagebox.showerror("Error", "Please specify an output file path.")
            return

        if not os.path.isfile(oca_path):
            messagebox.showerror("Error", f"The OCA file '{oca_path}' does not exist.")
            return

        # Attempt to parse JSON to ensure it's valid
        try:
            oca_content = self.text_editor.get(1.0, tk.END)
            oca_data = json.loads(oca_content)
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON format:\n{e}")
            self.status_message.set("Processing failed.")
            return

        # Disable the process button to prevent multiple clicks
        self.process_button.config(state='disabled')
        self.processing = True
        self.status_message.set("Processing started...")
        self.progress['value'] = 0
        self.root.update_idletasks()

        # Start processing in a separate thread to keep the GUI responsive
        threading.Thread(target=self.run_processing, args=(oca_data, oca_path, output_path, output_format), daemon=True).start()

    def run_processing(self, oca_data, oca_path, output_path, output_format):
        """
        Execute the processing of the OCA file in a separate thread.

        Args:
            oca_data (dict): Parsed OCA data.
            oca_path (str): Path to the original OCA file.
            output_path (str): Path to save the output animation.
            output_format (str): Output format ('gif' or 'mp4').

        Returns:
            None
        """
        try:
            end_time = oca_data.get('endTime', 0)
            frame_rate = oca_data.get('frameRate', 12)
            total_frames = calculate_total_frames(end_time, frame_rate)
            logging.info(f"endTime: {end_time}, frameRate: {frame_rate}, total_frames: {total_frames}")

            # Map layers to frames
            layer_mappings = map_layer_frames(oca_data, total_frames)

            # Get background color
            background_color = oca_data.get('backgroundColor', [1, 1, 1, 1])

            # Determine the directory of the OCA file for relative paths
            oca_dir = os.path.dirname(oca_path)

            # Create a backup before saving changes
            backup_filepath = create_backup(oca_path)

            # Save the current content of the text editor to the OCA file
            self.save_oca_file()

            # Composite frames with progress callback
            frames = []
            composite_frames_func = composite_frames

            def progress_callback(current, total):
                progress_percent = (current / total) * 100
                self.progress['value'] = progress_percent
                self.status_message.set(f"Processing frame {current}/{total} ({progress_percent:.2f}%)")
                self.root.update_idletasks()

            frames = composite_frames_func(
                oca_data,
                layer_mappings,
                total_frames,
                background_color,
                oca_dir=oca_dir,
                progress_callback=progress_callback
            )

            # Log the number of successfully processed frames
            logging.info(f"Successfully processed {len(frames)} frames.")

            # Save the animation
            self.status_message.set("Saving the animation...")
            if output_format == 'gif':
                save_as_gif(frames, output_path, frame_rate)
            elif output_format == 'mp4':
                save_as_video(frames, output_path, frame_rate)
            else:
                messagebox.showerror("Error", f"Unsupported output format: {output_format}")
                self.reset_ui()
                return

            # Open the resulting output file
            open_file(output_path)

            # Update thumbnail after processing
            threading.Thread(target=self.generate_thumbnail_preview, daemon=True).start()

            self.status_message.set("Processing completed successfully.")
            messagebox.showinfo("Success", f"Animation saved to {output_path}")

        except ValueError as ve:
            logging.error(ve)
            messagebox.showerror("Error", str(ve))
            self.status_message.set("Processing failed.")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")
            self.status_message.set("Processing failed.")
        finally:
            self.reset_ui()

    def reset_ui(self):
        """
        Reset the UI elements after processing is complete.
        """
        self.processing = False
        self.process_button.config(state='normal')
        self.progress['value'] = 0

    def restart_program(self):
        """
        Restart the current program.
        """
        try:
            logging.info("Restarting the application...")
            self.root.destroy()  # Close the current window
            os.execl(sys.executable, sys.executable, *sys.argv)  # Relaunch the script
        except Exception as e:
            logging.error(f"Failed to restart the application: {e}")
            messagebox.showerror("Error", f"Failed to restart the application:\n{e}")

    def toggle_fullscreen(self):
        """
        Toggle full-screen mode on and off.
        """
        self.fullscreen = not self.fullscreen
        self.root.attributes('-fullscreen', self.fullscreen)
        if not self.fullscreen:
            self.root.geometry("800x600")  # Set default size when exiting full-screen
        else:
            self.root.geometry("")  # Let the window manager handle the size when entering full-screen
        logging.info(f"Full-screen mode set to {self.fullscreen}")
        self.status_message.set(f"Full-screen mode {'enabled' if self.fullscreen else 'disabled'}.")

    def exit_fullscreen(self, event=None):
        """
        Exit full-screen mode when the Escape key is pressed.
        """
        if self.fullscreen:
            self.fullscreen = False
            self.root.attributes('-fullscreen', False)
            self.root.geometry("800x600")  # Set a default window size after exiting full screen
            self.status_message.set("Full-screen mode disabled.")
            logging.info("Full-screen mode disabled via Escape key.")

    def generate_thumbnail_preview(self, from_text_editor=False):
        """
        Generate an overlay-based thumbnail preview of the OCA animation.

        Args:
            from_text_editor (bool): If True, generate thumbnail from Text Editor's current content.
                                     If False, generate from the loaded OCA file.
        """
        if from_text_editor:
            # Read from Text Editor
            oca_text = self.text_editor.get(1.0, tk.END)
            try:
                oca_data = json.loads(oca_text)
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON format in Text Editor: {e}")
                self.status_message.set("Failed to generate thumbnail: Invalid JSON format.")
                return
            oca_dir = os.path.dirname(self.oca_file_path.get()) if self.oca_file_path.get() else "."
        else:
            # Read from file
            if not self.oca_file_path.get():
                return  # No OCA file loaded
            oca_path = self.oca_file_path.get()
            try:
                oca_data = load_oca_file(oca_path)
            except Exception as e:
                logging.error(f"Error loading OCA file: {e}")
                self.status_message.set("Failed to generate thumbnail.")
                return
            oca_dir = os.path.dirname(oca_path)

        try:
            end_time = oca_data.get('endTime', 0)
            frame_rate = oca_data.get('frameRate', 12)
            total_frames = calculate_total_frames(end_time, frame_rate)
            layer_mappings = map_layer_frames(oca_data, total_frames)
            background_color = oca_data.get('backgroundColor', [1, 1, 1, 1])

            # Generate overlay composite thumbnail
            thumbnail_frame = self.overlay_composite_thumbnail(
                oca_data,
                layer_mappings,
                background_color,
                oca_dir=oca_dir
            )

            # Put the thumbnail into the queue to be processed by the main thread
            self.thumbnail_frames_queue.put([thumbnail_frame])

            logging.info("Thumbnail frame generated and queued for display.")

        except Exception as e:
            logging.error(f"Error generating thumbnail: {e}")
            self.status_message.set("Failed to generate thumbnail.")

    def overlay_composite_thumbnail(self, oca_data, layer_mappings, background_color, oca_dir):
        """
        Create an overlay composite thumbnail by layering all unique images.

        Args:
            oca_data (dict): Parsed OCA data.
            layer_mappings (list): Mappings of layers to their frames.
            background_color (list): Background color in [R, G, B, A] format.
            oca_dir (str): Directory of the OCA file for relative paths.

        Returns:
            PIL.ImageTk.PhotoImage: The composite thumbnail image.
        """
        # Set thumbnail size
        thumbnail_width, thumbnail_height = 320, 180

        # Convert background color from [0-1] to [0-255]
        try:
            bg_color = tuple([int(max(0, min(c, 1)) * 255) for c in background_color[:3]] + [int(max(0, min(background_color[3], 1)) * 255)])
        except Exception as e:
            logging.warning(f"Invalid backgroundColor format. Using white background. Error: {e}")
            bg_color = (255, 255, 255, 255)

        # Create a new canvas for the thumbnail
        thumbnail_canvas = Image.new('RGBA', (thumbnail_width, thumbnail_height), bg_color)

        # Collect unique image file paths
        unique_images = set()
        for layer_mapping in layer_mappings:
            # Assuming the last frame represents the final state
            frame = layer_mapping['frames'][-1]
            file_path = frame.get('fileName')
            if file_path:
                if not os.path.isabs(file_path):
                    file_path = os.path.join(oca_dir, file_path)
                unique_images.add(file_path)

        unique_images = list(unique_images)

        # Load and paste images onto the thumbnail canvas in order
        for file_path in unique_images:
            try:
                if not os.path.isfile(file_path):
                    logging.warning(f"File '{file_path}' not found for thumbnail. Skipping.")
                    continue

                image = Image.open(file_path).convert('RGBA')
                image = image.resize((thumbnail_width, thumbnail_height), resample=Image.LANCZOS)
                # Overlay the image onto the thumbnail canvas
                thumbnail_canvas = Image.alpha_composite(thumbnail_canvas, image)
            except Exception as e:
                logging.warning(f"Error loading image '{file_path}' for thumbnail: {e}")
                continue

        # Convert to PhotoImage
        thumbnail_photo = ImageTk.PhotoImage(thumbnail_canvas)
        return thumbnail_photo  # Return as a single-element list to maintain consistency with the queue

    def generate_thumbnail_manual(self):
        """
        Manually trigger the thumbnail generation process using the Text Editor's current content.
        """
        if not self.oca_file_path.get():
            messagebox.showerror("Error", "No OCA file is currently loaded.")
            return
        self.status_message.set("Generating thumbnail...")
        logging.info("Manual thumbnail generation triggered.")
        threading.Thread(target=self.generate_thumbnail_preview, args=(True,), daemon=True).start()

    def check_thumbnail_queue(self):
        """
        Check if there are thumbnail frames in the queue and update the canvas.
        """
        try:
            while not self.thumbnail_frames_queue.empty():
                thumbnail_frames = self.thumbnail_frames_queue.get_nowait()
                # Since overlay_composite_thumbnail returns a list with one PhotoImage, unpack it
                if thumbnail_frames:
                    thumbnail_photo = thumbnail_frames[0]
                    self.thumbnail_canvas.delete("all")  # Clear previous images
                    self.thumbnail_canvas.create_image(0, 0, anchor=tk.NW, image=thumbnail_photo)
                    self.thumbnail_canvas.image = thumbnail_photo  # Keep a reference
                    self.status_message.set("Thumbnail generated successfully.")
                    logging.info("Thumbnail displayed successfully.")
        except queue.Empty:
            pass
        except Exception as e:
            logging.error(f"Error processing thumbnail queue: {e}")
            self.status_message.set("Failed to display thumbnail.")

        # Schedule the next check
        self.root.after(100, self.check_thumbnail_queue)

    def animate_thumbnail(self):
        """
        Animate the thumbnail preview by cycling through the frames.
        """
        if not self.thumbnail_photoimages:
            return

        frame = self.thumbnail_photoimages[self.current_thumbnail_frame]
        self.thumbnail_canvas.delete("all")  # Clear previous images
        self.thumbnail_canvas.create_image(0, 0, anchor=tk.NW, image=frame)

        self.current_thumbnail_frame = (self.current_thumbnail_frame + 1) % len(self.thumbnail_photoimages)
        self.root.after(200, self.animate_thumbnail)  # Update every 200 ms

    def stop_thumbnail_animation(self):
        """
        Stop the thumbnail animation.
        """
        self.thumbnail_running = False

def main():
    """
    Initialize and run the OCA Processor GUI application.
    """
    root = tk.Tk()
    app = OCAProcessorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
