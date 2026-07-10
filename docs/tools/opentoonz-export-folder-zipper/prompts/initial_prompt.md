# Initial prompt/context

Create a browser-only OpenToonz utility called "OpenToonz Export Folder Zipper".

The tool should package the folder created by OpenToonz Export > Export Scene into a downloadable ZIP file. OpenToonz currently creates an exported directory, not a ZIP, so the web app should let the user select that directory and generate the ZIP locally.

The app should:

- Run as a static web app suitable for OpenAnimationLibrary GitHub Pages first, with later submission to the OpenToonz Open-Prompted Anime Tools site.
- Use a folder picker / directory upload to select the exported scene directory.
- Preserve the folder hierarchy inside the ZIP.
- Summarize likely OpenToonz contents such as .tnz scene files, _otprj.xml project files, .tlv/.pli level files, .tpl palette files, image files, and text-readable support files.
- Warn about missing .tnz files, multiple roots, very large folders, suspicious paths, and script/executable-like file extensions.
- Create the ZIP locally in browser memory.
- Generate a SHA-256 receipt.
- Avoid server upload.
- Keep an optional manifest feature disabled by default so the exported folder is preserved exactly unless the user chooses otherwise.
