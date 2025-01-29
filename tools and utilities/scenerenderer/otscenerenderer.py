import os
import sys
import subprocess
import configparser
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QTextEdit, QWidget, QComboBox, QSpinBox, QMenuBar, QAction
)

class TaskListInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenToonz TaskList Interface")

        self.settings_file = "tasklist_settings.ini"
        self.config = configparser.ConfigParser()
        self.load_settings()

        self.layout = QVBoxLayout()

        # Menu bar
        menu_bar = QMenuBar(self)
        file_menu = menu_bar.addMenu("File")
        restart_action = QAction("Restart", self)
        restart_action.triggered.connect(self.restart_program)
        file_menu.addAction(restart_action)
        self.setMenuBar(menu_bar)

        # TComposer path input
        self.tcomposer_label = QLabel("TComposer Path:")
        self.tcomposer_input = QLineEdit()
        self.tcomposer_input.setText(self.config.get("Paths", "tcomposer_path", fallback="C:\\Program Files\\OpenToonz\\tcomposer.exe"))
        self.tcomposer_browse = QPushButton("Browse")
        self.tcomposer_browse.clicked.connect(self.browse_tcomposer_file)

        tcomposer_layout = QHBoxLayout()
        tcomposer_layout.addWidget(self.tcomposer_label)
        tcomposer_layout.addWidget(self.tcomposer_input)
        tcomposer_layout.addWidget(self.tcomposer_browse)

        self.layout.addLayout(tcomposer_layout)

        # Scene file input
        self.scene_label = QLabel("Scene File:")
        self.scene_input = QLineEdit()
        self.scene_input.setText(self.config.get("Paths", "scene_file", fallback=""))
        self.scene_browse = QPushButton("Browse")
        self.scene_browse.clicked.connect(self.browse_scene_file)

        scene_layout = QHBoxLayout()
        scene_layout.addWidget(self.scene_label)
        scene_layout.addWidget(self.scene_input)
        scene_layout.addWidget(self.scene_browse)

        self.layout.addLayout(scene_layout)

        # Output file input
        self.output_label = QLabel("Output File:")
        self.output_input = QLineEdit()
        self.output_input.setText(self.config.get("Paths", "output_file", fallback=os.path.join(os.getcwd(), "frame.png")))
        self.output_browse = QPushButton("Browse")
        self.output_browse.clicked.connect(self.browse_output_file)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(self.output_browse)

        self.layout.addLayout(output_layout)

        # Render options
        self.range_label = QLabel("Frame Range (Start-End):")
        self.range_start = QSpinBox()
        self.range_start.setMinimum(1)
        self.range_start.setValue(self.config.getint("RenderOptions", "range_start", fallback=1))
        self.range_end = QSpinBox()
        self.range_end.setMinimum(1)
        self.range_end.setValue(self.config.getint("RenderOptions", "range_end", fallback=1))

        range_layout = QHBoxLayout()
        range_layout.addWidget(self.range_label)
        range_layout.addWidget(self.range_start)
        range_layout.addWidget(self.range_end)

        self.layout.addLayout(range_layout)

        self.step_label = QLabel("Step:")
        self.step_input = QSpinBox()
        self.step_input.setMinimum(1)
        self.step_input.setValue(self.config.getint("RenderOptions", "step", fallback=1))
        self.layout.addWidget(self.step_label)
        self.layout.addWidget(self.step_input)

        self.shrink_label = QLabel("Shrink:")
        self.shrink_input = QSpinBox()
        self.shrink_input.setMinimum(1)
        self.shrink_input.setValue(self.config.getint("RenderOptions", "shrink", fallback=1))
        self.layout.addWidget(self.shrink_label)
        self.layout.addWidget(self.shrink_input)

        self.threads_label = QLabel("Threads:")
        self.threads_input = QComboBox()
        self.threads_input.addItems(["all", "1", "2", "4", "8"])
        self.threads_input.setCurrentText(self.config.get("RenderOptions", "threads", fallback="all"))
        self.layout.addWidget(self.threads_label)
        self.layout.addWidget(self.threads_input)

        self.tile_size_label = QLabel("Max Tile Size:")
        self.tile_size_input = QComboBox()
        self.tile_size_input.addItems(["none", "256", "512", "1024"])
        self.tile_size_input.setCurrentText(self.config.get("RenderOptions", "tile_size", fallback="none"))
        self.layout.addWidget(self.tile_size_label)
        self.layout.addWidget(self.tile_size_input)

        # Command preview and run
        self.cmd_preview = QTextEdit()
        self.update_cmd_button = QPushButton("Update Command")
        self.update_cmd_button.clicked.connect(self.update_command)

        self.run_button = QPushButton("Run TaskList")
        self.run_button.clicked.connect(self.run_tasklist)

        self.layout.addWidget(QLabel("Command Preview:"))
        self.layout.addWidget(self.cmd_preview)
        self.layout.addWidget(self.update_cmd_button)
        self.layout.addWidget(self.run_button)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            self.config.read(self.settings_file)

    def save_settings(self):
        with open(self.settings_file, "w") as file:
            self.config.write(file)

    def restart_program(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def browse_tcomposer_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select TComposer Executable", "", "Executable Files (*.exe)")
        if file_path:
            self.tcomposer_input.setText(file_path)

    def browse_scene_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Scene File", "", "Scene Files (*.tnz)")
        if file_path:
            self.scene_input.setText(file_path)

    def browse_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output File", "", "PNG Files (*.png)")
        if file_path:
            self.output_input.setText(file_path)

    def update_command(self):
        tcomposer_path = self.tcomposer_input.text()
        scene_file = self.scene_input.text()
        output_file = self.output_input.text()
        frame_range = f"-range {self.range_start.value()} {self.range_end.value()}"
        step = f"-step {self.step_input.value()}"
        shrink = f"-shrink {self.shrink_input.value()}"
        threads = f"-nthreads {self.threads_input.currentText()}"
        tile_size = f"-maxtilesize {self.tile_size_input.currentText()}"

        if not scene_file:
            self.cmd_preview.setText("Error: Scene file must be specified.")
            return

        command = (
            f"start \"TaskList\" /HIGH \"{tcomposer_path}\" \"{scene_file}\" {frame_range} {step} {shrink} -o \"{output_file}\" "
            f"{threads} {tile_size}"
        )

        self.cmd_preview.setText(command)

    def run_tasklist(self):
        command = self.cmd_preview.toPlainText()
        if not command or command.startswith("Error"):
            return

        self.save_settings()

        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            self.cmd_preview.setText(f"Error running command: {e}")

if __name__ == "__main__":
    app = QApplication([])
    window = TaskListInterface()
    window.show()
    app.exec_()
