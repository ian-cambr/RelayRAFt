import os
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
import threading
import subprocess
import tempfile
# import shutil # Keep for potential future use, though tempfile.TemporaryDirectory handles its own cleanup
import sys # For PyInstaller path detection
import math # For rounding quality values

# --- Core Dependencies Check ---
try:
    import rawpy
except ImportError:
    messagebox.showerror("Dependency Error", "The 'rawpy' library is not installed.\nPlease install it: pip install rawpy")
    if getattr(sys, 'frozen', False): print("CRITICAL ERROR: rawpy not found. Application cannot start.")
    sys.exit(1)

try:
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except ImportError:
    messagebox.showerror("Dependency Error", "The 'Pillow' library is not installed.\nPlease install it: pip install Pillow")
    if getattr(sys, 'frozen', False): print("CRITICAL ERROR: Pillow not found. Application cannot start.")
    sys.exit(1)

# --- Determine Base Paths ---
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BUNDLED_DATA_PATH = sys._MEIPASS
    APPLICATION_PATH = os.path.dirname(sys.executable)
elif __file__:
    script_path = os.path.abspath(__file__)
    BUNDLED_DATA_PATH = os.path.dirname(script_path)
    APPLICATION_PATH = os.path.dirname(script_path)
else:
    BUNDLED_DATA_PATH = os.getcwd()
    APPLICATION_PATH = os.getcwd()

# --- Default Path Configurations ---
DEFAULT_CJXL_SUBDIR = "cjxl"
DEFAULT_CJXL_EXE_NAME = "cjxl.exe"
DEFAULT_CJXL_EXE_PATH = os.path.normpath(os.path.join(BUNDLED_DATA_PATH, DEFAULT_CJXL_SUBDIR, DEFAULT_CJXL_EXE_NAME))

DEFAULT_AVIFENC_SUBDIR = "libavif" # As per user specification
DEFAULT_AVIFENC_EXE_NAME = "avifenc.exe"
DEFAULT_AVIFENC_EXE_PATH = os.path.normpath(os.path.join(BUNDLED_DATA_PATH, DEFAULT_AVIFENC_SUBDIR, DEFAULT_AVIFENC_EXE_NAME))

DEFAULT_EXIFTOOL_SUBDIR = "exiftool"
DEFAULT_EXIFTOOL_EXE_NAME = "exiftool.exe"
DEFAULT_EXIFTOOL_EXE_PATH = os.path.normpath(os.path.join(BUNDLED_DATA_PATH, DEFAULT_EXIFTOOL_SUBDIR, DEFAULT_EXIFTOOL_EXE_NAME))

DEFAULT_INPUT_SUBDIR = "input"
DEFAULT_OUTPUT_SUBDIR = "output"
DEFAULT_INPUT_FOLDER_PATH = os.path.normpath(os.path.join(APPLICATION_PATH, DEFAULT_INPUT_SUBDIR))
DEFAULT_OUTPUT_FOLDER_PATH = os.path.normpath(os.path.join(APPLICATION_PATH, DEFAULT_OUTPUT_SUBDIR))

# Global variables for encoder paths and status, updated by GUI checks
CJXL_EXECUTABLE_PATH = DEFAULT_CJXL_EXE_PATH
_CJXL_AVAILABLE = False
_CJXL_VERSION_INFO = "Not checked"

AVIFENC_EXECUTABLE_PATH = DEFAULT_AVIFENC_EXE_PATH
_AVIFENC_AVAILABLE = False
_AVIFENC_VERSION_INFO = "Not checked"

EXIFTOOL_EXECUTABLE_PATH = DEFAULT_EXIFTOOL_EXE_PATH
_EXIFTOOL_AVAILABLE = False
_EXIFTOOL_VERSION_INFO = "Not checked"

def check_specific_encoder_availability(encoder_type_to_check):
    """
    Checks availability of a specific encoder or tool (cjxl, avifenc, exiftool).
    Updates global status vars for that tool.
    """
    global _CJXL_AVAILABLE, _CJXL_VERSION_INFO, CJXL_EXECUTABLE_PATH
    global _AVIFENC_AVAILABLE, _AVIFENC_VERSION_INFO, AVIFENC_EXECUTABLE_PATH
    global _EXIFTOOL_AVAILABLE, _EXIFTOOL_VERSION_INFO, EXIFTOOL_EXECUTABLE_PATH

    path_to_check = ""
    exe_display_name = ""
    version_cmd_args = []

    if encoder_type_to_check == "cjxl":
        path_to_check = CJXL_EXECUTABLE_PATH
        exe_display_name = "cjxl.exe"
        version_cmd_args = [path_to_check, "--version"]
    elif encoder_type_to_check == "avifenc":
        path_to_check = AVIFENC_EXECUTABLE_PATH
        exe_display_name = "avifenc.exe"
        version_cmd_args = [path_to_check, "--version"]
    elif encoder_type_to_check == "exiftool":
        path_to_check = EXIFTOOL_EXECUTABLE_PATH
        exe_display_name = "exiftool.exe"
        version_cmd_args = [path_to_check, "-ver"]
    else:
        return False # Should not happen

    available_flag = False
    version_info_str = ""

    try:
        process = subprocess.run(version_cmd_args,
                                 capture_output=True, text=True, check=True,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if encoder_type_to_check == "exiftool": # exiftool -ver only outputs version to stdout
            version_info_str = process.stdout.strip()
        else:
            version_info_str = process.stdout.strip() + ((" | " + process.stderr.strip()) if process.stderr.strip() else "")
        available_flag = True
    except FileNotFoundError:
        version_info_str = f"'{path_to_check}' not found. Ensure it's in the expected location or the path is correctly set."
    except subprocess.CalledProcessError as e:
        version_info_str = f"Error calling '{' '.join(version_cmd_args)}': {e.stderr.strip() if e.stderr else 'No stderr'}"
    except Exception as e:
        version_info_str = f"An unexpected error occurred while checking '{path_to_check}': {e}"

    if encoder_type_to_check == "cjxl":
        _CJXL_AVAILABLE = available_flag
        _CJXL_VERSION_INFO = version_info_str
    elif encoder_type_to_check == "avifenc":
        _AVIFENC_AVAILABLE = available_flag
        _AVIFENC_VERSION_INFO = version_info_str
    elif encoder_type_to_check == "exiftool":
        _EXIFTOOL_AVAILABLE = available_flag
        _EXIFTOOL_VERSION_INFO = version_info_str
    
    return available_flag

# --- Core Conversion Logic ---
def convert_raw_files_core(source_folder, output_folder, 
                           quality_value, lossless_mode, 
                           progress_callback, status_callback,
                           resolution_scale, copy_metadata, output_format_str):
    global _CJXL_AVAILABLE, _CJXL_VERSION_INFO, CJXL_EXECUTABLE_PATH
    global _AVIFENC_AVAILABLE, _AVIFENC_VERSION_INFO, AVIFENC_EXECUTABLE_PATH
    global _EXIFTOOL_AVAILABLE, _EXIFTOOL_VERSION_INFO, EXIFTOOL_EXECUTABLE_PATH

    output_format_upper = output_format_str.upper()
    output_extension = ""
    current_encoder_path = ""
    encoder_name_for_log = ""

    if output_format_upper == "JXL":
        if not _CJXL_AVAILABLE:
            if status_callback: status_callback(f"Error: cjxl.exe is not available or not working. Last status: {_CJXL_VERSION_INFO}", error=True)
            return
        output_extension = ".jxl"
        current_encoder_path = CJXL_EXECUTABLE_PATH
        encoder_name_for_log = "cjxl.exe"
    elif output_format_upper == "AVIF":
        if not _AVIFENC_AVAILABLE:
            if status_callback: status_callback(f"Error: avifenc.exe is not available or not working. Last status: {_AVIFENC_VERSION_INFO}", error=True)
            return
        output_extension = ".avif"
        current_encoder_path = AVIFENC_EXECUTABLE_PATH
        encoder_name_for_log = "avifenc.exe"
    else:
        if status_callback: status_callback(f"Error: Unsupported output format '{output_format_str}'.", error=True)
        return
        
    if status_callback: status_callback(f"Target output format: {output_format_upper} using {encoder_name_for_log}")

    if not os.path.exists(source_folder):
        if status_callback: status_callback(f"Error: Source folder '{source_folder}' does not exist.", error=True)
        return
    if not os.path.exists(output_folder):
        try:
            os.makedirs(output_folder)
            if status_callback: status_callback(f"Created output folder: {output_folder}")
        except OSError as e:
            if status_callback: status_callback(f"Error creating output folder '{output_folder}': {e}", error=True)
            return

    raf_files = [f for f in os.listdir(source_folder) if f.lower().endswith(".raf")]
    total_files = len(raf_files)

    if total_files == 0:
        if status_callback: status_callback(f"No .RAF files found in '{source_folder}'.")
        if progress_callback: progress_callback(0, 0)
        return

    temp_dir_obj = tempfile.TemporaryDirectory(prefix="raf2img_")
    temp_dir = temp_dir_obj.name
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    try:
        for index, filename in enumerate(raf_files):
            raf_path = os.path.join(source_folder, filename)
            base_filename = os.path.splitext(filename)[0]
            safe_base_filename = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in base_filename).rstrip()
            
            output_filename_with_ext = safe_base_filename + output_extension
            output_file_full_path = os.path.join(output_folder, output_filename_with_ext)
            
            intermediate_png_path = os.path.join(temp_dir, f"{safe_base_filename}_temp.png")

            output_filename_jxl = safe_base_filename + ".jxl" # For checking existence
            output_file_full_path_jxl = os.path.join(output_folder, output_filename_jxl)
            output_filename_avif = safe_base_filename + ".avif" # For checking existence
            output_file_full_path_avif = os.path.join(output_folder, output_filename_avif)

            skip_processing = False
            skip_reason = ""
            if output_format_upper == "JXL" and os.path.exists(output_file_full_path_jxl):
                skip_processing = True; skip_reason = f"Output file '{output_filename_jxl}' already exists."
            elif output_format_upper == "AVIF" and os.path.exists(output_file_full_path_avif):
                 skip_processing = True; skip_reason = f"Output file '{output_filename_avif}' already exists."
            
            if skip_processing:
                if status_callback: status_callback(f"Skipping ({index+1}/{total_files}): {filename}. {skip_reason}")
                if progress_callback: progress_callback(index + 1, total_files)
                continue

            if status_callback: status_callback(f"Processing ({index+1}/{total_files}): {filename} -> {output_filename_with_ext}")

            try:
                if status_callback: status_callback(f"  Reading RAW: {filename}")
                with rawpy.imread(raf_path) as raw:
                    # MODIFIED: Changed output_bps from 16 to 8 for 24-bit RGB PNG
                    rgb_array = raw.postprocess(use_camera_wb=True, output_bps=8,
                                                output_color=rawpy.ColorSpace.sRGB, no_auto_bright=False)
                pil_image = Image.fromarray(rgb_array, mode='RGB')
                
                if resolution_scale != 1.0:
                    original_width, original_height = pil_image.size
                    new_width = int(original_width * resolution_scale)
                    new_height = int(original_height * resolution_scale)
                    if new_width > 0 and new_height > 0:
                        if status_callback: status_callback(f"  Resizing from {original_width}x{original_height} to {new_width}x{new_height} (scale: {resolution_scale:.2f})")
                        pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    else:
                        if status_callback: status_callback(f"  Warning: Invalid new dimensions for {filename}. Original size used.", warning=True)
                
                # MODIFIED: Log message updated to reflect 8-bit PNG
                if status_callback: status_callback(f"  Saving intermediate 8-bit PNG: {os.path.basename(intermediate_png_path)}")
                pil_image.save(intermediate_png_path, format="PNG")
            except Exception as e:
                if status_callback: status_callback(f"  Error processing RAW {filename} to PNG: {e}. Skipping.", error=True)
                if progress_callback: progress_callback(index + 1, total_files)
                continue 

            encoder_cmd = [current_encoder_path, intermediate_png_path, output_file_full_path]
            
            if output_format_upper == "JXL":
                if lossless_mode:
                    encoder_cmd.extend(["-d", "0"]) 
                else:
                    encoder_cmd.extend(["-q", str(quality_value)])
            elif output_format_upper == "AVIF":
                if lossless_mode:
                    encoder_cmd.extend(["-q", "100", "--depth", "10", "--yuv", "444"])
                else:
                    encoder_cmd.extend(["-q", str(quality_value), "--depth", "10", "--yuv", "444"])

            encoding_successful = False
            try:
                if status_callback: status_callback(f"  Encoding to {output_format_upper} (Lossless: {lossless_mode}, GUI Quality: {quality_value if not lossless_mode else '100'}): {output_filename_with_ext}")
                
                process = subprocess.run(encoder_cmd, capture_output=True, text=True, check=True, creationflags=creation_flags)
                
                if process.stderr and status_callback:
                    for line in process.stderr.splitlines():
                        if line.strip(): status_callback(f"    {encoder_name_for_log}: {line.strip()}")
                if status_callback: status_callback(f"  Saved {output_format_upper}: {output_file_full_path}")
                encoding_successful = True

            except FileNotFoundError:
                 if status_callback: status_callback(f"Error: '{current_encoder_path}' not found during conversion. Stopping batch.", error=True)
                 if output_format_upper == "JXL": _CJXL_AVAILABLE = False
                 elif output_format_upper == "AVIF": _AVIFENC_AVAILABLE = False
                 return 
            except subprocess.CalledProcessError as e:
                if status_callback:
                    status_callback(f"  Error encoding {output_filename_with_ext} with {encoder_name_for_log}. Skipping.", error=True)
                    status_callback(f"    Command: {' '.join(e.cmd)}", error=True)
                    status_callback(f"    Return Code: {e.returncode}", error=True)
                    status_callback(f"    Stdout: {e.stdout.strip() if e.stdout else ''}", error=True)
                    status_callback(f"    Stderr: {e.stderr.strip() if e.stderr else ''}", error=True)
            except Exception as e:
                if status_callback: status_callback(f"  Unexpected error during {output_format_upper} encoding for {filename}: {e}. Skipping.", error=True)

            if encoding_successful and copy_metadata:
                if _EXIFTOOL_AVAILABLE:
                    exiftool_cmd = [
                    EXIFTOOL_EXECUTABLE_PATH,
                    "-tagsFromFile", raf_path,
                    # Camera-related metadata
                    "-Make", "-Model",
                    "-Artist", "-Copyright",
                    "-DateTimeOriginal", "-CreateDate", "-ModifyDate",
                    "-ISO", "-ExposureTime", "-FNumber",
                    "-FocalLength", "-LensModel", "-LensMake",
                    "-WhiteBalance",
                    # GPS metadata (safe to transfer)
                    "-GPSLatitude", "-GPSLongitude", "-GPSAltitude",
                    "-GPSLatitudeRef", "-GPSLongitudeRef", "-GPSAltitudeRef",
                    "-GPSTimeStamp", "-GPSDateStamp",
                    # Descriptive metadata
                    "-Title", "-Description", "-Keywords", "-Subject",
                    "-Creator", "-Rights",
                    # Miscellaneous
                    "-m", "-overwrite_original",
                    output_file_full_path
                ]

                try:
                    env = os.environ.copy()
                    env['LANG'] = 'C.UTF-8'
                    exif_process = subprocess.run(
                        exiftool_cmd,
                        capture_output=True,
                        text=True,
                        check=True,
                        creationflags=creation_flags,
                        env=env
                    )

                    if exif_process.stdout and status_callback:
                        for line in exif_process.stdout.splitlines():
                            if line.strip():
                                if "image files updated" in line.lower() or "image files created" in line.lower():
                                    status_callback(f"      ExifTool: {line.strip()}")
                                else:
                                    status_callback(f"      ExifTool (info): {line.strip()}")

                    if exif_process.stderr and status_callback:
                        for line in exif_process.stderr.splitlines():
                            if line.strip():
                                status_callback(f"      ExifTool (stderr/warning): {line.strip()}", warning=True)

                    if status_callback:
                        status_callback(f"    Successfully copied safe metadata (including GPS) to {output_filename_with_ext}")

                except subprocess.CalledProcessError as e_exif:
                    if status_callback:
                        status_callback(f"    Error copying metadata to {output_filename_with_ext} using ExifTool. File is encoded, but metadata may be missing/original.", error=True)
                        status_callback(f"      ExifTool Command: {' '.join(e_exif.cmd)}", error=True)
                        status_callback(f"      Return Code: {e_exif.returncode}", error=True)
                        status_callback(f"      Stdout: {e_exif.stdout.strip() if e_exif.stdout else ''}", error=True)
                        status_callback(f"      Stderr: {e_exif.stderr.strip() if e_exif.stderr else ''}", error=True)
                except FileNotFoundError:
                    if status_callback: status_callback(f"Error: '{EXIFTOOL_EXECUTABLE_PATH}' not found during metadata copy. Disabling ExifTool for this session.", error=True)
                    _EXIFTOOL_AVAILABLE = False 
                except Exception as e_exif_other:
                    if status_callback: status_callback(f"    Unexpected error during ExifTool operation for {output_filename_with_ext}: {e_exif_other}", error=True)
                
            elif status_callback: 
                status_callback(f"    Skipping metadata copy: ExifTool is not available or not configured correctly. Last status: {_EXIFTOOL_VERSION_INFO}", warning=True)

            if progress_callback:
                progress_callback(index + 1, total_files)
    finally:
        if status_callback: status_callback(f"Temporary directory {temp_dir} will be cleaned up.")
        temp_dir_obj.cleanup()

    if status_callback: status_callback(f"Batch conversion process ({output_format_upper}) finished.")


# --- GUI Application Logic ---
class RAFConverterApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("RAF Converter (cjxl.exe / avifenc.exe / exiftool.exe)")
        self.root.geometry("750x980") 

        self.source_folder_var = tk.StringVar(value=DEFAULT_INPUT_FOLDER_PATH)
        self.output_folder_var = tk.StringVar(value=DEFAULT_OUTPUT_FOLDER_PATH)
        self.lossless_var = tk.BooleanVar(value=False)
        self.quality_var = tk.IntVar(value=90)
        
        self.cjxl_path_var = tk.StringVar(value=DEFAULT_CJXL_EXE_PATH)
        self.avifenc_path_var = tk.StringVar(value=DEFAULT_AVIFENC_EXE_PATH)
        self.exiftool_path_var = tk.StringVar(value=DEFAULT_EXIFTOOL_EXE_PATH)

        self.output_format_var = tk.StringVar(value="JXL")
        self.resolution_scale_var = tk.DoubleVar(value=1.0)
        self.copy_metadata_var = tk.BooleanVar(value=True)

        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)

        title_label = ttk.Label(main_frame, text="RAF to JXL/AVIF Batch Converter", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 15))

        tool_config_main_frame = ttk.LabelFrame(main_frame, text="External Tool Configuration", padding="10")
        tool_config_main_frame.pack(fill=tk.X, pady=(0,10))

        cjxl_frame = ttk.Frame(tool_config_main_frame, padding=(0,0,0,10))
        cjxl_frame.pack(fill=tk.X)
        ttk.Label(cjxl_frame, text="Path to cjxl.exe:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        cjxl_entry = ttk.Entry(cjxl_frame, textvariable=self.cjxl_path_var, width=60)
        cjxl_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(cjxl_frame, text="Check cjxl", command=lambda: self.check_tool_path_from_gui("cjxl")).grid(row=0, column=2, padx=5, pady=5)
        self.cjxl_status_label = ttk.Label(cjxl_frame, text="Status: (Auto-checked on start)", wraplength=650, justify=tk.LEFT)
        self.cjxl_status_label.grid(row=1, column=0, columnspan=3, padx=5, pady=(0,5), sticky=tk.W)
        cjxl_frame.columnconfigure(1, weight=1)

        avifenc_frame = ttk.Frame(tool_config_main_frame, padding=(0,0,0,10))
        avifenc_frame.pack(fill=tk.X)
        ttk.Label(avifenc_frame, text="Path to avifenc.exe:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        avifenc_entry = ttk.Entry(avifenc_frame, textvariable=self.avifenc_path_var, width=60)
        avifenc_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(avifenc_frame, text="Check avifenc", command=lambda: self.check_tool_path_from_gui("avifenc")).grid(row=0, column=2, padx=5, pady=5)
        self.avifenc_status_label = ttk.Label(avifenc_frame, text="Status: (Auto-checked on start)", wraplength=650, justify=tk.LEFT)
        self.avifenc_status_label.grid(row=1, column=0, columnspan=3, padx=5, pady=(0,5), sticky=tk.W)
        avifenc_frame.columnconfigure(1, weight=1)

        exiftool_frame = ttk.Frame(tool_config_main_frame) 
        exiftool_frame.pack(fill=tk.X)
        ttk.Label(exiftool_frame, text="Path to exiftool.exe:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        exiftool_entry = ttk.Entry(exiftool_frame, textvariable=self.exiftool_path_var, width=60)
        exiftool_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(exiftool_frame, text="Check ExifTool", command=lambda: self.check_tool_path_from_gui("exiftool")).grid(row=0, column=2, padx=5, pady=5)
        self.exiftool_status_label = ttk.Label(exiftool_frame, text="Status: (Auto-checked on start)", wraplength=650, justify=tk.LEFT)
        self.exiftool_status_label.grid(row=1, column=0, columnspan=3, padx=5, pady=(0,5), sticky=tk.W)
        exiftool_frame.columnconfigure(1, weight=1)

        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding="10")
        folder_frame.pack(fill=tk.X, pady=10)
        ttk.Label(folder_frame, text="Source RAF Folder:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        source_entry = ttk.Entry(folder_frame, textvariable=self.source_folder_var, width=50)
        source_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(folder_frame, text="Browse...", command=self.browse_source_folder).grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(folder_frame, text="Output Folder:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        output_entry = ttk.Entry(folder_frame, textvariable=self.output_folder_var, width=50)
        output_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(folder_frame, text="Browse...", command=self.browse_output_folder).grid(row=1, column=2, padx=5, pady=5)
        folder_frame.columnconfigure(1, weight=1)

        self.options_frame = ttk.LabelFrame(main_frame, text="Conversion Options", padding="10")
        self.options_frame.pack(fill=tk.X, pady=10)

        format_frame = ttk.Frame(self.options_frame)
        format_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Label(format_frame, text="Output Format:").pack(side=tk.LEFT, padx=(0,10), pady=5)
        ttk.Radiobutton(format_frame, text="JXL", variable=self.output_format_var, value="JXL", command=self.update_ui_for_format).pack(side=tk.LEFT, pady=5)
        ttk.Radiobutton(format_frame, text="AVIF", variable=self.output_format_var, value="AVIF", command=self.update_ui_for_format).pack(side=tk.LEFT, padx=(5,0), pady=5)

        self.lossless_check = ttk.Checkbutton(self.options_frame, text="Lossless", variable=self.lossless_var, command=self.toggle_quality_scale) 
        self.lossless_check.pack(anchor=tk.W, pady=5)
        
        quality_frame = ttk.Frame(self.options_frame)
        quality_frame.pack(fill=tk.X, pady=(0,5))
        ttk.Label(quality_frame, text="Quality (1-100, lossy only):").pack(side=tk.LEFT, padx=(0,5), pady=5)
        self.quality_scale = ttk.Scale(quality_frame, from_=1, to=100, variable=self.quality_var, orient=tk.HORIZONTAL, length=200)
        self.quality_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)
        self.quality_label_val = ttk.Label(quality_frame, text=str(int(self.quality_var.get())), width=4)
        self.quality_label_val.pack(side=tk.LEFT, padx=5, pady=5)
        self.quality_var.trace_add("write", lambda *args: self.quality_label_val.config(text=str(int(self.quality_var.get()))))
        
        resolution_frame = ttk.Frame(self.options_frame)
        resolution_frame.pack(fill=tk.X, pady=5)
        ttk.Label(resolution_frame, text="Resolution Scale:").pack(side=tk.LEFT, padx=(0,5), pady=5)
        self.resolution_scale_entry = ttk.Entry(resolution_frame, textvariable=self.resolution_scale_var, width=5)
        self.resolution_scale_entry.pack(side=tk.LEFT, padx=(0,5), pady=5)
        self.resolution_scale_val_label = ttk.Label(resolution_frame, text=f"{self.resolution_scale_var.get():.2f}", width=4)
        self.resolution_scale_val_label.pack(side=tk.LEFT, padx=(0,5), pady=5)
        ttk.Label(resolution_frame, text="(e.g., 0.5, 1.0)").pack(side=tk.LEFT, pady=5)
        
        def update_resolution_display(*args):
            try: val = float(self.resolution_scale_var.get()); self.resolution_scale_val_label.config(text=f"{val:.2f}")
            except ValueError: self.resolution_scale_val_label.config(text="---")
        self.resolution_scale_var.trace_add("write", update_resolution_display)
        update_resolution_display()

        self.copy_metadata_check = ttk.Checkbutton(self.options_frame, text="Copy metadata from source (requires ExifTool)", variable=self.copy_metadata_var)
        self.copy_metadata_check.pack(anchor=tk.W, pady=5)
        
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10)
        self.start_button = ttk.Button(action_frame, text="Start Conversion", command=self.start_conversion_thread, style="Accent.TButton")
        self.start_button.pack(pady=10, ipady=5, fill=tk.X)

        progress_status_frame = ttk.LabelFrame(main_frame, text="Progress & Log", padding="10")
        progress_status_frame.pack(expand=True, fill=tk.BOTH, pady=(5,0))
        self.progress_bar = ttk.Progressbar(progress_status_frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=(5,10), fill=tk.X)
        self.status_text = scrolledtext.ScrolledText(progress_status_frame, wrap=tk.WORD, height=10, state=tk.DISABLED, relief=tk.SOLID, borderwidth=1)
        self.status_text.pack(expand=True, fill=tk.BOTH, pady=5)
        self.status_text.tag_config("error_tag", foreground="red")
        self.status_text.tag_config("warning_tag", foreground="orange")
        self.status_text.tag_config("info_tag", foreground="blue")

        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 12, "bold"), padding=5)

        self.create_default_directories()
        self.check_tool_path_from_gui("cjxl", initial_check=True)
        self.check_tool_path_from_gui("avifenc", initial_check=True)
        self.check_tool_path_from_gui("exiftool", initial_check=True)
        self.toggle_quality_scale() 
        self.update_ui_for_format()
        self._init_complete = True


    def update_ui_for_format(self):
        selected_format = self.output_format_var.get()
        self.options_frame.config(text=f"Conversion Options ({selected_format})")
        
        lossless_text = "Lossless Conversion ("
        if selected_format == "JXL":
            lossless_text += "cjxl -d 0)"
        elif selected_format == "AVIF":
            lossless_text += "avifenc -q 100)" 
        self.lossless_check.config(text=lossless_text)

        if hasattr(self, '_init_complete') and self._init_complete: 
            self.log_status(f"Output format set to {selected_format}.", tag="info_tag")


    def create_default_directories(self):
        if not os.path.exists(DEFAULT_INPUT_FOLDER_PATH):
            try: os.makedirs(DEFAULT_INPUT_FOLDER_PATH); self.log_status(f"Created default input directory: {DEFAULT_INPUT_FOLDER_PATH}", tag="info_tag")
            except OSError as e: self.log_status(f"Could not create default input directory {DEFAULT_INPUT_FOLDER_PATH}: {e}", warning=True)
        else: self.log_status(f"Default input directory already exists: {DEFAULT_INPUT_FOLDER_PATH}", tag="info_tag")


    def check_tool_path_from_gui(self, tool_type, initial_check=False):
        global CJXL_EXECUTABLE_PATH, _CJXL_AVAILABLE, _CJXL_VERSION_INFO
        global AVIFENC_EXECUTABLE_PATH, _AVIFENC_AVAILABLE, _AVIFENC_VERSION_INFO
        global EXIFTOOL_EXECUTABLE_PATH, _EXIFTOOL_AVAILABLE, _EXIFTOOL_VERSION_INFO

        path_var, status_label_widget, exe_name_log = (None, None, "")
        
        if tool_type == "cjxl":
            path_var, status_label_widget, exe_name_log = self.cjxl_path_var, self.cjxl_status_label, "cjxl.exe"
            CJXL_EXECUTABLE_PATH = path_var.get().strip() 
        elif tool_type == "avifenc":
            path_var, status_label_widget, exe_name_log = self.avifenc_path_var, self.avifenc_status_label, "avifenc.exe"
            AVIFENC_EXECUTABLE_PATH = path_var.get().strip()
        elif tool_type == "exiftool":
            path_var, status_label_widget, exe_name_log = self.exiftool_path_var, self.exiftool_status_label, "exiftool.exe"
            EXIFTOOL_EXECUTABLE_PATH = path_var.get().strip()
        else: return False

        user_path = path_var.get().strip()
        if not user_path:
            status_msg = f"{exe_name_log} path cannot be empty."
            status_label_widget.config(text=f"Status: {status_msg}", foreground="red")
            if not initial_check: messagebox.showerror(f"{tool_type.upper()} Error", status_msg)
            if tool_type == "cjxl": _CJXL_AVAILABLE = False
            elif tool_type == "avifenc": _AVIFENC_AVAILABLE = False
            elif tool_type == "exiftool": _EXIFTOOL_AVAILABLE = False
            return False

        check_specific_encoder_availability(tool_type) 
        
        current_available, current_version_info = (False, "")
        if tool_type == "cjxl": current_available, current_version_info = _CJXL_AVAILABLE, _CJXL_VERSION_INFO
        elif tool_type == "avifenc": current_available, current_version_info = _AVIFENC_AVAILABLE, _AVIFENC_VERSION_INFO
        elif tool_type == "exiftool": current_available, current_version_info = _EXIFTOOL_AVAILABLE, _EXIFTOOL_VERSION_INFO
        
        if current_available:
            status_label_widget.config(text=f"Status: OK! Version: {current_version_info}", foreground="green")
            if not initial_check: self.log_status(f"{exe_name_log} check: OK. Path: '{user_path}'. Version: {current_version_info}", tag="info_tag")
        else:
            status_label_widget.config(text=f"Status: Error! {current_version_info}", foreground="red")
            if not initial_check:
                self.log_status(f"{exe_name_log} check failed for path '{user_path}': {current_version_info}", error=True)
                messagebox.showerror(f"{tool_type.upper()} Error", f"{exe_name_log} not found or not working at '{user_path}':\n{current_version_info}\n\nPlease ensure {exe_name_log} is at the specified path and is executable.")
        return current_available

    def log_status(self, message, error=False, warning=False, tag=None):
        self.status_text.config(state=tk.NORMAL)
        final_tag = ("error_tag",) if error else ("warning_tag",) if warning else (tag,) if tag else ()
        prefix = "ERROR: " if error else "WARNING: " if warning else ""
        self.status_text.insert(tk.END, prefix + message + "\n", final_tag)
        self.status_text.see(tk.END); self.status_text.config(state=tk.DISABLED); self.root.update_idletasks()

    def update_progress(self, current_val, total_val):
        self.progress_bar["value"] = (current_val / total_val) * 100 if total_val > 0 else 0
        self.root.update_idletasks()

    def browse_source_folder(self):
        initial_dir = self.source_folder_var.get()
        if not os.path.isdir(initial_dir): initial_dir = os.path.dirname(initial_dir)
        if not os.path.exists(initial_dir): initial_dir = APPLICATION_PATH 
        folder_selected = filedialog.askdirectory(title="Select Source RAF Folder", initialdir=initial_dir)
        if folder_selected:
            self.source_folder_var.set(folder_selected)
            self.log_status(f"Source folder selected: {folder_selected}")
            if self.output_folder_var.get() == DEFAULT_OUTPUT_FOLDER_PATH: 
                suggested_output = os.path.join(folder_selected, DEFAULT_OUTPUT_SUBDIR)
                self.output_folder_var.set(suggested_output)
                self.log_status(f"Output folder automatically set to: {suggested_output}", tag="info_tag")

    def browse_output_folder(self):
        current_output, initial_dir = self.output_folder_var.get(), APPLICATION_PATH
        if os.path.isdir(current_output): initial_dir = current_output
        elif os.path.isdir(os.path.dirname(current_output)): initial_dir = os.path.dirname(current_output)
        elif os.path.isdir(self.source_folder_var.get()): initial_dir = self.source_folder_var.get()
        if not os.path.exists(initial_dir): initial_dir = os.getcwd() 
        folder_selected = filedialog.askdirectory(title="Select Output Folder", initialdir=initial_dir)
        if folder_selected: self.output_folder_var.set(folder_selected); self.log_status(f"Output folder selected: {folder_selected}")

    def toggle_quality_scale(self):
        state = tk.DISABLED if self.lossless_var.get() else tk.NORMAL
        self.quality_scale.config(state=state)
        self.quality_label_val.config(state=state)

    def start_conversion_thread(self):
        selected_format = self.output_format_var.get()
        encoder_type_to_check = "cjxl" if selected_format == "JXL" else "avifenc"
        
        if not self.check_tool_path_from_gui(encoder_type_to_check): 
             self.log_status(f"{encoder_type_to_check}.exe is not configured correctly. Please check the path and try again.", error=True)
             return

        if self.copy_metadata_var.get() and not _EXIFTOOL_AVAILABLE:
            self.log_status(f"Metadata copying is enabled, but exiftool.exe is not available or configured. Last status: {_EXIFTOOL_VERSION_INFO}. Metadata will not be copied.", warning=True)
            
        source, output = self.source_folder_var.get(), self.output_folder_var.get()
        try:
            resolution_scale_value = float(self.resolution_scale_var.get())
            if resolution_scale_value <= 0: messagebox.showerror("Input Error", "Resolution scale must be positive."); return
        except ValueError: messagebox.showerror("Input Error", "Invalid resolution scale."); return
        
        if not source or not output: messagebox.showerror("Input Error", "Select source and output folders."); return
        if not os.path.isdir(source): messagebox.showerror("Input Error", f"Source folder does not exist: {source}"); return
        if not os.path.exists(output):
            try: os.makedirs(output); self.log_status(f"Created output folder: {output}")
            except OSError as e: messagebox.showerror("Output Error", f"Could not create output folder: {e}"); return
        elif not os.path.isdir(output): messagebox.showerror("Output Error", f"Output path is a file: {output}"); return

        self.start_button.config(state=tk.DISABLED); self.progress_bar["value"] = 0
        self.log_status(f"Starting conversion to {selected_format} using {encoder_type_to_check}.exe...")

        conv_thread = threading.Thread(target=convert_raw_files_core, args=(
            source, output, int(self.quality_var.get()), self.lossless_var.get(),
            self.update_progress, self.log_status, resolution_scale_value,
            self.copy_metadata_var.get(), selected_format), daemon=True)
        conv_thread.start()
        self.root.after(100, self.check_conversion_thread, conv_thread)

    def check_conversion_thread(self, thread):
        if thread.is_alive(): self.root.after(100, self.check_conversion_thread, thread)
        else: self.start_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    app_root = tk.Tk()
    app = RAFConverterApp(app_root)
    app_root.mainloop()