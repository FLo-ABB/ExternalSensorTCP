# This software is provided 'as-is', without any express or
# implied warranty. In no event will ABB be held liable for
# any damages arising from the use of this software.

import ctypes
import os
import re
import socket
import tkinter as tk
from tkinter import filedialog
import SensorLogger


def _get_scale_factor():
    return ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100


def _set_window_icon(window):
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


def show_sensor_config_dialog(input_title: str, default_address: str, default_port: str, logger_config_str: str = ""):
    sensor_config_window = tk.Tk()
    sensor_config_window.title(input_title)

    scale_factor = _get_scale_factor()
    scaled_x = int(scale_factor * 470)
    scaled_y = int(scale_factor * 370)
    ww = sensor_config_window.winfo_screenwidth()
    wh = sensor_config_window.winfo_screenheight()
    pos_x = int(ww / 2 - 470 * scale_factor / 2)
    pos_y = int(wh / 2 - 370 * scale_factor / 2)
    sensor_config_window.geometry(
        str(scaled_x) + "x" + str(scaled_y) + "+" + str(pos_x) + "+" + str(pos_y)
    )
    sensor_config_window.resizable(False, False)
    sensor_config_window.attributes("-topmost", True)
    _set_window_icon(sensor_config_window)
    sensor_config_window["bg"] = "#ffffff"

    server_config = []
    is_config_valid = False

    frame_blk1 = tk.Frame(
        sensor_config_window,
        background="#ffffff",
        highlightbackground="#ffffff",
        highlightcolor="#ffffff",
        borderwidth=0,
    )
    frame_blk1.pack(side="top", fill="x", padx=(22, 16), pady=(10, 0))

    frame_ip = tk.Frame(frame_blk1, background="#ffffff", borderwidth=0)
    frame_ip.pack(side="top", fill="x", pady=(0, 8))
    lb_ip = tk.Label(frame_ip, text="TCP server IP: ", font=("ABBvoice", 9), background="#ffffff")
    lb_ip.pack(side="left", anchor="nw", padx=(0, 10), pady=(0, 0))
    frame_ip_entry = tk.Frame(
        frame_ip, highlightbackground="#bababa", highlightcolor="#bababa", borderwidth=2
    )
    frame_ip_entry.pack(side="left", expand=True, fill="both")
    txt_ip = tk.Entry(frame_ip_entry, font=("ABBvoice", 9), relief="solid", borderwidth=0)
    txt_ip.pack(expand=True, fill="both")

    frame_port_row = tk.Frame(frame_blk1, background="#ffffff", borderwidth=0)
    frame_port_row.pack(side="top", fill="x", pady=(0, 0))
    lb_tcp = tk.Label(
        frame_port_row, text="TCP server port: ", font=("ABBvoice", 9), background="#ffffff"
    )
    lb_tcp.pack(side="left", anchor="nw", padx=(0, 10), pady=(0, 0))
    frame_port = tk.Frame(
        frame_port_row, highlightbackground="#bababa", highlightcolor="#bababa", borderwidth=2
    )
    frame_port.pack(side="left", expand=True, fill="both")
    txt_port = tk.Entry(frame_port, font=("ABBvoice", 9), relief="solid", borderwidth=0)
    txt_port.pack(expand=True, fill="both")
    txt_port.columnconfigure(0, weight=1)

    label_info = tk.Label(
        frame_blk1,
        text="IP example: 192.168.0.9 | port should be integer between 0 - 65535",
        justify="left",
        font=("ABBvoice", 9),
        foreground="#bababa",
        background="#ffffff",
    )
    label_info.pack(side="top", anchor="w")
    frame_blk2 = tk.Frame(frame_blk1, background="#ffffff", borderwidth=0)
    frame_blk2.pack(side="left", anchor="w", fill="y")

    lb_wrong_input = tk.Label(
        frame_blk1,
        text="The entered IP address or port is invalid, please check your input.",
        wraplength=int(290 * scale_factor),
        font=("ABBvoice", 9),
        justify="left",
        fg="#ffffff",
        background="#ffffff",
    )
    lb_wrong_input.pack(side="left", anchor="w")

    lb_connection_status = tk.Label(
        frame_blk1,
        text="",
        wraplength=int(390 * scale_factor),
        font=("ABBvoice", 9),
        justify="left",
        fg="#ffffff",
        background="#ffffff",
    )
    lb_connection_status.pack(side="top", anchor="w")

    txt_ip.insert(0, str(default_address))
    txt_port.insert(0, str(default_port))

    logger_config_out = ""
    log_enabled, log_folder, log_filename = SensorLogger.deserialize_config(logger_config_str)
    var_log_enabled = tk.BooleanVar(value=log_enabled)

    frame_logger = tk.Frame(sensor_config_window, bg="#ffffff")
    frame_logger.pack(side="top", fill="x", padx=(22, 16), pady=(0, 4))

    frame_sep = tk.Frame(frame_logger, bg="#e0e0e0", height=1)
    frame_sep.pack(side="top", fill="x", pady=(4, 8))

    frame_log_chk = tk.Frame(frame_logger, bg="#ffffff")
    frame_log_chk.pack(side="top", fill="x", pady=(0, 6))
    chk_log = tk.Checkbutton(
        frame_log_chk,
        text="Enable logging",
        variable=var_log_enabled,
        font=("ABBvoice", 9),
        bg="#ffffff",
        activebackground="#ffffff",
        command=lambda: _toggle_log_fields(),
    )
    chk_log.pack(side="left")

    frame_log_folder = tk.Frame(frame_logger, bg="#ffffff")
    frame_log_folder.pack(side="top", fill="x", pady=(0, 6))
    tk.Label(
        frame_log_folder, text="Log folder:", font=("ABBvoice", 9), bg="#ffffff", width=11, anchor="w"
    ).pack(side="left")
    frame_log_folder_entry = tk.Frame(
        frame_log_folder, highlightbackground="#bababa", highlightcolor="#bababa", borderwidth=2
    )
    frame_log_folder_entry.pack(side="left", expand=True, fill="both")
    txt_log_folder = tk.Entry(frame_log_folder_entry, font=("ABBvoice", 9), relief="solid", borderwidth=0)
    txt_log_folder.pack(expand=True, fill="both")
    txt_log_folder.insert(0, log_folder)
    btn_log_browse = tk.Button(
        frame_log_folder,
        text="Browse",
        font=("ABBvoice", 9),
        width=8,
        relief="solid",
        borderwidth=1,
        bg="#ffffff",
        activebackground="#ffffff",
        command=lambda: _browse_log_folder(),
    )
    btn_log_browse.pack(side="left", padx=(6, 0))

    frame_log_file = tk.Frame(frame_logger, bg="#ffffff")
    frame_log_file.pack(side="top", fill="x", pady=(0, 4))
    tk.Label(
        frame_log_file, text="File name:", font=("ABBvoice", 9), bg="#ffffff", width=11, anchor="w"
    ).pack(side="left")
    frame_log_file_entry = tk.Frame(
        frame_log_file, highlightbackground="#bababa", highlightcolor="#bababa", borderwidth=2
    )
    frame_log_file_entry.pack(side="left", expand=True, fill="both")
    txt_log_file = tk.Entry(frame_log_file_entry, font=("ABBvoice", 9), relief="solid", borderwidth=0)
    txt_log_file.pack(expand=True, fill="both")
    txt_log_file.insert(0, log_filename)

    tk.Label(
        frame_logger,
        text="Default: {}".format(SensorLogger._default_filename()),
        font=("ABBvoice", 9),
        fg="#bababa",
        bg="#ffffff",
        justify="left",
    ).pack(side="top", anchor="w")

    def ip_checker(ip_address: str):
        pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(pattern, ip_address):
            return False
        for part in ip_address.split("."):
            if int(part) < 0 or int(part) > 255:
                return False
        return True

    def port_checker(port: str):
        return re.match(r"^\d+$", port) and int(port) >= 0 and int(port) <= 65535

    connection_test_passed = False

    def _toggle_log_fields() -> None:
        state = "normal" if var_log_enabled.get() else "disabled"
        txt_log_folder.config(state=state)
        txt_log_file.config(state=state)
        btn_log_browse.config(state=state)

    def _browse_log_folder() -> None:
        initial = txt_log_folder.get() if os.path.isdir(txt_log_folder.get()) else SensorLogger._default_folder()
        chosen = filedialog.askdirectory(parent=sensor_config_window, initialdir=initial)
        if chosen:
            txt_log_folder.delete(0, "end")
            txt_log_folder.insert(0, chosen.replace("/", "\\"))

    def reset_test_status(event=None):
        nonlocal connection_test_passed
        connection_test_passed = False
        btn_ok.config(state="disabled")
        lb_connection_status.config(text="", fg="#ffffff")

    def close_window():
        nonlocal server_config, is_config_valid, logger_config_out
        ip_address = txt_ip.get().strip()
        server_port = txt_port.get().strip()

        if not ip_checker(ip_address) or not port_checker(server_port):
            lb_wrong_input.config(fg="red")
            lb_connection_status.config(text="Invalid IP address or port.", fg="red")
            return

        if not connection_test_passed:
            lb_connection_status.config(
                text="Please click Test and get a successful connection before OK.",
                fg="red",
            )
            return

        server_config = "{};{}".format(ip_address, server_port)
        logger_config_out = SensorLogger.serialize_config(
            var_log_enabled.get(), txt_log_folder.get().strip(), txt_log_file.get().strip()
        )
        is_config_valid = True
        sensor_config_window.destroy()

    def test_connection():
        nonlocal connection_test_passed
        ip_address = txt_ip.get().strip()
        server_port = txt_port.get().strip()

        if not ip_checker(ip_address) or not port_checker(server_port):
            connection_test_passed = False
            btn_ok.config(state="disabled")
            lb_wrong_input.config(fg="red")
            lb_connection_status.config(
                text="Connection test skipped: invalid IP address or port.",
                fg="red",
            )
            return

        try:
            with socket.create_connection((ip_address, int(server_port)), timeout=1.5):
                pass
            connection_test_passed = True
            btn_ok.config(state="normal")
            lb_connection_status.config(text="Connection successful.", fg="#009933")
        except OSError as ex:
            connection_test_passed = False
            btn_ok.config(state="disabled")
            lb_connection_status.config(text="Connection failed: {}".format(str(ex)), fg="red")

    btn_ok = tk.Button(
        sensor_config_window,
        text="OK",
        font=("ABBvoice", 9),
        width=12,
        height=1,
        command=close_window,
        relief="solid",
        borderwidth=0,
        bg="#3366FF",
        fg="white",
        activebackground="#3366FF",
        state="disabled",
    )
    btn_ok.pack(side="right", anchor="se", padx=(12, 16), pady=(0, 17))

    txt_ip.bind("<KeyRelease>", reset_test_status)
    txt_port.bind("<KeyRelease>", reset_test_status)

    frame_btn = tk.Frame(
        sensor_config_window,
        bg="#3366FF",
        highlightbackground="#3366FF",
        highlightcolor="#3366FF",
        borderwidth=1,
    )
    frame_btn.pack(side="right", anchor="s", padx=(12, 12), pady=(0, 16))

    btn_test = tk.Button(
        frame_btn,
        text="Test",
        font=("ABBvoice", 9),
        width=12,
        height=1,
        command=test_connection,
        relief="solid",
        borderwidth=0,
        bg="#ffffff",
        activebackground="#ffffff",
    )
    btn_test.pack(pady=(0, 4))

    btn_cancel = tk.Button(
        frame_btn,
        text="Cancel",
        font=("ABBvoice", 9),
        width=12,
        height=1,
        command=sensor_config_window.destroy,
        relief="solid",
        borderwidth=0,
        bg="#ffffff",
        activebackground="#ffffff",
    )
    btn_cancel.pack()

    sensor_config_window.protocol("WM_DELETE_WINDOW", sensor_config_window.destroy)
    _toggle_log_fields()
    sensor_config_window.mainloop()

    return is_config_valid, server_config, logger_config_out


def show_position_generator_config_dialog(input_title: str, config_info: str):
    position_generator_config_window = tk.Tk()
    position_generator_config_window.title(input_title)

    scale_factor = _get_scale_factor()
    scaled_x = int(scale_factor * 470)
    scaled_y = int(scale_factor * 139)
    ww = position_generator_config_window.winfo_screenwidth()
    wh = position_generator_config_window.winfo_screenheight()
    pos_x = int(ww / 2 - 470 * scale_factor / 2)
    pos_y = int(wh / 2 - 139 * scale_factor / 2)
    position_generator_config_window.geometry(
        str(scaled_x) + "x" + str(scaled_y) + "+" + str(pos_x) + "+" + str(pos_y)
    )
    position_generator_config_window.resizable(False, False)
    position_generator_config_window.attributes("-topmost", True)
    _set_window_icon(position_generator_config_window)
    position_generator_config_window["bg"] = "#ffffff"

    position_generator_index = []
    is_index_valid = False

    frame_blk1 = tk.Frame(
        position_generator_config_window,
        background="#ffffff",
        highlightbackground="#ffffff",
        highlightcolor="#ffffff",
        borderwidth=0,
    )
    frame_blk1.pack(side="top", expand=True, fill="x")
    label_position_generator_index = tk.Label(
        frame_blk1,
        text="Position generator index: ",
        font=("ABBvoice", 9),
        background="#ffffff",
    )
    label_position_generator_index.pack(side="left", anchor="nw", padx=(22, 10), pady=(0, 0))
    frame_index = tk.Frame(
        frame_blk1, highlightbackground="#bababa", highlightcolor="#bababa", borderwidth=2
    )
    frame_index.pack(side="top", expand=True, fill="both", padx=(0, 16))
    position_generator_index_num = tk.Entry(
        frame_index, font=("ABBvoice", 9), relief="solid", borderwidth=0
    )
    position_generator_index_num.pack(expand=True, fill="both")
    label_info = tk.Label(
        frame_blk1,
        text="use semicolon to split indexes",
        justify="left",
        font=("ABBvoice", 9),
        foreground="#bababa",
        background="#ffffff",
    )
    label_info.pack(side="top", anchor="w")
    frame_blk2 = tk.Frame(frame_blk1, background="#ffffff", borderwidth=0)
    frame_blk2.pack(side="left", anchor="w", fill="y")
    lb_wrong_input = tk.Label(
        frame_blk1,
        text="The entered index is invalid, please check your input.",
        wraplength=int(260 * scale_factor),
        font=("ABBvoice", 9),
        justify="left",
        fg="#ffffff",
        background="#ffffff",
    )
    lb_wrong_input.pack(side="left", anchor="w")

    position_generator_index_num.insert(0, config_info)

    def input_checker(input_value: str):
        pattern = "^(\\d+;)+(?=\\d+$)|^\\d+$"
        if re.match(pattern, input_value):
            position_generator_index_list = re.findall("\\d+", input_value)
            position_generator_index_set = set(position_generator_index_list)
            for index in position_generator_index_set:
                if position_generator_index_list.count(index) > 1:
                    lb_wrong_input.config(text="Duplicated index detected, please check your input.")
                    return False
            for index in position_generator_index_list:
                if int(index) < 0 or int(index) > 1000:
                    lb_wrong_input.config(text="The entered index is invalid, please check your input.")
                    return False
        else:
            lb_wrong_input.config(text="The entered index is invalid, please check your input.")
            return False
        return True

    def close_window():
        nonlocal position_generator_index, is_index_valid

        if input_checker(position_generator_index_num.get()):
            position_generator_index = position_generator_index_num.get()
            is_index_valid = True
            position_generator_config_window.destroy()
        else:
            lb_wrong_input.config(fg="red")

    btn_ok = tk.Button(
        position_generator_config_window,
        text="OK",
        font=("ABBvoice", 9),
        width=12,
        command=close_window,
        relief="solid",
        borderwidth=0,
        bg="#3366FF",
        fg="white",
        activebackground="#3366FF",
    )
    btn_ok.pack(side="right", anchor="se", padx=(12, 16), pady=(0, 17))
    frame_btn = tk.Frame(
        position_generator_config_window,
        bg="#3366FF",
        highlightbackground="#3366FF",
        highlightcolor="#3366FF",
        borderwidth=1,
    )
    frame_btn.pack(side="right", anchor="s", padx=(12, 12), pady=(0, 16))
    btn_cancel = tk.Button(
        frame_btn,
        text="Cancel",
        font=("ABBvoice", 9),
        width=12,
        command=position_generator_config_window.destroy,
        relief="solid",
        borderwidth=0,
        bg="#ffffff",
        activebackground="#ffffff",
    )
    btn_cancel.pack()

    position_generator_config_window.protocol("WM_DELETE_WINDOW", position_generator_config_window.destroy)
    position_generator_config_window.mainloop()

    return is_index_valid, position_generator_index
