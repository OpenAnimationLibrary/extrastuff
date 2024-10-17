import tkinter as tk
from tkinter import filedialog, messagebox, Menu, Spinbox
from PIL import Image, ImageTk
import numpy as np
import cv2
import os
import sys
import configparser
from collections import deque

class MagicWandApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Magic Wand Background Remover')
        self.config = configparser.ConfigParser()
        self.config_file = 'magicerasersettings.ini'
        self.load_settings()
        self.recent_files = self.load_recent_files()

        self.menu_bar = Menu(self.root)
        self.root.config(menu=self.menu_bar)

        self.file_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label='File', menu=self.file_menu)
        self.file_menu.add_command(label='Restart', command=self.restart_program)
        self.file_menu.add_command(label='Open Settings', command=self.open_settings)
        self.recent_menu = Menu(self.file_menu, tearoff=0)
        self.file_menu.add_cascade(label='Open Recent', menu=self.recent_menu)
        self.update_recent_menu()

        self.edit_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label='Edit', menu=self.edit_menu)
        self.edit_menu.add_command(label='Undo', command=self.undo, accelerator='Ctrl+Z')
        self.edit_menu.add_command(label='Redo', command=self.redo, accelerator='Ctrl+Y')
        self.root.bind_all('<Control-z>', self.undo)
        self.root.bind_all('<Control-y>', self.redo)

        self.help_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label='Help', menu=self.help_menu)
        self.help_menu.add_command(label='About', command=self.show_about_dialog)

        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack()
        self.canvas = tk.Canvas(self.canvas_frame, width=800, height=600, bg='white', cursor='cross')
        self.canvas.pack()
        self.load_button = tk.Button(root, text='Load Image', command=self.load_image)
        self.load_button.pack()
        self.save_button = tk.Button(root, text='Save Image', command=self.save_image)
        self.save_button.pack()
        self.checkerboard_var = tk.BooleanVar(value=self.config.getboolean('Settings', 'UseCheckerboard', fallback=False))
        self.checkerboard_checkbox = tk.Checkbutton(root, text='Use Checkerboard Pattern', variable=self.checkerboard_var, command=self.on_checkerboard_toggle)
        self.checkerboard_checkbox.pack()

        self.undo_stack = deque(maxlen=10)
        self.redo_stack = deque(maxlen=10)
        self.tk_image = None
        self.mask = None
        self.loaded_image_path = self.config.get('Settings', 'LoadedImagePath', fallback='magicwandimage.PNG')
        if not os.path.exists(self.loaded_image_path):
            self.loaded_image_path = None
        self.red_mask_image = None

        if self.loaded_image_path and os.path.exists(self.loaded_image_path):
            self.load_image(self.loaded_image_path)
        self.canvas.bind('<Button-1>', self.on_click)
        self.root.bind('<Configure>', self.on_resize)

    def load_settings(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            recognized_keys = {'UseCheckerboard', 'LoadedImagePath'}
            for section in self.config.sections():
                if section == 'Settings':
                    self.config[section] = {k: v for k, v in self.config[section].items() if k in recognized_keys}

    def save_settings(self):
        self.config['Settings'] = {
            'UseCheckerboard': str(self.checkerboard_var.get()),
            'LoadedImagePath': self.loaded_image_path if self.loaded_image_path else ''
        }
        for i, path in enumerate(self.recent_files, start=1):
            self.config['RecentFiles'][f'Recent{i}'] = path
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def load_recent_files(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            if 'RecentFiles' in self.config:
                return [self.config['RecentFiles'].get(f'Recent{i}', '') for i in range(1, 11)]
        return []

    def load_image(self, file_path=None):
        if not file_path:
            file_path = filedialog.askopenfilename(filetypes=[('Image Files', '*.png;*.jpg;*.jpeg')])
        if file_path:
            self.loaded_image_path = file_path
            self.image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
            if self.image is None:
                messagebox.showerror('Error', 'Could not load image.')
                return
            if len(self.image.shape) == 2 or self.image.shape[2] == 3:
                self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2BGRA)
            self.image = self.resize_image_to_fit(self.image, self.canvas.winfo_width(), self.canvas.winfo_height())
            self.mask = np.zeros(self.image.shape[:2], np.uint8)
            self.red_mask_image = self.image.copy()
            self.save_state_for_undo()
            self.display_image()
            self.update_recent_files()
        self.save_settings()
        self.update_recent_menu()

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
            if new_width > 0 and new_height > 0:
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        return image

    def display_image(self):
        if self.image is None:
            return
        display_img = self.red_mask_image.copy()
        if self.checkerboard_var.get():
            checkerboard = self.create_checkerboard_pattern(display_img.shape[:2], 10)
            alpha_channel = display_img[:, :, 3]
            mask = (alpha_channel == 0)
            display_img[mask] = checkerboard[mask]
        display_img = cv2.cvtColor(display_img, cv2.COLOR_BGRA2RGBA)
        display_img = Image.fromarray(display_img)
        self.tk_image = ImageTk.PhotoImage(display_img)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

    def create_checkerboard_pattern(self, shape, square_size):
        rows, cols = shape
        checkerboard = np.zeros((rows, cols, 4), dtype=np.uint8)
        for y in range(0, rows, square_size * 2):
            for x in range(0, cols, square_size * 2):
                checkerboard[y:y+square_size, x:x+square_size] = (200, 200, 200, 255)
                checkerboard[y+square_size:y+2*square_size, x+square_size:x+2*square_size] = (200, 200, 200, 255)
        return checkerboard

    def on_click(self, event):
        if self.image is None:
            return
        x, y = event.x, event.y
        seed_point = (x, y)
        new_val = (0, 0, 255)
        lo_diff = (20, 20, 20, 20)
        up_diff = (20, 20, 20, 20)
        mask = np.zeros((self.image.shape[0] + 2, self.image.shape[1] + 2), np.uint8)
        flood_flags = cv2.FLOODFILL_FIXED_RANGE | (4 << 8)
        bgr_image = cv2.cvtColor(self.red_mask_image, cv2.COLOR_BGRA2BGR)
        cv2.floodFill(bgr_image, mask, seedPoint=seed_point, newVal=new_val, loDiff=lo_diff, upDiff=up_diff, flags=flood_flags)
        self.red_mask_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2BGRA)
        self.save_state_for_undo()
        self.display_image()
        self.update_recent_files()
        self.save_settings()

    def on_checkerboard_toggle(self):
        self.display_image()
        self.update_recent_files()
        self.save_settings()

    def on_resize(self, event):
        if self.image is not None:
            self.image = self.resize_image_to_fit(self.image, event.width, event.height)
            self.red_mask_image = self.resize_image_to_fit(self.red_mask_image, event.width, event.height)
            self.display_image()

    def save_image(self):
        if self.image is None:
            messagebox.showwarning('Warning', 'No image to save.')
            return
        red_pixels = (self.red_mask_image[:, :, 2] == 255) & (self.red_mask_image[:, :, 1] == 0) & (self.red_mask_image[:, :, 0] == 0)
        self.image[red_pixels, 3] = 0
        file_path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG Files', '*.png')])
        if file_path:
            cv2.imwrite(file_path, self.image)
            cv2.imwrite('magicwandimage.PNG', self.image)
            messagebox.showinfo('Image Saved', f'Image saved to {file_path}')

    def update_recent_menu(self):
        self.recent_menu.delete(0, 'end')
        for file_path in self.recent_files:
            if file_path:
                self.recent_menu.add_command(label=file_path, command=lambda path=file_path: self.load_image(path))

    def update_recent_files(self):
        if self.loaded_image_path not in self.recent_files:
            self.recent_files.insert(0, self.loaded_image_path)
        self.recent_files = self.recent_files[:10]
        for i, path in enumerate(self.recent_files, start=1):
            self.config['RecentFiles'][f'Recent{i}'] = path

    def save_state_for_undo(self):
        if self.red_mask_image is not None:
            self.undo_stack.append(self.red_mask_image.copy())
        self.redo_stack.clear()

    def undo(self, event=None):
        if self.undo_stack:
            self.redo_stack.append(self.red_mask_image.copy())
            self.red_mask_image = self.undo_stack.pop()
            self.display_image()

    def redo(self, event=None):
        if self.redo_stack:
            self.undo_stack.append(self.red_mask_image.copy())
            self.red_mask_image = self.redo_stack.pop()
            self.display_image()

    def show_about_dialog(self):
        about_message = '''Magic Wand Background Remover
Version 1.0

Visit Github: https://github.com/OpenAnimationLibrary/extrastuff/tree/master/tools%20and%20utilities/magicerase'''
        messagebox.showinfo('About', about_message)

    def open_settings(self):
        try:
            os.startfile(self.config_file)
        except FileNotFoundError:
            messagebox.showerror('Error', 'Settings file not found.')

    def restart_program(self):
        self.update_recent_files()
        self.save_settings()
        restarting_dialog = tk.Toplevel(self.root)
        restarting_dialog.title('Restarting')
        tk.Label(restarting_dialog, text='Restarting...').pack(pady=20, padx=20)
        self.root.after(1000, lambda: self.restart_app())

    def restart_app(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

if __name__ == '__main__':
    root = tk.Tk()
    app = MagicWandApp(root)
    if app.loaded_image_path and os.path.exists(app.loaded_image_path):
        app.load_image(app.loaded_image_path)
    root.mainloop()
