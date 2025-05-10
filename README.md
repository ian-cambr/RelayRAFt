# RelayRAFt: Fuji .RAF to JXL/AVIF Converter

RelayRAFt is a Python-based graphical user interface (GUI) application designed to batch convert Fujifilm's proprietary .RAF (RAW) image files into modern, efficient image formats: JPEG XL (.jxl) or AVIF (.avif). It leverages powerful external command-line tools for the conversion process, providing a user-friendly way to manage these conversions.

## Use Case

Photographers using Fujifilm cameras who shoot in RAW (.RAF) format often need to convert their images to more widely compatible or space-efficient formats for archiving, sharing, or web use. JPEG XL and AVIF offer significant advantages in terms of compression efficiency and feature sets (like HDR and lossless compression) compared to older formats like JPEG. If you just want to use the tool, feel free to download the latest Windows executable from the Releases tab.

This tool aims to:
*   Simplify the batch conversion of .RAF files.
*   Provide control over output quality, including lossless options.
*   Allow image resizing during conversion.
*   Enable copying of essential metadata (including GPS tags) from the source .RAF to the output JXL/AVIF file.
*   Offer a straightforward GUI, removing the need for complex command-line incantations for users.

## Features

*   **Batch Conversion:** Process multiple .RAF files from a selected folder.
*   **Output Formats:**
    *   JPEG XL (.jxl) via `cjxl.exe`
    *   AVIF (.avif) via `avifenc.exe`
*   **Conversion Options:**
    *   **Lossless/Lossy Control:** Choose between lossless conversion or adjustable lossy quality.
    *   **Quality Slider (Lossy):** Fine-tune compression quality (1-100) for lossy JXL and AVIF.
    *   **Resolution Scaling:** Resize images (e.g., 0.5 for half-size, 1.0 for original size).
*   **Metadata Handling:**
    *   Option to copy metadata (EXIF, IPTC, GPS, etc.) from source .RAF to output files using `exiftool.exe`.
*   **User-Friendly GUI:**
    *   Easy selection of source and output folders.
    *   Configuration of external tool paths (`cjxl.exe`, `avifenc.exe`, `exiftool.exe`).
    *   Real-time status checks for external tools.
    *   Progress bar and detailed logging of the conversion process.
*   **Smart Defaults:**
    *   Automatically suggests default input/output folders.
    *   Attempts to locate bundled executables in predefined subdirectories.
*   **Error Handling:**
    *   Checks for Python library dependencies (`rawpy`, `Pillow`).
    *   Verifies availability and functionality of external tools.

## Prerequisites and Setup

### 1. Python Environment

*   **Python 3.7+** is recommended.
*   **Required Python Libraries:**
    *   `rawpy`: For reading and processing .RAF files.
    *   `Pillow`: For intermediate image manipulation (e.g., creating temporary PNGs).

    Install them using pip:
    ```bash
    pip install rawpy Pillow
    ```

### 2. External Tools (Executables)

You need to download the following command-line executables and place them in specific subdirectories relative to where `RelayRAFt.py` is run, or where the bundled application is located.

*   **`cjxl.exe` (for JPEG XL encoding):**
    *   Part of the `libjxl` project.
    *   Download pre-compiled binaries from the official `libjxl` releases page on GitHub (e.g., look for Windows CI artifacts or releases from projects that bundle `libjxl` like `jpeg-xl-toolbox`).
    *   **Expected location:** `cjxl/cjxl.exe`

*   **`avifenc.exe` (for AVIF encoding):**
    *   Part of the `libavif` project.
    *   Download pre-compiled binaries from the official `libavif` releases page on GitHub or from community builds (e.g., via `scoop` or other package managers for developers).
    *   **Expected location:** `libavif/avifenc.exe`

*   **`exiftool.exe` (for metadata copying):**
    *   By Phil Harvey.
    *   Download from the [ExifTool Official Website](https://exiftool.org/). Get the "Windows Executable" version. Rename `exiftool(-k).exe` to `exiftool.exe`.
    *   **Expected location:** `exiftool/exiftool.exe`

### 3. Directory Structure

If running the script directly, your directory structure should look like this:
RelayRAFt_Project/
├── RelayRAFt.py # The main script
├── cjxl/
│ └── cjxl.exe
├── libavif/
│ └── avifenc.exe
├── exiftool/
│ └── exiftool.exe
├── input/ # Default source folder (optional, created if not present)
└── output/ # Default output folder (optional, created if not present)

If you build an executable (see [Building](#building-with-pyinstaller)), these subdirectories (`cjxl`, `libavif`, `exiftool`) should be bundled with the application or placed relative to the main executable.

## Usage

1.  **Prepare:** Ensure Python and the required libraries are installed, and the external tools (`cjxl.exe`, `avifenc.exe`, `exiftool.exe`) are in their respective subdirectories (`cjxl/`, `libavif/`, `exiftool/`) next to the script.
2.  **Run the script:**
    ```bash
    python RelayRAFt.py
    ```
3.  **Configure Tool Paths (if necessary):**
    *   The application will attempt to auto-detect the tools in the default subdirectories.
    *   If a tool is not found or you wish to use a different version/location, update the path in the "External Tool Configuration" section of the GUI and click the corresponding "Check" button. The status (OK or Error) will be displayed.
4.  **Select Folders:**
    *   **Source RAF Folder:** Browse to the folder containing your .RAF files.
    *   **Output Folder:** Browse to or create a folder where the converted JXL/AVIF files will be saved.
5.  **Set Conversion Options:**
    *   **Output Format:** Choose "JXL" or "AVIF".
    *   **Lossless:** Check for lossless encoding. This disables the quality slider.
        *   For JXL: uses `cjxl -d 0`
        *   For AVIF: uses `avifenc -q 100` (highest quality, effectively lossless for RGB input)
    *   **Quality (1-100):** If not lossless, adjust the quality slider. Higher values mean better quality and larger files.
    *   **Resolution Scale:** Enter a scaling factor (e.g., `1.0` for original size, `0.5` for half size, `2.0` for double size).
    *   **Copy metadata:** Check this to transfer EXIF and other metadata from the .RAF file to the output file using ExifTool. (Requires ExifTool to be configured correctly).
6.  **Start Conversion:**
    *   Click the "Start Conversion" button.
    *   Progress will be shown in the progress bar, and detailed logs will appear in the text area below.
    *   The application will skip files if an output file with the same name already exists in the target format.
    *   Error messages or warnings from the external tools will also be logged.

## Building (with PyInstaller)

You can package `RelayRAFt.py` into a standalone executable using PyInstaller.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```
2.  **Bundle the application:**
    Ensure `cjxl.exe`, `avifenc.exe`, and `exiftool.exe` are in their respective subdirectories (`cjxl/`, `libavif/`, `exiftool/`) relative to `RelayRAFt.py`.

    Open your terminal/command prompt in the directory containing `RelayRAFt.py` and run:
    ```bash
    python -m PyInstaller --name RelayRAFt --windowed --onefile --add-data "cjxl:cjxl" --add-data "libavif:libavif" --add-data "exiftool:exiftool" RelayRAFt.py
    ```
    *   `--onefile`: Creates a single executable file.
    *   `--windowed`: Prevents a console window from appearing when the GUI app runs.
    *   `--add-data "source_folder;destination_in_bundle"`: Bundles the external tool directories.
        *   On Windows, use `;` as the separator: `cjxl;cjxl`.
        *   On macOS/Linux, use `:` as the separator: `cjxl:cjxl`.

    The executable will be found in the `dist` folder. The `cjxl`, `libavif`, and `exiftool` folders (with their executables) will be bundled alongside the main executable at runtime (PyInstaller extracts them to a temporary location).

## Troubleshooting

*   **"Dependency Error: 'rawpy'/'Pillow' library is not installed."**
    *   Make sure you have installed the required Python libraries: `pip install rawpy Pillow`.
*   **"cjxl.exe/avifenc.exe/exiftool.exe Status: Error! ... not found."**
    *   Ensure the respective `.exe` file is present in the correct subdirectory (`cjxl/`, `libavif/`, `exiftool/`) relative to the script or bundled application.
    *   Verify the path in the GUI's "External Tool Configuration" section is correct and click "Check".
    *   Make sure the executables have permission to run.
*   **Conversion fails for specific files:**
    *   The .RAF file might be corrupted.
    *   Check the log output for specific errors from `rawpy`, `cjxl.exe`, or `avifenc.exe`.
*   **Metadata not copied:**
    *   Ensure `exiftool.exe` is correctly configured and its status shows "OK!".
    *   The "Copy metadata" checkbox must be enabled.
    *   Some very specific or custom metadata tags might not be transferred by the default ExifTool command used.

## Licenses

This project, `RelayRAFt.py`, relies on several external tools and libraries, each with its own license. The use of these tools is subject to their respective licenses.

### RelayRAFt.py (This Application)
This `RelayRAFt.py` script itself and the compiled executable is provided with a specific license above. Please see LICENSE in the source.

### External Tools & Libraries:

**1. cjxl.exe (libjxl - JPEG XL Reference Implementation)**

The `libjxl` library and its associated tools like `cjxl.exe` are distributed under various permissive licenses for its different components. The primary license is the 3-Clause BSD License, but it also incorporates code under other compatible licenses.

*   **Primary License (JPEG XL Project Authors):**
    ```
    Copyright (c) the JPEG XL Project Authors.
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this
       list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright notice,
       this list of conditions and the following disclaimer in the documentation
       and/or other materials provided with the distribution.

    3. Neither the name of the copyright holder nor the names of its
       contributors may be used to endorse or promote products derived from
       this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
    FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
    DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
    CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
    OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    ```
*   **Other components within libjxl may be covered by (includes but not limited to):**
    *   Joe Drago License (similar to 2-Clause BSD)
    *   VideoLAN and dav1d authors License (2-Clause BSD)
    *   Independent JPEG Group (IJG) License
    *   Emmanuel Gil Peyrot License (2-Clause BSD)
    *   Apache License 2.0
    *   LibYuv Project Authors License (3-Clause BSD)

    Please refer to the `LICENSE` file distributed with `libjxl` for full details.

**2. avifenc.exe (libavif)**

The `libavif` library and its associated tools like `avifenc.exe` are primarily licensed under the 2-Clause BSD license. It also depends on other libraries (like libaom, rav1e, libdav1d) which have their own compatible licenses.

*   **Primary License (libavif - Joe Drago / AOMedia):**
    ```
    Copyright 2019 Joe Drago. All rights reserved.
    (And/Or Copyright by Alliance for Open Media (AOMedia) and other contributors)

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
    FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
    DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
    CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
    OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    ```
*   **Components like dav1d (used by libavif):**
    ```
    Copyright © 2018-2019, VideoLAN and dav1d authors
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this
       list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright notice,
       this list of conditions and the following disclaimer in the documentation
       and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
    ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
    ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    ```
    Please refer to the `LICENSE` file distributed with `libavif` for full details.

**3. exiftool.exe (ExifTool by Phil Harvey)**

*   **License:**
    ```
    This is free software; you can redistribute it and/or modify it under the same terms as Perl itself.
    ```
    (This typically means it's available under either the GNU General Public License (GPL) or the Artistic License, at your option.)

**4. Python Libraries (rawpy, Pillow)**
*   **rawpy:** LibRaw license (LGPL v2.1 or CDDL v1.0)
*   **Pillow:** HPND License (Historical Permission Notice and Disclaimer)

Please ensure compliance with all applicable licenses when using or distributing this software or its bundled components.

## Acknowledgements

*   The **JPEG XL Project Authors** for `libjxl` and `cjxl.exe`.
*   **Joe Drago, AOMedia, and the libavif contributors** for `libavif` and `avifenc.exe`.
*   **Phil Harvey** for the invaluable `ExifTool`.
*   The developers of `rawpy` and `Pillow` libraries.
