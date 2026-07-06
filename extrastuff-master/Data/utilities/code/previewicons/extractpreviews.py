#Extract all preview icons from eligible files into .preview text files
import os
import re

def extract_preview_data(directory):
    # Specify the file extensions to process
    extensions = ['.mdl', '.act', '.mat', '.prj', '.cho']
    
    # Loop through each file in the directory
    for filename in os.listdir(directory):
        file_extension = os.path.splitext(filename)[1]
        if file_extension in extensions:
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Use regex to find the preview data block
            preview_data = re.search(r'(<Preview>.*?</Preview>)', content, re.DOTALL)
            
            if preview_data:
                # Create a new file with the same name but with a .preview extension
                output_path = os.path.splitext(file_path)[0] + '.preview'
                with open(output_path, 'w', encoding='utf-8') as output_file:
                    output_file.write(preview_data.group(1))
                print(f"Preview data extracted to {output_path}")
            else:
                print(f"No preview data found in {file_path}")

# Example usage:
# Replace 'path_to_directory' with the path to your directory
extract_preview_data('F:/github-pages/amdata/')
