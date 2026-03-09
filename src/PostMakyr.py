# maykr_postbuild_patcher.py
import os
import re
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import dearpygui.dearpygui as dpg


APP_TITLE = "Maykr Post-Build Patcher"
DEFAULT_CARX_MODS_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\CarX Drift Racing Online\kino\mods"


state = {
    "root_dir": "",
    "maykr_exe": "",
    "kmc_files": [],
    "csproj_files": [],
    "selected_kmc": "",
    "selected_csproj": "",
    "carx_mods_dir": DEFAULT_CARX_MODS_DIR,
    "status": "Pick a project folder and scan.",
}


def set_status(msg: str) -> None:
    state["status"] = msg
    if dpg.does_item_exist("status_text"):
        dpg.set_value("status_text", msg)


def scan_project_root(root_dir: str):
    root = Path(root_dir)
    maykr_candidates = []
    kmc_files = []
    csproj_files = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        lower = path.name.lower()
        if lower == "maykr.exe":
            maykr_candidates.append(path)
        elif lower.endswith("_maykr.kmc"):
            kmc_files.append(path)
        elif lower.endswith(".csproj"):
            csproj_files.append(path)

    maykr_exe = ""
    if maykr_candidates:
        maykr_candidates.sort(key=lambda p: (len(p.parts), len(str(p))))
        maykr_exe = str(maykr_candidates[0])

    kmc_files = sorted(str(p) for p in kmc_files)
    csproj_files = sorted(str(p) for p in csproj_files)

    return maykr_exe, kmc_files, csproj_files


def quote_cmd(s: str) -> str:
    return f'"{s}"'


def build_post_build_command(maykr_exe: str, kmc_file: str, carx_mods_dir: str) -> str:
    return (
        f'{maykr_exe} $(TargetPath) '
        f'-c {kmc_file} '
        f'-o $(TargetDir) -np && '
        f'copy /Y "$(TargetDir)$(TargetName).ksm" "{os.path.join(carx_mods_dir, "$(TargetName).ksm")}"'
    )


def xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def patch_csproj(csproj_path: str, command: str) -> tuple[bool, str]:
    csproj = Path(csproj_path)

    if not csproj.exists():
        return False, f"Project file not found: {csproj_path}"

    backup_path = csproj.with_suffix(csproj.suffix + ".PostMakyrBackup")
    shutil.copy2(csproj, backup_path)

    try:
        text = csproj.read_text(encoding="utf-8")
        escaped_command = xml_escape(command)

        # Remove every existing PostBuildEvent block.
        text = re.sub(
            r'\s*<PostBuildEvent>.*?</PostBuildEvent>\s*',
            '\n',
            text,
            flags=re.DOTALL | re.IGNORECASE
        )

        # Remove any now-empty PropertyGroup blocks.
        text = re.sub(
            r'\s*<PropertyGroup>\s*</PropertyGroup>\s*',
            '\n',
            text,
            flags=re.DOTALL | re.IGNORECASE
        )

        # Preserve newline style.
        newline = "\r\n" if "\r\n" in text else "\n"

        # Normalize repeated blank lines a bit.
        text = re.sub(r'\n{3,}', '\n\n', text)
        if newline == "\r\n":
            text = text.replace("\n", "\r\n")

        new_block = (
            f"{newline}  <PropertyGroup>{newline}"
            f"    <PostBuildEvent>{escaped_command}</PostBuildEvent>{newline}"
            f"  </PropertyGroup>{newline}"
        )

        project_close_pattern = re.compile(r'</Project>\s*$', re.IGNORECASE)
        if not project_close_pattern.search(text):
            return False, "Could not find closing </Project> tag."

        new_text = project_close_pattern.sub(
            lambda m: new_block + "</Project>" + newline,
            text,
            count=1
        )

        csproj.write_text(new_text, encoding="utf-8")
        return True, f"Patched: {csproj_path} (backup: {backup_path.name})"

    except Exception as ex:
        return False, f"Failed to patch {csproj_path}: {ex}"
    

def refresh_ui_lists():
    kmc_items = state["kmc_files"] if state["kmc_files"] else ["<none found>"]
    csproj_items = state["csproj_files"] if state["csproj_files"] else ["<none found>"]

    dpg.configure_item("kmc_list", items=kmc_items)
    dpg.configure_item("csproj_list", items=csproj_items)

    selected_kmc = state["selected_kmc"] if state["selected_kmc"] in state["kmc_files"] else (state["kmc_files"][0] if state["kmc_files"] else "")
    selected_csproj = state["selected_csproj"] if state["selected_csproj"] in state["csproj_files"] else (state["csproj_files"][0] if state["csproj_files"] else "")

    state["selected_kmc"] = selected_kmc
    state["selected_csproj"] = selected_csproj

    dpg.set_value("kmc_list", selected_kmc if selected_kmc else "<none found>")
    dpg.set_value("csproj_list", selected_csproj if selected_csproj else "<none found>")
    dpg.set_value("maykr_exe_text", state["maykr_exe"] or "<none found>")

    update_preview()


def update_preview():
    maykr_exe = state["maykr_exe"]
    kmc_file = state["selected_kmc"]
    carx_mods_dir = dpg.get_value("carx_mods_input").strip()

    if maykr_exe and kmc_file and Path(maykr_exe).exists() and Path(kmc_file).exists():
        cmd = build_post_build_command(maykr_exe, kmc_file, carx_mods_dir)
        dpg.set_value("preview_command", cmd)
    else:
        dpg.set_value("preview_command", "Scan a folder and select a .kmc file to preview the command.")


def browse_for_directory(title: str, initial: str) -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    picked = filedialog.askdirectory(
        title=title,
        initialdir=initial if initial else str(Path.home())
    )

    root.destroy()
    return picked or ""


def on_browse_root():
    initial = dpg.get_value("root_input").strip() or str(Path.home())
    picked = browse_for_directory("Select mod/project folder", initial)
    if not picked:
        return

    state["root_dir"] = picked
    dpg.set_value("root_input", picked)
    set_status(f"Selected folder: {picked}")


def on_browse_carx_mods():
    initial = dpg.get_value("carx_mods_input").strip() or DEFAULT_CARX_MODS_DIR
    picked = browse_for_directory("Select CarX mods folder", initial)
    if not picked:
        return

    state["carx_mods_dir"] = picked
    dpg.set_value("carx_mods_input", picked)
    update_preview()
    set_status(f"Selected CarX mods folder: {picked}")


def on_scan_clicked():
    root_dir = dpg.get_value("root_input").strip()
    if not root_dir:
        set_status("Set a project folder first.")
        return

    if not Path(root_dir).exists():
        set_status("That folder does not exist.")
        return

    state["root_dir"] = root_dir
    state["carx_mods_dir"] = dpg.get_value("carx_mods_input").strip()

    maykr_exe, kmc_files, csproj_files = scan_project_root(root_dir)
    state["maykr_exe"] = maykr_exe
    state["kmc_files"] = kmc_files
    state["csproj_files"] = csproj_files

    refresh_ui_lists()

    set_status(
        f"Scan complete. maykr.exe: {'yes' if maykr_exe else 'no'}, "
        f".kmc files: {len(kmc_files)}, .csproj files: {len(csproj_files)}"
    )


def on_kmc_changed(sender, app_data):
    if app_data in state["kmc_files"]:
        state["selected_kmc"] = app_data
    update_preview()


def on_csproj_changed(sender, app_data):
    if app_data in state["csproj_files"]:
        state["selected_csproj"] = app_data


def on_apply_selected():
    maykr_exe = state["maykr_exe"]
    kmc_file = state["selected_kmc"]
    csproj_file = state["selected_csproj"]
    carx_mods_dir = dpg.get_value("carx_mods_input").strip()

    if not maykr_exe:
        set_status("No maykr.exe found.")
        return
    if not kmc_file:
        set_status("No *_maykr.kmc file selected.")
        return
    if not csproj_file:
        set_status("No .csproj file selected.")
        return
    if not Path(maykr_exe).exists():
        set_status("Selected maykr.exe does not exist.")
        return
    if not Path(kmc_file).exists():
        set_status("Selected .kmc file does not exist.")
        return

    command = build_post_build_command(maykr_exe, kmc_file, carx_mods_dir)
    ok, msg = patch_csproj(csproj_file, command)
    set_status(msg if ok else f"Error: {msg}")


def on_apply_all():
    maykr_exe = state["maykr_exe"]
    kmc_file = state["selected_kmc"]
    csproj_files = state["csproj_files"]
    carx_mods_dir = dpg.get_value("carx_mods_input").strip()

    if not maykr_exe:
        set_status("No maykr.exe found.")
        return
    if not kmc_file:
        set_status("No *_maykr.kmc file selected.")
        return
    if not csproj_files:
        set_status("No .csproj files found.")
        return
    if not Path(maykr_exe).exists():
        set_status("Selected maykr.exe does not exist.")
        return
    if not Path(kmc_file).exists():
        set_status("Selected .kmc file does not exist.")
        return

    command = build_post_build_command(maykr_exe, kmc_file, carx_mods_dir)

    success_count = 0
    messages = []
    for csproj_file in csproj_files:
        ok, msg = patch_csproj(csproj_file, command)
        messages.append(msg)
        if ok:
            success_count += 1

    if len(messages) == 1:
        set_status(messages[0])
    else:
        set_status(f"Patched {success_count}/{len(csproj_files)} project(s). Last: {messages[-1]}")


def on_copy_preview():
    preview = dpg.get_value("preview_command")
    dpg.set_clipboard_text(preview)
    set_status("Preview command copied to clipboard.")


dpg.create_context()

with dpg.window(label=APP_TITLE, tag="main_window", no_resize=False):
    dpg.add_text("Pick a mod/project folder, scan it, then patch the .csproj post-build event.")
    dpg.add_separator()

    with dpg.group(horizontal=True):
        dpg.add_input_text(label="Project Folder", tag="root_input", width=700, default_value=state["root_dir"])
        dpg.add_button(label="Browse", callback=on_browse_root)
        dpg.add_button(label="Scan", callback=on_scan_clicked)

    with dpg.group(horizontal=True):
        dpg.add_input_text(
            label="CarX Mods Folder",
            tag="carx_mods_input",
            width=700,
            default_value=DEFAULT_CARX_MODS_DIR,
            callback=lambda: update_preview(),
        )
        dpg.add_button(label="Browse", callback=on_browse_carx_mods)

    dpg.add_separator()
    dpg.add_text("Found maykr.exe:")
    dpg.add_input_text(tag="maykr_exe_text", readonly=True, width=950, default_value="<none found>")

    with dpg.group(horizontal=True):
        with dpg.child_window(width=470, height=220, border=True):
            dpg.add_text("Found *_maykr.kmc files")
            dpg.add_listbox(tag="kmc_list", items=["<none found>"], num_items=8, width=-1, callback=on_kmc_changed)

        with dpg.child_window(width=470, height=220, border=True):
            dpg.add_text("Found .csproj files")
            dpg.add_listbox(tag="csproj_list", items=["<none found>"], num_items=8, width=-1, callback=on_csproj_changed)

    dpg.add_separator()
    dpg.add_text("Post-Build Command Preview")
    dpg.add_input_text(tag="preview_command", multiline=True, readonly=True, width=950, height=80, default_value="")

    with dpg.group(horizontal=True):
        dpg.add_button(label="Copy Preview", callback=on_copy_preview)
        dpg.add_button(label="Apply To Selected Project", callback=on_apply_selected)
        dpg.add_button(label="Apply To All Projects", callback=on_apply_all)

    dpg.add_separator()
    dpg.add_text(state["status"], tag="status_text")

dpg.create_viewport(title=APP_TITLE, width=1020, height=560, resizable=True)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("main_window", True)
dpg.start_dearpygui()
dpg.destroy_context()