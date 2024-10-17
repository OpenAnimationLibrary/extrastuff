Initial demo of magic erase process.

To do:

- [x] Add standard File menu Reload/Restart to allow fast iterating of improvements to the program (See Note 1)

- [ ] Add MagicEraserSettings.ini file to store Preferences as well as recently used images etc.

- [ ] Add option to display a checkerboard pattern rather than red in the UI.  (Partially implemented as of 2024/10/16 but works only when loading images)

- [ ] Add a pixel paint brush so the user can manually paint/mask areas.

- [ ] Add an Erase brush to accomplish some off the above but with anticipated user experience

- [ ] Add Erode and Dialate option to chip away at pixels or add outlines.

- [ ] Add Invert option (various options to output color separated RGBA channels)

- [ ] Allow for full color processing.  (Currently have not tested full color images to determine shortfalls).

- [ ] Add "debugging" option that saves a PNG image at each step of the process in sequential image format.  This is useful when troubleshooting and also can produce some useful content.

- [ ] Add filtering processes to detect if an image is pure black and white and if not convert it for the purpose of this program.

- [ ] Add option to process entire directories although note locations of maskings change from image to image so we need special processes to allow for this.

Note 1:  Restarting the program should account for any image currently loaded and reload that image as well.
