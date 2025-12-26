import os
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
import threading
import subprocess
import tempfile
import sys 
import math 

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

DEFAULT_AVIFENC_SUBDIR = "libavif" 
DEFAULT_AVIFENC_EXE_NAME = "avifenc.exe"
DEFAULT_AVIFENC_EXE_PATH = os.path.normpath(os.path.join(BUNDLED_DATA_PATH, DEFAULT_AVIFENC_SUBDIR, DEFAULT_AVIFENC_EXE_NAME))

DEFAULT_EXIFTOOL_SUBDIR = "exiftool"
DEFAULT_EXIFTOOL_EXE_NAME = "exiftool.exe"
DEFAULT_EXIFTOOL_EXE_PATH = os.path.normpath(os.path.join(BUNDLED_DATA_PATH, DEFAULT_EXIFTOOL_SUBDIR, DEFAULT_EXIFTOOL_EXE_NAME))

DEFAULT_INPUT_SUBDIR = "input"
DEFAULT_OUTPUT_SUBDIR = "output"
DEFAULT_INPUT_FOLDER_PATH = os.path.normpath(os.path.join(APPLICATION_PATH, DEFAULT_INPUT_SUBDIR))
DEFAULT_OUTPUT_FOLDER_PATH = os.path.normpath(os.path.join(APPLICATION_PATH, DEFAULT_OUTPUT_SUBDIR))

# Global variables
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
    global _CJXL_AVAILABLE, _CJXL_VERSION_INFO, CJXL_EXECUTABLE_PATH
    global _AVIFENC_AVAILABLE, _AVIFENC_VERSION_INFO, AVIFENC_EXECUTABLE_PATH
    global _EXIFTOOL_AVAILABLE, _EXIFTOOL_VERSION_INFO, EXIFTOOL_EXECUTABLE_PATH

    path_to_check = ""
    version_cmd_args = []

    if encoder_type_to_check == "cjxl":
        path_to_check = CJXL_EXECUTABLE_PATH
        version_cmd_args = [path_to_check, "--version"]
    elif encoder_type_to_check == "avifenc":
        path_to_check = AVIFENC_EXECUTABLE_PATH
        version_cmd_args = [path_to_check, "--version"]
    elif encoder_type_to_check == "exiftool":
        path_to_check = EXIFTOOL_EXECUTABLE_PATH
        version_cmd_args = [path_to_check, "-ver"]
    else:
        return False

    available_flag = False
    version_info_str = ""

    try:
        process = subprocess.run(version_cmd_args,
                                 capture_output=True, text=True, check=True,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        version_info_str = process.stdout.strip() if encoder_type_to_check == "exiftool" else (process.stdout.strip() + ((" | " + process.stderr.strip()) if process.stderr.strip() else ""))
        available_flag = True
    except Exception as e:
        version_info_str = str(e)

    if encoder_type_to_check == "cjxl":
        _CJXL_AVAILABLE, _CJXL_VERSION_INFO = available_flag, version_info_str
    elif encoder_type_to_check == "avifenc":
        _AVIFENC_AVAILABLE, _AVIFENC_VERSION_INFO = available_flag, version_info_str
    elif encoder_type_to_check == "exiftool":
        _EXIFTOOL_AVAILABLE, _EXIFTOOL_VERSION_INFO = available_flag, version_info_str
    
    return available_flag

def convert_raw_files_core(source_folder, output_folder, 
                           quality_value, lossless_mode, 
                           progress_callback, status_callback,
                           resolution_scale, copy_metadata, output_format_str, recursive):
    global _CJXL_AVAILABLE, _AVIFENC_AVAILABLE, _EXIFTOOL_AVAILABLE

    output_format_upper = output_format_str.upper()
    output_extension = ".jxl" if output_format_upper == "JXL" else ".avif"
    current_encoder_path = CJXL_EXECUTABLE_PATH if output_format_upper == "JXL" else AVIFENC_EXECUTABLE_PATH
    encoder_name = os.path.basename(current_encoder_path)

    supported_exts = (".raf", ".png")
    tasks = []

    if recursive:
        for root, dirs, files in os.walk(source_folder):
            for f in files:
                if f.lower().endswith(supported_exts):
                    full_src = os.path.join(root, f)
                    rel_path = os.path.relpath(full_src, source_folder)
                    tasks.append((full_src, rel_path))
    else:
        for f in os.listdir(source_folder):
            if f.lower().endswith(supported_exts):
                tasks.append((os.path.join(source_folder, f), f))

    total_files = len(tasks)
    if total_files == 0:
        if status_callback: status_callback("No supported files found.")
        return

    temp_dir_obj = tempfile.TemporaryDirectory(prefix="img2convert_")
    temp_dir = temp_dir_obj.name

    try:
        for index, (src_path, rel_path) in enumerate(tasks):
            base_name = os.path.splitext(os.path.basename(src_path))[0]
            # Sanitize filename
            safe_base = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in base_name).rstrip()
            
            # Recreate subfolder structure in output
            rel_dir = os.path.dirname(rel_path)
            target_output_dir = os.path.join(output_folder, rel_dir)
            os.makedirs(target_output_dir, exist_ok=True)

            dest_path = os.path.join(target_output_dir, safe_base + output_extension)
            
            if os.path.exists(dest_path):
                if status_callback: status_callback(f"Skipping: {rel_path} (Exists)")
                if progress_callback: progress_callback(index + 1, total_files)
                continue

            if status_callback: status_callback(f"Processing ({index+1}/{total_files}): {rel_path}")
            
            try:
                # Load Image
                if src_path.lower().endswith(".raf"):
                    with rawpy.imread(src_path) as raw:
                        rgb_array = raw.postprocess(use_camera_wb=True, output_bps=8, output_color=rawpy.ColorSpace.sRGB)
                    pil_image = Image.fromarray(rgb_array, mode='RGB')
                else:
                    pil_image = Image.open(src_path)
                    if pil_image.mode not in ("RGB", "RGBA"):
                        pil_image = pil_image.convert("RGBA" if "A" in pil_image.mode or pil_image.info.get("transparency") else "RGB")

                # Resize
                if resolution_scale != 1.0:
                    nw, nh = int(pil_image.width * resolution_scale), int(pil_image.height * resolution_scale)
                    pil_image = pil_image.resize((nw, nh), Image.Resampling.LANCZOS)

                intermediate_png = os.path.join(temp_dir, f"tmp_{index}.png")
                pil_image.save(intermediate_png, format="PNG")

                # Encode
                cmd = [current_encoder_path, intermediate_png, dest_path]
                if output_format_upper == "JXL":
                    cmd.extend(["-d", "0"] if lossless_mode else ["-q", str(quality_value)])
                else:
                    cmd.extend(["-q", "100" if lossless_mode else str(quality_value), "--depth", "10", "--yuv", "444"])

                subprocess.run(cmd, capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

                # Metadata
                if copy_metadata and _EXIFTOOL_AVAILABLE:
                    exif_cmd = [EXIFTOOL_EXECUTABLE_PATH, "-tagsFromFile", src_path, "-all:all", "-overwrite_original", dest_path]
                    subprocess.run(exif_cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            except Exception as e:
                if status_callback: status_callback(f"Error processing {rel_path}: {e}", error=True)

            if progress_callback: progress_callback(index + 1, total_files)
    finally:
        temp_dir_obj.cleanup()
    if status_callback: status_callback("Process Finished.")

class RAFConverterApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Image Converter (Recursive)")
        self.root.geometry("750x980") 

        self.source_folder_var = tk.StringVar(value=DEFAULT_INPUT_FOLDER_PATH)
        self.output_folder_var = tk.StringVar(value=DEFAULT_OUTPUT_FOLDER_PATH)
        self.recursive_var = tk.BooleanVar(value=False)
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

        # --- Tools UI ---
        tool_config_main_frame = ttk.LabelFrame(main_frame, text="External Tool Configuration", padding="10")
        tool_config_main_frame.pack(fill=tk.X, pady=(0,10))
        
        for tool, var, lbl_attr in [("cjxl", self.cjxl_path_var, "cjxl_status_label"), 
                                    ("avifenc", self.avifenc_path_var, "avifenc_status_label"), 
                                    ("exiftool", self.exiftool_path_var, "exiftool_status_label")]:
            f = ttk.Frame(tool_config_main_frame, padding=(0,0,0,5))
            f.pack(fill=tk.X)
            ttk.Label(f, text=f"Path to {tool}:", width=15).grid(row=0, column=0, sticky=tk.W)
            ttk.Entry(f, textvariable=var).grid(row=0, column=1, sticky=tk.EW, padx=5)
            ttk.Button(f, text="Check", command=lambda t=tool: self.check_tool_path_from_gui(t)).grid(row=0, column=2)
            setattr(self, lbl_attr, ttk.Label(f, text="Status: Not checked", font=("Arial", 8)))
            getattr(self, lbl_attr).grid(row=1, column=1, sticky=tk.W)
            f.columnconfigure(1, weight=1)

        # --- Folder UI ---
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding="10")
        folder_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(folder_frame, text="Source Folder:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(folder_frame, textvariable=self.source_folder_var).grid(row=0, column=1, sticky=tk.EW, padx=5)
        ttk.Button(folder_frame, text="Browse...", command=self.browse_source_folder).grid(row=0, column=2)
        
        # RECURSIVE CHECKBOX
        ttk.Checkbutton(folder_frame, text="Recursive (Include sub-directories)", variable=self.recursive_var).grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(folder_frame, text="Output Folder:").grid(row=2, column=0, sticky=tk.W, pady=(10,0))
        ttk.Entry(folder_frame, textvariable=self.output_folder_var).grid(row=2, column=1, sticky=tk.EW, padx=5, pady=(10,0))
        ttk.Button(folder_frame, text="Browse...", command=self.browse_output_folder).grid(row=2, column=2, pady=(10,0))
        folder_frame.columnconfigure(1, weight=1)

        # --- Options UI ---
        self.options_frame = ttk.LabelFrame(main_frame, text="Conversion Options", padding="10")
        self.options_frame.pack(fill=tk.X, pady=10)

        fmt_f = ttk.Frame(self.options_frame); fmt_f.pack(fill=tk.X)
        ttk.Label(fmt_f, text="Output Format:").pack(side=tk.LEFT)
        ttk.Radiobutton(fmt_f, text="JXL", variable=self.output_format_var, value="JXL").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(fmt_f, text="AVIF", variable=self.output_format_var, value="AVIF").pack(side=tk.LEFT)

        ttk.Checkbutton(self.options_frame, text="Lossless", variable=self.lossless_var, command=self.toggle_quality_scale).pack(anchor=tk.W, pady=5)
        
        q_f = ttk.Frame(self.options_frame); q_f.pack(fill=tk.X)
        ttk.Label(q_f, text="Quality (1-100):").pack(side=tk.LEFT)
        self.quality_scale = ttk.Scale(q_f, from_=1, to=100, variable=self.quality_var, orient=tk.HORIZONTAL)
        self.quality_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.quality_label_val = ttk.Label(q_f, text="90", width=4); self.quality_label_val.pack(side=tk.LEFT)
        self.quality_var.trace_add("write", lambda *a: self.quality_label_val.config(text=str(int(self.quality_var.get()))))
        
        res_f = ttk.Frame(self.options_frame); res_f.pack(fill=tk.X, pady=5)
        ttk.Label(res_f, text="Resolution Scale:").pack(side=tk.LEFT)
        ttk.Entry(res_f, textvariable=self.resolution_scale_var, width=8).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(self.options_frame, text="Copy metadata (ExifTool)", variable=self.copy_metadata_var).pack(anchor=tk.W)

        # --- Action & Log ---
        self.start_button = ttk.Button(main_frame, text="Start Conversion", command=self.start_conversion_thread)
        self.start_button.pack(pady=10, fill=tk.X)

        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=5)
        self.status_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=12, state=tk.DISABLED)
        self.status_text.pack(expand=True, fill=tk.BOTH)

        # Initial checks
        self.check_tool_path_from_gui("cjxl", True)
        self.check_tool_path_from_gui("avifenc", True)
        self.check_tool_path_from_gui("exiftool", True)

    def check_tool_path_from_gui(self, tool, init=False):
        global CJXL_EXECUTABLE_PATH, AVIFENC_EXECUTABLE_PATH, EXIFTOOL_EXECUTABLE_PATH
        if tool == "cjxl": CJXL_EXECUTABLE_PATH = self.cjxl_path_var.get().strip()
        elif tool == "avifenc": AVIFENC_EXECUTABLE_PATH = self.avifenc_path_var.get().strip()
        elif tool == "exiftool": EXIFTOOL_EXECUTABLE_PATH = self.exiftool_path_var.get().strip()
        
        available = check_specific_encoder_availability(tool)
        lbl = getattr(self, f"{tool}_status_label")
        if available:
            lbl.config(text="Status: OK", foreground="green")
        else:
            lbl.config(text="Status: Not Found", foreground="red")
        return available

    def log_status(self, msg, error=False):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, ("ERROR: " if error else "") + msg + "\n")
        self.status_text.see(tk.END); self.status_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def browse_source_folder(self):
        path = filedialog.askdirectory()
        if path: self.source_folder_var.set(path)

    def browse_output_folder(self):
        path = filedialog.askdirectory()
        if path: self.output_folder_var.set(path)

    def toggle_quality_scale(self):
        s = tk.DISABLED if self.lossless_var.get() else tk.NORMAL
        self.quality_scale.config(state=s)

    def start_conversion_thread(self):
        self.start_button.config(state=tk.DISABLED)
        t = threading.Thread(target=convert_raw_files_core, args=(
            self.source_folder_var.get(), self.output_folder_var.get(),
            int(self.quality_var.get()), self.lossless_var.get(),
            lambda c, total: self.progress_bar.config(value=(c/total)*100),
            self.log_status, self.resolution_scale_var.get(),
            self.copy_metadata_var.get(), self.output_format_var.get(),
            self.recursive_var.get()
        ), daemon=True)
        t.start()
        self.root.after(100, lambda: self.monitor(t))

    def monitor(self, t):
        if t.is_alive(): self.root.after(100, lambda: self.monitor(t))
        else: self.start_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    RAFConverterApp(root)
    root.mainloop()