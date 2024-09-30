import tkinter as tk
from tkinter import filedialog, messagebox
import os

class ModelExtractorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Model Extractor")
        self.master.geometry("400x300")
        
        self.project_file_path = ""
        
        self.label = tk.Label(master, text="Load Project File:")
        self.label.pack(pady=10)
        
        self.load_button = tk.Button(master, text="Load Project File", command=self.load_project_file)
        self.load_button.pack(pady=10)

        self.extract_button = tk.Button(master, text="Extract Models", command=self.extract_models)
        self.extract_button.pack(pady=10)
        
        self.model_list = tk.Listbox(master)
        self.model_list.pack(fill=tk.BOTH, expand=True, pady=10)

    def load_project_file(self):
        self.project_file_path = filedialog.askopenfilename(title="Select Project File", filetypes=[("Project Files", "*.prj")])
        if self.project_file_path:
            self.find_models()

    def find_models(self):
        self.model_list.delete(0, tk.END)  # Clear the list
        with open(self.project_file_path, 'r') as file:
            content = file.readlines()

        in_model_section = False
        current_model = []

        for line in content:
            if '<MODEL>' in line:
                in_model_section = True
                current_model = [line]  # Start a new model
            elif '</MODEL>' in line:
                if in_model_section:  # Check if we were in a model section
                    in_model_section = False
                    current_model.append(line)
                    model_name = f"Model_{len(self.model_list.get(0, tk.END)) + 1}.mdl"
                    self.model_list.insert(tk.END, model_name)  # Show model name in the list
                    # Save the extracted model as a standalone model file
                    self.save_model(model_name, current_model)
            elif in_model_section:
                current_model.append(line)

        if not self.model_list.size():
            messagebox.showinfo("Info", "No models found in the project file.")

    def save_model(self, model_name, model_content):
        # Wrap the content in <MODELFILE> tags and include necessary headers
        model_file_content = [
            '<MODELFILE>\n',
            'ProductVersion=19.5\n',
            'Release=19.5 PC\n',
            '<POSTEFFECTS>\n',
            '</POSTEFFECTS>\n',
            '<IMAGES>\n',
            '</IMAGES>\n',
            '<SOUNDS>\n',
            '</SOUNDS>\n',
            '<MATERIALS>\n',
            '</MATERIALS>\n',
            '<OBJECTS>\n',
        ]
        
        # Append the <MODEL> section extracted from the project file
        model_file_content.extend(model_content)
        
        # Close the <OBJECTS> and <MODELFILE> tags
        model_file_content.extend([
            '</OBJECTS>\n',
            '<ACTIONS>\n',
            '</ACTIONS>\n',
            '<CHOREOGRAPHIES>\n',
            '</CHOREOGRAPHIES>\n',
            'FileInfoPos=211\n',
            '</MODELFILE>\n'
        ])

        # Define the output path for the model file
        model_file_path = os.path.join(os.path.dirname(self.project_file_path), model_name)
        with open(model_file_path, 'w') as mdl_file:
            mdl_file.writelines(model_file_content)

    def extract_models(self):
        messagebox.showinfo("Success", "Models extracted successfully.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ModelExtractorApp(root)
    root.mainloop()
