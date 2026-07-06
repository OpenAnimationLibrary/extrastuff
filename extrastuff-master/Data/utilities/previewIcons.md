Importantly:

The A:M resources preview icon:

It is binhex RLE encoded raw RGB data.
You have the size in the [PREVIEW] header.
In the [DATA] section, you get a sequence of lines, R line, G line and B line, etc.
Then basic RLE stuff:
read byte
byte >= 0 ? read next n+1 bytes
byte


20240513 Would still love to see the data change to Base64.
As this is somewhat unlikely and would potentially effect connectivity with older releases...
Another option would be to have modern releases look first for a sidecar image with same name as resource.
If found it would use that image instead of any internally stored data (or the default icons for when no icon is assigned).

Todo:  Determine where A:M retrieves the default resource type preview from.
Is it the registry?

See python proof of concepts for extracting binhex RLE preview data and C++ preview switching code.
