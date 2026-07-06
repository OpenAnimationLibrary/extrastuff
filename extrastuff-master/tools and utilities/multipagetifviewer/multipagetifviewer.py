#This script authored by Rodney Baker and licensed CC-0.  For more information please see: <http://creativecommons.org/publicdomain/zero/1.0/>
#multipagetifviewer.py can view and play/animate multipage tifs at different FPS and trivially save out to animated GIF at that same speed.
#if you improve upon this program please share so that others will benefit.
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import time

class TiffViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Multipage TIF Viewer")
        self.geometry("800x600")

        # Initialize variables
        self.image = None
        self.pages = []
        self.current_page = 0
        self.playing = False
        self.fps = 1  # Frames per second

        # Create the menu
        self.create_menu()

        # Create the canvas to display the image
        self.canvas = tk.Canvas(self, width=800, height=500, bg="white")
        self.canvas.pack()

        # Create FPS slider
        self.fps_slider = tk.Scale(self, from_=1, to=30, orient=tk.HORIZONTAL, label="FPS", command=self.set_fps)
        self.fps_slider.set(self.fps)  # Default FPS is 1
        self.fps_slider.pack()

        # Play/Pause button
        self.play_button = tk.Button(self, text="Play", command=self.toggle_play)
        self.play_button.pack()

    def create_menu(self):
        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save as GIF", command=self.save_as_gif)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

    def open_file(self):
        # Open file dialog to select a TIFF file
        file_path = filedialog.askopenfilename(filetypes=[("TIF Files", "*.tif"), ("All Files", "*.*")])
        if file_path:
            self.load_tiff(file_path)

    def load_tiff(self, file_path):
        try:
            # Open the TIFF image
            self.image = Image.open(file_path)
            self.pages = []  # Clear previous pages

            # Load all pages
            try:
                while True:
                    self.pages.append(self.image.copy())
                    self.image.seek(len(self.pages))  # Move to the next page
            except EOFError:
                pass  # End of file

            self.current_page = 0
            self.playing = False
            self.show_page(self.current_page)

        except Exception as e:
            messagebox.showerror("Error", f"Could not load TIFF file: {str(e)}")

    def show_page(self, page_index):
        if 0 <= page_index < len(self.pages):
            # Convert the current page to a Tkinter-compatible image and display it
            img = ImageTk.PhotoImage(self.pages[page_index])
            self.canvas.create_image(0, 0, anchor=tk.NW, image=img)
            self.canvas.image = img  # Keep a reference to the image to avoid garbage collection

    def set_fps(self, value):
        self.fps = int(value)
        print(f"FPS set to: {self.fps}")

    def toggle_play(self):
        if not self.playing:
            self.play_button.config(text="Pause")
            self.playing = True
            self.play_images()
        else:
            self.play_button.config(text="Play")
            self.playing = False

    def play_images(self):
        if self.playing:
            self.current_page = (self.current_page + 1) % len(self.pages)
            self.show_page(self.current_page)
            self.after(int(1000 / self.fps), self.play_images)

    def save_as_gif(self):
        if not self.pages:
            messagebox.showinfo("No Image", "No TIFF file loaded to save as GIF.")
            return

        # Open a file dialog to save the GIF
        gif_path = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF Files", "*.gif")])
        if gif_path:
            try:
                # Save the pages as an animated GIF
                self.pages[0].save(gif_path, save_all=True, append_images=self.pages[1:], duration=int(1000 / self.fps), loop=0)
                messagebox.showinfo("Success", f"GIF saved successfully: {gif_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save GIF: {str(e)}")

if __name__ == "__main__":
    app = TiffViewerApp()
    app.mainloop()
