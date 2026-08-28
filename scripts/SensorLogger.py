import ctypes
import ctypes.wintypes
import datetime
import glob
import os
import sys
import tkinter as tk
import queue
import threading
from tkinter import filedialog


def _get_scale_factor() -> float:
    return ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100


def _set_window_icon(window: tk.Tk) -> None:
    icon_path = os.path.join(
        os.environ.get("PROGRAMDATA", "C:\\ProgramData"),
        "ABB",
        "PickMaster",
        "PMScripts",
        "ExternalSensorIcon.ico",
    )
    if not os.path.exists(icon_path):
        return
    try:
        window.iconbitmap(icon_path)
    except Exception:
        # Never block UI if icon cannot be loaded by the local Tk runtime.
        pass


def _default_filename() -> str:
    return "ExternalSensor.log"


def _default_folder() -> str:
    return r"C:\PMScriptsLog"


def _default_enabled() -> bool:
    return False


# Config string format: "enabled|folder|filename"
# | is not a valid Windows path character, so it is safe as a separator.

def serialize_config(enabled: bool, folder: str, filename: str) -> str:
    return "{}|{}|{}".format("1" if enabled else "0", folder, filename)


def deserialize_config(config_str: str) -> tuple:
    """Returns (enabled: bool, folder: str, filename: str)."""
    if config_str and "|" in config_str:
        parts = config_str.split("|", 2)
        if len(parts) == 3:
            return parts[0] == "1", parts[1], parts[2]
    return _default_enabled(), _default_folder(), _default_filename()


class SensorLogger:
    """Timestamped file logger controlled by a stored config string."""

    MAX_LOG_FILE_SIZE_BYTES = 50 * 1024 * 1024
    MAX_ROTATED_LOG_FILES = 5
    _write_queue: queue.Queue = queue.Queue()
    _worker_started = False
    _worker_lock = threading.Lock()

    def __init__(self, config_str: str = "") -> None:
        self.enabled, self.folder, self.filename = deserialize_config(config_str)

    @property
    def log_path(self) -> str:
        return os.path.join(self.folder, self.filename)

    @classmethod
    def _rotate_log_file(cls, log_path: str) -> None:
        if not os.path.exists(log_path):
            return

        base_name, extension = os.path.splitext(log_path)
        rotated_name = "{}_{}{}".format(
            base_name,
            datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
            extension,
        )
        os.replace(log_path, rotated_name)

        rotated_files = sorted(
            glob.glob("{}_*{}".format(base_name, extension)),
            key=os.path.getmtime,
        )
        while len(rotated_files) > cls.MAX_ROTATED_LOG_FILES:
            oldest_file = rotated_files.pop(0)
            try:
                os.remove(oldest_file)
            except OSError:
                pass

    @classmethod
    def _start_worker(cls) -> None:
        with cls._worker_lock:
            if cls._worker_started:
                return
            threading.Thread(target=cls._write_worker, name="SensorLogger", daemon=True).start()
            cls._worker_started = True

    @classmethod
    def _write_worker(cls) -> None:
        while True:
            log_path, folder, line = cls._write_queue.get()
            try:
                os.makedirs(folder, exist_ok=True)
                if os.path.exists(log_path) and os.path.getsize(log_path) >= cls.MAX_LOG_FILE_SIZE_BYTES:
                    cls._rotate_log_file(log_path)
                with open(log_path, "a", encoding="utf-8") as log_file:
                    log_file.write(line)
            except OSError as error:
                print("[SensorLogger] Failed to write log: {}".format(error), file=sys.stderr)
            finally:
                cls._write_queue.task_done()

    def log(self, context: str, message: str = "", success: bool = False) -> None:
        if not self.enabled:
            return
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        mark = "[SUCCESS]" if success else "[ERROR]"
        line = "[{}] {} [{}] {}\n".format(timestamp, mark, context, message)
        self._start_worker()
        self._write_queue.put((self.log_path, self.folder, line))


def show_logger_config_dialog(input_title: str, config_str: str) -> tuple:
    """Show the logger configuration dialog.

    Returns (is_valid: bool, new_config_str: str).
    is_valid is False when the user cancelled without saving.
    """
    enabled, folder, filename = deserialize_config(config_str)

    window = tk.Tk()
    window.title(input_title)
    window.resizable(False, False)
    window.attributes("-topmost", True)
    _set_window_icon(window)
    window["bg"] = "#ffffff"

    scale_factor = _get_scale_factor()
    scaled_x = int(scale_factor * 500)
    scaled_y = int(scale_factor * 230)
    ww = window.winfo_screenwidth()
    wh = window.winfo_screenheight()
    pos_x = int(ww / 2 - 500 * scale_factor / 2)
    pos_y = int(wh / 2 - 230 * scale_factor / 2)
    window.geometry("{}x{}+{}+{}".format(scaled_x, scaled_y, pos_x, pos_y))

    result_config: list[str] = [""]
    is_valid: list[bool] = [False]

    frame_main = tk.Frame(window, bg="#ffffff")
    frame_main.pack(fill="both", expand=True, padx=22, pady=(14, 0))

    # --- Enable checkbox ---
    var_enabled = tk.BooleanVar(value=enabled)
    frame_chk = tk.Frame(frame_main, bg="#ffffff")
    frame_chk.pack(side="top", fill="x", pady=(0, 12))
    chk_enable = tk.Checkbutton(
        frame_chk,
        text="Enable logging",
        variable=var_enabled,
        font=("ABBvoice", 9),
        bg="#ffffff",
        activebackground="#ffffff",
        command=lambda: _toggle_fields(),
    )
    chk_enable.pack(side="left")

    # --- Folder row ---
    frame_folder = tk.Frame(frame_main, bg="#ffffff")
    frame_folder.pack(side="top", fill="x", pady=(0, 8))
    tk.Label(
        frame_folder, text="Log folder:", font=("ABBvoice", 9), bg="#ffffff", width=11, anchor="w"
    ).pack(side="left")
    frame_folder_entry = tk.Frame(
        frame_folder, highlightbackground="#bababa", highlightcolor="#bababa", borderwidth=2
    )
    frame_folder_entry.pack(side="left", expand=True, fill="both")
    txt_folder = tk.Entry(frame_folder_entry, font=("ABBvoice", 9), relief="solid", borderwidth=0)
    txt_folder.pack(expand=True, fill="both")
    txt_folder.insert(0, folder)

    btn_browse = tk.Button(
        frame_folder,
        text="Browse",
        font=("ABBvoice", 9),
        width=8,
        relief="solid",
        borderwidth=1,
        bg="#ffffff",
        activebackground="#ffffff",
        command=lambda: _browse_folder(),
    )
    btn_browse.pack(side="left", padx=(6, 0))

    # --- Filename row ---
    frame_file = tk.Frame(frame_main, bg="#ffffff")
    frame_file.pack(side="top", fill="x", pady=(0, 4))
    tk.Label(
        frame_file, text="File name:", font=("ABBvoice", 9), bg="#ffffff", width=11, anchor="w"
    ).pack(side="left")
    frame_file_entry = tk.Frame(
        frame_file, highlightbackground="#bababa", highlightcolor="#bababa", borderwidth=2
    )
    frame_file_entry.pack(side="left", expand=True, fill="both")
    txt_file = tk.Entry(frame_file_entry, font=("ABBvoice", 9), relief="solid", borderwidth=0)
    txt_file.pack(expand=True, fill="both")
    txt_file.insert(0, filename)

    # --- Info label ---
    tk.Label(
        frame_main,
        text="Default file name: {}".format(_default_filename()),
        font=("ABBvoice", 9),
        fg="#bababa",
        bg="#ffffff",
        justify="left",
    ).pack(side="top", anchor="w")

    # --- Error label ---
    lb_error = tk.Label(
        frame_main, text="", font=("ABBvoice", 9), fg="#ffffff", bg="#ffffff", justify="left"
    )
    lb_error.pack(side="top", anchor="w", pady=(2, 0))

    def _toggle_fields() -> None:
        state = "normal" if var_enabled.get() else "disabled"
        txt_folder.config(state=state)
        txt_file.config(state=state)
        btn_browse.config(state=state)

    def _browse_folder() -> None:
        initial = txt_folder.get() if os.path.isdir(txt_folder.get()) else _default_folder()
        chosen = filedialog.askdirectory(parent=window, initialdir=initial)
        if chosen:
            txt_folder.delete(0, "end")
            txt_folder.insert(0, chosen.replace("/", "\\"))

    def _close_window() -> None:
        folder_val = txt_folder.get().strip()
        file_val = txt_file.get().strip()
        if var_enabled.get():
            if not folder_val:
                lb_error.config(text="Please select a log folder.", fg="red")
                return
            if not file_val:
                lb_error.config(text="Please enter a file name.", fg="red")
                return
        result_config[0] = serialize_config(var_enabled.get(), folder_val, file_val)
        is_valid[0] = True
        window.destroy()

    # --- Buttons ---
    frame_btn_row = tk.Frame(window, bg="#ffffff")
    frame_btn_row.pack(side="bottom", fill="x", padx=16, pady=(0, 16))

    frame_btn = tk.Frame(
        frame_btn_row,
        bg="#3366FF",
        highlightbackground="#3366FF",
        highlightcolor="#3366FF",
        borderwidth=1,
    )
    frame_btn.pack(side="right")

    tk.Button(
        frame_btn,
        text="Cancel",
        font=("ABBvoice", 9),
        width=12,
        relief="solid",
        borderwidth=0,
        bg="#ffffff",
        activebackground="#ffffff",
        command=window.destroy,
    ).pack(pady=(0, 4))

    tk.Button(
        frame_btn_row,
        text="OK",
        font=("ABBvoice", 9),
        width=12,
        relief="solid",
        borderwidth=0,
        bg="#3366FF",
        fg="white",
        activebackground="#3366FF",
        command=_close_window,
    ).pack(side="right", padx=(0, 12))

    window.protocol("WM_DELETE_WINDOW", window.destroy)
    _toggle_fields()
    window.mainloop()

    return is_valid[0], result_config[0]
