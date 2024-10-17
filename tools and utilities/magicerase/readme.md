Initial demo of magic erase process.

To do?:

- [ ] Add a pixel paint brush so the user can manually paint/mask areas.

- [ ] Add an Erase brush to accomplish some off the above but with anticipated user experience

- [ ] Add Erode and Dialate option to chip away at pixels or add outlines.

- [ ] Add Invert option (various options to output color separated RGBA channels)

- [ ] Allow for full color processing.  (Currently have not tested full color images to determine shortfalls).

- [ ] Add option to display a checkerboard pattern rather than red in the UI.  This should be trivial to implement but we do want to make sure the code uses the red rather than the checkerboard to create the alpha channel.

- [x] Add standard file menu items such as reloading the program (as that is so important to me for iterating improvements to the program)

- [ ] Add a "debugging" option that saves a PNG image at each step of the process in sequential image format.  I've found this to be a useful feature when wanting to play back animated steps of the process and depending on what is being done by the program can produce some useful content.

- [ ] Add filtering processes to detect if an image is pure black and white and if not convert it for the purpose of this program.

- [ ] Add an option to process entire directories although note that locations of maskings will change from image to image so we need specical processes to allow for this.
