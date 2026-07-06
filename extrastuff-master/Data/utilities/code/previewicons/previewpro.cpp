// previewpro.cpp : User provides a target file to replace the preview icon and the .preview file containing the image to use.
// WARNING:  Specified target will be replaced
// Need to warn and/or create a copy of the original

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>

std::string readFromFile(const std::string& filename) {
    std::ifstream file(filename);
    std::stringstream buffer;
    if (file) {
        buffer << file.rdbuf();
        file.close();
    }
    return buffer.str();
}

bool writeToFile(const std::string& filename, const std::string& content) {
    std::ofstream file(filename);
    if (file.is_open()) {
        file << content;
        file.close();
        return true;
    }
    return false;
}

int main() {
    std::string sourceFilename, previewFilename;
    std::cout << "Enter the source filename: ";
    std::cin >> sourceFilename;
    std::cout << "Enter the preview filename: ";
    std::cin >> previewFilename;

    // Read content from files
    std::string sourceContent = readFromFile(sourceFilename);
    std::string previewContent = readFromFile(previewFilename);

    // Find and replace the old <Preview> section
    size_t start = sourceContent.find("<Preview>");
    size_t end = sourceContent.find("</Preview>") + 10; // +10 to include "</Preview>"

    if (start != std::string::npos && end != std::string::npos) {
        // Erase old preview
        sourceContent.erase(start, end - start);
        // Insert new preview
        sourceContent.insert(start, previewContent);
    }
    else {
        std::cout << "No <Preview> section found in the source file." << std::endl;
        return 1;
    }

    // Write the modified content back to the source file
    if (writeToFile(sourceFilename, sourceContent)) {
        std::cout << "Preview section replaced successfully." << std::endl;
    }
    else {
        std::cout << "Failed to write to the source file." << std::endl;
        return 1;
    }
    std::cout << "Press ENTER to exit...";
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
    std::cin.get();
    return 0;
}
