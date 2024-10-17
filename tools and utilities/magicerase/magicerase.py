#https://github.com/OpenAnimationLibrary
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import cv2

class MagicWandApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Magic Wand Background Remover')

        # GUI Elements
        self.canvas = tk.Canvas(root, width=800, height=600, bg='white', cursor='cross')
        self.canvas.pack()

        self.load_button = tk.Button(root, text='Load Image', command=self.load_image)
        self.load_button.pack()

        self.save_button = tk.Button(root, text='Save Image', command=self.save_image)
        self.save_button.pack()

        # Variables
        self.image = None
        self.tk_image = None
        self.mask = None

        # Bindings
        self.canvas.bind('<Button-1>', self.on_click)

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[('Image Files', '*.png;*.jpg;*.jpeg')])
        if file_path:
            self.image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
            if self.image is None:
                messagebox.showerror('Error', 'Could not load image.')
                return

            if len(self.image.shape) == 2 or self.image.shape[2] == 3:
                # Convert to RGBA if not already
                self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2BGRA)

            # Resize image to fit canvas while maintaining aspect ratio
            self.image = self.resize_image_to_fit(self.image, 800, 600)

            self.mask = np.zeros(self.image.shape[:2], np.uint8)
            self.display_image()

    def resize_image_to_fit(self, image, max_width, max_height):
        height, width = image.shape[:2]
        aspect_ratio = width / height

        if width > max_width or height > max_height:
            if aspect_ratio > 1:
                new_width = max_width
                new_height = int(max_width / aspect_ratio)
            else:
                new_height = max_height
                new_width = int(max_height * aspect_ratio)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        return image

    def display_image(self):
        # Convert image to RGB for displaying in Tkinter
        display_img = cv2.cvtColor(self.image, cv2.COLOR_BGRA2RGBA)
        display_img = Image.fromarray(display_img)
        self.tk_image = ImageTk.PhotoImage(display_img)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

    def on_click(self, event):
        if self.image is None:
            return

        # Get click coordinates
        x, y = event.x, event.y

        # Flood fill parameters
        seed_point = (x, y)
        new_val = (0, 0, 255)  # Full Red
        lo_diff = (20, 20, 20, 20)
        up_diff = (20, 20, 20, 20)

        # Create mask and apply flood fill
        mask = np.zeros((self.image.shape[0] + 2, self.image.shape[1] + 2), np.uint8)
        flood_flags = cv2.FLOODFILL_FIXED_RANGE | (4 << 8)  # Use 4-connectivity and fixed range
        bgr_image = cv2.cvtColor(self.image, cv2.COLOR_BGRA2BGR)
        cv2.floodFill(bgr_image, mask, seedPoint=seed_point, newVal=new_val, loDiff=lo_diff, upDiff=up_diff, flags=flood_flags)

        # Convert back to BGRA
        self.image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2BGRA)

        self.display_image()

    def save_image(self):
        if self.image is None:
            messagebox.showwarning('Warning', 'No image to save.')
            return

        # Transfer red pixels to alpha channel as transparency
        red_pixels = (self.image[:, :, 2] == 255) & (self.image[:, :, 1] == 0) & (self.image[:, :, 0] == 0)
        self.image[red_pixels, 3] = 0

        file_path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG Files', '*.png')])
        if file_path:
            # Save the image as PNG with alpha channel
            cv2.imwrite(file_path, self.image)
            messagebox.showinfo('Image Saved', f'Image saved to {file_path}')

if __name__ == '__main__':
    root = tk.Tk()
    app = MagicWandApp(root)
    root.mainloop()
