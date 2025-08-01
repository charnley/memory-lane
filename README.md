# Memory Lane CLI

Memory Lane CLI is a Python tool designed to help groups organize and relive shared photo collections. It automatically sorts, renames, and clusters images based on metadata, making it easy to manage large sets of photos from trips or events. The project aims to support advanced features like duplicate detection, timeline and map generation, and collaborative photo filtering, with future plans for exporting to print-ready formats.

## Supported File Formats

Memory Lane CLI currently supports the following file formats:

- **Images:** JPG, JPEG, PNG, HEIC
- **Videos:** MOV, MP4

Support for additional formats may be added in the future.

## MVP

- From a folder full of images, find all images which are the same (no matter the name of the file)
- Rename images to YYYY-MM-DD-HHMM-SS-Author.png, using pillow and metadata of the image


## TODO

- Based photo filtering (based on human choice, location and time)
- Meta-data time-line and GPS location usage, for GPX-like map route generation
- Latex book export for easy printing service
