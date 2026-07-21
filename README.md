# PDF Photo Album Generator

This project is a Python script designed to automate the creation of photo albums in PDF format from an image directory (supports `.jpg`, `.jpeg` and `.png` formats). It generates asymmetrical, elegant and dynamic photo grids, and automatically sorts the images chronologically, prioritizing the date from the filename, EXIF metadata, or creation date as a fallback.

## Main Features

- **Chronological Sorting:** The script determines the date and time of each photograph following this priority order to sort them correctly:
  1. **Filename**: Checks if it has a specific date format (e.g., `2006-11-12_12-20-32`).
  2. **EXIF Metadata**: Reads tags like `DateTimeOriginal`, `DateTimeDigitized` or `DateTime` hidden in the original photograph.
  3. **Creation Date**: If the file lacks this data (e.g., images received via WhatsApp without EXIF), it uses the file's creation date on the system.
- **Dynamic and Asymmetrical Grids:** You can let the script randomly choose the page designs from a predefined list of highly visual aesthetic options, or you can freely specify which specific grid styles you want to use.
- **Automatic Cover:** Generates a first page that acts as a cover with a custom title and automatically includes the date range of the inputted photographs (e.g., *"From 12/03/2023 to 15/04/2023"*).
- **Time Information (Optional):** You can choose whether you want the date, the time, both at the same time, or to leave it blank under each photo (*Polaroid* style).
- **Careful and Elegant Design:** Uses A4 format with smart margins, a soft cream/gray background, and photo frames with shadows to simulate the look of real printed images, automatically correcting the visual orientation of vertically taken ones according to the camera's sensors.

## Requirements and Installation

This project requires **Python 3** and the following libraries:
- `Pillow` (for EXIF extraction and image manipulation)
- `reportlab` (for PDF document construction)

You can easily install them if you have the `requirements.txt` file:
```bash
pip install -r requirements.txt
```
*(Alternatively: `pip install Pillow reportlab`)*

## How to Use It

To run it easily with the default options (looking for images in the `Fotos` folder and without printing the date on the cells), simply execute:

```bash
python albumFotos.py
```
This will create a file named `album_def.pdf` inside your directory.

### Parameters (Command Line Arguments)

You can customize almost all aspects of the document directly from the terminal call using arguments (flags):

- `-i` or `--input`: Specifies the name or path of the source folder containing the photos to process. (Default: `Fotos`)
- `-o` or `--output`: Indicates the desired name for the PDF file to be created. (Default: `album_def.pdf`)
- `-t` or `--title`: Defines the title that will head the album cover. (Default: `"El meu Àlbum de Fotos"`)
- `--show-date`: Enables the inclusion of the photograph's date at the bottom of the cell (e.g., `14/05/2023`).
- `--show-time`: Enables the inclusion of the exact time at the bottom of the cell (e.g., `15:30`).
- `--layouts`: Allows you to force the exclusive use of certain grid styles you prefer, passing them as a comma-separated string.

### Examples and Use Cases

**1. Generate the album printing both the date and time of each photograph:**
```bash
python albumFotos.py --show-date --show-time
```

**2. Create an album from another folder, setting the title and the final document name:**
```bash
python albumFotos.py -i "Vacances_Roma" -o "Roma_2023.pdf" -t "Trip to Rome 2023"
```

**3. Complete example combining several options and forcing specific page designs:**
```bash
python albumFotos.py -i "Images" -o "MyParty.pdf" -t "Birthday Party" --show-date --layouts "2x2,3,2-3"
```

### How does the `--layouts` parameter work?

The layouts describe the structure of a page's photo grid. If you decide to set which ones to use with `--layouts`, you must use this nomenclature (using commas to separate multiple designs, which will alternate randomly):

- **XxF**: Creates multiple identical rows with the same elements. E.g., `2x2` indicates 2 rows and 2 columns per row (4 photos in total).
- **A-B-C**: Asymmetrical row designs indicating the quantity at each step. E.g., `2-3` means there will be 2 photos in the 1st row and 3 in the 2nd. If it were `1-2-1` there would be one on top, two in the middle, and one at the bottom.
- **N**: A single row fitting `N` photos. E.g., `3` (1 horizontal row fitting 3).

Valid arguments example: `--layouts "2x2,2-3,1-2-1,3"`
*(Note: If there are photos left at the end that do not meet the capacity of a complete grid, the program has auto-generated fallback structures to place them elegantly at the end of the document)*
