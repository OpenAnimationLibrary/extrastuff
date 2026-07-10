# OpenToonz Export Folder Zipper

A small, browser-only utility for packaging the folder created by **OpenToonz > Export > Export Scene** into a downloadable ZIP file.

This is intended as a first-stage Open Animation Library-hosted utility that can later be submitted to the OpenToonz Open-Prompted Anime Tools site.

## What it does

- Lets the user select the exported scene folder with a browser folder picker.
- Preserves the selected folder hierarchy inside the ZIP.
- Summarizes likely OpenToonz contents:
  - `.tnz` scene files
  - `_otprj.xml` project XML files
  - `.tlv`, `.pli`, `.tzp`, `.tzu` level/drawing files
  - `.tpl` palette files
  - common image files
  - text-previewable/support files
- Warns about missing `.tnz` files, multiple top-level roots, very large folders, and script/executable-like extensions.
- Creates the ZIP locally in browser memory.
- Generates a SHA-256 receipt for verification.
- Does not upload files to a server.

## How to use

1. In OpenToonz, use **Export > Export Scene**.
2. Open this web app.
3. Click **Choose Export Folder** and select the folder OpenToonz created.
4. Review the package summary.
5. Click **Create ZIP**.
6. Download the ZIP and share it for troubleshooting.

## Local testing

Because browsers may restrict folder picking from `file://` pages, test with a local web server:

```bash
cd opentoonz-export-folder-zipper
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/
```

## GitHub Pages placement

For an Open Animation Library repository, one simple placement is:

```text
docs/tools/opentoonz-export-folder-zipper/index.html
```

Then GitHub Pages can serve it from a URL like:

```text
https://openanimationlibrary.github.io/<repo-name>/tools/opentoonz-export-folder-zipper/
```

The exact URL depends on the repository name and GitHub Pages settings.

## Later OpenToonz site submission

For the OpenToonz `opentoonz.github.io` site, the intended placement is likely:

```text
ai_tools/apps/opentoonz_export_folder_zipper/index.html
ai_tools/apps/opentoonz_export_folder_zipper/meta.json
```

The included `meta.json` is a starter metadata file and may need adjustment to match the latest contribution schema.

## Dependency

This prototype loads JSZip from jsDelivr:

```html
<script src="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"></script>
```

If JSZip fails to load, the app falls back to a small built-in ZIP writer that creates a valid uncompressed ZIP. For a stricter final submission, JSZip can also be vendored locally if maintainers prefer no external CDN dependency.

## Version

Prototype version: `0.1.0`
