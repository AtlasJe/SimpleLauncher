import os
import io
import base64
import colorsys
import re
import sys
import threading
import subprocess
import shutil
import json
import hashlib
import zipfile
import webbrowser
import time
import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser
import requests
import customtkinter as ctk

# Ocultar permanentemente cualquier ventana de consola CMD que se cree en segundo plano
# (ej. descargas de Java, instaladores de Fabric/Forge, herramientas del sistema).
if os.name == 'nt':
    try:
        import ctypes
    except Exception:
        ctypes = None

    _orig_popen = subprocess.Popen
    class _SilentPopen(_orig_popen):
        def __init__(self, *args, **kwargs):
            flags = kwargs.get("creationflags", 0)
            kwargs["creationflags"] = flags | subprocess.CREATE_NO_WINDOW
            si = kwargs.get("startupinfo")
            if si is None:
                si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = si
            super().__init__(*args, **kwargs)

    subprocess.Popen = _SilentPopen
import minecraft_launcher_lib
from PIL import Image, ImageDraw
from datetime import datetime
from launcher_theme import (
    # Colores
    BG_DARK, BG_SIDE, BG_CARD, BG_CARD2, ACCENT, ACCENT_H, ACCENT_T,
    TEXT_M, TEXT_MAIN, BORDER_C, CARD_SEL, DANGER, DANGER_H,
    DANGER_SOFT, DANGER_SOFT_H, WARNING, WARNING_H, RESET_HEADER,
    RESET_CARD, RESET_CARD_BORDER, RESET_CRITICAL, RESET_CRITICAL_BORDER,
    RESET_TITLE, RESET_TEXT, generar_paleta,
    # Jerarquía de superficie M3 (Surface Containers)
    SURFACE, SURFACE_LOWEST, SURFACE_LOW, SURFACE_CONTAINER, SURFACE_HIGH, SURFACE_HIGHEST,
    # Espaciado M3 (Cuadrícula 8dp)
    SPACE_NONE, SPACE_XS, SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XL, SPACE_2XL,
    # Tipografía M3
    FONT_UI, FONT_MONO, FONT_CODE,
    FONT_DISPLAY, FONT_H1, FONT_H2, FONT_H3,
    FONT_TITLE, FONT_TITLE_M, FONT_TITLE_S,
    FONT_BODY_L, FONT_BODY, FONT_BODY_S, FONT_BODY_I, FONT_BODY_M_I,
    FONT_LABEL_L, FONT_SECTION, FONT_LABEL_S,
    FONT_CAPTION, FONT_CAPTION_B, FONT_CAPTION_S, FONT_HINT_I,
    # Iconos M3 (Material Symbols)
    ICON_SM, ICON_MD, ICON_LG, ICON_XL, ICON_HERO,
    FONT_ICON_SM, FONT_ICON_MD, FONT_ICON_LG, FONT_ICON_XL, FONT_ICON_HERO,
    ICON_ADD, ICON_EDIT, ICON_DELETE, ICON_CLOSE, ICON_FOLDER, ICON_FOLDER_OPEN,
    ICON_CAMERA, ICON_CLEANING, ICON_SETTINGS, ICON_SEARCH, ICON_REFRESH, ICON_BOLT,
    ICON_SAVE, ICON_CHECK, ICON_CHECK_CIRCLE, ICON_WARNING, ICON_INFO, ICON_PACKAGE,
    ICON_PERSON, ICON_ARROW_FORWARD, ICON_ARROW_BACK, ICON_PLAY, ICON_DOWNLOAD,
    ICON_CHART, ICON_EXTENSION, ICON_GAMEPAD, ICON_SPARKLE, ICON_ROCKET, ICON_SHIELD,
    ICON_PALETTE, ICON_CALENDAR, obtener_icono_ctk,
    # Forma M3 (corner_radius)
    R_NONE, R_XS, R_SM, R_MD, R_LG, R_XL, R_FULL,
    # Movimiento M3 (durations ms y transiciones)
    DUR_MICRO, DUR_SHORT, DUR_MEDIUM, DUR_LONG, DUR_SKELETON,
    animar_entrada_modal, animar_progreso,
)

# Estándares globales de Material Design 3 en CustomTkinter
ctk.ThemeManager.theme["CTkButton"]["corner_radius"] = R_FULL   # Botones en píldora oficial M3
ctk.ThemeManager.theme["CTkFrame"]["corner_radius"] = R_MD      # Contenedores y tarjetas M3 (12px)
ctk.ThemeManager.theme["CTkEntry"]["corner_radius"] = R_SM       # Campos de entrada M3 (8px)
ctk.ThemeManager.theme["CTkComboBox"]["corner_radius"] = R_SM    # Menús desplegables M3 (8px)
ctk.ThemeManager.theme["CTkCheckBox"]["corner_radius"] = R_XS    # Casillas M3 (4px)
ctk.ThemeManager.theme["CTkCheckBox"]["border_width"] = 2        # Borde limpio M3 (2px)

def obtener_ruta_recurso(nombre):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
        return os.path.join(base_path, nombre)
    base_path = os.path.dirname(os.path.abspath(__file__))
    candidatos = (
        os.path.join(base_path, nombre),
        os.path.join(os.path.dirname(base_path), "resources", nombre),
    )
    for candidato in candidatos:
        if os.path.exists(candidato):
            return candidato
    return candidatos[0]


def cargar_logo_svg(ruta_svg):
    """Renderiza las imágenes y trazos del SVG completo para CustomTkinter.

    El logo no es un único PNG: contiene tres imágenes incrustadas y varias
    líneas SVG. Extraer solamente la primera imagen hacía desaparecer las
    letras y parte del cubo.
    """
    try:
        with open(ruta_svg, "r", encoding="utf-8") as archivo_svg:
            contenido = archivo_svg.read()
        lienzo = Image.new("RGBA", (2000, 2000), (0, 0, 0, 0))
        def numero(valor):
            return float(str(valor).replace("px", ""))
        imagenes = {}
        patron_imagen = re.compile(
            r'<image id="([^"]+)" width="([^"]+)" height="([^"]+)"[^>]*'
            r'xlink:href="data:image/png;base64,([^"]+)"'
        )
        for identificador, ancho, alto, datos_b64 in patron_imagen.findall(contenido):
            imagenes[identificador] = (Image.open(io.BytesIO(base64.b64decode(datos_b64))).convert("RGBA"), numero(ancho), numero(alto))

        usos = re.compile(r'<use xlink:href="#([^"]+)" x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"')
        for identificador, x, y, ancho, alto in usos.findall(contenido):
            if identificador not in imagenes:
                continue
            imagen, _, _ = imagenes[identificador]
            destino = imagen.resize((round(numero(ancho)), round(numero(alto))), Image.Resampling.LANCZOS)
            lienzo.alpha_composite(destino, (round(numero(x)), round(numero(y))))

        # Trazos del SVG que forman las aristas del cubo.
        lineas = ImageDraw.Draw(lienzo)
        estilo = {"fill": "black", "width": 13}
        lineas.line([(1844.6, 520.119), (1000, 1000), (158.346, 513.653), (1001.473, 29.52), (1844.6, 520.119)], **estilo)
        lineas.line([(158.346, 514.76), (158.346, 1488.708), (1001.473, 1969.003), (1844.6, 1488.708), (1844.6, 520.602), (1000, 999.262), (158.346, 514.76)], **estilo)
        lineas.line([(1000, 1000), (1000, 1969.003)], **estilo)
        return lienzo
    except Exception as exc:
        print("No se pudo cargar el logo SVG:", exc)
        return None


def recolorear_logo(imagen, color_semilla="#72c3cb"):
    """Cambia únicamente el turquesa original del SVG y conserva negro/blanco."""
    valor = str(color_semilla or "#72c3cb").lstrip("#")
    if len(valor) != 6:
        valor = "72c3cb"
    destino = tuple(int(valor[i:i + 2], 16) for i in (0, 2, 4))
    dh, dl, ds = colorsys.rgb_to_hls(*(canal / 255 for canal in destino))
    origen = (114, 195, 203)
    salida = imagen.copy().convert("RGBA")
    pixeles = []
    for r, g, b, a in salida.getdata():
        distancia = ((r - origen[0]) ** 2 + (g - origen[1]) ** 2 + (b - origen[2]) ** 2) ** 0.5
        if a and distancia < 105 and g >= r and b >= r:
            _, luz, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            nr, ng, nb = colorsys.hls_to_rgb(dh, luz, min(1.0, max(0.22, ds) * max(0.55, sat / 0.44)))
            mezcla = max(0.0, min(1.0, 1.0 - distancia / 105.0))
            r = round(r * (1 - mezcla) + nr * 255 * mezcla)
            g = round(g * (1 - mezcla) + ng * 255 * mezcla)
            b = round(b * (1 - mezcla) + nb * 255 * mezcla)
        pixeles.append((r, g, b, a))
    salida.putdata(pixeles)
    return salida

def validar_ruta_dentro_de(base_dir, target_path):
    """Evita que una ruta de backup salga de la carpeta de destino."""
    base_abs = os.path.abspath(base_dir)
    target_abs = os.path.abspath(target_path)
    if os.path.commonpath((base_abs, target_abs)) != base_abs:
        raise ValueError(f"Ruta de backup fuera del destino: {target_path}")
    return target_abs

if os.name == 'nt':
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('mclauncher.simple.launcher.5')
    except Exception:
        pass

def cargar_fuentes():
    """Registra Nunito y Material Symbols temporalmente para que Tkinter pueda usarlas."""
    if os.name != 'nt':
        return
    fuentes = [
        os.path.join('Nunito', 'Nunito-VariableFont_wght.ttf'),
        'MaterialSymbolsOutlined.ttf',
        os.path.join('assets', 'fonts', 'MaterialSymbolsOutlined.ttf'),
    ]
    for f in fuentes:
        try:
            ruta_fuente = obtener_ruta_recurso(f)
            if os.path.isfile(ruta_fuente):
                ctypes.windll.gdi32.AddFontResourceExW(ruta_fuente, 0x10, 0)
        except Exception:
            pass

cargar_fuentes()

MINECRAFT_DIR = ""
CONFIG_FILE = ""
MODS_DIR = ""
VERSION_CACHE_FILE = ""
VERSION_CACHE_TTL = 900


def cargar_configuracion():
    global MINECRAFT_DIR, CONFIG_FILE, MODS_DIR, VERSION_CACHE_FILE
    default_dir = os.path.join(os.path.expanduser("~"), ".mi_launcher")
    config_dir  = os.path.join(os.path.expanduser("~"), ".mi_launcher_settings")
    os.makedirs(config_dir, exist_ok=True)
    settings_file = os.path.join(config_dir, "settings.json")
    VERSION_CACHE_FILE = os.path.join(config_dir, "versions_cache.json")

    config_data = {
        "minecraft_dir": default_dir,
        "active_profile": "",
        "profiles": {},
        "modpack_loaders": {},
        "modpack_slots": {},
        "auto_dependencias": False,
        "launcher_fullscreen": False,
        "language": "en",
        "fabric_enabled": True,
        "vulkan_enabled": True,
        "snapshots_enabled": False,
        "fullscreen_enabled": False,
        "show_uninstalled": False,
        "ui_sounds": True,
        "appearance_mode": "system",
        "accent_color": "#72c3cb",
        "onboarding_completed": False,
        "onboarding_step": 1,
        "onboarding_from_backup": False
    }

    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            config_data["minecraft_dir"]        = loaded.get("minecraft_dir",        default_dir)
            config_data["active_profile"]       = loaded.get("active_profile",       "")
            config_data["profiles"]             = loaded.get("profiles",             config_data["profiles"])
            config_data["modpack_loaders"]      = loaded.get("modpack_loaders",      {})
            config_data["modpack_slots"]        = loaded.get("modpack_slots",        {})
            config_data["auto_dependencias"]   = loaded.get("auto_dependencias",   False)
            config_data["launcher_fullscreen"] = loaded.get("launcher_fullscreen", False)
            config_data["language"]            = loaded.get("language",            "en")
            config_data["last_version"]         = loaded.get("last_version",         "")
            config_data["fabric_enabled"]      = loaded.get("fabric_enabled",      True)
            config_data["vulkan_enabled"]      = loaded.get("vulkan_enabled",      True)
            config_data["snapshots_enabled"]   = loaded.get("snapshots_enabled",   False)
            config_data["fullscreen_enabled"]  = loaded.get("fullscreen_enabled",  False)
            config_data["show_uninstalled"]    = loaded.get("show_uninstalled",    False)
            config_data["ui_sounds"]           = loaded.get("ui_sounds",           True)
            config_data["appearance_mode"]     = loaded.get("appearance_mode",     "system")
            config_data["accent_color"]        = loaded.get("accent_color",        "#72c3cb")
            config_data["onboarding_completed"] = loaded.get("onboarding_completed", False)
            config_data["onboarding_step"]      = loaded.get("onboarding_step",      1)
            config_data["onboarding_from_backup"] = loaded.get("onboarding_from_backup", False)
        except Exception:
            pass

    for data in config_data["profiles"].values():
        data.pop("username", None)

    MINECRAFT_DIR = os.path.normpath(config_data["minecraft_dir"])
    CONFIG_FILE   = os.path.join(MINECRAFT_DIR, "launcher_config.txt")
    MODS_DIR      = os.path.join(MINECRAFT_DIR, "mods")

    if config_data["active_profile"] not in config_data["profiles"]:
        if config_data["profiles"]:
            config_data["active_profile"] = sorted(config_data["profiles"].keys())[0]
        else:
            config_data["active_profile"] = ""
            config_data["onboarding_completed"] = False

    return config_data

def guardar_configuracion(config_data):
    config_dir = os.path.join(os.path.expanduser("~"), ".mi_launcher_settings")
    os.makedirs(config_dir, exist_ok=True)
    try:
        with open(os.path.join(config_dir, "settings.json"), "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
    except Exception:
        pass


# ──────────────────────────────────────────────
# SISTEMA DE SONIDOS
# ──────────────────────────────────────────────

class InstallCancelledException(Exception):
    pass

class ExportCancelledException(Exception):
    pass

class SoundManager:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self._initialized = False
        self._sounds = {}
        self._init_pygame()

    def _init_pygame(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._initialized = True
            sound_map = {
                "click": os.path.join("sounds", "click.mp3"),
                "select": os.path.join("sounds", "select.mp3"),
                "success": os.path.join("sounds", "success.ogg"),
            }
            for name, rel_path in sound_map.items():
                full_path = obtener_ruta_recurso(rel_path)
                if os.path.exists(full_path):
                    self._sounds[name] = pygame.mixer.Sound(full_path)
        except Exception:
            self._initialized = False

    def play(self, name):
        if not self.enabled or not self._initialized:
            return
        snd = self._sounds.get(name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)

STRINGS = {
    "en": {
        # Navigation
        "nav_jugar": "Play",
        "nav_versiones": "Versions",
        "nav_mods": "Mods",
        "nav_modrinth": "Modrinth",
        "nav_modpacks": "Modpacks",
        "nav_capturas": "Screenshots",
        "nav_skins": "Profiles",
        "nav_ajustes": "Settings",
        "usuario": "User",

        # Versions View
        "versiones_title": "Version Manager",
        "versiones_sub": "Install, explore and manage your Minecraft versions.",
        "filter_all": "All",
        "filter_installed": "Installed",
        "filter_releases": "Releases",
        "filter_snapshots": "Snapshots",
        "search_vers_ph": "Search version (e.g. 1.21, 1.20.1, 24w)...",
        "btn_uninstall": "Uninstall",
        "btn_install_ver": "Install",
        "status_installed": "✓ Installed",
        "status_not_installed": "Not installed",
        "select_version": "▶ Select",
        "selected_version": "✓ Active",
        "confirm_uninstall_title": "Uninstall Version",
        "confirm_uninstall_msg": "Are you sure you want to uninstall Minecraft {0}?\nThis will free up disk space.",
        "installing_title": "Installing Minecraft {0}...",
        "btn_cancel_install": "Cancel Installation",
        "install_cancelled": "Installation cancelled by user.",

        # Storage
        "storage_title": "Storage & Disk Usage",
        "btn_view_breakdown": "View Breakdown",
        "breakdown_title": "Storage Breakdown",
        "btn_close": "Close",
        "storage_total": "Total Space Used:",
        "storage_mc": "Minecraft (Versions, Assets & Libs):",
        "storage_mods": "Mods & Slots:",
        "storage_capturas": "Screenshots:",
        "storage_skins": "Skins & Cache:",
        "storage_perfiles": "Saves & Profiles:",
        "storage_refresh": "Recalculate Space",
        "storage_calculating": "Calculating...",

        # Play View
        "play_title": "Launcher",
        "play_subtitle": "Configure and launch your Minecraft session",
        "play_summary": "{0}  •  {1}  •  Slot: {2}",
        "ver_mc": "Minecraft Version",
        "loading_vers": "Loading versions...",
        "no_results": "No results",
        "launch_options": "Launch options",
        "version_filters": "Version filters",
        "fabric_mods": "Vanilla / Mods",
        "vulkan": "Vulkan (26.2+)",
        "snapshots": "Snapshots",
        "show_uninstalled": "Show uninstalled versions",
        "ver_not_installed_title": "Version Not Installed",
        "ver_not_installed_msg": "Minecraft {0} is not installed.\n\nWould you like to open the Version Manager and install it now?",
        "install_modal_warn": "Please wait while Minecraft is being installed. Do not close the launcher.",
        "fullscreen": "Fullscreen",
        "btn_play": "PLAY",
        "ready_to_launch": "Ready to launch.",
        "console_title": "Game Logs & Output",
        "console_copy": "Copy",
        "console_clear": "Clear",
        "console_ready": "[Launcher] Ready. Press PLAY to launch Minecraft...\n",
        "console_copied_title": "Copied",
        "console_copied_msg": "Console logs copied to clipboard.",
        "game_running": "Game is running!",

        # Mods View
        "mods_title": "Mod Manager",
        "mod_slot": "Mod Slot",
        "export_slot": "Export Slot",
        "import_slot": "Import Slot",
        "add_mods": "Add Mod(s)",
        "open_folder": "Open Folder",
        "search_mods_ph": "Filter installed mods...",
        "no_mods_found": "No mods found in this slot. Use 'Modrinth' to search and install mods.",

        # Modrinth View
        "modrinth_title": "Modrinth Explorer",
        "modrinth_sub": "Search and install mods directly to your active version slot.",
        "modrinth_search_ph": "Search mod (e.g. Sodium, Iris, Lithium, Mod Menu)...",
        "btn_search": "Search",
        "popular": "Popular:",
        "searching_modrinth": "Searching on Modrinth...",
        "no_results_modrinth": "No results found for '{0}'",
        "btn_install": "Install",
        "btn_installed": "Installed",
        "btn_downloading": "Downloading...",
        "author": "by",
        "downloads": "downloads",

        # Modpacks View
        "modpacks_title": "Modpacks Manager",
        "modpacks_sub": "Create, export and import your custom mod combinations.",
        "create_modpack": "Create Modpack",
        "export_modpack": "Export Modpack (.zip)",
        "import_modpack": "Import Modpack (.zip)",
        "no_modpacks": "No modpacks found. Create or import a modpack.",
        "apply_modpack": "Apply",
        "delete_modpack": "Delete",

        # Screenshots View
        "capturas_title": "Screenshots Gallery",
        "capturas_sub": "Explore, manage and export your in-game screenshots (F2).",
        "open_screenshot_dir": "Open Folder",
        "btn_refresh": "Refresh",
        "btn_view": "View",
        "no_screenshots": "No screenshots found.\nPress F2 inside Minecraft to take one.",
        "copy_image": "Copy",
        "copy_to": "Copy to...",
        "open_file": "Open file",
        "delete_image": "Delete",
        "rename_image": "Rename",
        "rename_capture_title": "Rename screenshot",
        "rename_capture_prompt": "New name for '{0}':",
        "screenshot_title": "Screenshot",
        "loading_hd": "Loading high definition...",
        "copy_capture_title": "Copy screenshot to...",
        "success_title": "Success",
        "confirm_title": "Confirm",
        "capture_copied_msg": "Screenshot copied to:\n{0}",
        "delete_capture_confirm": "Delete screenshot '{0}'?",
        "unknown": "unknown",
        "install_modpack_btn": "Install Modpack",
        "active_tag": "Active",

        # Skins View
        "skins_title": "Profiles & Skins",
        "skins_subtitle": "Customize your character skin (works offline and in multiplayer).",
        "char_preview": "Character Preview",
        "front": "Front",
        "back": "Back",
        "skin_options": "Skin Options",
        "load_png": "Load Skin from local file (.png):",
        "select_png": "Select PNG file",
        "load_nick": "Or load from official Minecraft Username (e.g. Steve, Notch):",
        "nick_ph": "Enter official Minecraft Username (e.g. Steve)...",
        "btn_load_nick": "Load Nick",
        "arm_model": "Arm model:",
        "skin_ready": "Skin ready.",
        "wardrobe_title": "Skin Wardrobe",
        "wardrobe_sub": "Saved skins — click to equip instantly",
        "wardrobe_empty": "No saved skins yet. Apply a skin and save it to the wardrobe.",
        "wardrobe_wear": "Wear",
        "wardrobe_save_title": "Save skin to wardrobe",
        "wardrobe_save_msg": "Give it a name to find it easily:",
        "wardrobe_save_btn": "Save",
        "wardrobe_rename_title": "Rename skin",
        "wardrobe_rename_msg": "Enter a new name for this skin:",

        # Settings View
        "ajustes_title": "Settings",
        "ajustes_subtitle": "Launcher preferences, paths and profiles",
        "language_title": "Language / Idioma",
        "game_folder": "Game folder",
        "btn_change": "Change",
        "behavior": "Behavior",
        "launcher_fs": "Launcher fullscreen (F11)",
        "auto_dep": "Auto-install mod dependencies",
        "ui_sounds": "Sounds",
        "users_profiles": "Backup",
        "export_profile": "Export Profile",
        "full_backup": "Full Backup",
        "selective_backup": "Selective Backup",
        "backup_select_items": "Select the profiles and mod slots to include.",
        "backup_profiles_group": "Profiles",
        "backup_slots_group": "Mod slots",
        "no_backup_items": "Select at least one profile or mod slot.",
        # Export Profiles Modal
        "export_profiles_title": "Export Profiles",
        "export_profiles_sub": "Select the profiles to include in the backup archive.",
        "select_all": "Select all",
        "btn_export_selected": "Export Selected",
        "no_profiles_selected": "Please select at least one profile to export.",
        "compressing_profile": "Compressing profile: {0} ({1}/{2})...",
        "btn_cancel_export": "Cancel Export",
        "export_cancelled": "Export cancelled by user.",
        "profiles_exported_success": "{0} profile(s) exported successfully to:\n{1}",

        "import_profile": "Import Profile",
        "import_general_backup": "Import Backup",

        # Dialogs & Alerts
        "alert_wait": "Wait",
        "alert_file_exists": "A file with that name already exists.",
        "alert_select_ver": "Please select a valid version.",
        "alert_nick_only": "Direct URL links are not allowed. Please enter an official Minecraft Username (e.g. Steve, Notch) or select a local PNG file.",
        "alert_nick_title": "Usernames Only",
        "alert_profile_exists": "A profile with that name already exists.",
        "alert_new_profile_title": "New Profile",
        "alert_new_profile_prompt": "New user/profile name:",
        "alert_rename_title": "Rename Profile",
        "alert_rename_prompt": "New name for '{0}':",
        "alert_delete_profile_title": "Delete Profile",
        "alert_delete_profile_confirm": "Are you sure you want to delete profile '{0}'?",
        "alert_created": "Profile '{0}' created.",
        "alert_slot_exists": "A slot with that name already exists.",
        "alert_new_slot_title": "New Slot",
        "alert_new_slot_prompt": "Name for the new slot:",
        "alert_delete_slot_confirm": "Are you sure you want to delete slot '{0}'?",
        "alert_clear_slot_confirm": "Are you sure you want to clear all mods in slot '{0}'?",
        "dir_changed_title": "Directory Changed",
        "dir_changed_msg": "New path:\n{0}",
        "profile_exported": "Profile '{0}' exported successfully.",
        "profile_imported": "Profile '{0}' imported successfully.",
        "zip_files": "ZIP Archive",
        "profile_zip_file": "Profile / Backup ZIP",
        "profile_prefix": "profile",
        "profiles_suffix": "profiles",
        "slot_zip_file": "Mod Slot ZIP",
        "export_slot_title": "Export Slot",
        "import_slot_title": "Import Slot",
        "no_mods_in_slot_export": "There are no mods in this slot to export.",
        "slot_exported_msg": "Slot '{0}' exported to:\n{1}",
        "import_slot_prompt": "Name for the imported slot:",
        "no_jars_in_zip": "The ZIP file does not contain any .jar files.",
        "slot_imported_msg": "{0} mods imported into slot '{1}'.",
        "alert_profile_exists_rename": "A profile named '{0}' already exists. New name:",
        "profiles_imported_count": "{0} profile(s) imported successfully.",
        "invalid_profile_zip": "The file is not a valid profile archive exported by this launcher.",
        "no_modpacks_installed": "No modpacks installed.\nUse the button above to install one.",
        "select_modpack_title": "Select a modpack",
        "modpack_install_confirm": "Install modpack '{0}' (Minecraft {1})?",
        "modpack_install_version_confirm": "This modpack requires Minecraft {0}. The required game version will be installed. Do you want to continue?",
        "modpack_invalid_manifest": "The selected file does not contain a valid Modrinth modpack manifest.",
        "modpack_filter": "Modpacks",
        "install_zip_title": "Install ZIP",
        "install_zip_prompt": "Name for the modpack slot:",
        "reading_modpack": "Reading modpack...",
        "downloading_n_mods": "Downloading {0} mods...",
        "extracting_overrides": "Extracting overrides...",
        "modpack_installed_status": "'{0}' installed successfully.",
        "modpack_installed_msg": "'{0}' (MC {1}) installed into slot '{2}'.",
        "modpack_tag": "MODPACK",
        "reading_zip": "Reading ZIP...",
        "no_jars_in_zip_status": "No .jar files found in the ZIP.",
        "zip_installed_status": "{0} mods installed into '{1}'.",
        "zip_installed_msg": "{0} mods installed into '{1}'.",
        "empty_slot_title": "Clear Slot",
        "empty_slot_confirm": "Delete ALL mods in slot '{0}'?\nThis action cannot be undone.",
        "empty_slot_success": "{0} mod(s) deleted from slot '{1}'.",
        # Install status strings
        "install_starting": "Starting download...",
        "install_cancelling": "Cancelling and cleaning files...",
        "install_cancelled_title": "Cancelled",
        "install_checking_java": "Checking Java for {0}...",
        "install_downloading_ver": "Downloading Minecraft {0}...",
        "install_checking_files": "Checking files for {0}...",
        "install_checking_java_short": "Checking Java...",
        "install_checking_fabric": "Checking Fabric...",
        "install_installing_fabric": "Installing Fabric Loader...",
        # Modrinth result strings
        "modrinth_n_results": "{0} mods found for '{1}'.",
        "modrinth_n_results_popular": "{0} popular mods found.",
        "modrinth_no_mods": "No mods found.",
        "modrinth_no_results_label": "No results found for this search.",
        "modrinth_error_connect": "Error connecting to Modrinth.",
        # Import & Export Slots / Backups Progress
        "importing_profile_title": "Importing Profile Backup",
        "importing_file": "Importing: {0}",
        "import_cancelled": "Import cancelled by user.",
        "reading_backup_zip": "Reading backup archive...",
        "extracting_profiles": "Extracting profiles...",
        "export_slots_title": "Export Mod Slots",
        "export_slots_sub": "Select the mod slots you want to back up to a ZIP archive.",
        "no_slots_found": "No mod slots found to export.",
        "no_slots_selected": "Please select at least one mod slot.",
        "slots_exported_success": "{0} mod slot(s) successfully exported to:\n{1}",
        "import_slots_title": "Import Mod Slots",
        "importing_slots_title": "Importing Mod Slots",
        "slots_imported_count": "{0} mod slot(s) imported successfully.",
        "slots_management": "Mod Slots & Backup",
        "export_slots_btn": "Export Mod Slots",
        "import_slots_btn": "Import Mod Slots",
        "pre_reset_title": "Pre-Reset Backup Selection",
        "pre_reset_sub": "Select the specific profiles and mod slots you wish to preserve:",
        "reset_backup_external_sub": "The unified backup selector will open separately. Choose what to preserve, then return here to confirm the reset.",
        "chk_backup_profiles": "Profiles & Worlds",
        "chk_backup_slots": "Mod Slots",
        "btn_export_and_continue": "Open Backup & Continue",
        "btn_continue_no_backup": "Continue without Backup",
        "no_items_selected_warn": "No profiles or mod slots were selected.\nDo you want to proceed without creating a backup?",
        "backup_total_success": "Unified backup created successfully with {0} profile(s) and {1} mod slot(s) at:\n{2}",
        "cannot_rename_default_slot": "Cannot rename the default slot.",
        "cannot_delete_default_slot": "Cannot delete the default slot.",
        "rename_slot_title": "Rename Slot",
        "rename_slot_prompt": "New name for slot '{0}':",
        "delete_mod_confirm": "Delete '{0}'?",
        "mods_installed_count": "{0}/{1} mod(s) installed successfully.",
        "delete_modpack_confirm": "Delete '{0}' (MC {1}) and all its mods?",
        "select_game_folder": "Select Game Folder",
        "dir_changed_title": "Directory Changed",
        "dir_changed_msg": "New game folder:\n{0}",
        "error_connecting_mojang": "Could not connect to Mojang:\n{0}",
        "error_launching_title": "Launch Error",
        "modrinth_info_error": "Could not retrieve mod information from Modrinth.",
        "incompatible_title": "Incompatible",
        "incompatible_mod_msg": "No compatible file found for '{0}'.",
        "mod_installed_success": "'{0}' installed successfully.",
        "download_error_title": "Download Error",
        "deps_required_title": "Required Dependencies",
        "deps_required_sub": "The following dependencies are required by your mods:",
        "btn_install_all_deps": "Install All",
        "btn_skip": "Skip",
        "deps_installed_count": "{0} dependency/dependencies installed.",
        "fetching_deps_data": "Fetching dependency information...",
        # Factory Reset
        "danger_zone_title": "Danger Zone",
        "reset_launcher_desc": "Factory reset the launcher: removes all profiles, worlds, versions, mods and saved data.",
        "btn_reset_launcher": "Factory Reset",
        "factory_reset_title": "Factory Reset",
        "reset_step1_title": "Factory Reset Confirmation",
        "reset_step1_msg": "Are you sure you want to completely reset the launcher?\n\nThis will wipe all profiles, saves/worlds, downloaded Minecraft versions, mods, screenshots, and wardrobe skins.",
        "reset_step2_title": "Backup Profiles & Slots?",
        "reset_step2_msg": "Would you like to export a backup of your profiles and mod slots before resetting everything?",
        "reset_step3_title": "FINAL CONFIRMATION",
        "reset_step3_msg": "WARNING: This action cannot be undone. All unbacked data will be permanently deleted and the launcher will reset to initial factory state.\n\nDo you want to proceed with the complete wipe?",
        "step_final_confirm_title": "Final Wipe Confirmation",
        "btn_wipe_all_confirm": "Permanently Wipe Everything",
        "btn_cancel": "Cancel",
        "btn_ok": "OK",
        "wiping_data_status": "Wiping all launcher data and recreating defaults...",
        "reset_completed_msg": "The launcher has been completely reset to factory defaults.",
        # Onboarding / Welcome Wizard
        "ob_welcome_title": "Welcome to Simple Launcher",
        "ob_step_indicator": "Step {0} of 6",
        "ob_step1_title": "Select your Language",
        "ob_step1_sub": "Choose the language you want to use in the launcher:",
        "ob_lang_es": "🇪🇸 Español",
        "ob_lang_en": "🇬🇧 English",
        "theme_title": "Appearance Mode",
        "accent_title": "Personalized color",
        "accent_subtitle": "Choose one color and the launcher will generate the rest of the palette automatically.",
        "accent_choose": "Choose color",
        "accent_choose_title": "Choose launcher color",
        "adaptive_theme_title": "Dynamic Color Atmosphere",
        "adaptive_theme_sub": "The entire launcher atmosphere (background, sidebar, cards) is derived from your chosen color.",
        "languages_work_notice": "Portuguese and French are available.",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "theme_system": "System",
        "ob_step1_theme_title": "Appearance Theme",
        "ob_step1_theme_sub": "Choose your preferred appearance mode:",
        "ob_btn_continue": "Continue ➔",
        "ob_btn_back": "⬅️ Back",
        "ob_step2_title": "Do you have a Backup?",
        "ob_step2_sub": "If you have an exported backup (.zip) from a previous installation, you can restore all your profiles, skins, and mod slots right now.",
        "ob_btn_import_backup": "Import Backup Archive (.zip)",
        "ob_btn_no_backup": "➡️ Fresh Setup (I don't have a backup)",
        "ob_backup_loaded_title": "Backup active ({0} profile(s) ready)",
        "ob_backup_loaded_sub": "Your profiles, mod slots, and configurations are loaded.",
        "ob_backup_success_jump": "Backup imported successfully! Jumping directly to Version Download.",
        "ob_step3_title": "Create your Player Profile",
        "ob_step3_sub": "Enter the nickname you want to use in-game and to store your worlds:",
        "ob_profile_name_label": "Player Name / Nickname:",
        "ob_profile_empty_warn": "Please enter a valid player name.",
        "ob_step4_title": "Choose your Skin (Optional)",
        "ob_step4_sub": "Customize your player character appearance. You can change this at any time in the Wardrobe.",
        "ob_btn_choose_skin": "Load Skin File (.png)",
        "ob_btn_skip_skin": "Skip this step ➔",
        "ob_model_classic": "Classic (Steve)",
        "ob_model_slim": "Slim (Alex)",
        "ob_step5_title": "Download Minecraft Version",
        "ob_step5_sub": "Select a Minecraft version to download and install for immediate play:",
        "ob_version_select_label": "Minecraft Version:",
        "ob_btn_download_ver": "Download & Install Version",
        "ob_btn_cancel_download": "Cancel Download",
        "ob_ver_installed_badge": "Version installed and ready to play!",
        "ob_btn_skip_download": "Skip download for now ➔",
        "ob_step6_title": "You're All Set!",
        "ob_step6_sub": "Here's a quick tour of what you can do in Simple Launcher:",
        "ob_feat_play_title": "Play",
        "ob_feat_play_desc": "Launch Minecraft with Fabric, skins, and mod slots in a single click.",
        "ob_feat_vers_title": "Version Manager",
        "ob_feat_vers_desc": "Download, install, and manage official release versions.",
        "ob_feat_slots_title": "Mod Slots",
        "ob_feat_slots_desc": "Organize separate mod collections per version without conflicts.",
        "ob_feat_modrinth_title": "Modrinth Explorer",
        "ob_feat_modrinth_desc": "Search, discover, and install mods with automatic dependency resolution.",
        "ob_feat_skins_title": "Skin Wardrobe",
        "ob_feat_skins_desc": "Switch custom skins offline with automatic compatibility.",
        "ob_feat_settings_title": "Settings & Backups",
        "ob_feat_settings_desc": "Full ZIP backups, RAM allocation, sound effects, and factory reset.",
        "ob_btn_get_started": "Get Started",
        "btn_use": "Use"
    },
    "es": {
        # Navigation
        "nav_jugar": "Jugar",
        "nav_versiones": "Versiones",
        "nav_mods": "Mods",
        "nav_modrinth": "Modrinth",
        "nav_modpacks": "Modpacks",
        "nav_capturas": "Capturas",
        "nav_skins": "Perfiles",
        "nav_ajustes": "Ajustes",
        "usuario": "Usuario",

        # Versions View
        "versiones_title": "Gestor de Versiones",
        "versiones_sub": "Instala, explora y administra tus versiones de Minecraft.",
        "filter_all": "Todas",
        "filter_installed": "Instaladas",
        "filter_releases": "Versiones",
        "filter_snapshots": "Snapshots",
        "search_vers_ph": "Buscar versión (ej. 1.21, 1.20.1, 24w)...",
        "btn_uninstall": "Desinstalar",
        "btn_install_ver": "Instalar",
        "status_installed": "✓ Instalada",
        "status_not_installed": "No instalada",
        "select_version": "▶ Seleccionar",
        "selected_version": "✓ Activa",
        "confirm_uninstall_title": "Desinstalar Versión",
        "confirm_uninstall_msg": "¿Seguro que deseas desinstalar Minecraft {0}?\nEsto liberará espacio en tu disco.",
        "installing_title": "Instalando Minecraft {0}...",
        "btn_cancel_install": "Cancelar Instalación",
        "install_cancelled": "Instalación cancelada por el usuario.",

        # Storage
        "storage_title": "Espacio de Almacenamiento",
        "btn_view_breakdown": "Ver Desglose",
        "breakdown_title": "Desglose de Almacenamiento",
        "btn_close": "Cerrar",
        "storage_total": "Espacio Total Ocupado:",
        "storage_mc": "Minecraft (Versiones, Assets y Libs):",
        "storage_mods": "Mods y Slots:",
        "storage_capturas": "Capturas de pantalla:",
        "storage_skins": "Skins y Caché:",
        "storage_perfiles": "Mundos y Perfiles:",
        "storage_refresh": "Recalcular Espacio",
        "storage_calculating": "Calculando...",

        # Play View
        "play_title": "Lanzador",
        "play_subtitle": "Configura y lanza tu partida de Minecraft",
        "play_summary": "{0}  •  {1}  •  Slot: {2}",
        "ver_mc": "Versión de Minecraft",
        "loading_vers": "Cargando versiones...",
        "no_results": "Sin resultados",
        "launch_options": "Opciones de lanzamiento",
        "version_filters": "Filtros de versiones",
        "fabric_mods": "Vanilla / Mods",
        "vulkan": "Vulkan (26.2+)",
        "snapshots": "Snapshots",
        "show_uninstalled": "Mostrar no instaladas",
        "ver_not_installed_title": "Versión No Instalada",
        "ver_not_installed_msg": "Minecraft {0} no está instalada.\n\n¿Deseas abrir el Gestor de Versiones e instalarla ahora?",
        "install_modal_warn": "Por favor espera mientras se descarga e instala Minecraft. No cierres el launcher.",
        "fullscreen": "Pantalla completa",
        "btn_play": "JUGAR",
        "ready_to_launch": "Listo para iniciar.",
        "console_title": "Consola y Registros del Juego",
        "console_copy": "Copiar",
        "console_clear": "Limpiar",
        "console_ready": "[Lanzador] Listo. Pulsa JUGAR para iniciar Minecraft...\n",
        "console_copied_title": "Copiado",
        "console_copied_msg": "Registros de la consola copiados al portapapeles.",
        "game_running": "¡Juego en ejecución!",

        # Mods View
        "mods_title": "Gestor de Mods",
        "mod_slot": "Ranura de Mods",
        "export_slot": "Exportar Slot",
        "import_slot": "Importar Slot",
        "add_mods": "Añadir Mod(s)",
        "open_folder": "Abrir Carpeta",
        "search_mods_ph": "Filtrar mods instalados...",
        "no_mods_found": "No hay mods en este slot. Usa 'Modrinth' para buscar e instalar mods.",

        # Modrinth View
        "modrinth_title": "Explorador Modrinth",
        "modrinth_sub": "Busca e instala mods directamente en la ranura de tu versión activa.",
        "modrinth_search_ph": "Buscar mod (ej. Sodium, Iris, Lithium, Mod Menu)...",
        "btn_search": "Buscar",
        "popular": "Populares:",
        "searching_modrinth": "Buscando en Modrinth...",
        "no_results_modrinth": "No se encontraron resultados para '{0}'",
        "btn_install": "Instalar",
        "btn_installed": "Instalado",
        "btn_downloading": "Descargando...",
        "author": "por",
        "downloads": "descargas",

        # Modpacks View
        "modpacks_title": "Gestor de Modpacks",
        "modpacks_sub": "Crea, exporta e importa combinaciones de mods personalizadas.",
        "create_modpack": "Crear Modpack",
        "export_modpack": "Exportar Modpack (.zip)",
        "import_modpack": "Importar Modpack (.zip)",
        "no_modpacks": "No hay modpacks. Crea o importa un modpack.",
        "apply_modpack": "Aplicar",
        "delete_modpack": "Eliminar",

        # Screenshots View
        "capturas_title": "Galería de Capturas",
        "capturas_sub": "Visualiza, administra y exporta las capturas tomadas en el juego (F2).",
        "open_screenshot_dir": "Abrir Carpeta",
        "btn_refresh": "Refrescar",
        "btn_view": "Ver",
        "no_screenshots": "No hay capturas de pantalla guardadas.\nPresiona F2 dentro de Minecraft para tomar una.",
        "copy_image": "Copiar",
        "copy_to": "Copiar a...",
        "open_file": "Abrir archivo",
        "delete_image": "Eliminar",
        "rename_image": "Renombrar",
        "rename_capture_title": "Renombrar captura",
        "rename_capture_prompt": "Nuevo nombre para '{0}':",
        "screenshot_title": "Captura",
        "loading_hd": "Cargando alta definición...",
        "copy_capture_title": "Copiar captura a...",
        "success_title": "Éxito",
        "confirm_title": "Confirmar",
        "capture_copied_msg": "Captura copiada a:\n{0}",
        "delete_capture_confirm": "¿Eliminar captura '{0}'?",
        "unknown": "desconocida",
        "install_modpack_btn": "Instalar Modpack",
        "active_tag": "Activo",

        # Skins View
        "skins_title": "Perfiles y Skins",
        "skins_subtitle": "Administra tus perfiles de jugador y personaliza tus aspectos.",
        "char_preview": "Vista Previa del Personaje",
        "front": "Frente",
        "back": "Espalda",
        "skin_options": "Opciones de Skin",
        "load_png": "Cargar Skin desde archivo local (.png):",
        "select_png": "Seleccionar archivo PNG",
        "load_nick": "O cargar desde Nick de jugador oficial (ej. Steve, Notch):",
        "nick_ph": "Escribe el Nick del jugador oficial (ej. Steve)...",
        "btn_load_nick": "Cargar Nick",
        "arm_model": "Modelo de brazo:",
        "skin_ready": "Skin lista.",
        "wardrobe_title": "Armario de Skins",
        "wardrobe_sub": "Skins guardadas — click para ponerte una al instante",
        "wardrobe_empty": "No hay skins guardadas. Aplica una skin y guarda en el armario.",
        "wardrobe_wear": "Usar",
        "wardrobe_save_title": "Guardar skin en el armario",
        "wardrobe_save_msg": "Escribe un nombre para recordarla:",
        "wardrobe_save_btn": "Guardar",
        "wardrobe_rename_title": "Renombrar skin",
        "wardrobe_rename_msg": "Escribe un nuevo nombre para esta skin:",

        # Settings View
        "ajustes_title": "Ajustes",
        "ajustes_subtitle": "Preferencias del lanzador, rutas y perfiles",
        "language_title": "Idioma / Language",
        "game_folder": "Carpeta del juego",
        "btn_change": "Cambiar",
        "behavior": "Comportamiento",
        "launcher_fs": "Pantalla completa del lanzador (F11)",
        "auto_dep": "Auto-instalar dependencias de mods",
        "ui_sounds": "Sonido",
        "users_profiles": "Backup",
        "export_profile": "Exportar Usuario/Perfil",
        "full_backup": "Backup Completo",
        "selective_backup": "Backup Selectivo",
        "backup_select_items": "Selecciona los perfiles y slots de mods que quieres incluir.",
        "backup_profiles_group": "Perfiles",
        "backup_slots_group": "Slots de mods",
        "no_backup_items": "Selecciona al menos un perfil o slot de mods.",
        # Export Profiles Modal
        "export_profiles_title": "Exportar Perfiles",
        "export_profiles_sub": "Selecciona los perfiles a incluir en la copia de seguridad.",
        "select_all": "Seleccionar todos",
        "btn_export_selected": "Exportar Selección",
        "no_profiles_selected": "Por favor, selecciona al menos un perfil para exportar.",
        "compressing_profile": "Comprimiendo perfil: {0} ({1}/{2})...",
        "btn_cancel_export": "Cancelar Exportación",
        "export_cancelled": "Exportación cancelada por el usuario.",
        "profiles_exported_success": "{0} perfil(es) exportado(s) correctamente en:\n{1}",

        "import_profile": "Importar Usuario/Perfil",
        "import_general_backup": "Importar Backup",

        # Dialogs & Alerts
        "alert_wait": "Espera",
        "alert_file_exists": "Ya existe un archivo con ese nombre.",
        "alert_select_ver": "Selecciona una versión válida.",
        "alert_nick_only": "No se permiten enlaces directos. Por favor, escribe únicamente el Nick de un jugador oficial de Minecraft (ej. Steve, Notch) o selecciona un archivo PNG local.",
        "alert_nick_title": "Solo Nicks",
        "alert_profile_exists": "Ya existe un perfil con ese nombre.",
        "alert_new_profile_title": "Nuevo Perfil",
        "alert_new_profile_prompt": "Nombre del nuevo usuario/perfil:",
        "alert_rename_title": "Renombrar Perfil",
        "alert_rename_prompt": "Nuevo nombre para '{0}':",
        "alert_delete_profile_title": "Eliminar Perfil",
        "alert_delete_profile_confirm": "¿Seguro que quieres eliminar el perfil '{0}'?",
        "alert_created": "Perfil '{0}' creado.",
        "alert_slot_exists": "Ya existe un slot con ese nombre.",
        "alert_new_slot_title": "Nuevo Slot",
        "alert_new_slot_prompt": "Nombre del nuevo slot:",
        "alert_delete_slot_confirm": "¿Seguro que quieres eliminar el slot '{0}'?",
        "alert_clear_slot_confirm": "¿Seguro que quieres vaciar todos los mods del slot '{0}'?",
        "dir_changed_title": "Directorio Cambiado",
        "dir_changed_msg": "Nueva ruta:\n{0}",
        "profile_exported": "Perfil '{0}' exportado correctamente.",
        "profile_imported": "Perfil '{0}' importado correctamente.",
        "zip_files": "Archivo ZIP",
        "profile_zip_file": "ZIP de Perfil / Backup",
        "profile_prefix": "perfil",
        "profiles_suffix": "perfiles",
        "slot_zip_file": "ZIP de Slot",
        "export_slot_title": "Exportar Slot",
        "import_slot_title": "Importar Slot",
        "no_mods_in_slot_export": "No hay mods en este slot para exportar.",
        "slot_exported_msg": "Slot '{0}' exportado a:\n{1}",
        "import_slot_prompt": "Nombre para el slot importado:",
        "no_jars_in_zip": "El ZIP no contiene archivos .jar.",
        "slot_imported_msg": "{0} mods importados en slot '{1}'.",
        "alert_profile_exists_rename": "Ya existe un perfil '{0}'. Nuevo nombre:",
        "profiles_imported_count": "{0} perfil(es) importado(s) correctamente.",
        "invalid_profile_zip": "El archivo no es un perfil válido exportado por este lanzador.",
        "no_modpacks_installed": "No hay modpacks instalados.\nUsa el botón de arriba para instalar uno.",
        "select_modpack_title": "Selecciona un modpack",
        "modpack_install_confirm": "¿Instalar el modpack '{0}' (Minecraft {1})?",
        "modpack_install_version_confirm": "Este modpack requiere Minecraft {0}. Se instalará la versión necesaria del juego. ¿Quieres continuar?",
        "modpack_invalid_manifest": "El archivo seleccionado no contiene un manifiesto válido de modpack Modrinth.",
        "modpack_filter": "Modpacks",
        "install_zip_title": "Instalar ZIP",
        "install_zip_prompt": "Nombre para el slot del modpack:",
        "reading_modpack": "Leyendo modpack...",
        "downloading_n_mods": "Descargando {0} mods...",
        "extracting_overrides": "Extrayendo overrides...",
        "modpack_installed_status": "'{0}' instalado correctamente.",
        "modpack_installed_msg": "'{0}' (MC {1}) instalado en el slot '{2}'.",
        "modpack_tag": "MODPACK",
        "reading_zip": "Leyendo ZIP...",
        "no_jars_in_zip_status": "No se encontraron .jar en el ZIP.",
        "zip_installed_status": "{0} mods instalados en '{1}'.",
        "zip_installed_msg": "{0} mods instalados en '{1}'.",
        "empty_slot_title": "Vaciar Slot",
        "empty_slot_confirm": "¿Eliminar TODOS los mods del slot '{0}'?\nEsta acción no se puede deshacer.",
        "empty_slot_success": "{0} mod(s) eliminados del slot '{1}'.",
        # Install status strings
        "install_starting": "Iniciando descarga...",
        "install_cancelling": "Cancelando y limpiando archivos...",
        "install_cancelled_title": "Cancelado",
        "install_checking_java": "Verificando Java para {0}...",
        "install_downloading_ver": "Descargando Minecraft {0}...",
        "install_checking_files": "Verificando archivos {0}...",
        "install_checking_java_short": "Verificando Java...",
        "install_checking_fabric": "Verificando Fabric...",
        "install_installing_fabric": "Instalando Fabric Loader...",
        # Modrinth result strings
        "modrinth_n_results": "{0} mods encontrados para '{1}'.",
        "modrinth_n_results_popular": "{0} mods populares encontrados.",
        "modrinth_no_mods": "No se encontraron mods.",
        "modrinth_no_results_label": "No se encontraron resultados para la búsqueda.",
        "modrinth_error_connect": "Error al conectar con Modrinth.",
        # Import & Export Slots / Backups Progress
        "importing_profile_title": "Importando Copia de Seguridad",
        "importing_file": "Importando: {0}",
        "import_cancelled": "Importación cancelada por el usuario.",
        "reading_backup_zip": "Leyendo archivo de copia de seguridad...",
        "extracting_profiles": "Extrayendo perfiles...",
        "export_slots_title": "Exportar Ranuras de Mods",
        "export_slots_sub": "Selecciona las ranuras de mods que deseas exportar a un archivo ZIP.",
        "no_slots_found": "No se encontraron ranuras de mods para exportar.",
        "no_slots_selected": "Selecciona al menos una ranura de mods.",
        "slots_exported_success": "{0} ranura(s) de mods exportadas con éxito en:\n{1}",
        "import_slots_title": "Importar Ranuras de Mods",
        "importing_slots_title": "Importando Ranuras de Mods",
        "slots_imported_count": "{0} ranura(s) de mods importada(s) correctamente.",
        "slots_management": "Ranuras de Mods y Copias",
        "export_slots_btn": "Exportar Slots de Mods",
        "import_slots_btn": "Importar Slots de Mods",
        "pre_reset_title": "Copia Previa al Restablecimiento",
        "pre_reset_sub": "Elige específicamente qué perfiles y qué ranuras de mods deseas respaldar:",
        "reset_backup_external_sub": "Se abrirá el selector de Backup unificado. Elige qué conservar y después volverás aquí para confirmar el restablecimiento.",
        "chk_backup_profiles": "Perfiles y Mundos",
        "chk_backup_slots": "Ranuras de Mods",
        "btn_export_and_continue": "Abrir Backup y Continuar",
        "btn_continue_no_backup": "Continuar sin Backup",
        "no_items_selected_warn": "No has seleccionado ningún perfil ni ranura de mods.\n¿Deseas continuar sin crear una copia de seguridad?",
        "backup_total_success": "Copia unificada creada con éxito ({0} perfil(es), {1} ranura(s)) en:\n{2}",
        "cannot_rename_default_slot": "No se puede renombrar el slot predeterminado.",
        "cannot_delete_default_slot": "No se puede eliminar el slot predeterminado.",
        "rename_slot_title": "Renombrar Slot",
        "rename_slot_prompt": "Nuevo nombre para el slot '{0}':",
        "delete_mod_confirm": "¿Eliminar '{0}'?",
        "mods_installed_count": "{0}/{1} mod(s) instalados correctamente.",
        "delete_modpack_confirm": "¿Eliminar '{0}' (MC {1}) y todos sus mods?",
        "select_game_folder": "Selecciona la carpeta del juego",
        "dir_changed_title": "Directorio Cambiado",
        "dir_changed_msg": "Nueva ruta del juego:\n{0}",
        "error_connecting_mojang": "No se pudo conectar con Mojang:\n{0}",
        "error_launching_title": "Error al lanzar",
        "modrinth_info_error": "No se pudo obtener información del mod en Modrinth.",
        "incompatible_title": "Incompatible",
        "incompatible_mod_msg": "No se encontró un archivo compatible para '{0}'.",
        "mod_installed_success": "'{0}' instalado correctamente.",
        "download_error_title": "Error de Descarga",
        "deps_required_title": "Dependencias Requeridas",
        "deps_required_sub": "Las siguientes dependencias son necesarias para tus mods:",
        "btn_install_all_deps": "Instalar Todas",
        "btn_skip": "Omitir",
        "deps_installed_count": "{0} dependencia(s) instaladas.",
        "fetching_deps_data": "Obteniendo datos de dependencias...",
        # Factory Reset
        "danger_zone_title": "Zona de Peligro",
        "reset_launcher_desc": "Restablece el launcher de fábrica: elimina todos los perfiles, mundos, versiones, mods y datos guardados.",
        "btn_reset_launcher": "Restablecer Todo",
        "factory_reset_title": "Restablecimiento de Fábrica",
        "reset_step1_title": "Confirmar Restablecimiento Total",
        "reset_step1_msg": "¿Estás seguro de que deseas restablecer por completo el launcher?\n\nEsta acción borrará todos los perfiles, mundos/partidas, versiones de Minecraft descargadas, mods, capturas y skins del armario.",
        "reset_step2_title": "¿Hacer Copia de Seguridad?",
        "reset_step2_msg": "¿Deseas exportar una copia de seguridad (backup) de tus perfiles y ranuras de mods antes de restablecer todo?",
        "reset_step3_title": "ÚLTIMA CONFIRMACIÓN",
        "reset_step3_msg": "ATENCIÓN: Esta acción no se puede deshacer. Se borrarán permanentemente todos los datos no respaldados y el launcher volverá a su estado inicial de fábrica.\n\n¿Deseas continuar con el borrado definitivo?",
        "step_final_confirm_title": "Confirmación Final de Borrado",
        "btn_wipe_all_confirm": "Borrar Todo Definitivamente",
        "btn_cancel": "Cancelar",
        "btn_ok": "Aceptar",
        "wiping_data_status": "Borrando todos los datos del launcher y recreando valores de fábrica...",
        "reset_completed_msg": "El launcher se ha restablecido por completo al estado de fábrica.",
        # Onboarding / Welcome Wizard
        "ob_welcome_title": "Bienvenido a Simple Launcher",
        "ob_step_indicator": "Paso {0} de 6",
        "ob_step1_title": "Selecciona tu Idioma",
        "ob_step1_sub": "Elige el idioma que deseas utilizar en el launcher:",
        "ob_lang_es": "🇪🇸 Español",
        "ob_lang_en": "🇬🇧 English",
        "theme_title": "Modo de Apariencia",
        "accent_title": "Color personalizado",
        "accent_subtitle": "Elige un color y el launcher generará automáticamente el resto de la paleta.",
        "accent_choose": "Elegir color",
        "accent_choose_title": "Elegir color del launcher",
        "adaptive_theme_title": "Color Dinámico e Inmersivo",
        "adaptive_theme_sub": "Toda la atmósfera del launcher (fondo, paneles y tarjetas) se genera a partir de tu color elegido.",
        "languages_work_notice": "Portugués y francés están disponibles.",
        "theme_dark": "Oscuro",
        "theme_light": "Claro",
        "theme_system": "Sistema",
        "ob_step1_theme_title": "Tema de Apariencia",
        "ob_step1_theme_sub": "Elige el estilo de apariencia que prefieras:",
        "ob_btn_continue": "Continuar ➔",
        "ob_btn_back": "⬅️ Atrás",
        "ob_step2_title": "¿Tienes una Copia de Seguridad?",
        "ob_step2_sub": "Si vienes de otra instalación o tienes un backup (.zip) de tus perfiles y mods, puedes importarlo ahora mismo.",
        "ob_btn_import_backup": "Importar Copia de Seguridad (.zip)",
        "ob_btn_no_backup": "➡️ Configurar de Cero (No tengo backup)",
        "ob_backup_loaded_title": "Copia activa ({0} perfil(es) listo(s))",
        "ob_backup_loaded_sub": "Tus perfiles, ranuras de mods y configuraciones están cargados.",
        "ob_backup_success_jump": "¡Copia importada con éxito! Pasando directamente a la descarga de versión.",
        "ob_step3_title": "Crea tu Perfil de Jugador",
        "ob_step3_sub": "Introduce el nombre de usuario que usarás en el juego y para guardar tus mundos:",
        "ob_profile_name_label": "Nombre de Jugador / Nickname:",
        "ob_profile_empty_warn": "Por favor introduce un nombre de jugador válido.",
        "ob_step4_title": "Elige tu Skin (Opcional)",
        "ob_step4_sub": "Personaliza la apariencia de tu personaje. Podrás cambiarla en cualquier momento desde el armario de skins.",
        "ob_btn_choose_skin": "Cargar Archivo de Skin (.png)",
        "ob_btn_skip_skin": "Omitir este paso ➔",
        "ob_model_classic": "Clásico (Steve)",
        "ob_model_slim": "Delgado (Alex)",
        "ob_step5_title": "Descargar Versión de Minecraft",
        "ob_step5_sub": "Selecciona una versión de Minecraft para descargarla e instalarla ahora mismo:",
        "ob_version_select_label": "Versión de Minecraft:",
        "ob_btn_download_ver": "Descargar e Instalar Versión",
        "ob_btn_cancel_download": "Cancelar Descarga",
        "ob_ver_installed_badge": "¡Versión instalada y lista para jugar!",
        "ob_btn_skip_download": "Omitir descarga por ahora ➔",
        "ob_step6_title": "¡Todo Listo!",
        "ob_step6_sub": "Aquí tienes un resumen de todo lo que puedes hacer en Simple Launcher:",
        "ob_feat_play_title": "Jugar",
        "ob_feat_play_desc": "Inicia Minecraft con Fabric, skins y ranuras de mods en un solo clic.",
        "ob_feat_vers_title": "Gestor de Versiones",
        "ob_feat_vers_desc": "Descarga, instala y administra versiones oficiales estables.",
        "ob_feat_slots_title": "Ranuras de Mods",
        "ob_feat_slots_desc": "Organiza colecciones de mods independientes por versión sin conflictos.",
        "ob_feat_modrinth_title": "Explorador de Modrinth",
        "ob_feat_modrinth_desc": "Busca e instala mods con resolución automática de dependencias.",
        "ob_feat_skins_title": "Armario de Skins",
        "ob_feat_skins_desc": "Cambia tus skins sin conexión con compatibilidad automática.",
        "ob_feat_settings_title": "Ajustes y Respaldos",
        "ob_feat_settings_desc": "Copias de seguridad ZIP completas, asignación de RAM, sonidos y restablecimiento.",
        "ob_btn_get_started": "Empezar",
        "btn_use": "Usar"
    }
}

# Locales adicionales. Las claves no visibles de compatibilidad conservan el
# inglés como fallback; las pantallas principales están traducidas aquí.
STRINGS["pt"] = dict(STRINGS["en"])
STRINGS["pt"].update({
    "mods_installed_count": "{0}/{1} mod(s) instalado(s) com sucesso.", "delete_modpack_confirm": "Excluir '{0}' (MC {1}) e todos os seus mods?", "ob_step_indicator": "Etapa {0} de 6",
    "nav_jugar": "Jogar", "nav_versiones": "Versões", "nav_mods": "Mods",
    "nav_modrinth": "Modrinth", "nav_modpacks": "Modpacks", "nav_capturas": "Capturas",
    "nav_skins": "Perfis", "nav_ajustes": "Configurações", "usuario": "Usuário",
    "versiones_title": "Gerenciador de versões", "versiones_sub": "Instale, explore e gerencie suas versões do Minecraft.",
    "filter_all": "Todas", "filter_installed": "Instaladas", "filter_releases": "Lançamentos", "filter_snapshots": "Snapshots",
    "search_vers_ph": "Pesquisar versão (ex.: 1.21, 1.20.1, 24w)...", "btn_uninstall": "Desinstalar",
    "btn_install_ver": "Instalar", "status_installed": "✓ Instalada", "status_not_installed": "Não instalada",
    "select_version": "▶ Selecionar", "selected_version": "✓ Ativa", "confirm_uninstall_title": "Desinstalar versão",
    "confirm_uninstall_msg": "Tem certeza de que deseja desinstalar o Minecraft {0}?\nIsso liberará espaço no disco.",
    "installing_title": "Instalando Minecraft {0}...", "btn_cancel_install": "Cancelar instalação",
    "install_cancelled": "Instalação cancelada pelo usuário.", "storage_title": "Armazenamento e uso do disco",
    "btn_view_breakdown": "Ver detalhes", "breakdown_title": "Detalhes do armazenamento", "btn_close": "Fechar",
    "storage_total": "Espaço total usado:", "storage_mc": "Minecraft (versões, recursos e bibliotecas):",
    "storage_mods": "Mods e slots:", "storage_capturas": "Capturas de tela:", "storage_skins": "Skins e cache:",
    "storage_perfiles": "Mundos e perfis:", "storage_refresh": "Recalcular espaço", "storage_calculating": "Calculando...",
    "play_title": "Launcher", "play_subtitle": "Configure e inicie sua sessão do Minecraft",
    "play_summary": "{0}  •  {1}  •  Slot: {2}", "ver_mc": "Versão do Minecraft", "loading_vers": "Carregando versões...",
    "no_results": "Nenhum resultado", "launch_options": "Opções de inicialização", "version_filters": "Filtros de versões",
    "fabric_mods": "Vanilla / Mods", "vulkan": "Vulkan (26.2+)", "snapshots": "Snapshots",
    "show_uninstalled": "Mostrar versões não instaladas", "ver_not_installed_title": "Versão não instalada",
    "ver_not_installed_msg": "O Minecraft {0} não está instalado.\n\nDeseja abrir o Gerenciador de versões e instalá-lo agora?",
    "install_modal_warn": "Aguarde enquanto o Minecraft é instalado. Não feche o launcher.", "fullscreen": "Tela cheia",
    "btn_play": "JOGAR", "ready_to_launch": "Pronto para iniciar.", "console_title": "Registros do jogo",
    "console_copy": "Copiar", "console_clear": "Limpar", "console_ready": "[Launcher] Pronto. Pressione JOGAR para iniciar o Minecraft...\n",
    "console_copied_title": "Copiado", "console_copied_msg": "Registros copiados para a área de transferência.", "game_running": "O jogo está em execução!",
    "mods_title": "Gerenciador de mods", "mod_slot": "Slot de mods", "export_slot": "Exportar slot", "import_slot": "Importar slot",
    "add_mods": "Adicionar mod(s)", "open_folder": "Abrir pasta", "search_mods_ph": "Filtrar mods instalados...",
    "no_mods_found": "Nenhum mod encontrado neste slot. Use o Modrinth para pesquisar e instalar mods.",
    "modrinth_title": "Explorador Modrinth", "modrinth_sub": "Pesquise e instale mods diretamente no seu slot ativo.",
    "modrinth_search_ph": "Pesquisar mod (ex.: Sodium, Iris, Lithium, Mod Menu)...", "btn_search": "Pesquisar",
    "popular": "Populares:", "searching_modrinth": "Pesquisando no Modrinth...", "no_results_modrinth": "Nenhum resultado para '{0}'",
    "btn_install": "Instalar", "btn_installed": "Instalado", "btn_downloading": "Baixando...", "author": "por", "downloads": "downloads",
    "modpacks_title": "Gerenciador de modpacks", "modpacks_sub": "Crie, exporte e importe suas combinações de mods.",
    "create_modpack": "Criar modpack", "export_modpack": "Exportar modpack (.zip)", "import_modpack": "Importar modpack (.zip)",
    "no_modpacks": "Nenhum modpack encontrado. Crie ou importe um modpack.", "apply_modpack": "Aplicar", "delete_modpack": "Excluir",
    "capturas_title": "Galeria de capturas", "capturas_sub": "Explore, gerencie e exporte suas capturas do jogo (F2).",
    "open_screenshot_dir": "Abrir pasta", "btn_refresh": "Atualizar", "btn_view": "Visualizar",
    "no_screenshots": "Nenhuma captura encontrada.\nPressione F2 dentro do Minecraft para tirar uma.", "copy_image": "Copiar",
    "copy_to": "Copiar para...", "open_file": "Abrir arquivo", "delete_image": "Excluir", "rename_image": "Renomear",
    "rename_capture_title": "Renomear captura", "rename_capture_prompt": "Novo nome para '{0}':", "screenshot_title": "Captura de tela",
    "loading_hd": "Carregando em alta definição...", "copy_capture_title": "Copiar captura para...", "success_title": "Sucesso",
    "confirm_title": "Confirmar", "capture_copied_msg": "Captura copiada para:\n{0}", "delete_capture_confirm": "Excluir a captura '{0}'?",
    "unknown": "desconhecido", "install_modpack_btn": "Instalar modpack", "active_tag": "Ativo",
    "skins_title": "Perfis e Skins", "skins_subtitle": "Personalize a skin do seu personagem (funciona offline e no multiplayer).",
    "char_preview": "Pré-visualização do personagem", "front": "Frente", "back": "Costas", "skin_options": "Opções da skin",
    "load_png": "Carregar skin de arquivo local (.png):", "select_png": "Selecionar arquivo PNG",
    "load_nick": "Ou carregar pelo nome oficial do Minecraft (ex.: Steve, Notch):", "nick_ph": "Digite um nome oficial do Minecraft...",
    "btn_load_nick": "Carregar nome", "arm_model": "Modelo dos braços:", "skin_ready": "Skin pronta.",
    "wardrobe_title": "Guarda-roupa de skins", "wardrobe_sub": "Skins salvas — clique para equipar instantaneamente",
    "wardrobe_empty": "Nenhuma skin salva. Aplique uma skin e salve-a no guarda-roupa.", "wardrobe_wear": "Usar",
    "wardrobe_save_title": "Salvar skin no guarda-roupa", "wardrobe_save_msg": "Dê um nome para encontrá-la facilmente:", "wardrobe_save_btn": "Salvar",
    "wardrobe_rename_title": "Renomear skin", "wardrobe_rename_msg": "Digite um novo nome para esta skin:",
    "ajustes_title": "Configurações", "ajustes_subtitle": "Preferências, pastas e perfis do launcher", "language_title": "Idioma",
    "game_folder": "Pasta do jogo", "btn_change": "Alterar", "behavior": "Comportamento", "launcher_fs": "Tela cheia do launcher (F11)",
    "auto_dep": "Instalar dependências dos mods automaticamente", "ui_sounds": "Sons", "users_profiles": "Backup", "full_backup": "Backup completo",
    "selective_backup": "Backup seletivo", "backup_select_items": "Selecione os perfis e slots de mods que deseja incluir.",
    "backup_profiles_group": "Perfis", "backup_slots_group": "Slots de mods", "no_backup_items": "Selecione pelo menos um perfil ou slot de mods.",
    "select_all": "Selecionar tudo", "btn_export_selected": "Exportar selecionados", "no_profiles_selected": "Selecione pelo menos um perfil para exportar.",
    "btn_cancel_export": "Cancelar exportação", "export_cancelled": "Exportação cancelada pelo usuário.", "import_general_backup": "Importar backup",
    "alert_wait": "Aguarde", "alert_file_exists": "Já existe um arquivo com esse nome.", "alert_select_ver": "Selecione uma versão válida.",
    "alert_profile_exists": "Já existe um perfil com esse nome.", "alert_new_profile_title": "Novo perfil", "alert_new_profile_prompt": "Nome do novo usuário/perfil:",
    "alert_rename_title": "Renomear perfil", "alert_rename_prompt": "Novo nome para '{0}':", "alert_delete_profile_title": "Excluir perfil",
    "alert_delete_profile_confirm": "Tem certeza de que deseja excluir o perfil '{0}'?", "alert_created": "Perfil '{0}' criado.",
    "alert_slot_exists": "Já existe um slot com esse nome.", "alert_new_slot_title": "Novo slot", "alert_new_slot_prompt": "Nome do novo slot:",
    "alert_delete_slot_confirm": "Tem certeza de que deseja excluir o slot '{0}'?", "alert_clear_slot_confirm": "Limpar todos os mods do slot '{0}'?",
    "profile_exported": "Perfil '{0}' exportado com sucesso.", "profile_imported": "Perfil '{0}' importado com sucesso.",
    "no_modpacks_installed": "Nenhum modpack instalado.\nUse o botão acima para instalar um.", "select_modpack_title": "Selecionar um modpack",
    "modpack_install_confirm": "Instalar o modpack '{0}' (Minecraft {1})?", "modpack_install_version_confirm": "Este modpack requer o Minecraft {0}. A versão necessária será instalada. Deseja continuar?",
    "modpack_invalid_manifest": "O arquivo selecionado não contém um manifesto válido de modpack Modrinth.", "modpack_filter": "Modpacks",
    "install_zip_title": "Instalar ZIP", "install_zip_prompt": "Nome para o slot do modpack:", "reading_modpack": "Lendo modpack...",
    "downloading_n_mods": "Baixando {0} mods...", "extracting_overrides": "Extraindo arquivos adicionais...", "modpack_tag": "MODPACK",
    "empty_slot_title": "Limpar slot", "empty_slot_confirm": "Excluir TODOS os mods do slot '{0}'?\nEsta ação não pode ser desfeita.",
    "empty_slot_success": "{0} mod(s) excluído(s) do slot '{1}'.", "install_starting": "Iniciando download...", "install_cancelling": "Cancelando e limpando arquivos...",
    "install_cancelled_title": "Cancelado", "install_checking_java": "Verificando Java para {0}...", "install_downloading_ver": "Baixando Minecraft {0}...",
    "install_checking_files": "Verificando arquivos de {0}...", "install_checking_java_short": "Verificando Java...", "install_checking_fabric": "Verificando Fabric...",
    "install_installing_fabric": "Instalando Fabric Loader...", "modrinth_no_mods": "Nenhum mod encontrado.", "modrinth_no_results_label": "Nenhum resultado para esta pesquisa.",
    "modrinth_error_connect": "Erro ao conectar ao Modrinth.", "importing_profile_title": "Importando backup de perfil", "importing_file": "Importando: {0}",
    "import_cancelled": "Importação cancelada pelo usuário.", "reading_backup_zip": "Lendo arquivo de backup...", "extracting_profiles": "Extraindo perfis...",
    "no_slots_found": "Nenhum slot de mods encontrado para exportar.", "no_slots_selected": "Selecione pelo menos um slot de mods.", "slots_management": "Slots de mods e backup",
    "export_slots_btn": "Exportar slots de mods", "import_slots_btn": "Importar slots de mods", "chk_backup_profiles": "Perfis e mundos", "chk_backup_slots": "Slots de mods",
    "btn_export_and_continue": "Abrir backup e continuar", "btn_continue_no_backup": "Continuar sem backup", "danger_zone_title": "Zona de perigo",
    "reset_launcher_desc": "Exclui os dados do launcher depois de permitir que você crie um backup.", "btn_reset_launcher": "Restabelecer launcher",
    "btn_wipe_all_confirm": "Excluir tudo", "btn_cancel": "Cancelar", "btn_ok": "OK", "wiping_data_status": "Excluindo dados...",
    "reset_completed_msg": "O launcher foi restaurado com sucesso.", "ob_welcome_title": "Bem-vindo ao Simple Launcher", "ob_step_indicator": "Etapa {0} de {1}",
    "ob_step1_title": "Vamos começar", "ob_step1_sub": "Escolha seu idioma e a aparência do launcher.", "ob_lang_es": "Espanhol", "ob_lang_en": "Inglês",
    "theme_title": "Aparência", "languages_work_notice": "Português e francês disponíveis.", "theme_dark": "Escuro", "theme_light": "Claro", "theme_system": "Sistema", "adaptive_theme_title": "Aparência adaptável", "adaptive_theme_sub": "O launcher seguirá automaticamente o modo claro ou escuro do seu sistema.",
    "ob_step1_theme_title": "Escolha o tema", "ob_step1_theme_sub": "Você poderá alterá-lo depois nas configurações.", "ob_btn_continue": "Continuar", "ob_btn_back": "Voltar",
    "ob_step2_title": "Você tem um backup?", "ob_step2_sub": "Importe seus perfis e configurações ou comece do zero.", "ob_btn_import_backup": "Importar backup", "ob_btn_no_backup": "Começar do zero",
    "ob_backup_success_jump": "Backup importado. Pulando para a próxima etapa...", "ob_step3_title": "Crie seu perfil", "ob_step3_sub": "Escolha um nome para seu perfil principal.",
    "ob_profile_name_label": "Nome do perfil", "ob_profile_empty_warn": "Digite um nome para continuar.", "ob_step4_title": "Escolha sua skin", "ob_step4_sub": "Adicione uma skin agora ou faça isso depois.",
    "ob_btn_choose_skin": "Escolher skin", "ob_btn_skip_skin": "Pular por enquanto", "ob_model_classic": "Clássico", "ob_model_slim": "Fino",
    "ob_step5_title": "Escolha uma versão", "ob_step5_sub": "Instale uma versão estável agora ou faça isso depois.", "ob_version_select_label": "Versão do Minecraft",
    "ob_btn_download_ver": "Baixar versão", "ob_btn_cancel_download": "Cancelar download", "ob_ver_installed_badge": "Instalada", "ob_btn_skip_download": "Pular download",
    "ob_step6_title": "Tudo pronto!", "ob_step6_sub": "O Simple Launcher está preparado para você.", "ob_feat_play_title": "Jogar", "ob_feat_play_desc": "Inicie o Minecraft rapidamente.",
    "ob_feat_vers_title": "Versões", "ob_feat_vers_desc": "Gerencie suas versões instaladas.", "ob_feat_slots_title": "Slots de mods", "ob_feat_slots_desc": "Organize diferentes combinações de mods.",
    "ob_feat_modrinth_title": "Modrinth", "ob_feat_modrinth_desc": "Encontre mods dentro do launcher.", "ob_feat_skins_title": "Skins", "ob_feat_skins_desc": "Gerencie suas skins offline.",
    "ob_feat_settings_title": "Configurações e backups", "ob_feat_settings_desc": "Proteja seus perfis e personalize o launcher.", "ob_btn_get_started": "Começar",
})
STRINGS["fr"] = dict(STRINGS["en"])
STRINGS["fr"].update({
    "mods_installed_count": "{0}/{1} mod(s) installé(s) avec succès.", "delete_modpack_confirm": "Supprimer « {0} » (MC {1}) et tous ses mods ?", "ob_step_indicator": "Étape {0} sur 6",
    "nav_jugar": "Jouer", "nav_versiones": "Versions", "nav_mods": "Mods", "nav_modrinth": "Modrinth",
    "nav_modpacks": "Modpacks", "nav_capturas": "Captures", "nav_skins": "Profils", "nav_ajustes": "Paramètres", "usuario": "Utilisateur",
    "versiones_title": "Gestionnaire de versions", "versiones_sub": "Installez, explorez et gérez vos versions de Minecraft.", "filter_all": "Toutes", "filter_installed": "Installées",
    "filter_releases": "Versions stables", "filter_snapshots": "Snapshots", "search_vers_ph": "Rechercher une version (ex. 1.21, 1.20.1, 24w)...",
    "btn_uninstall": "Désinstaller", "btn_install_ver": "Installer", "status_installed": "✓ Installée", "status_not_installed": "Non installée",
    "select_version": "▶ Sélectionner", "selected_version": "✓ Active", "confirm_uninstall_title": "Désinstaller la version", "confirm_uninstall_msg": "Voulez-vous vraiment désinstaller Minecraft {0} ?\nCela libérera de l'espace disque.",
    "installing_title": "Installation de Minecraft {0}...", "btn_cancel_install": "Annuler l'installation", "install_cancelled": "Installation annulée par l'utilisateur.",
    "storage_title": "Stockage et espace disque", "btn_view_breakdown": "Voir les détails", "breakdown_title": "Détails du stockage", "btn_close": "Fermer",
    "storage_total": "Espace total utilisé :", "storage_mc": "Minecraft (versions, ressources et bibliothèques) :", "storage_mods": "Mods et slots :",
    "storage_capturas": "Captures d'écran :", "storage_skins": "Skins et cache :", "storage_perfiles": "Mondes et profils :", "storage_refresh": "Recalculer l'espace", "storage_calculating": "Calcul en cours...",
    "play_title": "Launcher", "play_subtitle": "Configurez et lancez votre session Minecraft", "play_summary": "{0}  •  {1}  •  Slot : {2}", "ver_mc": "Version de Minecraft", "loading_vers": "Chargement des versions...", "no_results": "Aucun résultat",
    "launch_options": "Options de lancement", "version_filters": "Filtres de versions", "fabric_mods": "Vanilla / Mods", "vulkan": "Vulkan (26.2+)", "show_uninstalled": "Afficher les versions non installées",
    "ver_not_installed_title": "Version non installée", "ver_not_installed_msg": "Minecraft {0} n'est pas installé.\n\nVoulez-vous ouvrir le gestionnaire de versions pour l'installer maintenant ?", "install_modal_warn": "Veuillez patienter pendant l'installation de Minecraft. Ne fermez pas le launcher.",
    "fullscreen": "Plein écran", "btn_play": "JOUER", "ready_to_launch": "Prêt à lancer.", "console_title": "Journaux du jeu", "console_copy": "Copier", "console_clear": "Effacer",
    "console_ready": "[Launcher] Prêt. Appuyez sur JOUER pour lancer Minecraft...\n", "console_copied_title": "Copié", "console_copied_msg": "Les journaux ont été copiés dans le presse-papiers.", "game_running": "Le jeu est en cours d'exécution !",
    "mods_title": "Gestionnaire de mods", "mod_slot": "Slot de mods", "export_slot": "Exporter le slot", "import_slot": "Importer le slot", "add_mods": "Ajouter un ou plusieurs mods", "open_folder": "Ouvrir le dossier",
    "search_mods_ph": "Filtrer les mods installés...", "no_mods_found": "Aucun mod trouvé dans ce slot. Utilisez Modrinth pour rechercher et installer des mods.",
    "modrinth_title": "Explorateur Modrinth", "modrinth_sub": "Recherchez et installez des mods directement dans votre slot actif.", "modrinth_search_ph": "Rechercher un mod (ex. Sodium, Iris, Lithium, Mod Menu)...", "btn_search": "Rechercher",
    "popular": "Populaires :", "searching_modrinth": "Recherche sur Modrinth...", "no_results_modrinth": "Aucun résultat pour « {0} »", "btn_install": "Installer", "btn_installed": "Installé", "btn_downloading": "Téléchargement...", "author": "par", "downloads": "téléchargements",
    "modpacks_title": "Gestionnaire de modpacks", "modpacks_sub": "Créez, exportez et importez vos combinaisons de mods.", "create_modpack": "Créer un modpack", "export_modpack": "Exporter le modpack (.zip)", "import_modpack": "Importer le modpack (.zip)", "no_modpacks": "Aucun modpack trouvé. Créez ou importez-en un.", "apply_modpack": "Appliquer", "delete_modpack": "Supprimer",
    "capturas_title": "Galerie de captures", "capturas_sub": "Explorez, gérez et exportez vos captures du jeu (F2).", "open_screenshot_dir": "Ouvrir le dossier", "btn_refresh": "Actualiser", "btn_view": "Voir", "no_screenshots": "Aucune capture trouvée.\nAppuyez sur F2 dans Minecraft pour en prendre une.", "copy_image": "Copier", "copy_to": "Copier vers...", "open_file": "Ouvrir le fichier", "delete_image": "Supprimer", "rename_image": "Renommer",
    "rename_capture_title": "Renommer la capture", "rename_capture_prompt": "Nouveau nom pour « {0} » :", "screenshot_title": "Capture d'écran", "loading_hd": "Chargement en haute définition...", "copy_capture_title": "Copier la capture vers...", "success_title": "Succès", "confirm_title": "Confirmer", "capture_copied_msg": "Capture copiée vers :\n{0}", "delete_capture_confirm": "Supprimer la capture « {0} » ?", "unknown": "inconnu", "install_modpack_btn": "Installer un modpack", "active_tag": "Actif",
    "skins_title": "Profils et Skins", "skins_subtitle": "Personnalisez le skin de votre personnage (hors ligne et en multijoueur).", "char_preview": "Aperçu du personnage", "front": "Avant", "back": "Arrière", "skin_options": "Options du skin", "load_png": "Charger un skin depuis un fichier local (.png) :", "select_png": "Sélectionner un fichier PNG", "load_nick": "Ou charger depuis un nom Minecraft officiel (ex. Steve, Notch) :", "nick_ph": "Saisissez un nom Minecraft officiel...", "btn_load_nick": "Charger le nom", "arm_model": "Modèle des bras :", "skin_ready": "Skin prêt.",
    "wardrobe_title": "Garde-robe de skins", "wardrobe_sub": "Skins enregistrés — cliquez pour équiper instantanément", "wardrobe_empty": "Aucun skin enregistré. Appliquez un skin puis enregistrez-le dans la garde-robe.", "wardrobe_wear": "Porter", "wardrobe_save_title": "Enregistrer le skin dans la garde-robe", "wardrobe_save_msg": "Donnez-lui un nom pour le retrouver facilement :", "wardrobe_save_btn": "Enregistrer", "wardrobe_rename_title": "Renommer le skin", "wardrobe_rename_msg": "Saisissez un nouveau nom pour ce skin :",
    "ajustes_title": "Paramètres", "ajustes_subtitle": "Préférences, dossiers et profils du launcher", "language_title": "Langue", "game_folder": "Dossier du jeu", "btn_change": "Modifier", "behavior": "Comportement", "launcher_fs": "Launcher en plein écran (F11)", "auto_dep": "Installer automatiquement les dépendances des mods", "ui_sounds": "Sons", "users_profiles": "Backup", "full_backup": "Backup complet", "selective_backup": "Backup sélectif", "backup_select_items": "Sélectionnez les profils et slots de mods à inclure.", "backup_profiles_group": "Profils", "backup_slots_group": "Slots de mods", "no_backup_items": "Sélectionnez au moins un profil ou un slot de mods.", "select_all": "Tout sélectionner", "btn_export_selected": "Exporter la sélection", "no_profiles_selected": "Sélectionnez au moins un profil à exporter.", "btn_cancel_export": "Annuler l'exportation", "export_cancelled": "Exportation annulée par l'utilisateur.", "import_general_backup": "Importer un backup",
    "alert_wait": "Patientez", "alert_file_exists": "Un fichier portant ce nom existe déjà.", "alert_select_ver": "Sélectionnez une version valide.", "alert_profile_exists": "Un profil portant ce nom existe déjà.", "alert_new_profile_title": "Nouveau profil", "alert_new_profile_prompt": "Nom du nouvel utilisateur/profil :", "alert_rename_title": "Renommer le profil", "alert_rename_prompt": "Nouveau nom pour « {0} » :", "alert_delete_profile_title": "Supprimer le profil", "alert_delete_profile_confirm": "Voulez-vous vraiment supprimer le profil « {0} » ?", "alert_created": "Profil « {0} » créé.", "alert_slot_exists": "Un slot portant ce nom existe déjà.", "alert_new_slot_title": "Nouveau slot", "alert_new_slot_prompt": "Nom du nouveau slot :", "alert_delete_slot_confirm": "Voulez-vous vraiment supprimer le slot « {0} » ?", "alert_clear_slot_confirm": "Supprimer tous les mods du slot « {0} » ?", "profile_exported": "Profil « {0} » exporté avec succès.", "profile_imported": "Profil « {0} » importé avec succès.",
    "no_modpacks_installed": "Aucun modpack installé.\nUtilisez le bouton ci-dessus pour en installer un.", "select_modpack_title": "Sélectionner un modpack", "modpack_install_confirm": "Installer le modpack « {0} » (Minecraft {1}) ?", "modpack_install_version_confirm": "Ce modpack nécessite Minecraft {0}. La version requise sera installée. Voulez-vous continuer ?", "modpack_invalid_manifest": "Le fichier sélectionné ne contient pas de manifeste de modpack Modrinth valide.", "modpack_filter": "Modpacks", "install_zip_title": "Installer un ZIP", "install_zip_prompt": "Nom du slot du modpack :", "reading_modpack": "Lecture du modpack...", "downloading_n_mods": "Téléchargement de {0} mods...", "extracting_overrides": "Extraction des fichiers supplémentaires...", "modpack_tag": "MODPACK",
    "empty_slot_title": "Vider le slot", "empty_slot_confirm": "Supprimer TOUS les mods du slot « {0} » ?\nCette action est irréversible.", "empty_slot_success": "{0} mod(s) supprimé(s) du slot « {1} ».", "install_starting": "Démarrage du téléchargement...", "install_cancelling": "Annulation et nettoyage des fichiers...", "install_cancelled_title": "Annulé", "install_checking_java": "Vérification de Java pour {0}...", "install_downloading_ver": "Téléchargement de Minecraft {0}...", "install_checking_files": "Vérification des fichiers de {0}...", "install_checking_java_short": "Vérification de Java...", "install_checking_fabric": "Vérification de Fabric...", "install_installing_fabric": "Installation de Fabric Loader...", "modrinth_no_mods": "Aucun mod trouvé.", "modrinth_no_results_label": "Aucun résultat pour cette recherche.", "modrinth_error_connect": "Erreur de connexion à Modrinth.", "importing_profile_title": "Importation du backup de profil", "importing_file": "Importation : {0}", "import_cancelled": "Importation annulée par l'utilisateur.", "reading_backup_zip": "Lecture de l'archive de backup...", "extracting_profiles": "Extraction des profils...", "no_slots_found": "Aucun slot de mods trouvé à exporter.", "no_slots_selected": "Sélectionnez au moins un slot de mods.", "slots_management": "Slots de mods et backup", "export_slots_btn": "Exporter les slots de mods", "import_slots_btn": "Importer les slots de mods", "chk_backup_profiles": "Profils et mondes", "chk_backup_slots": "Slots de mods", "btn_export_and_continue": "Ouvrir le backup et continuer", "btn_continue_no_backup": "Continuer sans backup",
    "danger_zone_title": "Zone dangereuse", "reset_launcher_desc": "Supprime les données du launcher après vous avoir permis de créer un backup.", "btn_reset_launcher": "Réinitialiser le launcher", "btn_wipe_all_confirm": "Tout supprimer", "btn_cancel": "Annuler", "btn_ok": "OK", "wiping_data_status": "Suppression des données...", "reset_completed_msg": "Le launcher a été réinitialisé avec succès.",
    "ob_welcome_title": "Bienvenue dans Simple Launcher", "ob_step_indicator": "Étape {0} sur {1}", "ob_step1_title": "Commençons", "ob_step1_sub": "Choisissez la langue et l'apparence du launcher.", "ob_lang_es": "Espagnol", "ob_lang_en": "Anglais", "theme_title": "Apparence", "languages_work_notice": "Portugais et français disponibles.", "theme_dark": "Sombre", "theme_light": "Clair", "theme_system": "Système", "ob_step1_theme_title": "Choisissez un thème", "ob_step1_theme_sub": "Vous pourrez le modifier plus tard dans les paramètres.", "ob_btn_continue": "Continuer", "ob_btn_back": "Retour", "ob_step2_title": "Avez-vous un backup ?", "ob_step2_sub": "Importez vos profils et paramètres ou commencez de zéro.", "ob_btn_import_backup": "Importer un backup", "ob_btn_no_backup": "Commencer de zéro", "ob_backup_success_jump": "Backup importé. Passage à l'étape suivante...", "ob_step3_title": "Créez votre profil", "ob_step3_sub": "Choisissez un nom pour votre profil principal.", "ob_profile_name_label": "Nom du profil", "ob_profile_empty_warn": "Saisissez un nom pour continuer.", "ob_step4_title": "Choisissez votre skin", "ob_step4_sub": "Ajoutez un skin maintenant ou faites-le plus tard.", "ob_btn_choose_skin": "Choisir un skin", "ob_btn_skip_skin": "Passer pour l'instant", "ob_model_classic": "Classique", "ob_model_slim": "Fin", "ob_step5_title": "Choisissez une version", "ob_step5_sub": "Installez une version stable maintenant ou faites-le plus tard.", "ob_version_select_label": "Version de Minecraft", "ob_btn_download_ver": "Télécharger la version", "ob_btn_cancel_download": "Annuler le téléchargement", "ob_ver_installed_badge": "Installée", "ob_btn_skip_download": "Passer le téléchargement", "ob_step6_title": "Tout est prêt !", "ob_step6_sub": "Simple Launcher est prêt à être utilisé.", "ob_feat_play_title": "Jouer", "ob_feat_play_desc": "Lancez Minecraft rapidement.", "ob_feat_vers_title": "Versions", "ob_feat_vers_desc": "Gérez vos versions installées.", "ob_feat_slots_title": "Slots de mods", "ob_feat_slots_desc": "Organisez différentes combinaisons de mods.", "ob_feat_modrinth_title": "Modrinth", "ob_feat_modrinth_desc": "Trouvez des mods depuis le launcher.", "ob_feat_skins_title": "Skins", "ob_feat_skins_desc": "Gérez vos skins hors ligne.", "ob_feat_settings_title": "Paramètres et backups", "ob_feat_settings_desc": "Protégez vos profils et personnalisez le launcher.", "ob_btn_get_started": "Commencer",
})

# Mensagens secundárias usadas por fluxos antigos e diálogos especializados.
STRINGS["pt"].update({
    "export_profile": "Exportar perfil", "export_profiles_title": "Exportar perfis", "export_profiles_sub": "Selecione os perfis para incluir no arquivo de backup.",
    "compressing_profile": "Comprimindo perfil: {0} ({1}/{2})...", "profiles_exported_success": "{0} perfil(is) exportado(s) com sucesso para:\n{1}", "import_profile": "Importar perfil",
    "alert_nick_only": "Links diretos não são permitidos. Digite um nome oficial do Minecraft ou selecione um PNG local.", "alert_nick_title": "Somente nomes de usuário",
    "dir_changed_title": "Pasta alterada", "dir_changed_msg": "Novo caminho:\n{0}", "zip_files": "Arquivo ZIP", "profile_zip_file": "ZIP de perfil/backup", "profile_prefix": "perfil", "profiles_suffix": "perfis", "slot_zip_file": "ZIP de slot de mods",
    "export_slot_title": "Exportar slot", "import_slot_title": "Importar slot", "no_mods_in_slot_export": "Não há mods neste slot para exportar.", "slot_exported_msg": "Slot '{0}' exportado para:\n{1}", "import_slot_prompt": "Nome do slot importado:", "no_jars_in_zip": "O arquivo ZIP não contém arquivos .jar.", "slot_imported_msg": "{0} mods importados para o slot '{1}'.", "alert_profile_exists_rename": "Já existe um perfil chamado '{0}'. Novo nome:", "profiles_imported_count": "{0} perfil(is) importado(s) com sucesso.", "invalid_profile_zip": "O arquivo não é um backup de perfil válido exportado por este launcher.",
    "modpack_filter": "Modpacks", "modpack_installed_status": "'{0}' instalado com sucesso.", "modpack_installed_msg": "'{0}' (MC {1}) instalado no slot '{2}'.", "reading_zip": "Lendo ZIP...", "no_jars_in_zip_status": "Nenhum arquivo .jar encontrado no ZIP.", "zip_installed_status": "{0} mods instalados em '{1}'.", "zip_installed_msg": "{0} mods instalados em '{1}'.",
    "modrinth_n_results": "{0} mods encontrados para '{1}'.", "modrinth_n_results_popular": "{0} mods populares encontrados.", "export_slots_title": "Exportar slots de mods", "export_slots_sub": "Selecione os slots de mods que deseja salvar em um arquivo ZIP.", "slots_exported_success": "{0} slot(s) de mods exportado(s) com sucesso para:\n{1}", "import_slots_title": "Importar slots de mods", "importing_slots_title": "Importando slots de mods", "slots_imported_count": "{0} slot(s) de mods importado(s) com sucesso.",
    "pre_reset_title": "Seleção de backup antes da restauração", "pre_reset_sub": "Selecione os perfis e slots de mods que deseja preservar:", "reset_backup_external_sub": "O seletor de backup unificado será aberto separadamente. Escolha o que preservar e volte para confirmar a restauração.", "no_items_selected_warn": "Nenhum perfil ou slot foi selecionado.\nDeseja continuar sem criar um backup?", "backup_total_success": "Backup unificado criado com {0} perfil(is) e {1} slot(s) em:\n{2}", "cannot_rename_default_slot": "Não é possível renomear o slot padrão.", "cannot_delete_default_slot": "Não é possível excluir o slot padrão.", "rename_slot_title": "Renomear slot", "rename_slot_prompt": "Novo nome para '{0}':", "delete_mod_confirm": "Excluir o mod '{0}'?", "mods_installed_count": "{0} mod(s) instalado(s).", "delete_modpack_confirm": "Excluir o modpack '{0}'?", "select_game_folder": "Selecionar pasta do jogo",
    "error_connecting_mojang": "Não foi possível conectar à Mojang:\n{0}", "error_launching_title": "Erro ao iniciar o jogo", "modrinth_info_error": "Não foi possível carregar as informações do Modrinth.", "incompatible_title": "Loader incompatível", "incompatible_mod_msg": "Nenhum arquivo compatível encontrado para '{0}'.", "mod_installed_success": "'{0}' instalado com sucesso.", "download_error_title": "Erro de download", "deps_required_title": "Dependências necessárias", "deps_required_sub": "Alguns mods precisam de dependências adicionais.", "btn_install_all_deps": "Instalar todas as dependências", "btn_skip": "Pular", "deps_installed_count": "{0} dependência(s) instalada(s).", "fetching_deps_data": "Buscando informações das dependências...",
    "factory_reset_title": "Restauração de fábrica", "reset_step1_title": "Etapa 1 — Backup", "reset_step1_msg": "Crie um backup antes de continuar.", "reset_step2_title": "Etapa 2 — Confirmação", "reset_step2_msg": "Esta ação removerá os dados do launcher.", "reset_step3_title": "Etapa 3 — Confirmação final", "reset_step3_msg": "Todos os dados selecionados serão excluídos.", "step_final_confirm_title": "Confirmar restauração", "ob_backup_loaded_title": "Backup ativo ({0} perfil(is) pronto(s))", "ob_backup_loaded_sub": "Um backup foi encontrado e está pronto para ser importado.",
})
STRINGS["fr"].update({
    "export_profile": "Exporter le profil", "export_profiles_title": "Exporter les profils", "export_profiles_sub": "Sélectionnez les profils à inclure dans l'archive de backup.", "compressing_profile": "Compression du profil : {0} ({1}/{2})...", "profiles_exported_success": "{0} profil(s) exporté(s) avec succès vers :\n{1}", "import_profile": "Importer un profil",
    "alert_nick_only": "Les liens directs ne sont pas autorisés. Saisissez un nom Minecraft officiel ou sélectionnez un PNG local.", "alert_nick_title": "Noms d'utilisateur uniquement", "dir_changed_title": "Dossier modifié", "dir_changed_msg": "Nouveau chemin :\n{0}", "zip_files": "Archive ZIP", "profile_zip_file": "ZIP de profil/backup", "profile_prefix": "profil", "profiles_suffix": "profils", "slot_zip_file": "ZIP de slot de mods",
    "export_slot_title": "Exporter le slot", "import_slot_title": "Importer le slot", "no_mods_in_slot_export": "Aucun mod à exporter dans ce slot.", "slot_exported_msg": "Slot « {0} » exporté vers :\n{1}", "import_slot_prompt": "Nom du slot importé :", "no_jars_in_zip": "L'archive ZIP ne contient aucun fichier .jar.", "slot_imported_msg": "{0} mods importés dans le slot « {1} ».", "alert_profile_exists_rename": "Un profil nommé « {0} » existe déjà. Nouveau nom :", "profiles_imported_count": "{0} profil(s) importé(s) avec succès.", "invalid_profile_zip": "Le fichier n'est pas une archive de profil valide exportée par ce launcher.",
    "modpack_filter": "Modpacks", "modpack_installed_status": "« {0} » installé avec succès.", "modpack_installed_msg": "« {0} » (MC {1}) installé dans le slot « {2} ».", "reading_zip": "Lecture du ZIP...", "no_jars_in_zip_status": "Aucun fichier .jar trouvé dans le ZIP.", "zip_installed_status": "{0} mods installés dans « {1} ».", "zip_installed_msg": "{0} mods installés dans « {1} ».",
    "modrinth_n_results": "{0} mods trouvés pour « {1} ».", "modrinth_n_results_popular": "{0} mods populaires trouvés.", "export_slots_title": "Exporter les slots de mods", "export_slots_sub": "Sélectionnez les slots de mods à sauvegarder dans une archive ZIP.", "slots_exported_success": "{0} slot(s) de mods exporté(s) avec succès vers :\n{1}", "import_slots_title": "Importer les slots de mods", "importing_slots_title": "Importation des slots de mods", "slots_imported_count": "{0} slot(s) de mods importé(s) avec succès.",
    "pre_reset_title": "Sélection du backup avant réinitialisation", "pre_reset_sub": "Sélectionnez les profils et slots de mods à préserver :", "reset_backup_external_sub": "Le sélecteur de backup unifié s'ouvrira séparément. Choisissez ce qui doit être conservé puis revenez confirmer la réinitialisation.", "no_items_selected_warn": "Aucun profil ou slot n'a été sélectionné.\nVoulez-vous continuer sans créer de backup ?", "backup_total_success": "Backup unifié créé avec {0} profil(s) et {1} slot(s) ici :\n{2}", "cannot_rename_default_slot": "Impossible de renommer le slot par défaut.", "cannot_delete_default_slot": "Impossible de supprimer le slot par défaut.", "rename_slot_title": "Renommer le slot", "rename_slot_prompt": "Nouveau nom pour « {0} » :", "delete_mod_confirm": "Supprimer le mod « {0} » ?", "mods_installed_count": "{0} mod(s) installé(s).", "delete_modpack_confirm": "Supprimer le modpack « {0} » ?", "select_game_folder": "Sélectionner le dossier du jeu",
    "error_connecting_mojang": "Impossible de se connecter à Mojang :\n{0}", "error_launching_title": "Erreur au lancement du jeu", "modrinth_info_error": "Impossible de charger les informations Modrinth.", "incompatible_title": "Loader incompatible", "incompatible_mod_msg": "Aucun fichier compatible trouvé pour « {0} ».", "mod_installed_success": "« {0} » installé avec succès.", "download_error_title": "Erreur de téléchargement", "deps_required_title": "Dépendances requises", "deps_required_sub": "Certains mods nécessitent des dépendances supplémentaires.", "btn_install_all_deps": "Installer toutes les dépendances", "btn_skip": "Passer", "deps_installed_count": "{0} dépendance(s) installée(s).", "fetching_deps_data": "Recherche des informations sur les dépendances...",
    "factory_reset_title": "Réinitialisation d'usine", "reset_step1_title": "Étape 1 — Backup", "reset_step1_msg": "Créez un backup avant de continuer.", "reset_step2_title": "Étape 2 — Confirmation", "reset_step2_msg": "Cette action supprimera les données du launcher.", "reset_step3_title": "Étape 3 — Confirmation finale", "reset_step3_msg": "Toutes les données sélectionnées seront supprimées.", "step_final_confirm_title": "Confirmer la réinitialisation", "ob_backup_loaded_title": "Backup actif ({0} profil(s) prêt(s))", "ob_backup_loaded_sub": "Un backup a été trouvé et est prêt à être importé.",
})

# Ajustes finales de mensajes con variables dinámicas.
STRINGS["pt"].update({
    "accent_title": "Cor personalizada", "accent_subtitle": "Escolha uma cor e o launcher gerará automaticamente o restante da paleta.", "accent_choose": "Escolher cor", "accent_choose_title": "Escolher cor do launcher",
    "mods_installed_count": "{0}/{1} mod(s) instalado(s) com sucesso.",
    "delete_modpack_confirm": "Excluir '{0}' (MC {1}) e todos os seus mods?",
    "ob_step_indicator": "Etapa {0} de 6",
    "btn_use": "Usar",
})
STRINGS["fr"].update({
    "accent_title": "Couleur personnalisée", "accent_subtitle": "Choisissez une couleur et le launcher générera automatiquement le reste de la palette.", "accent_choose": "Choisir une couleur", "accent_choose_title": "Choisir la couleur du launcher",
    "mods_installed_count": "{0}/{1} mod(s) installé(s) avec succès.",
    "delete_modpack_confirm": "Supprimer « {0} » (MC {1}) et tous ses mods ?",
    "ob_step_indicator": "Étape {0} sur 6",
    "btn_use": "Utiliser",
})

STRINGS["pt"].update({
    "adaptive_theme_title": "Aparência adaptável",
    "adaptive_theme_sub": "O launcher seguirá automaticamente o modo claro ou escuro do seu sistema.",
})
STRINGS["fr"].update({
    "adaptive_theme_title": "Apparence adaptative",
    "adaptive_theme_sub": "Le launcher suivra automatiquement le mode clair ou sombre de votre système.",
})

class MinecraftLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Launcher")
        self.root.geometry("940x580")
        self.root.resizable(True, True)
        self.root.configure(fg_color=BG_DARK)

        self.ruta_icono = obtener_ruta_recurso("icon.ico")
        if os.path.exists(self.ruta_icono):
            try:
                self.root.iconbitmap(self.ruta_icono)
            except Exception:
                pass

        self.todas_las_versiones = []
        self.max_progress = 0
        self.vista_actual  = "jugar"
        self.nav_buttons   = {}
        self.nav_accents   = {}
        self.vistas        = {}
        self._size_cache   = {}
        self._skin_preview_cache = {}
        self._skin_3d_angle = 0
        self._capture_thumb_cache = {}
        self.config_data   = cargar_configuracion()
        self._aplicar_paleta(self.config_data.get("accent_color", "#72c3cb"))
        self.root.configure(fg_color=BG_DARK)
        self.lang          = self.config_data.get("language", "en")
        self.sound         = SoundManager(enabled=self.config_data.get("ui_sounds", True))

        # Apariencia oscura inmersiva con temática generada dinámicamente
        try: ctk.set_appearance_mode("dark")
        except Exception: pass

        # Configurar modo pantalla completa del lanzador
        self.is_launcher_fs = self.config_data.get("launcher_fullscreen", False)
        if self.is_launcher_fs:
            try: self.root.attributes("-fullscreen", True)
            except Exception: pass

        self.root.bind("<F11>", lambda e: self.toggle_launcher_fullscreen())
        self.root.bind("<Escape>", lambda e: self.exit_launcher_fullscreen())

        # Logo
        self._crear_logo_dinamico()

        # Descarga de versiones en segundo plano
        threading.Thread(target=self._descargar_versiones, daemon=True).start()

        # Iniciar UI según estado de onboarding
        if not self.config_data.get("onboarding_completed", False):
            self._iniciar_onboarding()
        else:
            self._iniciar_ui_principal()

    def _aplicar_paleta(self, color_semilla):
        """Actualiza los roles de color usados por las vistas del launcher."""
        paleta = generar_paleta(color_semilla)
        for nombre, valor in paleta.items():
            if not nombre.startswith("_"):
                globals()[nombre] = valor

    def _crear_logo_dinamico(self):
        """Carga el SVG incluido y adapta su turquesa al color elegido."""
        self.logo_ctk = None
        ruta_logo_svg = obtener_ruta_recurso("icon.svg")
        img_logo = cargar_logo_svg(ruta_logo_svg) if os.path.exists(ruta_logo_svg) else None
        if img_logo is None and os.path.exists(self.ruta_icono):
            try:
                img_logo = Image.open(self.ruta_icono).convert("RGBA")
            except Exception:
                img_logo = None
        if img_logo is not None:
            img_logo = recolorear_logo(img_logo, self.config_data.get("accent_color", "#72c3cb"))
            logo_h = 36
            logo_w = max(1, round(logo_h * img_logo.width / img_logo.height))
            self.logo_ctk = ctk.CTkImage(light_image=img_logo, dark_image=img_logo, size=(logo_w, logo_h))

    def _cambiar_color_semilla(self):
        actual = self.config_data.get("accent_color", "#72c3cb")
        elegido = colorchooser.askcolor(color=actual, title=self.t("accent_choose_title"))
        color = elegido[1] if elegido and elegido[1] else None
        if not color:
            return
        self.config_data["accent_color"] = color.lower()
        guardar_configuracion(self.config_data)
        self._aplicar_paleta(color)
        self._crear_logo_dinamico()
        self.root.configure(fg_color=BG_DARK)
        self._reconstruir_ui()


    # ──────────────────────────────────────────────
    # SISTEMA DE ONBOARDING / PANTALLA DE BIENVENIDA
    # ──────────────────────────────────────────────
    def _iniciar_onboarding(self):
        """Inicia el asistente de bienvenida y configuración inicial de 6 pasos."""
        for w in self.root.winfo_children():
            w.destroy()

        self._onboarding_from_backup = self.config_data.get("onboarding_from_backup", False)

        self.onboarding_frame = ctk.CTkFrame(self.root, fg_color=BG_DARK, corner_radius=0)
        self.onboarding_frame.pack(fill="both", expand=True)

        # Barra superior con logo, título e indicador de paso
        top_bar = ctk.CTkFrame(self.onboarding_frame, fg_color=BG_SIDE, height=60, corner_radius=0)
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)

        logo_title = ctk.CTkFrame(top_bar, fg_color="transparent")
        logo_title.pack(side="left", padx=20, pady=10)
        if self.logo_ctk:
            ctk.CTkLabel(logo_title, image=self.logo_ctk, text="").pack(side="left", padx=(0, 10))
        ctk.CTkLabel(logo_title, text="Simple Launcher", font=FONT_TITLE_S, text_color=ACCENT).pack(side="left")

        # Badge del paso actual
        self.lbl_ob_step_badge = ctk.CTkLabel(top_bar, text="", font=FONT_SECTION,
                                              fg_color=BG_CARD2, text_color=TEXT_MAIN, corner_radius=8,
                                              width=110, height=28)
        self.lbl_ob_step_badge.pack(side="right", padx=20, pady=16)

        # Barra de progreso visual
        self.ob_prog_bar = ctk.CTkProgressBar(self.onboarding_frame, height=4, corner_radius=0,
                                             progress_color=ACCENT, fg_color=BG_CARD2)
        self.ob_prog_bar.pack(fill="x", side="top")

        # Contenedor central scrollable para el contenido del paso
        self.ob_scroll = ctk.CTkScrollableFrame(self.onboarding_frame, fg_color="transparent")
        self.ob_scroll.pack(fill="both", expand=True, padx=40, pady=(20, 20))

        # Determinar el paso inicial guardado
        paso_guardado = self.config_data.get("onboarding_step", 1)
        if not isinstance(paso_guardado, int) or paso_guardado < 1 or paso_guardado > 6:
            paso_guardado = 1

        self._mostrar_paso_onboarding(paso_guardado)

    def _mostrar_paso_onboarding(self, step_num):
        self.config_data["onboarding_step"] = step_num
        guardar_configuracion(self.config_data)

        # Actualizar badge y barra
        self.lbl_ob_step_badge.configure(text=self.t("ob_step_indicator", step_num))
        animar_progreso(self.ob_prog_bar, (step_num - 1) / 5.0, self.root, duracion=DUR_SHORT)

        # Limpiar contenedor de contenido
        for w in self.ob_scroll.winfo_children():
            w.destroy()

        if step_num == 1:
            self._build_ob_paso1_idioma()
        elif step_num == 2:
            self._build_ob_paso2_backup()
        elif step_num == 3:
            self._build_ob_paso3_perfil()
        elif step_num == 4:
            self._build_ob_paso4_skin()
        elif step_num == 5:
            self._build_ob_paso5_version()
        elif step_num == 6:
            self._build_ob_paso6_intro()

    def _build_ob_paso1_idioma(self):
        """Paso 1: Selección de idioma y explicación de la apariencia adaptable."""
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step1_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(pady=(10, 4))
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step1_sub"), font=FONT_BODY, text_color=TEXT_M).pack(pady=(0, 16))

        # --- SECCIÓN 1: IDIOMA ---
        cards_f = ctk.CTkFrame(self.ob_scroll, fg_color="transparent")
        cards_f.pack(pady=(0, 20))

        # Tarjeta Español
        es_active = (self.lang == "es")
        card_es = ctk.CTkFrame(cards_f, fg_color=CARD_SEL if es_active else BG_CARD,
                               border_width=2 if es_active else 1,
                               border_color=ACCENT if es_active else BORDER_C,
                               corner_radius=12, width=165, height=110)
        card_es.pack(side="left", padx=5)
        card_es.pack_propagate(False)

        ctk.CTkLabel(card_es, text="🇪🇸", font=FONT_ICON_XL).pack(pady=(SPACE_MD, SPACE_XS))
        ctk.CTkLabel(card_es, text="Español", font=FONT_SECTION, text_color=TEXT_MAIN).pack()
        if es_active:
            ctk.CTkLabel(card_es, text="✓ Seleccionado", font=FONT_LABEL_S, text_color=ACCENT).pack(pady=(2, 0))

        def select_es(e=None):
            if hasattr(self, "sound"): self.sound.play("click")
            self.lang = "es"
            self.config_data["language"] = "es"
            guardar_configuracion(self.config_data)
            self._mostrar_paso_onboarding(1)

        card_es.bind("<Button-1>", select_es)
        for child in card_es.winfo_children(): child.bind("<Button-1>", select_es)

        # Tarjeta Inglés
        en_active = (self.lang == "en")
        card_en = ctk.CTkFrame(cards_f, fg_color=CARD_SEL if en_active else BG_CARD,
                               border_width=2 if en_active else 1,
                               border_color=ACCENT if en_active else BORDER_C,
                               corner_radius=12, width=165, height=110)
        card_en.pack(side="left", padx=5)
        card_en.pack_propagate(False)

        ctk.CTkLabel(card_en, text="🇬🇧", font=FONT_ICON_XL).pack(pady=(SPACE_MD, SPACE_XS))
        ctk.CTkLabel(card_en, text="English", font=FONT_SECTION, text_color=TEXT_MAIN).pack()
        if en_active:
            ctk.CTkLabel(card_en, text="✓ Selected", font=FONT_LABEL_S, text_color=ACCENT).pack(pady=(2, 0))

        def select_en(e=None):
            if hasattr(self, "sound"): self.sound.play("click")
            self.lang = "en"
            self.config_data["language"] = "en"
            guardar_configuracion(self.config_data)
            self._mostrar_paso_onboarding(1)

        card_en.bind("<Button-1>", select_en)
        for child in card_en.winfo_children(): child.bind("<Button-1>", select_en)

        def crear_tarjeta_idioma(codigo, bandera, nombre):
            activo = self.lang == codigo
            tarjeta = ctk.CTkFrame(cards_f, fg_color=CARD_SEL if activo else BG_CARD,
                                   border_width=2 if activo else 1,
                                   border_color=ACCENT if activo else BORDER_C,
                                   corner_radius=12, width=165, height=110)
            tarjeta.pack(side="left", padx=5)
            tarjeta.pack_propagate(False)
            ctk.CTkLabel(tarjeta, text=bandera, font=FONT_ICON_XL).pack(pady=(SPACE_MD, SPACE_XS))
            ctk.CTkLabel(tarjeta, text=nombre, font=FONT_SECTION, text_color=TEXT_MAIN).pack()
            if activo:
                ctk.CTkLabel(tarjeta, text="✓ Seleccionado", font=FONT_LABEL_S, text_color=ACCENT).pack(pady=(2, 0))

            def seleccionar(e=None):
                if hasattr(self, "sound"): self.sound.play("click")
                self.lang = codigo
                self.config_data["language"] = codigo
                guardar_configuracion(self.config_data)
                self._mostrar_paso_onboarding(1)

            tarjeta.bind("<Button-1>", seleccionar)
            for child in tarjeta.winfo_children():
                child.bind("<Button-1>", seleccionar)

        crear_tarjeta_idioma("pt", "🇧🇷", "Português")
        crear_tarjeta_idioma("fr", "🇫🇷", "Français")
        ctk.CTkLabel(self.ob_scroll, text=self.t("languages_work_notice"),
                     font=FONT_BODY_I, text_color=TEXT_M).pack(pady=(0, 12))

        # Material 3 adaptable: el launcher sigue automáticamente el sistema.
        ctk.CTkLabel(self.ob_scroll, text=self.t("adaptive_theme_title"),
                     font=FONT_TITLE_S, text_color=TEXT_MAIN).pack(pady=(8, 2))
        ctk.CTkLabel(self.ob_scroll, text=self.t("adaptive_theme_sub"),
                     font=FONT_BODY, text_color=TEXT_M, wraplength=520,
                     justify="center").pack(pady=(0, 20))

        # Botón Continuar
        ctk.CTkButton(self.ob_scroll, text=self.t("ob_btn_continue"), font=FONT_LABEL_L,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                      height=44, width=220, corner_radius=R_FULL,
                      command=lambda: (getattr(self, "sound", None) and self.sound.play("click"), self._mostrar_paso_onboarding(2))).pack(pady=(4, 10))

    def _build_ob_paso2_backup(self):
        """Paso 2: Detección o Importación de Backup previo."""
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step2_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(pady=(10, 4))
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step2_sub"), font=FONT_BODY, text_color=TEXT_M, wraplength=520, justify="center").pack(pady=(0, 20))

        container = ctk.CTkFrame(self.ob_scroll, fg_color="transparent")
        container.pack(fill="x", pady=(0, 14))

        # Si ya había una copia importada activa en esta sesión / guardada
        if getattr(self, "_onboarding_from_backup", False) or self.config_data.get("onboarding_from_backup", False):
            self._onboarding_from_backup = True
            card_active = ctk.CTkFrame(container, fg_color=CARD_SEL, border_width=2, border_color=ACCENT, corner_radius=12)
            card_active.pack(fill="x", pady=(0, 10), padx=40)

            c_act = ctk.CTkFrame(card_active, fg_color="transparent")
            c_act.pack(fill="x", padx=18, pady=14)
            ctk.CTkLabel(c_act, text=ICON_CHECK_CIRCLE, font=FONT_ICON_XL, text_color=ACCENT).pack(side="left", padx=(0, SPACE_MD))
            c_txt = ctk.CTkFrame(c_act, fg_color="transparent")
            c_txt.pack(side="left", fill="both", expand=True)
            profs_cnt = len(self.config_data.get("profiles", {}))
            ctk.CTkLabel(c_txt, text=self.t("ob_backup_loaded_title", profs_cnt), font=FONT_TITLE_S, text_color=TEXT_MAIN, anchor="w").pack(anchor="w")
            ctk.CTkLabel(c_txt, text=self.t("ob_backup_loaded_sub"), font=FONT_BODY_S, text_color=TEXT_M, anchor="w").pack(anchor="w", pady=(2, 0))

            btn_use_it = ctk.CTkButton(c_act, text=self.t("ob_btn_continue"), width=120, height=36, font=FONT_LABEL_L,
                                       fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                                       corner_radius=R_FULL,
                                       command=lambda: (getattr(self, "sound", None) and self.sound.play("click"), self._mostrar_paso_onboarding(5)))
            btn_use_it.pack(side="right", padx=(10, 0))

        # Opción 1: Importar Backup
        card_imp = ctk.CTkFrame(container, fg_color=BG_CARD, border_width=1, border_color=ACCENT, corner_radius=12)
        card_imp.pack(fill="x", pady=6, padx=40)

        c1_in = ctk.CTkFrame(card_imp, fg_color="transparent")
        c1_in.pack(fill="x", padx=18, pady=16)

        ctk.CTkLabel(c1_in, text=ICON_SAVE, font=FONT_ICON_XL, text_color=ACCENT).pack(side="left", padx=(0, SPACE_MD))
        c1_txt = ctk.CTkFrame(c1_in, fg_color="transparent")
        c1_txt.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(c1_txt, text=self.t("ob_btn_import_backup"), font=FONT_TITLE_S, text_color=TEXT_MAIN, anchor="w").pack(anchor="w")
        ctk.CTkLabel(c1_txt, text=self.t("import_backup_sub"), font=FONT_BODY_S, text_color=TEXT_M, anchor="w").pack(anchor="w", pady=(2, 0))

        # Frame de progreso de importación inline
        frame_status = ctk.CTkFrame(card_imp, fg_color=BG_CARD2, corner_radius=8)
        lbl_st = ctk.CTkLabel(frame_status, text="", font=FONT_BODY_S, text_color=TEXT_M)
        lbl_st.pack(anchor="w", padx=12, pady=(8, 2))
        p_bar = ctk.CTkProgressBar(frame_status, progress_color=ACCENT, height=6)
        p_bar.pack(fill="x", padx=12, pady=(0, 8))
        p_bar.set(0)

        btn_pick_zip = ctk.CTkButton(c1_in, text=ICON_FOLDER, width=40, height=40, font=FONT_ICON_MD,
                                     corner_radius=R_FULL,
                                     fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T)
        btn_pick_zip.pack(side="right", padx=(10, 0))

        def on_import_click():
            if hasattr(self, "sound"): self.sound.play("click")
            zip_p = filedialog.askopenfilename(
                title=self.t("import_profile"),
                filetypes=[(self.t("zip_files"), "*.zip")]
            )
            if not zip_p: return
            btn_pick_zip.configure(state="disabled")
            frame_status.pack(fill="x", padx=18, pady=(0, 14))
            threading.Thread(target=self._importar_backup_en_onboarding,
                             args=(zip_p, frame_status, lbl_st, p_bar), daemon=True).start()

        btn_pick_zip.configure(command=on_import_click)

        # Opción 2: Configurar de cero
        card_fresh = ctk.CTkFrame(container, fg_color=BG_CARD, border_width=1, border_color=BORDER_C, corner_radius=12)
        card_fresh.pack(fill="x", pady=6, padx=40)

        c2_in = ctk.CTkFrame(card_fresh, fg_color="transparent")
        c2_in.pack(fill="x", padx=18, pady=16)

        ctk.CTkLabel(c2_in, text=ICON_BOLT, font=FONT_ICON_XL, text_color=ACCENT).pack(side="left", padx=(0, SPACE_MD))
        c2_txt = ctk.CTkFrame(c2_in, fg_color="transparent")
        c2_txt.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(c2_txt, text=self.t("ob_btn_no_backup"), font=FONT_TITLE_S, text_color=TEXT_MAIN, anchor="w").pack(anchor="w")
        ctk.CTkLabel(c2_txt, text=self.t("ob_step3_sub"), font=FONT_BODY_S, text_color=TEXT_M, anchor="w").pack(anchor="w", pady=(2, 0))

        def ir_paso3_fresco():
            if hasattr(self, "sound"): self.sound.play("click")
            self._onboarding_from_backup = False
            self.config_data["onboarding_from_backup"] = False
            guardar_configuracion(self.config_data)
            self._mostrar_paso_onboarding(3)

        btn_fresh = ctk.CTkButton(c2_in, text=ICON_ARROW_FORWARD, width=40, height=40, font=FONT_ICON_MD,
                                  corner_radius=R_FULL,
                                  fg_color=BG_CARD2, hover_color=BORDER_C, text_color=TEXT_MAIN,
                                  command=ir_paso3_fresco)
        btn_fresh.pack(side="right", padx=(10, 0))

        # Botón Atrás
        btn_bar = ctk.CTkFrame(self.ob_scroll, fg_color="transparent")
        btn_bar.pack(fill="x", padx=40, pady=10)
        ctk.CTkButton(btn_bar, text=self.t("ob_btn_back"), font=FONT_BODY,
                      fg_color=BG_CARD2, hover_color=BORDER_C, text_color=TEXT_MAIN, height=38, width=120,
                      command=lambda: (getattr(self, "sound", None) and self.sound.play("click"), self._mostrar_paso_onboarding(1))).pack(side="left")

    def _importar_backup_en_onboarding(self, zip_path, frame_status, lbl_st, p_bar):
        """Importa un backup en onboarding, registra perfiles y guarda de inmediato."""
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                nl = zf.namelist()
                total = len(nl)
                for i, m in enumerate(nl):
                    destino = validar_ruta_dentro_de(MINECRAFT_DIR, os.path.join(MINECRAFT_DIR, m))
                    if m.endswith("/"):
                        os.makedirs(destino, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(destino), exist_ok=True)
                        with zf.open(m) as origen, open(destino, "wb") as salida:
                            shutil.copyfileobj(origen, salida)
                    pct = (i + 1) / max(total, 1)
                    self.root.after(0, lambda p=pct, fn=m: (
                        p_bar.set(p),
                        lbl_st.configure(text=fn[:40])
                    ))

            # Los backups de perfiles guardan el contenido jugable dentro de
            # profiles/<nombre>/game/. El launcher usa directamente
            # profiles/<nombre>/, así que aplanamos esa carpeta igual que el
            # importador normal de perfiles (incluyendo skin y armario).
            profs_root = os.path.join(MINECRAFT_DIR, "profiles")
            if os.path.exists(profs_root):
                for p_name in os.listdir(profs_root):
                    p_root = os.path.join(profs_root, p_name)
                    game_root = os.path.join(p_root, "game")
                    if not os.path.isdir(game_root):
                        continue
                    for item_name in os.listdir(game_root):
                        src_item = os.path.join(game_root, item_name)
                        dst_item = os.path.join(p_root, item_name)
                        if os.path.isdir(src_item):
                            shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src_item, dst_item)

                    self._migrar_wardrobe_a_armario(p_root)
                    shutil.rmtree(game_root, ignore_errors=True)

            # Recargar configuración y asegurar sincronización de perfiles
            self.config_data = cargar_configuracion()

            profs_dir = os.path.join(MINECRAFT_DIR, "profiles")
            if os.path.exists(profs_dir):
                for p_name in os.listdir(profs_dir):
                    if os.path.isdir(os.path.join(profs_dir, p_name)):
                        self.config_data.setdefault("profiles", {}).setdefault(p_name, {"selected_slots": {}, "skin_model": "classic"})
                if self.config_data["profiles"] and self.config_data.get("active_profile") not in self.config_data["profiles"]:
                    self.config_data["active_profile"] = sorted(self.config_data["profiles"].keys())[0]

            self.config_data["language"] = self.lang
            self.config_data["onboarding_from_backup"] = True
            self.config_data["onboarding_step"] = 5
            self.config_data["onboarding_completed"] = False
            guardar_configuracion(self.config_data)

            self._onboarding_from_backup = True

            if hasattr(self, "sound"): self.sound.play("success")
            self.root.after(0, lambda: [
                lbl_st.configure(text=self.t("ob_backup_success_jump"), text_color="#66ff88"),
                self.root.after(800, lambda: self._mostrar_paso_onboarding(5))
            ])
        except Exception as e:
            self.root.after(0, lambda err=e: [
                lbl_st.configure(text=f"Error: {str(err)}", text_color="#ff6666")
            ])

    def _build_ob_paso3_perfil(self):
        """Paso 3: Crear Perfil de Jugador (Limpio si es de cero)."""
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step3_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(pady=(10, 4))
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step3_sub"), font=FONT_BODY, text_color=TEXT_M, wraplength=520, justify="center").pack(pady=(0, 24))

        card = ctk.CTkFrame(self.ob_scroll, fg_color=BG_CARD, corner_radius=12)
        card.pack(fill="x", padx=60, pady=(0, 16))

        ctk.CTkLabel(card, text=ICON_PERSON, font=FONT_ICON_HERO).pack(pady=(20, 6))
        ctk.CTkLabel(card, text=self.t("ob_profile_name_label"), font=FONT_SECTION, text_color=TEXT_MAIN).pack(pady=(0, 8))

        entry_name = ctk.CTkEntry(card, width=280, height=40, font=FONT_BODY, justify="center", placeholder_text="Jugador / Steve", fg_color=BG_CARD2)
        entry_name.pack(pady=(0, 8))

        ses_name = getattr(self, "_ob_temp_profile_name", "")
        if ses_name:
            entry_name.insert(0, ses_name)

        lbl_err = ctk.CTkLabel(card, text="", font=FONT_CAPTION, text_color="#ff6666")
        lbl_err.pack(pady=(0, 16))

        def continuar_perfil():
            raw = entry_name.get().strip()
            name = "".join(c for c in raw if c.isalnum() or c in " .-_").strip()
            if not name:
                lbl_err.configure(text=self.t("ob_profile_empty_warn"))
                return
            if hasattr(self, "sound"): self.sound.play("click")
            self._ob_temp_profile_name = name
            self.config_data["active_profile"] = name
            self.config_data.setdefault("profiles", {}).setdefault(name, {"selected_slots": {}, "skin_model": "classic"})
            os.makedirs(os.path.join(MINECRAFT_DIR, "profiles", name), exist_ok=True)
            guardar_configuracion(self.config_data)
            self._mostrar_paso_onboarding(4)

        # Botones Atrás y Continuar
        btn_bar = ctk.CTkFrame(self.ob_scroll, fg_color="transparent")
        btn_bar.pack(fill="x", padx=60, pady=10)

        ctk.CTkButton(btn_bar, text=self.t("ob_btn_back"), font=FONT_BODY,
                      fg_color=BG_CARD2, hover_color=BORDER_C, text_color=TEXT_MAIN, height=40, width=120,
                      command=lambda: (getattr(self, "sound", None) and self.sound.play("click"), self._mostrar_paso_onboarding(2))).pack(side="left")

        ctk.CTkButton(btn_bar, text=self.t("ob_btn_continue"), font=FONT_LABEL_L,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                      height=40, width=160, corner_radius=R_FULL,
                      command=continuar_perfil).pack(side="right")

    def _build_ob_paso4_skin(self):
        """Paso 4: Skin (Opcional / Omitible)."""
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step4_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(pady=(10, 4))
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step4_sub"), font=FONT_BODY, text_color=TEXT_M, wraplength=520, justify="center").pack(pady=(0, 20))

        active_prof = self.config_data.get("active_profile", "Jugador")
        p_dir = os.path.join(MINECRAFT_DIR, "profiles", active_prof)
        skin_actual_path = os.path.join(p_dir, "skin.png")

        main_card = ctk.CTkFrame(self.ob_scroll, fg_color=BG_CARD, corner_radius=R_MD)
        main_card.pack(fill="x", padx=50, pady=(0, 20))

        row_content = ctk.CTkFrame(main_card, fg_color="transparent")
        row_content.pack(fill="both", expand=True, padx=20, pady=20)

        # Vista previa de skin
        prev_box = ctk.CTkFrame(row_content, fg_color=BG_CARD2, width=140, height=170, corner_radius=R_MD)
        prev_box.pack(side="left", padx=(10, 24))
        prev_box.pack_propagate(False)

        lbl_skin_img = ctk.CTkLabel(prev_box, text=ICON_PERSON, font=FONT_ICON_HERO, text_color=TEXT_M)
        lbl_skin_img.pack(expand=True)

        def refrescar_preview():
            if os.path.exists(skin_actual_path):
                try:
                    img_preview = self._generar_preview_skin_2d(skin_actual_path, scale=5)
                    if img_preview:
                        lbl_skin_img.configure(image=img_preview, text="")
                        lbl_skin_img._img_ref = img_preview
                        return
                except Exception:
                    pass
            lbl_skin_img.configure(image=None, text=ICON_PERSON, font=FONT_ICON_HERO)

        refrescar_preview()

        # Opciones y carga
        opts_f = ctk.CTkFrame(row_content, fg_color="transparent")
        opts_f.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(opts_f, text=active_prof, font=FONT_TITLE_M, text_color=TEXT_MAIN).pack(anchor="w", pady=(4, 8))

        # Selección de Modelo
        p_data = self.config_data.setdefault("profiles", {}).setdefault(active_prof, {})
        model_var = tk.StringVar(value=p_data.get("skin_model", "classic"))

        def cambiar_modelo(m):
            model_var.set(m)
            p_data["skin_model"] = m
            guardar_configuracion(self.config_data)

        m_row = ctk.CTkFrame(opts_f, fg_color="transparent")
        m_row.pack(anchor="w", pady=(0, 14))
        ctk.CTkRadioButton(m_row, text=self.t("ob_model_classic"), variable=model_var, value="classic",
                           command=lambda: cambiar_modelo("classic"), font=FONT_BODY).pack(side="left", padx=(0, 14))
        ctk.CTkRadioButton(m_row, text=self.t("ob_model_slim"), variable=model_var, value="slim",
                           command=lambda: cambiar_modelo("slim"), font=FONT_BODY).pack(side="left")

        def cargar_skin_archivo():
            if hasattr(self, "sound"): self.sound.play("click")
            ruta_sel = filedialog.askopenfilename(
                title=self.t("ob_btn_choose_skin"),
                filetypes=[("Minecraft Skins (*.png)", "*.png")]
            )
            if not ruta_sel: return
            try:
                os.makedirs(p_dir, exist_ok=True)
                shutil.copy(ruta_sel, skin_actual_path)
                # Guardar copia en armario
                skins_dir = os.path.join(MINECRAFT_DIR, "skins")
                os.makedirs(skins_dir, exist_ok=True)
                dst_armario = os.path.join(skins_dir, os.path.basename(ruta_sel))
                if not os.path.exists(dst_armario):
                    shutil.copy(ruta_sel, dst_armario)
                refrescar_preview()
                if hasattr(self, "sound"): self.sound.play("success")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ctk.CTkButton(opts_f, text=self.t("ob_btn_choose_skin"), font=FONT_SECTION,
                      fg_color=BG_CARD2, hover_color=BORDER_C, text_color=TEXT_MAIN, height=36,
                      command=cargar_skin_archivo).pack(anchor="w", pady=(0, 6))

        # Botones de navegación del paso 4
        btn_bar = ctk.CTkFrame(self.ob_scroll, fg_color="transparent")
        btn_bar.pack(fill="x", padx=50, pady=10)

        ctk.CTkButton(btn_bar, text=self.t("ob_btn_back"), font=FONT_BODY,
                      fg_color=BG_CARD2, hover_color=BORDER_C, text_color=TEXT_MAIN, height=38, width=100,
                      command=lambda: (getattr(self, "sound", None) and self.sound.play("click"), self._mostrar_paso_onboarding(3))).pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_bar, text=self.t("ob_btn_skip_skin"), font=FONT_BODY,
                      fg_color="transparent", hover_color=BG_CARD2, text_color=TEXT_M, height=38,
                      command=lambda: (getattr(self, "sound", None) and self.sound.play("click"), self._mostrar_paso_onboarding(5))).pack(side="left")

        ctk.CTkButton(btn_bar, text=self.t("ob_btn_continue"), font=FONT_SECTION,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, height=38, width=140,
                      command=lambda: (getattr(self, "sound", None) and self.sound.play("click"), self._mostrar_paso_onboarding(5))).pack(side="right")

    def _build_ob_paso5_version(self):
        """Paso 5: Descargar Versión de Minecraft (Penúltimo paso)."""
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step5_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(pady=(10, 4))
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step5_sub"), font=FONT_BODY, text_color=TEXT_M, wraplength=520, justify="center").pack(pady=(0, 20))

        card = ctk.CTkFrame(self.ob_scroll, fg_color=BG_CARD, corner_radius=12)
        card.pack(fill="x", padx=50, pady=(0, 20))

        ctk.CTkLabel(card, text=ICON_PACKAGE, font=FONT_ICON_HERO, text_color=ACCENT).pack(pady=(16, 4))
        ctk.CTkLabel(card, text=self.t("ob_version_select_label"), font=FONT_SECTION, text_color=TEXT_MAIN).pack(pady=(0, 8))

        # En el onboarding solo se ofrecen versiones estables (releases).
        releases = []
        if hasattr(self, "todas_las_versiones") and self.todas_las_versiones:
            for v in self.todas_las_versiones:
                if v.get("type") == "release":
                    releases.append(v.get("id"))
        else:
            threading.Thread(target=self._descargar_versiones, daemon=True).start()

        if not releases:
            releases = ["1.21.4", "1.21.1", "1.21", "1.20.6", "1.20.4", "1.20.1", "1.19.4", "1.18.2", "1.16.5", "1.12.2"]

        combo_ver = ctk.CTkComboBox(card, values=releases, width=240, height=36, font=FONT_BODY, fg_color=BG_CARD2)
        combo_ver.pack(pady=(0, 14))
        self._ob_combo_ver = combo_ver

        last_v = self.config_data.get("last_version", "")
        if last_v and last_v in releases:
            combo_ver.set(last_v)
        else:
            combo_ver.set(releases[0])

        lbl_badge = ctk.CTkLabel(card, text="", font=FONT_SECTION, text_color="#4ec9b0")
        lbl_badge.pack(pady=(0, 6))

        p_bar = ctk.CTkProgressBar(card, progress_color=ACCENT, height=8, width=320)
        lbl_st = ctk.CTkLabel(card, text="", font=FONT_CAPTION, text_color=TEXT_M)

        # Botón de navegación continuar (barra inferior)
        btn_bar = ctk.CTkFrame(self.ob_scroll, fg_color="transparent")
        btn_bar.pack(fill="x", padx=50, pady=10)

        paso_previo = 2 if getattr(self, "_onboarding_from_backup", False) else 4
        btn_back = ctk.CTkButton(btn_bar, text=self.t("ob_btn_back"), font=FONT_BODY,
                                 fg_color=BG_CARD2, hover_color=BORDER_C, text_color=TEXT_MAIN, height=38, width=100,
                                 command=lambda: (getattr(self, "sound", None) and self.sound.play("click"), self._mostrar_paso_onboarding(paso_previo)))
        btn_back.pack(side="left", padx=(0, 10))

        btn_skip = ctk.CTkButton(btn_bar, text=self.t("ob_btn_skip_download"), font=FONT_BODY,
                                 fg_color="transparent", hover_color=BG_CARD2, text_color=TEXT_M, height=38,
                                 command=lambda: (getattr(self, "sound", None) and self.sound.play("click"), self._mostrar_paso_onboarding(6)))
        btn_skip.pack(side="left")

        btn_cont = ctk.CTkButton(btn_bar, text=self.t("ob_btn_continue"), font=FONT_SECTION,
                                 fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, height=38, width=140,
                                 command=lambda: (getattr(self, "sound", None) and self.sound.play("click"), self._mostrar_paso_onboarding(6)))
        btn_cont.pack(side="right")

        btn_dl = ctk.CTkButton(card, text=self.t("ob_btn_download_ver"), font=FONT_SECTION,
                               fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, height=38, width=240)
        btn_dl.pack(pady=(0, 16))

        # Botón de cancelar descarga
        btn_cancel_dl = ctk.CTkButton(card, text=self.t("ob_btn_cancel_download"), font=FONT_SECTION,
                                      fg_color=DANGER, hover_color=DANGER_H, text_color="white", height=38, width=240)

        def verificar_instalada():
            sel = combo_ver.get().strip()
            inst_set = self._obtener_versiones_instaladas_set()
            if sel in inst_set:
                lbl_badge.configure(text=self.t("ob_ver_installed_badge"))
                btn_dl.configure(state="disabled", text=self.t("btn_installed"))
            else:
                lbl_badge.configure(text="")
                btn_dl.configure(state="normal", text=self.t("ob_btn_download_ver"))

        combo_ver.configure(command=lambda _: verificar_instalada())
        verificar_instalada()

        def cancelar_descarga():
            if hasattr(self, "sound"): self.sound.play("click")
            self._cancel_ob_download = True
            lbl_st.configure(text=self.t("install_cancelling"))
            btn_cancel_dl.configure(state="disabled")

        btn_cancel_dl.configure(command=cancelar_descarga)

        def al_descargar():
            ver = combo_ver.get().strip()
            if not ver: return
            self.config_data["last_version"] = ver
            perfil = self.config_data.get("active_profile", "Jugador")
            self.config_data.setdefault("profiles", {}).setdefault(perfil, {})["last_version"] = ver
            guardar_configuracion(self.config_data)

            self._cancel_ob_download = False

            # Bloquear navegación y selector
            combo_ver.configure(state="disabled")
            btn_bar.pack_forget()

            btn_dl.pack_forget()
            lbl_st.pack(pady=(0, 4))
            p_bar.pack(pady=(0, 10))
            p_bar.set(0)
            btn_cancel_dl.configure(state="normal")
            btn_cancel_dl.pack(pady=(0, 16))

            threading.Thread(target=self._iniciar_descarga_version_onboarding,
                             args=(ver, lbl_st, p_bar, btn_dl, btn_cancel_dl, combo_ver, btn_bar, btn_cont, lbl_badge), daemon=True).start()

        btn_dl.configure(command=al_descargar)

    def _iniciar_descarga_version_onboarding(self, ver, lbl_st, p_bar, btn_dl, btn_cancel_dl, combo_ver, btn_bar, btn_cont, lbl_badge):
        """Descarga e instala una versión desde cero en el paso 5 de onboarding con soporte para cancelar."""
        try:
            def check_cancel():
                if getattr(self, "_cancel_ob_download", False):
                    raise InstallCancelledException(self.t("install_cancelled"))

            def st(t):
                check_cancel()
                self.root.after(0, lambda text=t: lbl_st.configure(text=text))

            max_val = [1]
            def sm(m):
                check_cancel()
                max_val[0] = max(m, 1)

            def sp(p):
                check_cancel()
                self.root.after(0, lambda val=p: p_bar.set(val / max_val[0]))

            # 1. Java runtime
            try:
                st(self.t("install_checking_java_short"))
                info = minecraft_launcher_lib.runtime.get_version_runtime_information(ver, MINECRAFT_DIR)
                if info and not minecraft_launcher_lib.runtime.get_executable_path(info["name"], MINECRAFT_DIR):
                    minecraft_launcher_lib.runtime.install_jvm_runtime(
                        info["name"], MINECRAFT_DIR, callback={"setStatus": st, "setMax": sm, "setProgress": sp})
            except InstallCancelledException:
                raise
            except Exception:
                pass

            check_cancel()

            # 2. Descargar archivos de Minecraft
            st(self.t("install_checking_files", ver))
            minecraft_launcher_lib.install.install_minecraft_version(
                ver, MINECRAFT_DIR, callback={"setStatus": st, "setMax": sm, "setProgress": sp})

            check_cancel()

            if hasattr(self, "sound"): self.sound.play("success")
            self.root.after(0, lambda: [
                p_bar.set(1.0),
                lbl_st.configure(text=""),
                btn_cancel_dl.pack_forget(),
                combo_ver.configure(state="normal"),
                lbl_badge.configure(text=self.t("ob_ver_installed_badge")),
                btn_dl.configure(text=self.t("btn_installed"), state="disabled"),
                btn_dl.pack(pady=(0, 16)),
                btn_bar.pack(fill="x", padx=50, pady=10),
                btn_cont.configure(state="normal")
            ])
        except InstallCancelledException:
            # Limpiar versión incompleta
            v_dir = os.path.join(MINECRAFT_DIR, "versions", ver)
            if os.path.exists(v_dir):
                try: shutil.rmtree(v_dir, ignore_errors=True)
                except Exception: pass

            self.root.after(0, lambda: [
                p_bar.set(0),
                p_bar.pack_forget(),
                btn_cancel_dl.pack_forget(),
                combo_ver.configure(state="normal"),
                lbl_st.configure(text=self.t("install_cancelled"), text_color="#ffaa66"),
                btn_dl.configure(state="normal", text=self.t("ob_btn_download_ver")),
                btn_dl.pack(pady=(0, 16)),
                btn_bar.pack(fill="x", padx=50, pady=10)
            ])
        except Exception as e:
            self.root.after(0, lambda err=e: [
                btn_cancel_dl.pack_forget(),
                combo_ver.configure(state="normal"),
                lbl_st.configure(text=f"Error: {str(err)}", text_color="#ff6666"),
                btn_dl.configure(state="normal", text=self.t("ob_btn_download_ver")),
                btn_dl.pack(pady=(0, 16)),
                btn_bar.pack(fill="x", padx=50, pady=10)
            ])

    def _build_ob_paso6_intro(self):
        """Paso 6: Introducción de funciones y botón para empezar."""
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step6_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(pady=(10, 4))
        ctk.CTkLabel(self.ob_scroll, text=self.t("ob_step6_sub"), font=FONT_BODY, text_color=TEXT_M, wraplength=520, justify="center").pack(pady=(0, 20))

        grid_f = ctk.CTkFrame(self.ob_scroll, fg_color="transparent")
        grid_f.pack(fill="x", padx=30, pady=(0, 24))
        grid_f.columnconfigure(0, weight=1)
        grid_f.columnconfigure(1, weight=1)

        features = [
            ("ob_feat_play_title", "ob_feat_play_desc"),
            ("ob_feat_vers_title", "ob_feat_vers_desc"),
            ("ob_feat_slots_title", "ob_feat_slots_desc"),
            ("ob_feat_modrinth_title", "ob_feat_modrinth_desc"),
            ("ob_feat_skins_title", "ob_feat_skins_desc"),
            ("ob_feat_settings_title", "ob_feat_settings_desc"),
        ]

        for i, (t_k, d_k) in enumerate(features):
            r = i // 2
            c = i % 2
            f_card = ctk.CTkFrame(grid_f, fg_color=BG_CARD, corner_radius=R_MD)
            f_card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

            f_in = ctk.CTkFrame(f_card, fg_color="transparent")
            f_in.pack(fill="both", expand=True, padx=14, pady=12)

            ctk.CTkLabel(f_in, text=self.t(t_k), font=FONT_TITLE_S, text_color=TEXT_MAIN, anchor="w").pack(anchor="w")
            ctk.CTkLabel(f_in, text=self.t(d_k), font=FONT_BODY_S, text_color=TEXT_M, justify="left", wraplength=210, anchor="w").pack(anchor="w", pady=(3, 0))

        # Botones del Paso 6 (Atrás y Empezar)
        btn_bar = ctk.CTkFrame(self.ob_scroll, fg_color="transparent")
        btn_bar.pack(fill="x", padx=30, pady=(0, 20))

        ctk.CTkButton(btn_bar, text=self.t("ob_btn_back"), font=FONT_BODY,
                      fg_color=BG_CARD2, hover_color=BORDER_C, text_color=TEXT_MAIN, height=44, width=120,
                      corner_radius=R_FULL,
                      command=lambda: (getattr(self, "sound", None) and self.sound.play("click"), self._mostrar_paso_onboarding(5))).pack(side="left")

        ctk.CTkButton(btn_bar, text=self.t("ob_btn_get_started"), font=FONT_LABEL_L,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                      height=46, width=240, corner_radius=R_FULL,
                      command=self._finalizar_onboarding).pack(side="right")

    def _finalizar_onboarding(self):
        """Finaliza el onboarding y carga la interfaz principal en la vista Jugar."""
        if hasattr(self, "sound"): self.sound.play("success")
        self.config_data["onboarding_completed"] = True
        self.config_data.pop("onboarding_step", None)
        guardar_configuracion(self.config_data)

        if hasattr(self, "onboarding_frame") and self.onboarding_frame:
            self.onboarding_frame.destroy()
            self.onboarding_frame = None

        self._iniciar_ui_principal()

    # ──────────────────────────────────────────────
    # INICIALIZACIÓN DE LA UI PRINCIPAL
    # ──────────────────────────────────────────────
    def _iniciar_ui_principal(self):
        self.sidebar = ctk.CTkFrame(self.root, width=80, fg_color=BG_SIDE, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = ctk.CTkFrame(self.root, fg_color=BG_DARK, corner_radius=0)
        self.content.pack(side="right", fill="both", expand=True)

        self._build_sidebar()
        self._build_vista_jugar()
        self._build_vista_versiones()
        self._build_vista_mods()
        self._build_vista_modrinth()
        self._build_vista_modpacks()
        self._build_vista_capturas()
        self._build_vista_skins()
        self._build_vista_ajustes()

        self.mostrar_vista("jugar")
        self._sync_sidebar_perfil()
        self.aplicar_filtros()

    # ──────────────────────────────────────────────
    # SIDEBAR
    # ──────────────────────────────────────────────
    def t(self, key, *args):
        lang_dict = STRINGS.get(self.lang, STRINGS["en"])
        val = lang_dict.get(key, STRINGS["en"].get(key, key))
        if args:
            try: return val.format(*args)
            except Exception: pass
        return val

    def al_cambiar_idioma(self, val):
        self.lang = {
            "English": "en",
            "Español": "es",
            "Português": "pt",
            "Français": "fr"
        }.get(val, "en")
        self.config_data["language"] = self.lang
        guardar_configuracion(self.config_data)
        self._reconstruir_ui()

    def _reconstruir_ui(self):
        if not self.config_data.get("onboarding_completed", False):
            if hasattr(self, "onboarding_frame") and self.onboarding_frame:
                self._mostrar_paso_onboarding(self.config_data.get("onboarding_step", 1))
            else:
                self._iniciar_onboarding()
            return

        cur = self.vista_actual
        # Refresh container backgrounds so palette changes take effect
        try: self.root.configure(fg_color=BG_DARK)
        except Exception: pass
        if hasattr(self, "sidebar") and self.sidebar:
            try: self.sidebar.configure(fg_color=BG_SIDE)
            except Exception: pass
            for w in self.sidebar.winfo_children():
                w.destroy()
        if hasattr(self, "content") and self.content:
            try: self.content.configure(fg_color=BG_DARK)
            except Exception: pass
            for w in self.content.winfo_children():
                w.destroy()
        self.vistas.clear()
        self.nav_buttons.clear()
        self.nav_accents.clear()
        self._build_sidebar()
        self._build_vista_jugar()
        self._build_vista_versiones()
        self._build_vista_mods()
        self._build_vista_modrinth()
        self._build_vista_modpacks()
        self._build_vista_capturas()
        self._build_vista_skins()
        self._build_vista_ajustes()
        self._sync_sidebar_perfil()
        self.mostrar_vista(cur)
        self.aplicar_filtros()

    def _build_sidebar(self):
        # ── Navigation Rail Oficial Material Design 3 (Ancho 80px) ─────────────────
        # Logo centrado
        logo_f = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=46)
        logo_f.pack(fill="x", pady=(10, 4))
        logo_f.pack_propagate(False)
        if self.logo_ctk:
            ctk.CTkLabel(logo_f, image=self.logo_ctk, text="").pack(expand=True)
        else:
            ico_logo = obtener_icono_ctk(ICON_GAMEPAD, ACCENT, 22)
            ctk.CTkLabel(logo_f, image=ico_logo, text="").pack(expand=True)

        ctk.CTkFrame(self.sidebar, fg_color=BORDER_C, height=1, width=44).pack(pady=(0, 6))

        # Avatar de usuario / perfil al fondo del Navigation Rail
        ctk.CTkFrame(self.sidebar, fg_color=BORDER_C, height=1, width=44).pack(side="bottom", pady=(4, 6))

        prof_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        prof_box.pack(side="bottom", pady=(0, 10))

        # Avatar con ring ACCENT (M3 profile ring)
        p_act = self.config_data.get("active_profile", "Jugador")
        mc_dir = self.config_data.get("minecraft_dir") or MINECRAFT_DIR or os.path.expanduser("~/.mi_launcher")
        skin_p = os.path.join(mc_dir, "profiles", p_act, "skin.png")
        init_head = self._generar_avatar_cabeza(skin_p, size=40)
        ctk_init_head = ctk.CTkImage(light_image=init_head, dark_image=init_head, size=(40, 40))

        # Ring frame: borde ACCENT de 2px, fondo de la sidebar
        ring_frame = ctk.CTkFrame(prof_box, fg_color=ACCENT, corner_radius=24, width=48, height=48)
        ring_frame.pack(pady=(0, 2))
        ring_frame.pack_propagate(False)

        self.lbl_perfil_avatar = ctk.CTkButton(ring_frame, text="", image=ctk_init_head,
                                               width=44, height=44, corner_radius=22,
                                               fg_color=BG_SIDE, hover_color=SURFACE_HIGH,
                                               border_width=0,
                                               command=lambda: self.mostrar_vista("skins"))
        self.lbl_perfil_avatar._img_ref = ctk_init_head
        self.lbl_perfil_avatar.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_perfil_nombre = ctk.CTkLabel(prof_box, text=p_act, font=FONT_CAPTION_S, text_color=TEXT_M, height=14)
        self.lbl_perfil_nombre.pack(pady=(0, 0))

        # Elementos de navegación M3 (Píldora activa + etiqueta debajo)
        nav_items = [
            ("jugar", "nav_jugar", ICON_GAMEPAD),
            ("versiones", "nav_versiones", ICON_BOLT),
            ("mods", "nav_mods", ICON_EXTENSION),
            ("modrinth", "nav_modrinth", ICON_SEARCH),
            ("modpacks", "nav_modpacks", ICON_PACKAGE),
            ("capturas", "nav_capturas", ICON_CAMERA),
            ("skins", "nav_skins", ICON_PERSON),
            ("ajustes", "nav_ajustes", ICON_SETTINGS),
        ]
        self.nav_item_meta = {}
        for key, nav_k, glyph in nav_items:
            label = self.t(nav_k)
            item_f = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=48)
            item_f.pack(fill="x", pady=0)
            item_f.pack_propagate(False)

            ico_norm = obtener_icono_ctk(glyph, TEXT_M, size=18)
            ico_act = obtener_icono_ctk(glyph, ACCENT, size=18)
            self.nav_item_meta[key] = (glyph, ico_norm, ico_act)

            pill = ctk.CTkButton(item_f, text="", image=ico_norm, width=52, height=26,
                                 corner_radius=13, fg_color="transparent", hover_color=SURFACE_HIGH,
                                 command=lambda k=key: self.mostrar_vista(k))
            pill.pack(pady=(2, 0))

            txt_lbl = ctk.CTkLabel(item_f, text=label, font=FONT_CAPTION_S, text_color=TEXT_M, height=14)
            txt_lbl.pack(pady=(0, 2))

            self.nav_buttons[key] = (pill, txt_lbl)

    def _generar_avatar_cabeza(self, skin_path, size=32):
        try:
            if skin_path and os.path.isfile(skin_path):
                img = Image.open(skin_path).convert("RGBA")
            else:
                img = Image.new("RGBA", (64, 64), (80, 90, 115, 255))

            head = img.crop((8, 8, 16, 16)).copy()
            if img.size[0] >= 64:
                hat = img.crop((40, 8, 48, 16))
                head.paste(hat, (0, 0), hat)

            head_scaled = head.resize((size, size), Image.Resampling.NEAREST)

            # Recorte circular M3 oficial
            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size - 1, size - 1), fill=255)
            circ = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            circ.paste(head_scaled, (0, 0), mask=mask)
            return circ
        except Exception:
            return Image.new("RGBA", (size, size), (80, 90, 115, 255))

    def _actualizar_avatar_perfil(self, perfil=None):
        if not hasattr(self, "lbl_perfil_avatar") or not self.lbl_perfil_avatar: return
        if not perfil:
            perfil = self.config_data.get("active_profile", "Jugador")
        mc_dir = self.config_data.get("minecraft_dir") or MINECRAFT_DIR or os.path.expanduser("~/.mi_launcher")
        skin_path = os.path.join(mc_dir, "profiles", perfil, "skin.png")
        head_img = self._generar_avatar_cabeza(skin_path, size=40)
        ctk_head = ctk.CTkImage(light_image=head_img, dark_image=head_img, size=(40, 40))
        self.lbl_perfil_avatar._img_ref = ctk_head
        self.lbl_perfil_avatar.configure(image=ctk_head)
        if hasattr(self.lbl_perfil_avatar, "_draw"):
            self.lbl_perfil_avatar._draw()

    def mostrar_vista(self, nombre):
        if getattr(self, "vista_actual", None) != nombre and hasattr(self, "sound"):
            self.sound.play("click")
        for f in self.vistas.values():
            f.pack_forget()
        target_v = self.vistas[nombre]
        target_v.pack(fill="both", expand=True, pady=(20, 0))
        self.vista_actual = nombre

        # Transición fluida de entrada Material 3 (Desaceleración suave hacia arriba)
        def _animar_entrada(paso=1):
            total_pasos = 8
            if paso <= total_pasos and getattr(self, "vista_actual", None) == nombre:
                t = paso / float(total_pasos)
                factor = 1.0 - (1.0 - t) ** 3  # Cubic ease-out
                desplazamiento = int(round(20 * (1.0 - factor)))
                try:
                    target_v.pack_configure(pady=(desplazamiento, 0))
                except Exception:
                    pass
                self.root.after(18, lambda: _animar_entrada(paso + 1))
            else:
                try:
                    target_v.pack_configure(pady=0)
                except Exception:
                    pass
        self.root.after(18, lambda: _animar_entrada(1))

        for k, (pill, txt_lbl) in self.nav_buttons.items():
            glyph, ico_norm, ico_act = getattr(self, "nav_item_meta", {}).get(k, (None, None, None))
            if k == nombre:
                pill.configure(fg_color=CARD_SEL, image=ico_act)
                txt_lbl.configure(text_color=ACCENT, font=FONT_CAPTION_B)
            else:
                pill.configure(fg_color="transparent", image=ico_norm)
                txt_lbl.configure(text_color=TEXT_M, font=FONT_CAPTION_S)

        if nombre == "versiones":
            self._actualizar_lista_versiones_ui()
        elif nombre == "mods":
            self.actualizar_lista_slots_ui()
        elif nombre == "modpacks":
            self.actualizar_lista_modpacks()
        elif nombre == "modrinth":
            self._modrinth_cargado = True
            self.iniciar_busqueda_modrinth()
        elif nombre == "capturas":
            self.root.after(80, self.actualizar_galeria_capturas)
        elif nombre == "skins":
            self._actualizar_preview_skin()
            self.root.after(0, self._actualizar_vista_armario)
            threading.Thread(target=self._asegurar_mod_skin, daemon=True).start()

    def _sync_sidebar_perfil(self, sel=None):
        perfiles = sorted(self.config_data.get("profiles", {}).keys())
        activo = sel or self.config_data.get("active_profile", "Jugador")
        if hasattr(self, "combo_perfil") and self.combo_perfil:
            try:
                self.combo_perfil.configure(values=perfiles)
                self.combo_perfil.set(activo)
            except Exception:
                pass
        if hasattr(self, "lbl_perfil_nombre") and self.lbl_perfil_nombre:
            try:
                self.lbl_perfil_nombre.configure(text=activo)
            except Exception:
                pass
        self._actualizar_avatar_perfil(activo)

    # ──────────────────────────────────────────────
    # VISTA: JUGAR
    # ──────────────────────────────────────────────
    def _build_vista_jugar(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.vistas["jugar"] = f

        ctk.CTkLabel(f, text=self.t("play_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(anchor="w", padx=SPACE_2XL, pady=(SPACE_XL, SPACE_XS))
        ctk.CTkLabel(f, text=self.t("play_subtitle"), font=FONT_BODY, text_color=TEXT_M).pack(anchor="w", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_LG))

        # Versión
        vc = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        vc.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))
        ctk.CTkLabel(vc, text=self.t("ver_mc"), font=FONT_SECTION, text_color=TEXT_M).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))
        self.combo_version = ctk.CTkComboBox(vc, state="readonly", font=FONT_BODY_L, height=38,
                                             fg_color=SURFACE_HIGH, button_color=ACCENT,
                                             button_hover_color=ACCENT_H, corner_radius=R_SM,
                                             command=self.al_cambiar_version)
        self.combo_version.pack(fill="x", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_MD))
        self.combo_version.set(self.t("loading_vers"))
        self.lbl_play_summary = ctk.CTkLabel(f, text="", font=FONT_BODY_S, text_color=TEXT_M, anchor="w")
        self.lbl_play_summary.pack(fill="x", padx=SPACE_2XL + SPACE_XS, pady=(SPACE_NONE, SPACE_SM))

        # Opciones de lanzamiento
        sc = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        sc.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))
        ctk.CTkLabel(sc, text=self.t("launch_options"), font=FONT_SECTION, text_color=TEXT_M).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))
        grid = ctk.CTkFrame(sc, fg_color="transparent")
        grid.pack(fill="x", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_MD))
        grid.columnconfigure((0, 1), weight=1)

        self.fabric_var           = tk.BooleanVar(value=self.config_data.get("fabric_enabled", True))
        self.vulkan_var           = tk.BooleanVar(value=self.config_data.get("vulkan_enabled", True))
        self.snapshots_var        = tk.BooleanVar(value=self.config_data.get("snapshots_enabled", False))
        self.fullscreen_var       = tk.BooleanVar(value=self.config_data.get("fullscreen_enabled", False))
        self.show_uninstalled_var = tk.BooleanVar(value=self.config_data.get("show_uninstalled", False))

        def _guardar_switches(filtrar=False):
            if hasattr(self, "sound"): self.sound.play("click")
            self.config_data["fabric_enabled"]    = self.fabric_var.get()
            self.config_data["vulkan_enabled"]    = self.vulkan_var.get()
            self.config_data["snapshots_enabled"] = self.snapshots_var.get()
            self.config_data["fullscreen_enabled"]= self.fullscreen_var.get()
            self.config_data["show_uninstalled"]  = self.show_uninstalled_var.get()
            guardar_configuracion(self.config_data)
            if filtrar:
                self.aplicar_filtros()

        def check(parent, text, var, cmd=None, row=0, col=0):
            ctk.CTkCheckBox(parent, text=text, variable=var, font=FONT_BODY,
                            checkbox_width=20, checkbox_height=20, corner_radius=R_XS,
                            border_width=2, fg_color=ACCENT, hover_color=ACCENT_H,
                            command=cmd).grid(row=row, column=col, sticky="w", padx=SPACE_SM, pady=SPACE_XS)

        def _cambiar_mods():
            _guardar_switches(False)
            self._actualizar_estado_slot_jugar()
            self._actualizar_resumen_jugar()

        check(grid, self.t("fabric_mods"), self.fabric_var, _cambiar_mods, row=0, col=0)
        check(grid, self.t("fullscreen"), self.fullscreen_var, lambda: _guardar_switches(False), row=0, col=1)

        self.lbl_slot_jugar = ctk.CTkLabel(grid, text=self.t("mod_slot"), font=FONT_BODY, text_color=TEXT_M)
        self.lbl_slot_jugar.grid(row=1, column=0, sticky="w", padx=SPACE_SM, pady=(SPACE_SM, SPACE_XS))
        self.combo_slot_jugar = ctk.CTkComboBox(grid, state="readonly", font=FONT_BODY, height=32,
                                                fg_color=SURFACE_HIGH, button_color=ACCENT,
                                                button_hover_color=ACCENT_H, corner_radius=R_SM,
                                                command=self._al_cambiar_slot_desde_jugar)
        self.combo_slot_jugar.grid(row=1, column=1, sticky="ew", padx=SPACE_SM, pady=SPACE_XS)

        # Filtros separados de las opciones que afectan al lanzamiento.
        fc = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        fc.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))
        ctk.CTkLabel(fc, text=self.t("version_filters"), font=FONT_SECTION, text_color=TEXT_M).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))
        filters_row = ctk.CTkFrame(fc, fg_color="transparent")
        filters_row.pack(fill="x", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_SM))
        check(filters_row, self.t("vulkan"), self.vulkan_var, lambda: _guardar_switches(True), row=0, col=0)
        check(filters_row, self.t("snapshots"), self.snapshots_var, lambda: _guardar_switches(True), row=0, col=1)
        check(filters_row, self.t("show_uninstalled"), self.show_uninstalled_var, lambda: _guardar_switches(True), row=0, col=2)
        filters_row.columnconfigure((0, 1, 2), weight=1)
        self._actualizar_estado_slot_jugar()
        self._actualizar_resumen_jugar()

        bot = ctk.CTkFrame(f, fg_color="transparent")
        bot.pack(fill="x", padx=SPACE_2XL, side="bottom", pady=(SPACE_NONE, SPACE_LG))

        # Consola Integrada
        cc = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        cc.pack(fill="both", expand=True, padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))

        c_hdr = ctk.CTkFrame(cc, fg_color="transparent", height=28)
        c_hdr.pack(fill="x", padx=SPACE_LG, pady=(SPACE_SM, SPACE_XS))
        c_hdr.pack_propagate(False)

        ctk.CTkLabel(c_hdr, text=self.t("console_title"), font=FONT_SECTION, text_color=TEXT_M).pack(side="left")

        c_btns = ctk.CTkFrame(c_hdr, fg_color="transparent")
        c_btns.pack(side="right")

        ctk.CTkButton(c_btns, text=self.t("console_copy"), font=FONT_LABEL_S, fg_color=SURFACE_HIGH,
                      hover_color=BORDER_C, height=26, width=70, corner_radius=R_FULL, command=self._copiar_consola).pack(side="left", padx=SPACE_XS)
        ctk.CTkButton(c_btns, text=self.t("console_clear"), font=FONT_LABEL_S, fg_color=SURFACE_HIGH,
                      hover_color=BORDER_C, height=26, width=70, corner_radius=R_FULL, command=self._limpiar_consola).pack(side="left", padx=SPACE_XS)

        self.txt_console = ctk.CTkTextbox(cc, font=FONT_CODE, fg_color="#0a0a14", text_color="#bbbbcc",
                                          corner_radius=R_SM, wrap="char")
        self.txt_console.pack(fill="both", expand=True, padx=SPACE_MD, pady=(SPACE_NONE, SPACE_SM))
        self.txt_console.insert("end", self.t("console_ready"))
        self.txt_console.configure(state="disabled")

        ico_play = obtener_icono_ctk(ICON_GAMEPAD, ACCENT_T, 22)
        self.btn_jugar = ctk.CTkButton(bot, text="  " + self.t("btn_play"), image=ico_play, compound="left", font=FONT_TITLE_M,
                                       fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                                       corner_radius=R_FULL, height=48,
                                       command=self.iniciar_hilo_juego)
        self.btn_jugar.pack(fill="x", pady=(SPACE_SM, SPACE_NONE))

        self.progress_bar = ctk.CTkProgressBar(bot, progress_color=ACCENT, height=6, corner_radius=R_FULL)
        self.progress_bar.pack(fill="x", pady=(SPACE_SM, SPACE_XS))
        self.progress_bar.set(0)

        self.lbl_estado = ctk.CTkLabel(bot, text=self.t("ready_to_launch"), font=FONT_BODY_S, text_color=TEXT_M)
        self.lbl_estado.pack(anchor="w")

    def _append_console_log(self, text):
        if not hasattr(self, "txt_console"): return
        try:
            self.txt_console.configure(state="normal")
            self.txt_console.insert("end", text)
            try:
                lines = int(float(self.txt_console.index("end-1c")))
                if lines > 3000:
                    self.txt_console.delete("1.0", f"{lines - 2500}.0")
            except Exception:
                pass
            self.txt_console.see("end")
            self.txt_console.configure(state="disabled")
        except Exception:
            pass

    def _limpiar_consola(self):
        if hasattr(self, "sound"): self.sound.play("click")
        if hasattr(self, "txt_console"):
            self.txt_console.configure(state="normal")
            self.txt_console.delete("1.0", "end")
            self.txt_console.insert("end", self.t("console_ready"))
            self.txt_console.configure(state="disabled")

    def _copiar_consola(self):
        if hasattr(self, "txt_console"):
            txt = self.txt_console.get("1.0", "end-1c")
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            if hasattr(self, "sound"): self.sound.play("success")
            messagebox.showinfo(self.t("console_copied_title"), self.t("console_copied_msg"))

    # ──────────────────────────────────────────────
    # VISTA: GESTOR DE VERSIONES
    # ──────────────────────────────────────────────
    def _build_vista_versiones(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.vistas["versiones"] = f

        hdr = ctk.CTkFrame(f, fg_color="transparent")
        hdr.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_XL, SPACE_SM))
        ctk.CTkLabel(hdr, text=self.t("versiones_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(hdr, text=self.t("versiones_sub"), font=FONT_BODY, text_color=TEXT_M).pack(anchor="w", pady=(2, 0))

        bar = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        bar.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))

        b_inner = ctk.CTkFrame(bar, fg_color="transparent")
        b_inner.pack(fill="x", padx=SPACE_LG, pady=SPACE_MD)

        self.filtro_ver_modo = "releases"
        chips_f = ctk.CTkFrame(b_inner, fg_color="transparent")
        chips_f.pack(side="left")

        self.btn_chip_todas = ctk.CTkButton(chips_f, text=self.t("filter_all"), font=FONT_BODY,
                                            fg_color=BG_CARD2, text_color=TEXT_MAIN, hover_color=BORDER_C,
                                            height=30, width=74, corner_radius=R_FULL,
                                            command=lambda: self._cambiar_filtro_versiones("todas"))
        self.btn_chip_todas.pack(side="left", padx=(0, 4))

        self.btn_chip_inst = ctk.CTkButton(chips_f, text=self.t("filter_installed"), font=FONT_BODY,
                                           fg_color=BG_CARD2, text_color=TEXT_MAIN, hover_color=BORDER_C,
                                           height=30, width=90, corner_radius=R_FULL,
                                           command=lambda: self._cambiar_filtro_versiones("instaladas"))
        self.btn_chip_inst.pack(side="left", padx=4)

        self.btn_chip_rel = ctk.CTkButton(chips_f, text=self.t("filter_releases"), font=FONT_SECTION,
                                          fg_color=ACCENT, text_color=ACCENT_T, hover_color=ACCENT_H,
                                          height=30, width=86, corner_radius=R_FULL,
                                          command=lambda: self._cambiar_filtro_versiones("releases"))
        self.btn_chip_rel.pack(side="left", padx=4)

        self.btn_chip_snap = ctk.CTkButton(chips_f, text=self.t("filter_snapshots"), font=FONT_BODY,
                                           fg_color=BG_CARD2, text_color=TEXT_MAIN, hover_color=BORDER_C,
                                           height=30, width=86, corner_radius=R_FULL,
                                           command=lambda: self._cambiar_filtro_versiones("snapshots"))
        self.btn_chip_snap.pack(side="left", padx=4)

        self.entry_buscar_ver = ctk.CTkEntry(b_inner, placeholder_text=self.t("search_vers_ph"),
                                             font=FONT_BODY, height=34, fg_color=SURFACE_HIGH, corner_radius=R_SM)
        self.entry_buscar_ver.pack(side="right", fill="x", expand=True, padx=(SPACE_MD, SPACE_NONE))
        self.entry_buscar_ver.bind("<KeyRelease>", lambda e: self._actualizar_lista_versiones_ui())

        self.scroll_versiones = ctk.CTkScrollableFrame(f, fg_color=SURFACE,
                                                      scrollbar_fg_color=SURFACE_LOWEST,
                                                      scrollbar_button_color=ACCENT,
                                                      scrollbar_button_hover_color=ACCENT_H)
        self.scroll_versiones.pack(fill="both", expand=True, padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_LG))

        self._cancel_requested_ver = False
        self._instalando_ver_actual = None

    def _cambiar_filtro_versiones(self, modo):
        if hasattr(self, "sound"): self.sound.play("click")
        self.filtro_ver_modo = modo
        chips = [
            (self.btn_chip_todas, "todas"),
            (self.btn_chip_inst, "instaladas"),
            (self.btn_chip_rel, "releases"),
            (self.btn_chip_snap, "snapshots")
        ]
        for btn, m in chips:
            if m == modo:
                btn.configure(fg_color=ACCENT, text_color=ACCENT_T)
            else:
                btn.configure(fg_color=BG_CARD2, text_color=TEXT_MAIN)
        self._actualizar_lista_versiones_ui()

    def _obtener_versiones_instaladas_set(self):
        inst_dir = os.path.join(MINECRAFT_DIR, "versions")
        if not os.path.exists(inst_dir):
            return set()
        res = set()
        try:
            for item in os.listdir(inst_dir):
                if os.path.isdir(os.path.join(inst_dir, item)):
                    if os.path.exists(os.path.join(inst_dir, item, f"{item}.json")):
                        res.add(item)
        except Exception:
            pass
        return res

    def _actualizar_lista_versiones_ui(self):
        if not hasattr(self, "scroll_versiones"): return
        for w in self.scroll_versiones.winfo_children():
            w.destroy()

        if not self.todas_las_versiones:
            ctk.CTkLabel(self.scroll_versiones, text=self.t("loading_vers"),
                         font=FONT_BODY_M_I, text_color=TEXT_M).pack(pady=40)
            return

        instaladas = self._obtener_versiones_instaladas_set()
        query = self.entry_buscar_ver.get().strip().lower() if hasattr(self, "entry_buscar_ver") else ""
        activa = self.combo_version.get() if hasattr(self, "combo_version") else ""

        filtradas = []
        for v in self.todas_las_versiones:
            vid = v.get("id", "")
            vtype = v.get("type", "release")

            if query and query not in vid.lower():
                continue

            esta_inst = vid in instaladas

            if self.filtro_ver_modo == "instaladas" and not esta_inst:
                continue
            elif self.filtro_ver_modo == "releases" and vtype != "release":
                continue
            elif self.filtro_ver_modo == "snapshots" and vtype != "snapshot":
                continue

            filtradas.append((v, esta_inst, vid == activa))

        if self.filtro_ver_modo in ["todas", "instaladas"]:
            ids_oficiales = {v.get("id") for v in self.todas_las_versiones}
            for local_id in sorted(instaladas):
                if local_id not in ids_oficiales and not local_id.startswith("fabric-loader-"):
                    if query and query not in local_id.lower():
                        continue
                    filtradas.append(({"id": local_id, "type": "custom", "releaseTime": ""}, True, local_id == activa))

        if not filtradas:
            ctk.CTkLabel(self.scroll_versiones, text=self.t("no_results"),
                         font=FONT_BODY, text_color=TEXT_M).pack(pady=40)
            return

        for v_info, esta_inst, es_activa in filtradas[:60]:
            vid = v_info.get("id", "")
            vtype = v_info.get("type", "release")
            rel_time = str(v_info.get("releaseTime", ""))[:10]

            card = ctk.CTkFrame(self.scroll_versiones, fg_color=BG_CARD, corner_radius=R_MD)
            card.pack(fill="x", pady=4, padx=2)

            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True, padx=14, pady=10)

            t_row = ctk.CTkFrame(left, fg_color="transparent")
            t_row.pack(anchor="w")

            ctk.CTkLabel(t_row, text=vid, font=FONT_TITLE_S, text_color=TEXT_MAIN).pack(side="left")

            type_color = ACCENT if vtype == "release" else ("#c586c0" if vtype == "snapshot" else "#dcdcaa")
            ctk.CTkLabel(t_row, text=f"  {vtype.upper()}  ", font=FONT_LABEL_S,
                         fg_color=BG_CARD2, text_color=type_color, corner_radius=R_SM).pack(side="left", padx=8)

            if esta_inst:
                v_path = os.path.join(MINECRAFT_DIR, "versions", vid)
                size_str = ""
                try:
                    s_b = sum(os.path.getsize(os.path.join(v_path, f)) for f in os.listdir(v_path) if os.path.isfile(os.path.join(v_path, f)))
                    size_str = f" • {s_b / (1024*1024):.1f} MB"
                except Exception:
                    pass
                sub_txt = f"{self.t('status_installed')}{size_str}  •  {rel_time}" if rel_time else f"{self.t('status_installed')}{size_str}"
                ctk.CTkLabel(left, text=sub_txt, font=FONT_BODY_S, text_color="#4ec9b0", anchor="w").pack(anchor="w", pady=(2, 0))
            else:
                sub_txt = f"{self.t('status_not_installed')}  •  {rel_time}" if rel_time else self.t('status_not_installed')
                ctk.CTkLabel(left, text=sub_txt, font=FONT_BODY_S, text_color=TEXT_M, anchor="w").pack(anchor="w", pady=(2, 0))

            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(side="right", padx=12, pady=10)

            if esta_inst:
                if es_activa:
                    btn_sel = ctk.CTkButton(actions, text=self.t("selected_version"), font=FONT_SECTION,
                                            fg_color=BG_DARK, text_color=TEXT_M, width=95, height=32,
                                            corner_radius=R_FULL, state="disabled")
                    btn_sel.pack(side="left", padx=(0, 6))
                else:
                    btn_sel = ctk.CTkButton(actions, text=self.t("select_version"), font=FONT_BODY,
                                            fg_color=BG_CARD2, hover_color=BORDER_C, text_color=TEXT_MAIN,
                                            width=95, height=32, corner_radius=R_FULL,
                                            command=lambda v_id=vid: self._seleccionar_version_desde_gestor(v_id))
                    btn_sel.pack(side="left", padx=(0, 6))

                btn_del = ctk.CTkButton(actions, text=self.t("btn_uninstall"), font=FONT_BODY,
                                        fg_color=DANGER_SOFT, hover_color=DANGER_SOFT_H, text_color=DANGER,
                                        width=95, height=32, corner_radius=R_FULL,
                                        command=lambda v_id=vid: self._desinstalar_version(v_id))
                btn_del.pack(side="left")
            else:
                btn_inst = ctk.CTkButton(actions, text=self.t("btn_install_ver"), font=FONT_SECTION,
                                         fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                                         width=105, height=32, corner_radius=R_FULL,
                                         command=lambda v_id=vid: self._iniciar_instalacion_version_gestor(v_id))
                btn_inst.pack(side="left")

    def _seleccionar_version_desde_gestor(self, vid):
        if hasattr(self, "sound"): self.sound.play("select")
        if hasattr(self, "combo_version"):
            vals = list(self.combo_version.cget("values"))
            if vid not in vals:
                vals.insert(0, vid)
                self.combo_version.configure(values=vals)
            self.combo_version.set(vid)
            self.al_cambiar_version(vid)
        self._actualizar_lista_versiones_ui()

    def _desinstalar_version(self, vid):
        if hasattr(self, "sound"): self.sound.play("click")
        if not messagebox.askyesno(self.t("confirm_uninstall_title"), self.t("confirm_uninstall_msg", vid)):
            return
        try:
            v_dir = os.path.join(MINECRAFT_DIR, "versions", vid)
            if os.path.exists(v_dir):
                shutil.rmtree(v_dir)
            inst_dir = os.path.join(MINECRAFT_DIR, "versions")
            if os.path.exists(inst_dir):
                for item in os.listdir(inst_dir):
                    if item.startswith("fabric-loader-") and item.endswith(f"-{vid}"):
                        try: shutil.rmtree(os.path.join(inst_dir, item))
                        except Exception: pass

            if hasattr(self, "sound"): self.sound.play("click")
            self._actualizar_lista_versiones_ui()
            self.aplicar_filtros()
            if hasattr(self, "_actualizar_espacio_almacenamiento"):
                self._actualizar_espacio_almacenamiento()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _mostrar_modal_instalacion(self, ver):
        top = ctk.CTkToplevel(self.root)
        top.title(self.t("installing_title", ver))
        top.geometry("480x260")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()
        top.configure(fg_color=BG_DARK)

        try:
            top.update_idletasks()
            rx = self.root.winfo_rootx() + (self.root.winfo_width() - 480) // 2
            ry = self.root.winfo_rooty() + (self.root.winfo_height() - 260) // 2
            top.geometry(f"480x260+{max(0, rx)}+{max(0, ry)}")
        except Exception:
            pass
        animar_entrada_modal(top)

        hdr = ctk.CTkFrame(top, fg_color=BG_SIDE, height=44, corner_radius=0)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=f"{self.t('installing_title', ver)}", font=FONT_SECTION, text_color=TEXT_MAIN).pack(side="left", padx=16)

        content = ctk.CTkFrame(top, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=22, pady=16)

        lbl_st = ctk.CTkLabel(content, text=self.t("install_starting"), font=FONT_BODY, text_color=TEXT_M, anchor="w")
        lbl_st.pack(fill="x", pady=(0, 6))

        p_bar = ctk.CTkProgressBar(content, progress_color=ACCENT, height=10)
        p_bar.pack(fill="x", pady=(0, 4))
        p_bar.set(0)

        lbl_pct = ctk.CTkLabel(content, text="0%", font=FONT_CAPTION_B, text_color=ACCENT, anchor="e")
        lbl_pct.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(content, text=self.t("install_modal_warn"), font=FONT_HINT_I, text_color="#8888aa").pack(fill="x", pady=(0, 10))

        btn_cancel = ctk.CTkButton(content, text=self.t("btn_cancel_install"), font=FONT_SECTION,
                                   fg_color=DANGER, hover_color=DANGER_H, text_color="white", height=34,
                                   command=self._solicitar_cancelar_instalacion)
        btn_cancel.pack(fill="x")

        top.protocol("WM_DELETE_WINDOW", self._solicitar_cancelar_instalacion)

        self._modal_install = top
        self._modal_lbl_status = lbl_st
        self._modal_pbar = p_bar
        self._modal_lbl_pct = lbl_pct

    def _iniciar_instalacion_version_gestor(self, vid):
        if hasattr(self, "sound"): self.sound.play("click")
        if getattr(self, "_instalando_ver_actual", None):
            return
        self._cancel_requested_ver = False
        self._instalando_ver_actual = vid

        self._mostrar_modal_instalacion(vid)
        threading.Thread(target=self._hilo_instalar_version_gestor, args=(vid,), daemon=True).start()

    def _solicitar_cancelar_instalacion(self):
        if hasattr(self, "sound"): self.sound.play("click")
        self._cancel_requested_ver = True
        if hasattr(self, "_modal_lbl_status") and self._modal_lbl_status.winfo_exists():
            self._modal_lbl_status.configure(text=self.t("install_cancelling"))

    def _hilo_instalar_version_gestor(self, ver):
        def st(t):
            if self._cancel_requested_ver:
                raise InstallCancelledException("Cancelado")
            def _up():
                if hasattr(self, "_modal_lbl_status") and self._modal_lbl_status.winfo_exists():
                    self._modal_lbl_status.configure(text=t)
            self.root.after(0, _up)

        def sm(v):
            if self._cancel_requested_ver:
                raise InstallCancelledException("Cancelado")
            self._max_ver_prog = v

        def sp(v):
            if self._cancel_requested_ver:
                raise InstallCancelledException("Cancelado")
            if getattr(self, "_max_ver_prog", 0) > 0:
                p_val = min(v / self._max_ver_prog, 1.0)
                pct_str = f"{int(p_val * 100)}%"
                def _up_p():
                    if hasattr(self, "_modal_pbar") and self._modal_pbar.winfo_exists():
                        self._modal_pbar.set(p_val)
                    if hasattr(self, "_modal_lbl_pct") and self._modal_lbl_pct.winfo_exists():
                        self._modal_lbl_pct.configure(text=pct_str)
                self.root.after(0, _up_p)

        try:
            st(self.t("install_checking_java", ver))
            try:
                info = minecraft_launcher_lib.runtime.get_version_runtime_information(ver, MINECRAFT_DIR)
                if info and not minecraft_launcher_lib.runtime.get_executable_path(info["name"], MINECRAFT_DIR):
                    minecraft_launcher_lib.runtime.install_jvm_runtime(
                        info["name"], MINECRAFT_DIR, callback={"setStatus": st, "setMax": sm, "setProgress": sp})
            except InstallCancelledException:
                raise
            except Exception: pass

            if self._cancel_requested_ver:
                raise InstallCancelledException("Cancelado")

            st(self.t("install_downloading_ver", ver))
            minecraft_launcher_lib.install.install_minecraft_version(
                ver, MINECRAFT_DIR, callback={"setStatus": st, "setMax": sm, "setProgress": sp})

            self.root.after(0, lambda: self.sound.play("success"))
            self.root.after(0, lambda: self._finalizar_instalacion_gestor(ver, exito=True))
        except InstallCancelledException:
            try:
                v_dir = os.path.join(MINECRAFT_DIR, "versions", ver)
                if os.path.exists(v_dir):
                    shutil.rmtree(v_dir)
            except Exception: pass
            self.root.after(0, lambda: self._finalizar_instalacion_gestor(ver, exito=False, cancelado=True))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self._finalizar_instalacion_gestor(ver, exito=False))

    def _finalizar_instalacion_gestor(self, ver, exito=True, cancelado=False):
        if hasattr(self, "_modal_install") and self._modal_install and self._modal_install.winfo_exists():
            try:
                self._modal_install.grab_release()
                self._modal_install.destroy()
            except Exception: pass
        self._modal_install = None
        self._instalando_ver_actual = None
        self._cancel_requested_ver = False

        if exito:
            self._seleccionar_version_desde_gestor(ver)
        elif cancelado:
            messagebox.showinfo(self.t("install_cancelled_title"), self.t("install_cancelled"))

        self._actualizar_lista_versiones_ui()
        self.aplicar_filtros()
        if hasattr(self, "_actualizar_espacio_almacenamiento"):
            self._actualizar_espacio_almacenamiento()

    # ──────────────────────────────────────────────
    # VISTA: MODS
    # ──────────────────────────────────────────────
    def _build_vista_mods(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.vistas["mods"] = f

        hdr = ctk.CTkFrame(f, fg_color="transparent")
        hdr.pack(fill="x", padx=30, pady=(25, 14))
        ctk.CTkLabel(hdr, text=self.t("mods_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(side="left")
        links = ctk.CTkFrame(hdr, fg_color="transparent")
        links.pack(side="right")
        for lbl, cmd in [("Fabric API", self.abrir_fabric_api), ("Mod Menu", self.abrir_modmenu)]:
            ctk.CTkButton(links, text=lbl, font=FONT_LABEL_S, fg_color=BG_CARD2,
                          hover_color=BORDER_C, height=30, width=85, corner_radius=R_FULL, command=cmd).pack(side="left", padx=2)
        ctk.CTkButton(links, text="Modrinth", font=FONT_LABEL_S, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=ACCENT_T, height=30, corner_radius=R_FULL,
                      command=self.abrir_modrinth).pack(side="left", padx=2)

        sc = ctk.CTkFrame(f, fg_color=BG_CARD, corner_radius=R_MD)
        sc.pack(fill="x", padx=30, pady=(0, 10))
        si = ctk.CTkFrame(sc, fg_color="transparent")
        si.pack(fill="x", padx=18, pady=(12, 6))
        ctk.CTkLabel(si, text=self.t("mod_slot"), font=FONT_SECTION, text_color=TEXT_M).pack(side="left")
        sb = ctk.CTkFrame(si, fg_color="transparent")
        sb.pack(side="right")
        for txt, clr, hov, cmd in [
            (ICON_ADD, ACCENT, ACCENT_H, self.crear_slot),
            (ICON_EDIT, SURFACE_HIGH, BORDER_C, self.renombrar_slot),
            (ICON_DELETE, WARNING, WARNING_H, self.vaciar_slot),
            (ICON_CLOSE, DANGER_SOFT, DANGER_SOFT_H, self.eliminar_slot),
        ]:
            ctk.CTkButton(sb, text=txt, width=32, height=32, font=FONT_ICON_SM, fg_color=clr, hover_color=hov,
                          text_color=ACCENT_T if clr == ACCENT else TEXT_MAIN, corner_radius=R_FULL,
                          command=cmd).pack(side="left", padx=SPACE_XS)

        self.combo_slot = ctk.CTkComboBox(sc, state="readonly", font=FONT_BODY, height=34,
                                          fg_color=BG_CARD2, button_color=ACCENT,
                                          button_hover_color=ACCENT_H, corner_radius=R_SM,
                                          command=self.al_cambiar_slot)
        self.combo_slot.pack(fill="x", padx=18, pady=(0, 8))

        self.scrollable_mods = ctk.CTkScrollableFrame(f, fg_color=BG_CARD, corner_radius=R_MD,
                                                      scrollbar_button_color=ACCENT)
        self.scrollable_mods.pack(fill="both", expand=True, padx=30, pady=(0, 10))

        ar = ctk.CTkFrame(f, fg_color="transparent")
        ar.pack(fill="x", padx=30, pady=(0, 20))
        ctk.CTkButton(ar, text=self.t("add_mods"), font=FONT_LABEL_L,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, height=40,
                      corner_radius=R_FULL, command=self.añadir_mods).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(ar, text=self.t("open_folder"), font=FONT_LABEL_L,
                      fg_color=BG_CARD2, hover_color=BORDER_C, height=40,
                      corner_radius=R_FULL, command=self.abrir_carpeta_mods).pack(side="right", expand=True, fill="x", padx=(6, 0))

    # ──────────────────────────────────────────────
    # VISTA: MODRINTH
    # ──────────────────────────────────────────────
    def _build_vista_modrinth(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.vistas["modrinth"] = f

        hdr = ctk.CTkFrame(f, fg_color="transparent")
        hdr.pack(fill="x", padx=30, pady=(25, 4))
        ctk.CTkLabel(hdr, text=self.t("modrinth_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(side="left")

        ctk.CTkLabel(f, text=self.t("modrinth_sub"),
                     font=FONT_BODY, text_color=TEXT_M).pack(anchor="w", padx=30, pady=(0, 10))

        search_card = ctk.CTkFrame(f, fg_color=BG_CARD, corner_radius=R_MD)
        search_card.pack(fill="x", padx=30, pady=(0, 10))

        sb_inner = ctk.CTkFrame(search_card, fg_color="transparent")
        sb_inner.pack(fill="x", padx=14, pady=10)

        self.entry_modrinth = ctk.CTkEntry(sb_inner, placeholder_text=self.t("modrinth_search_ph"),
                                            font=FONT_BODY, height=38, fg_color=BG_CARD2, corner_radius=R_SM)
        self.entry_modrinth.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_modrinth.bind("<Return>", lambda e: self.iniciar_busqueda_modrinth())

        ctk.CTkButton(sb_inner, text=self.t("btn_search"), font=FONT_LABEL_L,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                      height=38, width=105, corner_radius=R_FULL, command=self.iniciar_busqueda_modrinth).pack(side="right")

        pills_f = ctk.CTkFrame(f, fg_color="transparent")
        pills_f.pack(fill="x", padx=30, pady=(0, 10))
        ctk.CTkLabel(pills_f, text=self.t("popular"), font=FONT_SECTION, text_color=TEXT_M).pack(side="left", padx=(0, 6))

        def p_search(q):
            if hasattr(self, "sound"): self.sound.play("click")
            self.entry_modrinth.delete(0, "end")
            self.entry_modrinth.insert(0, q)
            self.iniciar_busqueda_modrinth()

        for q in ["Sodium", "Lithium", "Iris", "Fabric API", "Mod Menu", "Zoomify"]:
            ctk.CTkButton(pills_f, text=q, font=FONT_LABEL_S, fg_color=BG_CARD2,
                          hover_color=BORDER_C, height=28, corner_radius=R_FULL,
                          command=lambda query=q: p_search(query)).pack(side="left", padx=2)

        self.lbl_modrinth_status = ctk.CTkLabel(f, text="", font=FONT_BODY_S, text_color=TEXT_M)
        self.lbl_modrinth_status.pack(anchor="w", padx=30, pady=(0, 4))

        self.scrollable_modrinth = ctk.CTkScrollableFrame(f, fg_color=BG_CARD, corner_radius=R_MD,
                                                          scrollbar_button_color=ACCENT)
        self.scrollable_modrinth.pack(fill="both", expand=True, padx=30, pady=(0, 20))

    def iniciar_busqueda_modrinth(self):
        if hasattr(self, "sound"): self.sound.play("click")
        query = self.entry_modrinth.get().strip()
        self.lbl_modrinth_status.configure(text=self.t("searching_modrinth"))
        threading.Thread(target=self._hilo_busqueda_modrinth, args=(query,), daemon=True).start()

    def _hilo_busqueda_modrinth(self, query):
        try:
            ver = self.combo_version.get()
            facets_list = [["categories:fabric"], ["project_type:mod"]]
            if ver and ver not in [self.t("loading_vers"), self.t("no_results")]:
                facets_list.append([f"versions:{ver}"])

            params = {
                "query": query if query else "",
                "limit": 20,
                "facets": json.dumps(facets_list)
            }
            res = requests.get("https://api.modrinth.com/v2/search", params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                hits = data.get("hits", [])
                self.root.after(0, lambda: self._mostrar_resultados_modrinth(hits, query))
            else:
                self.root.after(0, lambda: self.lbl_modrinth_status.configure(text=self.t("modrinth_error_connect")))
        except Exception as e:
            self.root.after(0, lambda: self.lbl_modrinth_status.configure(text=f"Error: {str(e)[:50]}"))

    def _mostrar_resultados_modrinth(self, hits, query):
        for w in self.scrollable_modrinth.winfo_children():
            w.destroy()

        if not hits:
            self.lbl_modrinth_status.configure(text=self.t("modrinth_no_mods"))
            ctk.CTkLabel(self.scrollable_modrinth, text=self.t("modrinth_no_results_label"),
                         font=FONT_BODY_I, text_color=TEXT_M).pack(pady=40)
            return

        if query:
            self.lbl_modrinth_status.configure(text=self.t("modrinth_n_results", len(hits), query))
        else:
            self.lbl_modrinth_status.configure(text=self.t("modrinth_n_results_popular", len(hits)))

        mods_instalados = set()
        mods_dir = self._mods_dir()
        if os.path.exists(mods_dir):
            for fn in os.listdir(mods_dir):
                if fn.endswith(".jar") or fn.endswith(".jar.disabled"):
                    info = self._obtener_info_mod(os.path.join(mods_dir, fn))
                    mods_instalados.add(info["name"].lower())
                    mods_instalados.add(fn.lower())
                    if info.get("mod_id"):
                        mods_instalados.add(info["mod_id"].lower())

        for hit in hits:
            self._crear_tarjeta_modrinth(hit, mods_instalados)

    def _crear_tarjeta_modrinth(self, hit, mods_instalados):
        title = hit.get("title", hit.get("slug", "Mod"))
        author = hit.get("author", "Desconocido")
        desc = hit.get("description", "Sin descripción.")
        downloads = hit.get("downloads", 0)
        icon_url = hit.get("icon_url")
        project_id = hit.get("project_id")

        card = ctk.CTkFrame(self.scrollable_modrinth, fg_color=BG_CARD2, corner_radius=10)
        card.pack(fill="x", pady=4, padx=4)

        icon_label = ctk.CTkLabel(card, text=ICON_PACKAGE, font=FONT_ICON_LG, text_color=ACCENT)
        icon_label.pack(side="left", padx=(12, 6), pady=8)

        if icon_url:
            def cargar_img(url, lbl=icon_label):
                try:
                    r = requests.get(url, timeout=5)
                    if r.status_code == 200:
                        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(36, 36))
                        self.root.after(0, lambda: lbl.configure(image=ctk_img, text=""))
                except Exception:
                    pass
            threading.Thread(target=cargar_img, args=(icon_url,), daemon=True).start()

        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=6, pady=6)

        t_lbl = ctk.CTkLabel(info_frame, text=title, font=FONT_SECTION, text_color=TEXT_MAIN, anchor="w")
        t_lbl.pack(anchor="w")

        dl_formatted = f"{downloads:,}".replace(",", ".")
        sub_txt = f"{self.t('author')} {author}  •  {dl_formatted} {self.t('downloads')}"
        ctk.CTkLabel(info_frame, text=sub_txt, font=FONT_CAPTION_S, text_color=TEXT_M, anchor="w").pack(anchor="w")

        d_txt = desc[:80] + "..." if len(desc) > 83 else desc
        ctk.CTkLabel(info_frame, text=d_txt, font=FONT_CAPTION, text_color=TEXT_M, anchor="w", justify="left").pack(anchor="w", pady=(2, 0))

        ya_instalado = title.lower() in mods_instalados or hit.get("slug", "").lower() in mods_instalados
        btn_text = self.t("btn_installed") if ya_instalado else self.t("btn_install")
        btn_color = BG_DARK if ya_instalado else ACCENT
        btn_state = "disabled" if ya_instalado else "normal"

        btn_inst = ctk.CTkButton(card, text=btn_text, font=FONT_SECTION,
                                 fg_color=btn_color, hover_color=ACCENT_H,
                                 text_color=ACCENT_T if not ya_instalado else TEXT_M,
                                 width=95, height=32, state=btn_state)
        btn_inst.pack(side="right", padx=10, pady=8)

        if not ya_instalado:
            btn_inst.configure(command=lambda p_id=project_id, t=title, b=btn_inst, url=icon_url, s=hit.get("slug", ""):
                               self.iniciar_descarga_modrinth(p_id, t, b, icon_url=url, slug=s))

    def iniciar_descarga_modrinth(self, project_id, title, button, icon_url="", slug=""):
        if hasattr(self, "sound"): self.sound.play("click")
        button.configure(state="disabled", text="⏳ ...")
        threading.Thread(target=self._hilo_descargar_modrinth, args=(project_id, title, button, icon_url, slug), daemon=True).start()

    def _hilo_descargar_modrinth(self, project_id, title, button, icon_url="", slug=""):
        try:
            ver = self.combo_version.get()
            url_versiones = f"https://api.modrinth.com/v2/project/{project_id}/version"
            res = requests.get(url_versiones, timeout=10)
            if res.status_code != 200:
                self.root.after(0, lambda: messagebox.showerror("Error", self.t("modrinth_info_error")))
                self.root.after(0, lambda: button.configure(state="normal", text=self.t("btn_install")))
                return

            versiones = res.json()
            target_version = None

            for v in versiones:
                loaders = v.get("loaders", [])
                g_vers  = v.get("game_versions", [])
                if "fabric" in loaders:
                    if ver in g_vers:
                        target_version = v
                        break
                    elif not target_version:
                        target_version = v

            if not target_version and versiones:
                target_version = versiones[0]

            if not target_version or not target_version.get("files"):
                self.root.after(0, lambda: messagebox.showwarning(self.t("incompatible_title"), self.t("incompatible_mod_msg", title)))
                self.root.after(0, lambda: button.configure(state="normal", text=self.t("btn_install")))
                return

            file_info = target_version["files"][0]
            for f_item in target_version["files"]:
                if f_item.get("primary", False):
                    file_info = f_item
                    break

            dl_url = file_info["url"]
            file_name = file_info["filename"]
            dest_path = os.path.join(self._mods_dir(), file_name)

            r = requests.get(dl_url, stream=True, timeout=30)
            with open(dest_path, "wb") as f_out:
                for chunk in r.iter_content(8192):
                    f_out.write(chunk)

            self._guardar_mod_meta(self._mods_dir(), file_name, {
                "title": title,
                "project_id": project_id,
                "slug": slug or project_id,
                "icon_url": icon_url
            })

            self.root.after(0, lambda: button.configure(text=self.t("btn_installed"), fg_color=BG_DARK, text_color=TEXT_M, state="disabled"))
            self.root.after(0, lambda: self.lbl_modrinth_status.configure(text=self.t("mod_installed_success", title)))
            self.root.after(0, lambda: self.sound.play("success"))
            if hasattr(self, "_mod_cache"):
                self._mod_cache.clear()
            self.root.after(0, self.actualizar_lista_mods)

            deps_reqs = [d for d in target_version.get("dependencies", [])
                         if d.get("dependency_type") == "required" and d.get("project_id")]
            if deps_reqs:
                threading.Thread(target=self._verificar_dependencias,
                                 args=(deps_reqs,), daemon=True).start()

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(self.t("download_error_title"), str(e)))
            self.root.after(0, lambda: button.configure(state="normal", text=self.t("btn_install")))

    def _verificar_dependencias(self, deps_reqs):
        mods_dir = self._mods_dir()
        installed = set()
        if os.path.exists(mods_dir):
            for fn in os.listdir(mods_dir):
                if fn.endswith(".jar") or fn.endswith(".jar.disabled"):
                    inf = self._obtener_info_mod(os.path.join(mods_dir, fn))
                    if inf.get("mod_id"):
                        m_id = inf["mod_id"].lower()
                        installed.add(m_id)
                        installed.add(m_id.replace("-", "").replace("_", ""))
                    if inf.get("name"):
                        n_id = inf["name"].lower()
                        installed.add(n_id)
                        installed.add(n_id.replace("'", "").replace("’", "").replace(" ", "").replace("-", "").replace("_", ""))
                    if inf.get("slug"):
                        s_id = inf["slug"].lower()
                        installed.add(s_id)
                        installed.add(s_id.replace("-", "").replace("_", ""))
                    if inf.get("project_id"):
                        installed.add(inf["project_id"].lower())
                    installed.add(fn.lower())
                    installed.add(fn.lower().replace("-", "").replace("_", ""))

        pendientes = []
        for dep in deps_reqs:
            pid = dep["project_id"]
            try:
                res = requests.get(f"https://api.modrinth.com/v2/project/{pid}", timeout=8)
                if res.status_code == 200:
                    proj = res.json()
                    slug = proj.get("slug", "")
                    dep_title = proj.get("title", pid)
                    icon_url = proj.get("icon_url", "")
                    desc = proj.get("description", "")
                    s_norm = slug.lower().replace("-", "").replace("_", "")
                    p_norm = pid.lower().replace("-", "").replace("_", "")
                    if (slug.lower() not in installed and 
                        s_norm not in installed and 
                        dep_title.lower() not in installed and 
                        pid.lower() not in installed and
                        p_norm not in installed):
                        pendientes.append({
                            "project_id": pid,
                            "slug": slug,
                            "title": dep_title,
                            "icon_url": icon_url,
                            "description": desc
                        })
            except Exception:
                pass

        if not pendientes:
            return

        auto = self.config_data.get("auto_dependencias", False)
        if auto:
            for dep in pendientes:
                self._descargar_dep(dep["project_id"], dep["title"])
            self.root.after(0, self.actualizar_lista_mods)
            self.root.after(0, lambda: self.lbl_modrinth_status.configure(
                text=self.t("deps_installed_count", len(pendientes))))
        else:
            self.root.after(0, lambda: self._dialogo_dependencias(pendientes))

    def _iniciar_dialogo_deps_faltantes(self, dep_ids):
        if hasattr(self, "lbl_estado"):
            self.lbl_estado.configure(text=self.t("fetching_deps_data"))
        threading.Thread(target=self._hilo_cargar_y_mostrar_deps, args=(dep_ids,), daemon=True).start()

    def _hilo_cargar_y_mostrar_deps(self, dep_ids):
        rich_deps = []
        for pid in dep_ids:
            try:
                res = requests.get(f"https://api.modrinth.com/v2/project/{pid}", timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    rich_deps.append({
                        "project_id": pid,
                        "title": data.get("title", pid),
                        "icon_url": data.get("icon_url", ""),
                        "description": data.get("description", "")
                    })
                else:
                    rich_deps.append({"project_id": pid, "title": pid, "icon_url": "", "description": ""})
            except Exception:
                rich_deps.append({"project_id": pid, "title": pid, "icon_url": "", "description": ""})
        self.root.after(0, lambda: self._dialogo_dependencias(rich_deps))

    def _dialogo_dependencias(self, deps):
        top = ctk.CTkToplevel(self.root)
        top.title(self.t("deps_required_title"))
        top.geometry("500x420")
        top.grab_set()
        top.configure(fg_color=BG_DARK)
        animar_entrada_modal(top)

        ctk.CTkLabel(top, text=self.t('deps_required_title'),
                     font=FONT_TITLE_M, text_color=TEXT_MAIN).pack(pady=(16, 4), padx=20, anchor="w")
        ctk.CTkLabel(top, text=self.t("deps_required_sub"),
                     font=FONT_BODY, text_color=TEXT_M).pack(padx=20, anchor="w")

        scroll = ctk.CTkScrollableFrame(top, fg_color=BG_CARD, corner_radius=10, scrollbar_button_color=ACCENT)
        scroll.pack(fill="both", expand=True, padx=20, pady=(10, 10))

        for dep in deps:
            card = ctk.CTkFrame(scroll, fg_color=BG_CARD2, corner_radius=8)
            card.pack(fill="x", pady=4, padx=4)

            ctk_img = None
            if dep.get("icon_url"):
                try:
                    r_img = requests.get(dep["icon_url"], timeout=5)
                    if r_img.status_code == 200:
                        img_data = Image.open(io.BytesIO(r_img.content)).convert("RGBA")
                        ctk_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(32, 32))
                except Exception:
                    pass

            if ctk_img:
                ctk.CTkLabel(card, image=ctk_img, text="").pack(side="left", padx=(10, 8), pady=8)
            else:
                ctk.CTkLabel(card, text=ICON_PACKAGE, font=FONT_ICON_LG, text_color=ACCENT).pack(side="left", padx=(12, 10), pady=8)

            text_frame = ctk.CTkFrame(card, fg_color="transparent")
            text_frame.pack(side="left", fill="both", expand=True, pady=6)

            ctk.CTkLabel(text_frame, text=dep["title"],
                         font=FONT_SECTION, text_color=TEXT_MAIN, anchor="w").pack(anchor="w")
            desc = dep.get("description", "")
            if desc:
                if len(desc) > 60: desc = desc[:57] + "..."
                ctk.CTkLabel(text_frame, text=desc, font=FONT_CAPTION_S,
                             text_color=TEXT_M, anchor="w").pack(anchor="w")

            btn_one = ctk.CTkButton(card, text=ICON_DOWNLOAD, width=32, height=32,
                                    font=FONT_ICON_SM, fg_color=ACCENT, hover_color=ACCENT_H,
                                    text_color=ACCENT_T, corner_radius=R_FULL)
            btn_one.pack(side="right", padx=(0, 10), pady=8)
            btn_one.configure(
                command=lambda d=dep, b=btn_one: (
                    b.configure(state="disabled", text=ICON_CHECK),
                    threading.Thread(target=self._descargar_dep,
                                     args=(d.get("project_id"), d.get("title")),
                                     kwargs={"icon_url": d.get("icon_url", ""), "slug": d.get("slug", "")},
                                     daemon=True).start()
                )
            )

        def instalar_todas():
            top.destroy()
            threading.Thread(target=self._instalar_deps_seleccionadas, args=(deps,), daemon=True).start()

        btns = ctk.CTkFrame(top, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(btns, text=self.t("btn_install_all_deps"), font=FONT_SECTION,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, height=38,
                      command=instalar_todas).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(btns, text=self.t("btn_skip"), font=FONT_BODY, fg_color=BG_CARD2,
                      hover_color=BORDER_C, height=38, command=top.destroy).pack(side="right", expand=False, width=90)

    def _instalar_deps_seleccionadas(self, deps):
        if hasattr(self, "_mod_cache"):
            self._mod_cache.clear()
        for dep in deps:
            self._descargar_dep(
                dep.get("project_id"),
                dep.get("title"),
                icon_url=dep.get("icon_url", ""),
                slug=dep.get("slug", "")
            )
        self.root.after(0, self.actualizar_lista_mods)
        if hasattr(self, "lbl_modrinth_status"):
            self.root.after(0, lambda: self.lbl_modrinth_status.configure(
                text=self.t("deps_installed_count", len(deps))))

    def _guardar_mod_meta(self, mods_dir, filename, meta_dict):
        try:
            os.makedirs(mods_dir, exist_ok=True)
            meta_path = os.path.join(mods_dir, ".mod_metadata.json")
            data = {}
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data[filename] = meta_dict
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Error guardando mod metadata:", e)

    def _obtener_mod_meta(self, mods_dir, filename):
        meta_path = os.path.join(mods_dir, ".mod_metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get(filename, {})
            except Exception:
                pass
        return {}

    def _descargar_dep(self, project_id, title, icon_url="", slug=""):
        try:
            ver = self.combo_version.get()
            if not slug or not icon_url:
                try:
                    p_res = requests.get(f"https://api.modrinth.com/v2/project/{project_id}", timeout=6)
                    if p_res.status_code == 200:
                        p_data = p_res.json()
                        title    = title or p_data.get("title", project_id)
                        icon_url = icon_url or p_data.get("icon_url", "")
                        slug     = slug or p_data.get("slug", project_id)
                except Exception:
                    pass

            res = requests.get(f"https://api.modrinth.com/v2/project/{project_id}/version", timeout=10)
            if res.status_code != 200: return
            versiones = res.json()
            target = None
            for v in versiones:
                if "fabric" in v.get("loaders", []) and ver in v.get("game_versions", []):
                    target = v; break
            if not target:
                for v in versiones:
                    if "fabric" in v.get("loaders", []):
                        target = v; break
            if not target and versiones:
                target = versiones[0]
            if not target or not target.get("files"): return
            fi = next((f for f in target["files"] if f.get("primary")), target["files"][0])
            r = requests.get(fi["url"], stream=True, timeout=30)
            file_name = fi["filename"]
            dest = os.path.join(self._mods_dir(), file_name)
            with open(dest, "wb") as out:
                for chunk in r.iter_content(8192):
                    out.write(chunk)

            self._guardar_mod_meta(self._mods_dir(), file_name, {
                "title": title,
                "project_id": project_id,
                "slug": slug or project_id,
                "icon_url": icon_url
            })

            if hasattr(self, "_mod_cache"):
                self._mod_cache.clear()
            self.root.after(0, self.actualizar_lista_mods)
        except Exception as e:
            print(f"Error descargando dep {title}: {e}")

    # ──────────────────────────────────────────────
    # VISTA: MODPACKS
    # ──────────────────────────────────────────────
    def _build_vista_modpacks(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.vistas["modpacks"] = f

        hdr = ctk.CTkFrame(f, fg_color="transparent")
        hdr.pack(fill="x", padx=30, pady=(25, 6))
        ctk.CTkLabel(hdr, text=self.t("modpacks_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkButton(hdr, text=self.t("install_modpack_btn"), font=FONT_LABEL_L,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, height=38,
                      corner_radius=R_FULL, command=self.instalar_modpack).pack(side="right")

        ctk.CTkLabel(f, text=self.t("modpacks_sub"),
                     font=FONT_BODY, text_color=TEXT_M).pack(anchor="w", padx=30, pady=(0, 14))

        self.scrollable_modpacks = ctk.CTkScrollableFrame(f, fg_color=BG_CARD, corner_radius=R_MD,
                                                          scrollbar_button_color=ACCENT)
        self.scrollable_modpacks.pack(fill="both", expand=True, padx=30, pady=(0, 8))

        self.lbl_modpack_status = ctk.CTkLabel(f, text="", font=FONT_BODY_S, text_color=TEXT_M)
        self.lbl_modpack_status.pack(padx=30, pady=(4, 2))

        self.progress_modpack = ctk.CTkProgressBar(f, progress_color=ACCENT, height=6, corner_radius=R_FULL)
        self.progress_modpack.pack(fill="x", padx=30, pady=(0, 14))
        self.progress_modpack.set(0)

    # ──────────────────────────────────────────────
    # VISTA: GESTOR DE SKINS
    # ──────────────────────────────────────────────
    def _dir_skin_perfil(self):
        perfil = self.config_data.get("active_profile", "Jugador")
        d = os.path.join(MINECRAFT_DIR, "profiles", perfil)
        os.makedirs(d, exist_ok=True)
        return d

    def _migrar_wardrobe_a_armario(self, perfil_root):
        """Convierte el armario exportado por versiones antiguas del launcher."""
        wardrobe_root = os.path.join(perfil_root, "wardrobe")
        wardrobe_meta = os.path.join(wardrobe_root, "meta.json")
        if not os.path.isfile(wardrobe_meta):
            return

        armario_root = os.path.join(perfil_root, "armario")
        armario_json = os.path.join(armario_root, "armario.json")
        os.makedirs(armario_root, exist_ok=True)
        entradas = []
        if os.path.isfile(armario_json):
            try:
                        with open(armario_json, encoding="utf-8") as archivo_json:
                            entradas = json.load(archivo_json)
                        if not isinstance(entradas, list):
                            entradas = []
            except (OSError, ValueError):
                entradas = []

        archivos_existentes = {e.get("archivo") for e in entradas if isinstance(e, dict)}
        try:
            with open(wardrobe_meta, encoding="utf-8") as archivo_meta:
                wardrobe_entries = json.load(archivo_meta)
        except (OSError, ValueError):
            return
        if not isinstance(wardrobe_entries, list):
            return

        for entrada in wardrobe_entries:
            if not isinstance(entrada, dict):
                continue
            archivo = str(entrada.get("file", "")).strip()
            if not archivo or archivo in archivos_existentes:
                continue
            src_skin = os.path.join(wardrobe_root, archivo)
            dst_skin = os.path.join(armario_root, archivo)
            if not os.path.isfile(src_skin):
                continue
            shutil.copy2(src_skin, dst_skin)
            entradas.append({
                "nombre": entrada.get("name", "Skin"),
                "archivo": archivo,
                "url": entrada.get("online_url", ""),
                "fecha": entrada.get("date", "")
            })
            archivos_existentes.add(archivo)

        entradas = self._normalizar_armario(entradas, perfil_root)
        with open(armario_json, "w", encoding="utf-8") as archivo_json:
            json.dump(entradas, archivo_json, ensure_ascii=False, indent=2)

    def _build_vista_skins(self):
        f = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.vistas["skins"] = f

        hdr = ctk.CTkFrame(f, fg_color="transparent")
        hdr.pack(fill="x", padx=30, pady=(25, 4))
        ctk.CTkLabel(hdr, text=self.t("skins_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(side="left")

        ctk.CTkLabel(f, text=self.t("skins_subtitle"),
                     font=FONT_BODY, text_color=TEXT_M).pack(anchor="w", padx=30, pady=(0, 14))

        # Tarjeta de gestión de perfil activo (Material 3 Profile Management)
        prof_card = ctk.CTkFrame(f, fg_color=BG_CARD, corner_radius=R_MD)
        prof_card.pack(fill="x", padx=30, pady=(0, 14))

        prof_row = ctk.CTkFrame(prof_card, fg_color="transparent")
        prof_row.pack(fill="x", padx=18, pady=12)

        ctk.CTkLabel(prof_row, text=self.t("usuario") + ":", font=FONT_SECTION, text_color=TEXT_M).pack(side="left", padx=(0, 10))

        self.combo_perfil = ctk.CTkComboBox(prof_row, state="readonly", font=FONT_BODY, height=32, width=170,
                                            command=self.al_cambiar_perfil,
                                            fg_color=BG_CARD2, button_color=ACCENT,
                                            button_hover_color=ACCENT_H, corner_radius=R_SM)
        self.combo_perfil.pack(side="left", padx=(0, 14))

        ico_add_p = obtener_icono_ctk(ICON_ADD, ACCENT_T, 16)
        ico_edit_p = obtener_icono_ctk(ICON_EDIT, TEXT_MAIN, 16)
        ico_del_p = obtener_icono_ctk(ICON_CLOSE, (DANGER[0], "#ff8888"), 16)

        ctk.CTkButton(prof_row, text="  " + self.t("alert_new_profile_title"), image=ico_add_p, compound="left",
                      height=32, fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, corner_radius=R_FULL,
                      font=FONT_LABEL_S, command=self.crear_perfil).pack(side="left", padx=3)
        ctk.CTkButton(prof_row, text="  " + self.t("alert_rename_title"), image=ico_edit_p, compound="left",
                      height=32, fg_color=SURFACE_HIGH, hover_color=BORDER_C, corner_radius=R_FULL,
                      font=FONT_LABEL_S, command=self.renombrar_perfil).pack(side="left", padx=3)
        ctk.CTkButton(prof_row, text="  " + self.t("alert_delete_profile_title"), image=ico_del_p, compound="left",
                      height=32, fg_color=DANGER_SOFT, hover_color=DANGER_SOFT_H, text_color=DANGER[1], corner_radius=R_FULL,
                      font=FONT_LABEL_S, command=self.eliminar_perfil).pack(side="left", padx=3)

        mid_f = ctk.CTkFrame(f, fg_color="transparent")
        mid_f.pack(fill="x", padx=30, pady=(0, 14))

        prev_card = ctk.CTkFrame(mid_f, fg_color=BG_CARD, corner_radius=12, width=200)
        prev_card.pack(side="left", fill="both", padx=(0, 12))

        ctk.CTkLabel(prev_card, text=self.t("char_preview"), font=FONT_SECTION, text_color=TEXT_M).pack(anchor="w", padx=14, pady=(12, 4))

        canvas_f = ctk.CTkFrame(prev_card, fg_color=BG_CARD2, corner_radius=8)
        canvas_f.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # Single label for the 3D render
        self.lbl_skin_front = ctk.CTkLabel(canvas_f, text="", font=FONT_CAPTION, text_color=TEXT_M)
        self.lbl_skin_front.pack(expand=True, padx=8, pady=12)
        # Keep lbl_skin_back as alias so _actualizar_preview_skin doesn't crash
        self.lbl_skin_back = self.lbl_skin_front

        # Rotation control row
        rot_row = ctk.CTkFrame(prev_card, fg_color="transparent")
        rot_row.pack(fill="x", padx=12, pady=(0, 10))

        # Left rotate button
        ctk.CTkButton(rot_row, text="◀", font=FONT_SECTION, width=36, height=30,
                      fg_color=BG_CARD2, hover_color=ACCENT, text_color=TEXT_MAIN,
                      corner_radius=8,
                      command=lambda: self._rotar_skin_3d(-1)).pack(side="left", padx=(0, 4))

        # Auto-rotate toggle
        self._skin_autorot_var = tk.BooleanVar(value=False)
        self._skin_autorot_btn = ctk.CTkButton(rot_row, text="↺ Auto", font=FONT_CAPTION,
                                               width=70, height=30,
                                               fg_color=BG_CARD2, hover_color=ACCENT,
                                               text_color=TEXT_MAIN, corner_radius=8,
                                               command=self._toggle_autorot_skin)
        self._skin_autorot_btn.pack(side="left", padx=(0, 4), expand=True, fill="x")

        # Right rotate button
        ctk.CTkButton(rot_row, text="▶", font=FONT_SECTION, width=36, height=30,
                      fg_color=BG_CARD2, hover_color=ACCENT, text_color=TEXT_MAIN,
                      corner_radius=8,
                      command=lambda: self._rotar_skin_3d(1)).pack(side="right")

        ctrl_card = ctk.CTkFrame(mid_f, fg_color=BG_CARD, corner_radius=12)
        ctrl_card.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(ctrl_card, text=self.t("skin_options"), font=FONT_SECTION, text_color=TEXT_M).pack(anchor="w", padx=18, pady=(12, 4))

        f_btn = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        f_btn.pack(fill="x", padx=18, pady=8)
        ctk.CTkLabel(f_btn, text=self.t("load_png"), font=FONT_BODY, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 4))

        btn_row = ctk.CTkFrame(f_btn, fg_color="transparent")
        btn_row.pack(fill="x")
        ctk.CTkButton(btn_row, text=self.t("select_png"), font=FONT_SECTION,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, height=36,
                      command=self.seleccionar_skin_local).pack(side="left", padx=(0, 8))

        f_net = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        f_net.pack(fill="x", padx=18, pady=8)
        ctk.CTkLabel(f_net, text=self.t("load_nick"), font=FONT_BODY, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 4))

        net_row = ctk.CTkFrame(f_net, fg_color="transparent")
        net_row.pack(fill="x")
        self.entry_skin_url = ctk.CTkEntry(net_row, placeholder_text=self.t("nick_ph"),
                                           font=FONT_BODY, height=36, fg_color=BG_CARD2)
        self.entry_skin_url.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(net_row, text=self.t("btn_load_nick"), font=FONT_SECTION,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, height=36, width=110,
                      command=self.aplicar_skin_url).pack(side="right")

        f_model = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        f_model.pack(fill="x", padx=18, pady=12)
        ctk.CTkLabel(f_model, text=self.t("arm_model"), font=FONT_BODY, text_color=TEXT_MAIN).pack(side="left", padx=(0, 10))
        self.combo_skin_model = ctk.CTkComboBox(f_model, values=["classic (Steve)", "slim (Alex)"],
                                                state="readonly", font=FONT_BODY, height=32,
                                                fg_color=BG_CARD2, button_color=ACCENT,
                                                button_hover_color=ACCENT_H,
                                                command=self._al_cambiar_modelo_skin)
        self.combo_skin_model.pack(side="left")
        self.combo_skin_model.set("classic (Steve)")

        self.lbl_skin_status = ctk.CTkLabel(ctrl_card, text=self.t("skin_ready"), font=FONT_BODY_I, text_color=TEXT_M)
        self.lbl_skin_status.pack(anchor="w", padx=18, pady=(16, 2))

        self.progress_skin = ctk.CTkProgressBar(ctrl_card, progress_color=ACCENT, height=6)
        self.progress_skin.pack(fill="x", padx=18, pady=(0, 14))
        self.progress_skin.set(1.0)

        arm_hdr = ctk.CTkFrame(f, fg_color="transparent")
        arm_hdr.pack(fill="x", padx=30, pady=(10, 4))
        ctk.CTkLabel(arm_hdr, text=self.t("wardrobe_title"), font=FONT_TITLE_S, text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(arm_hdr, text=self.t("wardrobe_sub"),
                     font=FONT_CAPTION, text_color=TEXT_M).pack(side="left", padx=(10, 0))

        self.scrollable_armario = ctk.CTkScrollableFrame(f, fg_color=BG_CARD, corner_radius=12,
                                                         height=220, scrollbar_button_color=ACCENT)
        self.scrollable_armario.pack(fill="x", padx=30, pady=(0, 14))

    def _render_skin_iso3d(self, skin_path, angle=0, scale=3):
        """
        Renders a pseudo-3D isometric Minecraft character from the skin texture.
        angle: 0=front, 1=right, 2=back, 3=left (90-degree steps)
        scale: pixels per skin pixel
        Returns a PIL RGBA Image.
        """
        try:
            if skin_path and os.path.isfile(skin_path):
                img = Image.open(skin_path).convert("RGBA")
            else:
                img = Image.new("RGBA", (64, 64), (80, 90, 115, 255))

            w, h = img.size
            is_1_8 = (h == 64)

            # ── Skin UV regions (x,y,w,h) in skin pixels ──
            # Format: (left, top, right, bottom) for img.crop()
            UV = {
                # HEAD (8x8 box at pixel offset 0,0)
                "head_top":    (8,  0, 16, 8),
                "head_front":  (8,  8, 16, 16),
                "head_right":  (0,  8,  8, 16),
                "head_left":   (16, 8, 24, 16),
                "head_back":   (24, 8, 32, 16),
                "head_bot":    (16, 0, 24, 8),
                # HEAD OVERLAY (hat)
                "hat_top":     (40, 0, 48,  8),
                "hat_front":   (40, 8, 48, 16),
                "hat_right":   (32, 8, 40, 16),
                "hat_left":    (48, 8, 56, 16),
                "hat_back":    (56, 8, 64, 16),
                # TORSO (8w x 12h)
                "torso_top":   (20, 16, 28, 20),
                "torso_front": (20, 20, 28, 32),
                "torso_right": (16, 20, 20, 32),
                "torso_left":  (28, 20, 32, 32),
                "torso_back":  (32, 20, 40, 32),
                # RIGHT ARM (classic: 4w x 12h)
                "rarm_top":    (44, 16, 48, 20),
                "rarm_front":  (44, 20, 48, 32),
                "rarm_right":  (40, 20, 44, 32),
                "rarm_left":   (48, 20, 52, 32),
                "rarm_back":   (52, 20, 56, 32),
                # LEFT ARM (1.8+: 4w x 12h)
                "larm_top":    (36, 48, 40, 52),
                "larm_front":  (36, 52, 40, 64),
                "larm_right":  (32, 52, 36, 64),
                "larm_left":   (40, 52, 44, 64),
                "larm_back":   (44, 52, 48, 64),
                # RIGHT LEG (4w x 12h)
                "rleg_top":    (4,  16,  8, 20),
                "rleg_front":  (4,  20,  8, 32),
                "rleg_right":  (0,  20,  4, 32),
                "rleg_left":   (8,  20, 12, 32),
                "rleg_back":   (12, 20, 16, 32),
                # LEFT LEG (1.8+: 4w x 12h)
                "lleg_top":    (20, 48, 24, 52),
                "lleg_front":  (20, 52, 24, 64),
                "lleg_right":  (16, 52, 20, 64),
                "lleg_left":   (24, 52, 28, 64),
                "lleg_back":   (28, 52, 32, 64),
            }

            def face(key):
                """Crop a face from the skin, return RGBA image."""
                box = UV[key]
                return img.crop(box).convert("RGBA")

            def shade(pil_img, factor):
                """Multiply RGB channels by factor (0..1) for shading."""
                r, g, b, a = pil_img.split()
                r = r.point(lambda x: int(x * factor))
                g = g.point(lambda x: int(x * factor))
                b = b.point(lambda x: int(x * factor))
                return Image.merge("RGBA", (r, g, b, a))

            # ── Isometric projection helpers ──
            # We project a W x H block face onto a parallelogram.
            # Top face:   rhombus (lighter)
            # Front face: straight quad (medium)
            # Side face:  skewed quad (darker)
            #
            # Isometric: each pixel moves (1,-0.5) for X-axis, (0,1) for Y-axis
            # We use a simpler "cabinet" projection:
            #   Front face: pixel at (x,y) -> canvas (ox+x, oy+y)
            #   Right face: pixel at (x,y) -> canvas (ox+W+x*0.5, oy+x*0.5+y)
            #   Top face:   pixel at (x,y) -> canvas (ox+x+y*0.5, oy-H_top+y*0.5)

            def draw_front_face(canvas, src_img, ox, oy, W, H, shade_f=1.0):
                """Draw a front-facing rectangle. W,H in canvas pixels."""
                raw = src_img.resize((W, H), Image.Resampling.NEAREST)
                if shade_f != 1.0:
                    raw = shade(raw, shade_f)
                canvas.paste(raw, (ox, oy), raw)

            def draw_side_face(canvas, src_img, ox, oy, W, H, depth, shade_f=0.7):
                """
                Draw a right-side face with cabinet projection.
                W = face width in skin pixels (will be projected to depth*scale//2 wide on canvas)
                H = face height in canvas pixels
                depth = depth of the block in skin pixels
                """
                proj_w = max(1, depth * scale // 2)
                proj_h = H
                raw = src_img.resize((depth * scale, proj_h), Image.Resampling.NEAREST)
                if shade_f != 1.0:
                    raw = shade(raw, shade_f)
                # Shear the side face: each row shifts right by 0.5 pixel per row going up
                sheared = Image.new("RGBA", (proj_w + proj_h // 2, proj_h), (0, 0, 0, 0))
                for row in range(proj_h):
                    shift = (proj_h - 1 - row) // 2
                    row_img = raw.crop((0, row, depth * scale, row + 1))
                    row_img = row_img.resize((proj_w, 1), Image.Resampling.NEAREST)
                    sheared.paste(row_img, (shift, row), row_img)
                canvas.paste(sheared, (ox, oy), sheared)

            def draw_top_face(canvas, src_img, ox, oy, W, D, shade_f=1.1):
                """
                Draw a top face (rhombus-like) with cabinet projection.
                W = block width in skin pixels, D = block depth in skin pixels
                """
                proj_w = W * scale
                proj_d = max(1, D * scale // 2)
                raw = src_img.resize((proj_w, D * scale), Image.Resampling.NEAREST)
                # Shear top face: each column shifts up by 0.5px per column
                top_img = Image.new("RGBA", (proj_w + proj_d, proj_d + 1), (0, 0, 0, 0))
                for col in range(proj_w):
                    shift = (proj_w - 1 - col) // 2
                    col_strip = raw.crop((col, 0, col + 1, D * scale))
                    col_strip = col_strip.resize((1, proj_d), Image.Resampling.NEAREST)
                    if shade_f > 1.0:
                        r2, g2, b2, a2 = col_strip.split()
                        r2 = r2.point(lambda x: min(255, int(x * shade_f)))
                        g2 = g2.point(lambda x: min(255, int(x * shade_f)))
                        b2 = b2.point(lambda x: min(255, int(x * shade_f)))
                        col_strip = Image.merge("RGBA", (r2, g2, b2, a2))
                    top_img.paste(col_strip, (col, proj_d - shift - 1), col_strip)
                canvas.paste(top_img, (ox, oy - proj_d), top_img)

            # ── Body part dimensions (in skin pixels) ──
            HEAD_W, HEAD_H, HEAD_D = 8, 8, 8
            TORSO_W, TORSO_H, TORSO_D = 8, 12, 4
            ARM_W, ARM_H, ARM_D = 4, 12, 4
            LEG_W, LEG_H, LEG_D = 4, 12, 4
            # Gap between legs
            LEG_GAP = 0

            S = scale

            # Canvas size: wide enough for character + side projection
            depth_offset = max(HEAD_D, TORSO_D) * S // 2  # extra width for side faces
            top_offset   = HEAD_D * S // 2  # extra height for top faces

            cw = TORSO_W * S + depth_offset + 6 * S  # total canvas width
            # Total height: head(8) + torso(12) + leg(12) + top offset
            total_body_h = (HEAD_H + TORSO_H + LEG_H) * S
            ch = total_body_h + top_offset + 4 * S

            canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))

            # ── Origin: where front-left corner of torso starts ──
            # Center the torso horizontally
            torso_x = (cw - TORSO_W * S - depth_offset) // 2
            torso_y = top_offset + HEAD_H * S

            # rotate UV faces based on angle:
            # angle 0 = front, 1 = right (90° CW), 2 = back, 3 = left
            def rotated_faces(prefix, angle):
                """Return (front_key, side_key, top_key) for a given angle."""
                sides = ["front", "left", "back", "right"]
                faces_cycle = [sides[i % 4] for i in range(angle, angle + 4)]
                return (
                    prefix + "_" + faces_cycle[0],   # front visible face
                    prefix + "_" + faces_cycle[1],   # right side visible face
                    prefix + "_top",                  # top always same
                )

            def draw_block(prefix, ox, oy, W, H, D):
                """Draw a full block (front + side + top) at canvas position (ox,oy)."""
                front_key, side_key, top_key = rotated_faces(prefix, angle)
                # Front face
                front_img_src = face(front_key)
                # Overlay (hat on head) – merge if hat exists
                if prefix == "head" and angle < 2:
                    try:
                        hat_front = face("hat_" + front_key.split("_")[1])
                        # Composite hat over head
                        merged = front_img_src.copy()
                        merged.paste(hat_front, (0, 0), hat_front)
                        front_img_src = merged
                    except Exception:
                        pass
                draw_front_face(canvas, front_img_src, ox, oy, W * S, H * S)
                # Side face (right)
                side_img_src = face(side_key)
                draw_side_face(canvas, side_img_src, ox + W * S, oy, D, H * S, D)
                # Top face
                top_img_src = face(top_key)
                draw_top_face(canvas, top_img_src, ox, oy, W, D)

            # ── Draw body parts from bottom to top ──
            # RIGHT LEG
            rleg_x = torso_x
            rleg_y = torso_y + TORSO_H * S
            draw_block("rleg", rleg_x, rleg_y, LEG_W, LEG_H, LEG_D)

            # LEFT LEG
            lleg_prefix = "lleg" if is_1_8 else "rleg"
            lleg_x = torso_x + (LEG_W + LEG_GAP) * S
            lleg_y = rleg_y
            draw_block(lleg_prefix, lleg_x, lleg_y, LEG_W, LEG_H, LEG_D)

            # TORSO
            draw_block("torso", torso_x, torso_y, TORSO_W, TORSO_H, TORSO_D)

            # RIGHT ARM (left of torso)
            rarm_x = torso_x - ARM_W * S
            rarm_y = torso_y
            draw_block("rarm", rarm_x, rarm_y, ARM_W, ARM_H, ARM_D)

            # LEFT ARM (right of torso)
            larm_prefix = "larm" if is_1_8 else "rarm"
            larm_x = torso_x + TORSO_W * S
            larm_y = torso_y
            draw_block(larm_prefix, larm_x, larm_y, ARM_W, ARM_H, ARM_D)

            # HEAD (centered over torso)
            head_x = torso_x - (HEAD_W - TORSO_W) * S // 2
            head_y = torso_y - HEAD_H * S
            draw_block("head", head_x, head_y, HEAD_W, HEAD_H, HEAD_D)

            # Crop to actual content bounding box
            bbox = canvas.getbbox()
            if bbox:
                canvas = canvas.crop(bbox)

            return canvas

        except Exception as e:
            print("Error render 3D skin:", e)
            import traceback; traceback.print_exc()
            blank = Image.new("RGBA", (120, 200), (60, 60, 80, 100))
            return blank

    def _generar_preview_skin_2d(self, skin_path, scale=6):
        try:
            cache_key = (skin_path or "__default__", scale)
            mtime = os.path.getmtime(skin_path) if skin_path and os.path.exists(skin_path) else None
            cached = self._skin_preview_cache.get(cache_key)
            if cached and cached[0] == mtime:
                return cached[1], cached[2]

            if skin_path and os.path.exists(skin_path):
                img = Image.open(skin_path).convert("RGBA")
            else:
                img = Image.new("RGBA", (64, 64), (80, 80, 100, 255))

            w, h = img.size

            # Frente
            front = Image.new("RGBA", (16 * scale, 32 * scale), (0, 0, 0, 0))
            def p_front(box, pos):
                bw = (box[2] - box[0]) * scale
                bh = (box[3] - box[1]) * scale
                part = img.crop(box).resize((bw, bh), Image.Resampling.NEAREST)
                front.paste(part, (pos[0] * scale, pos[1] * scale), part)

            p_front((8, 8, 16, 16), (4, 0))
            p_front((40, 8, 48, 16), (4, 0))
            p_front((20, 20, 28, 32), (4, 8))
            p_front((20, 36, 28, 48), (4, 8))
            p_front((44, 20, 48, 32), (0, 8))
            p_front((44, 36, 48, 48), (0, 8))
            if h == 64:
                p_front((36, 52, 40, 64), (12, 8))
                p_front((48, 52, 52, 64), (12, 8))
            else:
                p_front((44, 20, 48, 32), (12, 8))
            p_front((4, 20, 8, 32), (4, 20))
            p_front((4, 36, 8, 48), (4, 20))
            if h == 64:
                p_front((20, 52, 24, 64), (8, 20))
                p_front((4, 52, 8, 64), (8, 20))
            else:
                p_front((4, 20, 8, 32), (8, 20))

            # Espalda
            back = Image.new("RGBA", (16 * scale, 32 * scale), (0, 0, 0, 0))
            def p_back(box, pos):
                bw = (box[2] - box[0]) * scale
                bh = (box[3] - box[1]) * scale
                part = img.crop(box).resize((bw, bh), Image.Resampling.NEAREST)
                back.paste(part, (pos[0] * scale, pos[1] * scale), part)

            p_back((24, 8, 32, 16), (4, 0))
            p_back((56, 8, 64, 16), (4, 0))
            p_back((32, 20, 40, 32), (4, 8))
            p_back((32, 36, 40, 48), (4, 8))
            p_back((52, 20, 56, 32), (12, 8))
            p_back((52, 36, 56, 48), (12, 8))
            if h == 64:
                p_back((44, 52, 48, 64), (0, 8))
                p_back((56, 52, 60, 64), (0, 8))
            else:
                p_back((52, 20, 56, 32), (0, 8))
            p_back((12, 20, 16, 32), (8, 20))
            p_back((12, 36, 16, 48), (8, 20))
            if h == 64:
                p_back((28, 52, 32, 64), (4, 20))
                p_back((12, 52, 16, 64), (4, 20))
            else:
                p_back((12, 20, 16, 32), (4, 20))

            self._skin_preview_cache[cache_key] = (mtime, front, back)
            return front, back
        except Exception as e:
            print("Error generando preview skin:", e)
            empty = Image.new("RGBA", (96, 192), (60, 60, 80, 255))
            return empty, empty

    def _actualizar_preview_skin(self):
        d_prof = self._dir_skin_perfil()
        skin_path = os.path.join(d_prof, "skin.png")

        render_3d = self._render_skin_iso3d(skin_path, angle=getattr(self, "_skin_3d_angle", 0), scale=4)
        ctk_render = ctk.CTkImage(light_image=render_3d, dark_image=render_3d, size=render_3d.size)

        self.lbl_skin_front._img_ref = ctk_render
        self.lbl_skin_front.configure(image=ctk_render, text="")

        self._actualizar_avatar_perfil()

    def _rotar_skin_3d(self, delta):
        """Rotate the 3D skin preview by delta steps (1=right, -1=left)."""
        self._skin_3d_angle = (getattr(self, "_skin_3d_angle", 0) + delta) % 4
        self._actualizar_preview_skin()

    def _toggle_autorot_skin(self):
        """Toggle auto-rotation of the 3D skin."""
        current = getattr(self, "_skin_autorot_active", False)
        self._skin_autorot_active = not current
        if self._skin_autorot_active:
            self._skin_autorot_btn.configure(fg_color=ACCENT, text_color=ACCENT_T)
            self._autorot_tick()
        else:
            self._skin_autorot_btn.configure(fg_color=BG_CARD2, text_color=TEXT_MAIN)

    def _autorot_tick(self):
        """Advance auto-rotation one step and schedule next tick."""
        if not getattr(self, "_skin_autorot_active", False): return
        if getattr(self, "vista_actual", None) != "skins": return
        self._rotar_skin_3d(1)
        self.root.after(700, self._autorot_tick)

    def seleccionar_skin_local(self):
        if hasattr(self, "sound"): self.sound.play("click")
        path = filedialog.askopenfilename(
            title="Seleccionar Skin PNG",
            filetypes=[("Imagen PNG", "*.png"), ("Todos los archivos", "*.*")]
        )
        if not path: return

        threading.Thread(target=self._hilo_subir_y_sincronizar_skin, args=(path, None), daemon=True).start()

    def aplicar_skin_url(self):
        if hasattr(self, "sound"): self.sound.play("click")
        val = self.entry_skin_url.get().strip()
        if not val: return
        if val.startswith("http://") or val.startswith("https://") or "/" in val or "\\" in val:
            messagebox.showwarning(self.t("alert_nick_title"), self.t("alert_nick_only"))
            return
        threading.Thread(target=self._hilo_subir_y_sincronizar_skin, args=(None, val), daemon=True).start()

    def _dir_armario(self):
        d = os.path.join(self._dir_skin_perfil(), "armario")
        os.makedirs(d, exist_ok=True)
        return d

    def _cargar_armario(self):
        path = os.path.join(self._dir_armario(), "armario.json")
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    entradas = json.load(f)
                normalizadas = self._normalizar_armario(entradas)
                if normalizadas != entradas:
                    self._guardar_armario_json(normalizadas)
                return normalizadas
            except Exception: pass
        return []

    def _normalizar_armario(self, entradas, perfil_root=None):
        """Elimina entradas repetidas por archivo o por contenido de imagen."""
        if not isinstance(entradas, list):
            return []
        armario_dir = os.path.join(perfil_root, "armario") if perfil_root else self._dir_armario()
        resultado = []
        vistos_archivos = set()
        vistos_hash = {}

        def calidad(entry):
            nombre = str(entry.get("nombre", "")).strip().lower()
            archivo = os.path.splitext(os.path.basename(str(entry.get("archivo", ""))))[0].lower()
            return int(bool(nombre and nombre != archivo and nombre != "skin"))

        for entrada in entradas:
            if not isinstance(entrada, dict):
                continue
            archivo = os.path.basename(str(entrada.get("archivo", "")).strip())
            if not archivo or archivo in vistos_archivos:
                continue
            candidato = dict(entrada)
            candidato["archivo"] = archivo
            ruta = os.path.join(armario_dir, archivo)
            digest = None
            try:
                if os.path.isfile(ruta):
                    sha = hashlib.sha256()
                    with open(ruta, "rb") as imagen:
                        for bloque in iter(lambda: imagen.read(1024 * 1024), b""):
                            sha.update(bloque)
                    digest = sha.hexdigest()
            except OSError:
                pass

            if digest and digest in vistos_hash:
                pos = vistos_hash[digest]
                if calidad(candidato) > calidad(resultado[pos]):
                    resultado[pos] = candidato
                vistos_archivos.add(archivo)
                continue

            vistos_archivos.add(archivo)
            if digest:
                vistos_hash[digest] = len(resultado)
            resultado.append(candidato)
        return resultado

    def _guardar_armario_json(self, entradas):
        path = os.path.join(self._dir_armario(), "armario.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entradas, f, ensure_ascii=False, indent=2)

    def _guardar_en_armario(self, nombre, src_png, online_url):
        try:
            d = self._dir_armario()
            entradas = self._cargar_armario()
            idx = len(entradas)
            dest = os.path.join(d, f"skin_{idx}.png")
            if src_png and os.path.exists(src_png):
                shutil.copy(src_png, dest)
            entradas.append({
                "nombre": nombre,
                "archivo": f"skin_{idx}.png",
                "url": online_url or "",
                "fecha": datetime.now().strftime("%Y-%m-%d")
            })
            self._guardar_armario_json(entradas)
            self.root.after(0, self._actualizar_vista_armario)
        except Exception as e:
            print("Error guardando en armario:", e)

    def _actualizar_vista_armario(self):
        for w in self.scrollable_armario.winfo_children():
            w.destroy()
        entradas = self._cargar_armario()
        if not entradas:
            ctk.CTkLabel(self.scrollable_armario,
                         text="No hay skins guardadas. Aplica una skin y guarda en el armario.",
                         font=FONT_BODY_I, text_color=TEXT_M).pack(pady=20)
            return
        for i, entry in enumerate(entradas):
            self._crear_tarjeta_armario(i, entry)

    def _crear_tarjeta_armario(self, idx, entry):
        d = self._dir_armario()
        skin_path = os.path.join(d, entry.get("archivo", ""))
        card = ctk.CTkFrame(self.scrollable_armario, fg_color=BG_CARD2, corner_radius=10)
        card.pack(side="left", padx=6, pady=6)

        ph = ctk.CTkImage(Image.new("RGBA", (48, 96), (20, 20, 36, 255)), size=(48, 96))
        lbl_prev = ctk.CTkLabel(card, image=ph, text="", cursor="hand2")
        lbl_prev.pack(padx=10, pady=(10, 4))
        lbl_prev._img_ref = ph

        def _cargar_thumb(sp=skin_path, lbl=lbl_prev):
            try:
                fi, _ = self._generar_preview_skin_2d(sp, scale=3)
                ctk_fi = ctk.CTkImage(light_image=fi, dark_image=fi, size=fi.size)
                def _set(img=ctk_fi, l=lbl):
                    l._img_ref = img
                    l.configure(image=img)
                self.root.after(0, _set)
            except Exception: pass
        threading.Thread(target=_cargar_thumb, daemon=True).start()

        ctk.CTkLabel(card, text=entry.get("nombre", "Skin")[:14],
                     font=FONT_CAPTION_B, text_color=TEXT_MAIN).pack()
        ctk.CTkLabel(card, text=entry.get("fecha", ""),
                     font=FONT_CAPTION_S, text_color=TEXT_M).pack(pady=(0, 4))

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(pady=(0, SPACE_SM))
        ctk.CTkButton(btns, text=ICON_EDIT, font=FONT_ICON_SM,
                      fg_color=SURFACE_HIGH, hover_color=BORDER_C,
                      height=28, width=28, corner_radius=R_SM,
                      command=lambda i=idx: self._renombrar_del_armario(i)).pack(side="left", padx=SPACE_XS)
        ctk.CTkButton(btns, text=self.t("btn_use"), font=FONT_LABEL_S,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                      height=28, width=54, corner_radius=R_SM,
                      command=lambda e=entry: self._aplicar_desde_armario(e)).pack(side="left", padx=SPACE_XS)
        ctk.CTkButton(btns, text=ICON_DELETE, font=FONT_ICON_SM,
                      fg_color=DANGER_SOFT, hover_color=DANGER_SOFT_H,
                      height=28, width=28, corner_radius=R_SM,
                      command=lambda i=idx: self._eliminar_del_armario(i)).pack(side="left", padx=SPACE_XS)

        lbl_prev.bind("<Button-1>", lambda e, en=entry: self._aplicar_desde_armario(en))

    def _aplicar_desde_armario(self, entry):
        if hasattr(self, "sound"): self.sound.play("select")
        d = self._dir_armario()
        skin_path = os.path.join(d, entry.get("archivo", ""))
        online_url = entry.get("url", "")
        threading.Thread(target=self._hilo_subir_y_sincronizar_skin,
                         args=(skin_path if os.path.exists(skin_path) else None, online_url or None),
                         kwargs={"desde_armario": True},
                         daemon=True).start()

    def _eliminar_del_armario(self, idx):
        if hasattr(self, "sound"): self.sound.play("click")
        try:
            d = self._dir_armario()
            entradas = self._cargar_armario()
            if 0 <= idx < len(entradas):
                archivo = entradas[idx].get("archivo", "")
                try: os.remove(os.path.join(d, archivo))
                except Exception: pass
                entradas.pop(idx)
                self._guardar_armario_json(entradas)
                self._actualizar_vista_armario()
        except Exception as e:
            print("Error eliminando del armario:", e)

    def _renombrar_del_armario(self, idx):
        """Permite cambiar solo el nombre visible de una skin guardada."""
        if hasattr(self, "sound"): self.sound.play("click")
        try:
            entradas = self._cargar_armario()
            if not 0 <= idx < len(entradas):
                return
            actual = entradas[idx].get("nombre", "Skin")
            dialogo = ctk.CTkInputDialog(
                text=f"{self.t('wardrobe_rename_msg')}\n\n{actual}",
                title=self.t("wardrobe_rename_title"))
            nuevo = dialogo.get_input()
            if nuevo and nuevo.strip():
                entradas[idx]["nombre"] = nuevo.strip()
                self._guardar_armario_json(entradas)
                self._actualizar_vista_armario()
        except Exception as e:
            print("Error renombrando skin:", e)

    def _dialogo_guardar_armario(self, src_png, online_url):
        top = ctk.CTkToplevel(self.root)
        top.title(self.t("wardrobe_save_title"))
        top.geometry("340x160")
        top.grab_set()
        top.configure(fg_color=BG_DARK)
        animar_entrada_modal(top)
        ctk.CTkLabel(top, text=self.t("wardrobe_save_title"),
                     font=FONT_SECTION, text_color=TEXT_MAIN).pack(pady=(16, 6), padx=20, anchor="w")
        ctk.CTkLabel(top, text=self.t("wardrobe_save_msg"),
                     font=FONT_BODY, text_color=TEXT_M).pack(padx=20, anchor="w")
        entry_n = ctk.CTkEntry(top, placeholder_text="Ej. Mi Skin Steve",
                               font=FONT_BODY, height=34, fg_color=BG_CARD2)
        entry_n.pack(fill="x", padx=20, pady=8)
        entry_n.focus()

        def guardar():
            nombre = entry_n.get().strip() or "Skin"
            top.destroy()
            threading.Thread(target=self._guardar_en_armario, args=(nombre, src_png, online_url), daemon=True).start()

        entry_n.bind("<Return>", lambda e: guardar())
        ctk.CTkButton(top, text="\U0001f4be Guardar", font=FONT_SECTION,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, height=32,
                      command=guardar).pack(padx=20, pady=(0, 14), fill="x")

    def _al_cambiar_modelo_skin(self, val):
        if hasattr(self, "sound"): self.sound.play("click")
        perfil = self.config_data.get("active_profile", "Jugador")
        self.config_data.setdefault("profiles", {}).setdefault(perfil, {})["skin_model"] = val
        guardar_configuracion(self.config_data)

    def _hilo_subir_y_sincronizar_skin(self, path_local, nick_or_url, desde_armario=False):
        perfil = self.config_data.get("active_profile", "Jugador")
        d_prof = self._dir_skin_perfil()
        dest_skin = os.path.join(d_prof, "skin.png")

        def set_st(t, prog):
            self.root.after(0, lambda: self.lbl_skin_status.configure(text=t))
            self.root.after(0, lambda: self.progress_skin.set(prog))

        try:
            set_st("Procesando skin local...", 0.2)
            online_url = None

            if path_local and os.path.exists(path_local):
                shutil.copy(path_local, dest_skin)
                set_st("Subiendo skin a servidor multijugador...", 0.5)
                try:
                    with open(dest_skin, "rb") as f_up:
                        r = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f_up}, timeout=10)
                        if r.status_code == 200:
                            data = r.json()
                            raw_url = data.get("data", {}).get("url", "")
                            if raw_url:
                                online_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                except Exception as e:
                    print("Advertencia subida online:", e)
            elif nick_or_url:
                if nick_or_url.startswith("http://") or nick_or_url.startswith("https://"):
                    online_url = nick_or_url
                    try:
                        r = requests.get(online_url, timeout=8)
                        if r.status_code == 200:
                            with open(dest_skin, "wb") as f_out:
                                f_out.write(r.content)
                    except Exception: pass
                else:
                    try:
                        r = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{nick_or_url}", timeout=6)
                        if r.status_code == 200:
                            uuid = r.json().get("id")
                            skin_dl = f"https://crafatar.com/skins/{uuid}"
                            online_url = skin_dl
                            r_img = requests.get(skin_dl, timeout=8)
                            if r_img.status_code == 200:
                                with open(dest_skin, "wb") as f_out:
                                    f_out.write(r_img.content)
                    except Exception: pass

            set_st("Configurando mod de skins...", 0.8)
            self._asegurar_mod_skin(d_prof)
            self._sincronizar_skin_activa_con_juego(d_prof, perfil)

            self.config_data.setdefault("profiles", {}).setdefault(perfil, {})["skin_url"] = online_url or ""
            guardar_configuracion(self.config_data)

            self.root.after(0, self._actualizar_preview_skin)
            self.root.after(0, self._actualizar_vista_armario)
            set_st("¡Skin configurada con éxito en local y multijugador!", 1.0)
            self.root.after(0, lambda: self.sound.play("success"))
            if not desde_armario:
                dest_skin_final = os.path.join(d_prof, "skin.png")
                self.root.after(400, lambda u=online_url, sp=dest_skin_final: self._dialogo_guardar_armario(sp, u))
        except Exception as ex:
            set_st(f"Error al configurar skin: {ex}", 0.0)

    def _sincronizar_skin_activa_con_juego(self, game_dir, perfil):
        try:
            d_prof = os.path.join(MINECRAFT_DIR, "profiles", perfil)
            skin_src = os.path.join(d_prof, "skin.png")
            if not os.path.exists(skin_src):
                return

            csl_base = os.path.join(game_dir, "CustomSkinLoader")
            csl_skins = os.path.join(csl_base, "LocalSkin", "skins")
            csl_caches = os.path.join(csl_base, "caches")
            os.makedirs(csl_skins, exist_ok=True)

            shutil.copy(skin_src, os.path.join(csl_skins, f"{perfil}.png"))
            shutil.copy(skin_src, os.path.join(csl_skins, f"{perfil.lower()}.png"))
            shutil.copy(skin_src, os.path.join(csl_skins, "default.png"))

            if os.path.exists(csl_caches):
                try:
                    for cf in os.listdir(csl_caches):
                        fp = os.path.join(csl_caches, cf)
                        if os.path.isfile(fp):
                            os.remove(fp)
                        elif os.path.isdir(fp):
                            shutil.rmtree(fp, ignore_errors=True)
                except Exception:
                    pass

            csl_cfg_path = os.path.join(csl_base, "CustomSkinLoader.json")
            csl_cfg = {
                "version": "15.0.1",
                "buildNumber": 40,
                "loadlist": [
                    {
                        "name": "LocalSkin",
                        "type": "Legacy",
                        "checkPNG": False,
                        "skin": "LocalSkin/skins/{USERNAME}.png",
                        "model": "auto"
                    },
                    {
                        "name": "LocalSkinLower",
                        "type": "Legacy",
                        "checkPNG": False,
                        "skin": "LocalSkin/skins/{USERNAMELOWER}.png",
                        "model": "auto"
                    },
                    {
                        "name": "Mojang",
                        "type": "Mojang"
                    }
                ],
                "enableTransparentSkin": True,
                "forceLoadAllTextures": True,
                "enableCape": True,
                "cacheExpiry": 0,
                "forceDisableCache": True
            }
            try:
                with open(csl_cfg_path, "w", encoding="utf-8") as f_cfg:
                    json.dump(csl_cfg, f_cfg, indent=2)
            except Exception:
                pass

            ft_dir = os.path.join(game_dir, "config", "fabrictailor", "skins")
            os.makedirs(ft_dir, exist_ok=True)
            shutil.copy(skin_src, os.path.join(ft_dir, f"{perfil}.png"))
            shutil.copy(skin_src, os.path.join(ft_dir, f"{perfil.lower()}.png"))

            rp_base = os.path.join(game_dir, "resourcepacks", "LauncherSkin")
            rp_wide = os.path.join(rp_base, "assets", "minecraft", "textures", "entity", "player", "wide")
            rp_slim = os.path.join(rp_base, "assets", "minecraft", "textures", "entity", "player", "slim")
            rp_legacy = os.path.join(rp_base, "assets", "minecraft", "textures", "entity")
            os.makedirs(rp_wide, exist_ok=True)
            os.makedirs(rp_slim, exist_ok=True)
            os.makedirs(rp_legacy, exist_ok=True)

            with open(os.path.join(rp_base, "pack.mcmeta"), "w", encoding="utf-8") as f_mcm:
                json.dump({
                    "pack": {
                        "pack_format": 15,
                        "description": "Simple Launcher Skin"
                    }
                }, f_mcm, indent=2)

            shutil.copy(skin_src, os.path.join(rp_wide, "steve.png"))
            shutil.copy(skin_src, os.path.join(rp_slim, "alex.png"))
            shutil.copy(skin_src, os.path.join(rp_legacy, "steve.png"))
            shutil.copy(skin_src, os.path.join(rp_legacy, "alex.png"))

            opt_path = os.path.join(game_dir, "options.txt")
            if os.path.exists(opt_path):
                try:
                    with open(opt_path, "r", encoding="utf-8") as f_opt:
                        lines = f_opt.readlines()
                    new_lines = []
                    found_rp = False
                    for line in lines:
                        if line.startswith("resourcePacks:"):
                            found_rp = True
                            val_str = line[len("resourcePacks:"):].strip()
                            try:
                                rps = json.loads(val_str)
                                if "file/LauncherSkin" not in rps:
                                    rps.append("file/LauncherSkin")
                                new_lines.append(f"resourcePacks:{json.dumps(rps)}\n")
                            except Exception:
                                new_lines.append('resourcePacks:["vanilla","file/LauncherSkin"]\n')
                        else:
                            new_lines.append(line)
                    if not found_rp:
                        new_lines.append('resourcePacks:["vanilla","file/LauncherSkin"]\n')
                    with open(opt_path, "w", encoding="utf-8") as f_opt_out:
                        f_opt_out.writelines(new_lines)
                except Exception:
                    pass

        except Exception as e:
            print("Error sincronizando skin activa:", e)

    def _asegurar_mod_skin(self, game_dir=None):
        try:
            perfil = self.config_data.get("active_profile", "Jugador")
            if not game_dir:
                game_dir = os.path.join(MINECRAFT_DIR, "profiles", perfil)

            mods_slot = self._mods_dir()
            mods_gen = os.path.join(game_dir, "mods")
            os.makedirs(mods_slot, exist_ok=True)
            os.makedirs(mods_gen, exist_ok=True)

            for d in [mods_slot, mods_gen]:
                for f in os.listdir(d):
                    if f.endswith(".jar") and "fabrictailor" in f.lower():
                        try: os.remove(os.path.join(d, f))
                        except Exception: pass

            tiene_slot = any("customskinloader" in f.lower() for f in os.listdir(mods_slot) if f.endswith(".jar"))
            tiene_gen = any("customskinloader" in f.lower() for f in os.listdir(mods_gen) if f.endswith(".jar"))

            if not tiene_slot or not tiene_gen:
                print("Descargando e instalando CustomSkinLoader...")
                self._descargar_dep("customskinloader", "CustomSkinLoader")

                for item in os.listdir(mods_slot):
                    if item.endswith(".jar") and "customskinloader" in item.lower():
                        try:
                            shutil.copy(os.path.join(mods_slot, item), os.path.join(mods_gen, item))
                        except Exception: pass

            if hasattr(self, "fabric_var"):
                self.root.after(0, lambda: self.fabric_var.set(True))
        except Exception as e:
            print("Error asegurando mod de skins:", e)

    # ──────────────────────────────────────────────
    # VISTA: CAPTURAS DE PANTALLA
    # ──────────────────────────────────────────────
    def _dir_capturas(self):
        perfil = self.config_data.get("active_profile", "Jugador")
        d = os.path.join(MINECRAFT_DIR, "profiles", perfil, "screenshots")
        os.makedirs(d, exist_ok=True)
        return d

    def _build_vista_capturas(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.vistas["capturas"] = f

        hdr = ctk.CTkFrame(f, fg_color="transparent")
        hdr.pack(fill="x", padx=30, pady=(25, 6))
        ctk.CTkLabel(hdr, text=self.t("capturas_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(side="left")

        btns_hdr = ctk.CTkFrame(hdr, fg_color="transparent")
        btns_hdr.pack(side="right")

        ctk.CTkButton(btns_hdr, text=self.t("btn_refresh"), font=FONT_BODY, fg_color=BG_CARD2,
                      hover_color=BORDER_C, height=32, command=self.actualizar_galeria_capturas).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btns_hdr, text=self.t("open_screenshot_dir"), font=FONT_SECTION,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, height=36,
                      command=self.abrir_carpeta_capturas).pack(side="left")

        ctk.CTkLabel(f, text=self.t("capturas_sub"),
                     font=FONT_BODY, text_color=TEXT_M).pack(anchor="w", padx=30, pady=(0, 14))

        self.scrollable_capturas = ctk.CTkScrollableFrame(f, fg_color=BG_CARD, corner_radius=12,
                                                         scrollbar_button_color=ACCENT)
        self.scrollable_capturas.pack(fill="both", expand=True, padx=30, pady=(0, 14))

    def abrir_carpeta_capturas(self):
        if hasattr(self, "sound"): self.sound.play("click")
        try:
            d = self._dir_capturas()
            os.makedirs(d, exist_ok=True)
            os.startfile(d)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def actualizar_galeria_capturas(self):
        if hasattr(self, "sound"): self.sound.play("click")
        for w in self.scrollable_capturas.winfo_children():
            w.destroy()

        d = self._dir_capturas()
        archivos = []
        if os.path.exists(d):
            try:
                archivos = sorted(
                    [f for f in os.listdir(d) if f.lower().endswith((".png", ".jpg", ".jpeg"))],
                    key=lambda x: os.path.getmtime(os.path.join(d, x)), reverse=True
                )
            except Exception:
                pass

        if not archivos:
            ctk.CTkLabel(self.scrollable_capturas,
                         text=self.t("no_screenshots"),
                         font=FONT_BODY_M_I, text_color=TEXT_M).pack(pady=40)
            return

        COLS = 3
        for i in range(0, len(archivos), COLS):
            fila = ctk.CTkFrame(self.scrollable_capturas, fg_color="transparent")
            fila.pack(fill="x", padx=4, pady=4)

            batch = archivos[i:i + COLS]
            for fn in batch:
                path_img = os.path.join(d, fn)

                try:
                    mtime = os.path.getmtime(path_img)
                    fecha_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    fecha_str = self.t("unknown")

                try:
                    file_bytes = os.path.getsize(path_img)
                    if file_bytes >= 1024 * 1024:
                        tamano_str = f"{file_bytes / (1024*1024):.2f} MB"
                    else:
                        tamano_str = f"{file_bytes / 1024:.0f} KB"
                except Exception:
                    tamano_str = "?"

                card = ctk.CTkFrame(fila, fg_color=BG_CARD2, corner_radius=10)
                card.pack(side="left", expand=True, fill="both", padx=6)

                if not hasattr(self, "_placeholder_thumb"):
                    self._placeholder_thumb = ctk.CTkImage(Image.new("RGBA", (240, 135), (18, 18, 32, 255)), size=(240, 135))

                thumb_btn = ctk.CTkButton(card, text="", image=self._placeholder_thumb, fg_color=BG_CARD,
                                          hover_color=BG_CARD2, height=130, corner_radius=8,
                                          command=lambda p=path_img: self._abrir_visor_captura(p))
                thumb_btn.pack(fill="x", padx=8, pady=(8, 4))

                threading.Thread(target=self._hilo_cargar_miniatura_captura,
                                 args=(path_img, thumb_btn), daemon=True).start()

                info_f = ctk.CTkFrame(card, fg_color="transparent")
                info_f.pack(fill="x", padx=8, pady=(0, 4))

                d_name = fn[:22] + "..." if len(fn) > 25 else fn
                ctk.CTkLabel(info_f, text=d_name, font=FONT_CAPTION_B,
                             text_color=TEXT_MAIN, anchor="w").pack(anchor="w")
                ctk.CTkLabel(info_f, text=f"{fecha_str}  \u2022  {tamano_str}",
                             font=FONT_CAPTION_S, text_color=TEXT_M, anchor="w").pack(anchor="w")

                act_f = ctk.CTkFrame(card, fg_color="transparent")
                act_f.pack(fill="x", padx=8, pady=(2, 8))

                ctk.CTkButton(act_f, text=self.t("btn_view"), font=FONT_LABEL_S,
                              fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                              height=28, corner_radius=R_SM,
                              command=lambda p=path_img: self._abrir_visor_captura(p)).pack(
                                  side="left", expand=True, fill="x", padx=(0, SPACE_XS))

                ctk.CTkButton(act_f, text=self.t("copy_image"), font=FONT_BODY_S,
                              fg_color=SURFACE_HIGH, hover_color=BORDER_C,
                              height=28, corner_radius=R_SM, width=68,
                                  command=lambda p=path_img, fn2=fn: self._copiar_captura(p, fn2)).pack(
                                  side="left", padx=SPACE_XS)

                ctk.CTkButton(act_f, text=self.t("rename_image"), font=FONT_BODY_S,
                              fg_color=SURFACE_HIGH, hover_color=BORDER_C,
                              height=28, corner_radius=R_SM, width=78,
                              command=lambda p=path_img, fn2=fn: self._renombrar_captura(p, fn2)).pack(
                                  side="left", padx=SPACE_XS)

                ctk.CTkButton(act_f, text=ICON_DELETE, font=FONT_ICON_SM,
                              fg_color=DANGER_SOFT, hover_color=DANGER_SOFT_H,
                              height=28, corner_radius=R_SM, width=32,
                              command=lambda p=path_img, fn2=fn: self._eliminar_captura(p, fn2)).pack(
                                  side="right", padx=(SPACE_XS, 0))

            for _ in range(COLS - len(batch)):
                ctk.CTkFrame(fila, fg_color="transparent").pack(side="left", expand=True, fill="both", padx=6)

    def _hilo_cargar_miniatura_captura(self, path_img, btn_thumb):
        try:
            mtime = os.path.getmtime(path_img)
            cached = self._capture_thumb_cache.get(path_img)
            if cached and cached[0] == mtime:
                img = cached[1]
            else:
                img = Image.open(path_img).convert("RGBA")
                img.thumbnail((240, 135), Image.Resampling.LANCZOS)
                self._capture_thumb_cache[path_img] = (mtime, img)
            w, h = img.size

            def aplicar(pil_img=img, bw=w, bh=h):
                try:
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(bw, bh))
                    btn_thumb._img_ref = ctk_img
                    btn_thumb.configure(image=ctk_img, text="")
                except Exception as e:
                    print("Error aplicando miniatura:", e)

            self.root.after(0, aplicar)
        except Exception as e:
            print("Error cargando miniatura:", e)

    def _copiar_captura(self, path_img, filename):
        if hasattr(self, "sound"): self.sound.play("click")
        dest = filedialog.asksaveasfilename(
            title=self.t("copy_capture_title"),
            initialfile=filename,
            defaultextension=os.path.splitext(filename)[1],
            filetypes=[("Imagen PNG", "*.png"), ("Todos los archivos", "*.*")]
        )
        if not dest: return
        try:
            shutil.copy(path_img, dest)
            if hasattr(self, "sound"): self.sound.play("success")
            messagebox.showinfo(self.t("success_title"), self.t("capture_copied_msg", dest))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _eliminar_captura(self, path_img, filename):
        if hasattr(self, "sound"): self.sound.play("click")
        if messagebox.askyesno(self.t("confirm_title"), self.t("delete_capture_confirm", filename)):
            try:
                if os.path.exists(path_img):
                    os.remove(path_img)
                self.actualizar_galeria_capturas()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _renombrar_captura(self, path_img, filename):
        """Renombra una captura conservando su extensión y evitando colisiones."""
        actual = os.path.splitext(filename)[0]
        dialogo = ctk.CTkInputDialog(
            text=self.t("rename_capture_prompt", actual),
            title=self.t("rename_capture_title"))
        nuevo = dialogo.get_input()
        if not nuevo:
            return
        nuevo = "".join(c for c in nuevo.strip() if c.isalnum() or c in " .-_()[]").strip(" .")
        if not nuevo:
            return
        extension = os.path.splitext(filename)[1].lower()
        destino = os.path.join(os.path.dirname(path_img), nuevo + extension)
        if os.path.normcase(destino) != os.path.normcase(path_img) and os.path.exists(destino):
            messagebox.showwarning(self.t("alert_wait"), self.t("alert_file_exists"))
            return
        try:
            os.replace(path_img, destino)
            if hasattr(self, "_capture_thumb_cache"):
                self._capture_thumb_cache.pop(path_img, None)
            self.actualizar_galeria_capturas()
        except OSError as e:
            messagebox.showerror("Error", str(e))

    def _abrir_visor_captura(self, path_img):
        if hasattr(self, "sound"): self.sound.play("click")
        top = ctk.CTkToplevel(self.root)
        filename = os.path.basename(path_img)
        top.title(f"{self.t('screenshot_title')}: {filename}")
        top.geometry("900x620")
        top.grab_set()
        top.configure(fg_color=BG_DARK)
        animar_entrada_modal(top)

        hdr = ctk.CTkFrame(top, fg_color=BG_SIDE, height=44, corner_radius=0)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=filename, font=FONT_SECTION, text_color=TEXT_MAIN).pack(side="left", padx=16)

        img_container = ctk.CTkFrame(top, fg_color="#0a0a12", corner_radius=0)
        img_container.pack(fill="both", expand=True)

        lbl_img = ctk.CTkLabel(img_container, text=self.t("loading_hd"), font=FONT_BODY_M_I, text_color=TEXT_M)
        lbl_img.pack(fill="both", expand=True)

        def cargar_hd():
            try:
                img_orig = Image.open(path_img).convert("RGBA")
                w_orig, h_orig = img_orig.size
                ratio = min(860 / w_orig, 520 / h_orig)
                w_new, h_new = int(w_orig * ratio), int(h_orig * ratio)
                img_scaled = img_orig.resize((w_new, h_new), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img_scaled, dark_image=img_scaled, size=(w_new, h_new))
                self.root.after(0, lambda: lbl_img.configure(image=ctk_img, text=""))
            except Exception as e:
                self.root.after(0, lambda: lbl_img.configure(text=f"Error cargando imagen: {e}"))

        threading.Thread(target=cargar_hd, daemon=True).start()

        bbar = ctk.CTkFrame(top, fg_color=BG_SIDE, height=54, corner_radius=0)
        bbar.pack(fill="x", side="bottom")
        bbar.pack_propagate(False)

        inner_bbar = ctk.CTkFrame(bbar, fg_color="transparent")
        inner_bbar.pack(fill="both", expand=True, padx=16, pady=8)

        ctk.CTkButton(inner_bbar, text="Abrir archivo", font=FONT_BODY, fg_color=BG_CARD2,
                      hover_color=BORDER_C, height=34,
                      command=lambda: (hasattr(self, "sound") and self.sound.play("click"), os.startfile(path_img))).pack(side="left", padx=(0, 6))

        ctk.CTkButton(inner_bbar, text="Copiar a...", font=FONT_BODY, fg_color=BG_CARD2,
                      hover_color=BORDER_C, height=34,
                      command=lambda: self._copiar_captura(path_img, filename)).pack(side="left", padx=6)

        ctk.CTkButton(inner_bbar, text="Eliminar", font=FONT_SECTION, fg_color=DANGER_SOFT,
                      hover_color=DANGER_SOFT_H, height=34,
                      command=lambda: (top.destroy(), self._eliminar_captura(path_img, filename))).pack(side="left", padx=6)

        ctk.CTkButton(inner_bbar, text="Cerrar", font=FONT_BODY, fg_color=ACCENT,
                      hover_color=ACCENT_H, text_color=ACCENT_T, height=34, width=90,
                      command=lambda: (hasattr(self, "sound") and self.sound.play("click"), top.destroy())).pack(side="right")

    # ──────────────────────────────────────────────
    # VISTA: AJUSTES
    # ──────────────────────────────────────────────
    def _build_vista_ajustes(self):
        # Outer CTkFrame registered in vistas so pack_forget/pack works in mostrar_vista.
        # The inner CTkScrollableFrame provides scrolling for all settings cards.
        outer = ctk.CTkFrame(self.content, fg_color=SURFACE, corner_radius=0)
        self.vistas["ajustes"] = outer

        f = ctk.CTkScrollableFrame(outer, fg_color="transparent",
                                    scrollbar_fg_color=SURFACE_LOWEST,
                                    scrollbar_button_color=ACCENT,
                                    scrollbar_button_hover_color=ACCENT_H)
        f.pack(fill="both", expand=True)

        ctk.CTkLabel(f, text=self.t("ajustes_title"), font=FONT_TITLE, text_color=TEXT_MAIN).pack(anchor="w", padx=SPACE_2XL, pady=(SPACE_XL, SPACE_XS))
        ctk.CTkLabel(f, text=self.t("ajustes_subtitle"), font=FONT_BODY, text_color=TEXT_M).pack(anchor="w", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))

        # Idioma / Language
        lc = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        lc.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))
        ctk.CTkLabel(lc, text=self.t("language_title"), font=FONT_SECTION, text_color=TEXT_M).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))
        l_row = ctk.CTkFrame(lc, fg_color="transparent")
        l_row.pack(fill="x", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_MD))
        self.combo_idioma = ctk.CTkComboBox(l_row, values=["English", "Español", "Português", "Français"], state="readonly",
                                             font=FONT_BODY, height=36, width=170, corner_radius=R_SM,
                                             fg_color=SURFACE_HIGH, button_color=ACCENT, button_hover_color=ACCENT_H,
                                             command=self.al_cambiar_idioma)
        self.combo_idioma.pack(side="left")
        self.combo_idioma.set({"en": "English", "es": "Español", "pt": "Português", "fr": "Français"}.get(self.lang, "English"))
        ctk.CTkLabel(lc, text=self.t("languages_work_notice"), font=FONT_BODY_S,
                     text_color=TEXT_M).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_SM))

        # Color personalizado: la atmósfera completa del launcher se genera desde aquí
        ac = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        ac.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))
        ctk.CTkLabel(ac, text=self.t("accent_title"), font=FONT_SECTION,
                     text_color=TEXT_M).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))
        ctk.CTkLabel(ac, text=self.t("accent_subtitle"), font=FONT_BODY_S,
                     text_color=TEXT_M, wraplength=650).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_SM))
        ac_row = ctk.CTkFrame(ac, fg_color="transparent")
        ac_row.pack(fill="x", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_MD))
        color_actual = self.config_data.get("accent_color", "#72c3cb")
        ctk.CTkLabel(ac_row, text=color_actual.upper(), font=FONT_TITLE_S,
                     text_color=ACCENT_T, fg_color=ACCENT, corner_radius=R_SM,
                     width=110, height=36).pack(side="left", padx=(SPACE_NONE, SPACE_SM))
        ctk.CTkButton(ac_row, text=self.t("accent_choose"), font=FONT_LABEL_L,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                      height=36, corner_radius=R_FULL, command=self._cambiar_color_semilla).pack(side="left")

        # Carpeta del juego
        fc = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        fc.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))
        ctk.CTkLabel(fc, text=self.t("game_folder"), font=FONT_SECTION, text_color=TEXT_M).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))
        dr = ctk.CTkFrame(fc, fg_color="transparent")
        dr.pack(fill="x", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_MD))
        self.entry_dir = ctk.CTkEntry(dr, font=FONT_BODY, state="disabled", height=38, fg_color=SURFACE_HIGH, corner_radius=R_SM)
        self.entry_dir.pack(side="left", fill="x", expand=True, padx=(SPACE_NONE, SPACE_SM))
        self._actualizar_texto_ruta()
        ctk.CTkButton(dr, text=self.t("btn_change"), width=110, height=38, font=FONT_LABEL_L,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, corner_radius=R_FULL,
                      command=self.cambiar_directorio).pack(side="right")

        # Comportamiento
        bc = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        bc.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))
        ctk.CTkLabel(bc, text=self.t("behavior"), font=FONT_SECTION, text_color=TEXT_M).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))

        self.launcher_fs_var = tk.BooleanVar(value=self.is_launcher_fs)
        sw_fs = ctk.CTkCheckBox(bc, text=self.t("launcher_fs"),
                               variable=self.launcher_fs_var, font=FONT_BODY,
                               checkbox_width=20, checkbox_height=20, corner_radius=R_XS,
                               border_width=2, fg_color=ACCENT, hover_color=ACCENT_H,
                               command=lambda: self.toggle_launcher_fullscreen(self.launcher_fs_var.get()))
        sw_fs.pack(anchor="w", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_SM))

        self.auto_dep_var = tk.BooleanVar(value=self.config_data.get("auto_dependencias", False))
        sw_dep = ctk.CTkCheckBox(bc, text=self.t("auto_dep"),
                               variable=self.auto_dep_var, font=FONT_BODY,
                               checkbox_width=20, checkbox_height=20, corner_radius=R_XS,
                               border_width=2, fg_color=ACCENT, hover_color=ACCENT_H,
                               command=self._guardar_auto_dep)
        sw_dep.pack(anchor="w", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_SM))

        self.ui_sounds_var = tk.BooleanVar(value=self.config_data.get("ui_sounds", True))
        sw_snd = ctk.CTkCheckBox(bc, text=self.t("ui_sounds"),
                               variable=self.ui_sounds_var, font=FONT_BODY,
                               checkbox_width=20, checkbox_height=20, corner_radius=R_XS,
                               border_width=2, fg_color=ACCENT, hover_color=ACCENT_H,
                               command=self._guardar_ui_sounds)
        sw_snd.pack(anchor="w", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_MD))

        # Espacio de Almacenamiento
        st_c = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        st_c.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))

        st_hdr = ctk.CTkFrame(st_c, fg_color="transparent")
        st_hdr.pack(fill="x", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))
        ctk.CTkLabel(st_hdr, text=self.t("storage_title"), font=FONT_SECTION, text_color=TEXT_M).pack(side="left")

        st_body = ctk.CTkFrame(st_c, fg_color="transparent")
        st_body.pack(fill="x", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_MD))

        t_row = ctk.CTkFrame(st_body, fg_color=SURFACE_HIGH, corner_radius=R_SM)
        t_row.pack(fill="x")

        left_t = ctk.CTkFrame(t_row, fg_color="transparent")
        left_t.pack(side="left", padx=SPACE_LG, pady=SPACE_SM)

        ctk.CTkLabel(left_t, text=self.t("storage_total"), font=FONT_SECTION, text_color=TEXT_MAIN).pack(anchor="w")
        self.lbl_storage_total = ctk.CTkLabel(left_t, text=self.t("storage_calculating"), font=FONT_TITLE_S, text_color=ACCENT)
        self.lbl_storage_total.pack(anchor="w", pady=(2, 0))

        ctk.CTkButton(t_row, text=self.t("btn_view_breakdown"), font=FONT_LABEL_L,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                      height=36, corner_radius=R_FULL, command=self._abrir_ventana_desglose).pack(side="right", padx=SPACE_LG, pady=SPACE_SM)

        self._actualizar_espacio_almacenamiento()

        # Perfiles / Usuarios
        pc = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        pc.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_MD))
        ctk.CTkLabel(pc, text=self.t("users_profiles"), font=FONT_SECTION, text_color=TEXT_M).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))
        pf_btns = ctk.CTkFrame(pc, fg_color="transparent")
        pf_btns.pack(fill="x", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_MD))
        ctk.CTkButton(pf_btns, text=self.t("selective_backup"), font=FONT_LABEL_L, fg_color=SURFACE_HIGH,
                      hover_color=BORDER_C, height=36, corner_radius=R_FULL, command=self.exportar_backup_selectivo).pack(side="left", padx=(SPACE_NONE, SPACE_SM))
        ctk.CTkButton(pf_btns, text=self.t("import_general_backup"), font=FONT_LABEL_L, fg_color=SURFACE_HIGH,
                      hover_color=BORDER_C, height=36, corner_radius=R_FULL, command=self.importar_perfil).pack(side="left")
        # Zona de Peligro / Restablecimiento Total
        rc = ctk.CTkFrame(f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        rc.pack(fill="x", padx=SPACE_2XL, pady=(SPACE_NONE, SPACE_2XL + SPACE_SM))
        ctk.CTkLabel(rc, text=self.t("danger_zone_title"), font=FONT_SECTION, text_color="#ff5555").pack(anchor="w", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))
        r_row = ctk.CTkFrame(rc, fg_color="transparent")
        r_row.pack(fill="x", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_MD))
        ctk.CTkLabel(r_row, text=self.t("reset_launcher_desc"), font=FONT_BODY, text_color=TEXT_M, anchor="w", justify="left").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(r_row, text=self.t("btn_reset_launcher"), font=FONT_LABEL_L,
                      fg_color=DANGER, hover_color=DANGER_H, height=36, corner_radius=R_FULL,
                      command=self._iniciar_restablecimiento_total).pack(side="right", padx=(SPACE_MD, SPACE_NONE))

    def _iniciar_restablecimiento_total(self):
        """Abre la ventana dedicada del Asistente de Restablecimiento Total (Factory Reset)."""
        if hasattr(self, "sound"): self.sound.play("click")

        top = ctk.CTkToplevel(self.root)
        top.title(self.t("factory_reset_title"))
        top.geometry("560x620")
        top.resizable(False, False)
        top.grab_set()
        top.configure(fg_color=SURFACE_HIGHEST)
        animar_entrada_modal(top)

        # Encabezado con estilo de Zona de Peligro
        hdr = ctk.CTkFrame(top, fg_color=RESET_HEADER, height=56, corner_radius=0)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text=f"{self.t('danger_zone_title')}  •  {self.t('factory_reset_title')}",
                     font=FONT_TITLE_S, text_color=RESET_TITLE).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))
        lbl_hdr_sub = ctk.CTkLabel(hdr, text=self.t("reset_step1_title"), font=FONT_BODY_S, text_color=TEXT_M)
        lbl_hdr_sub.pack(anchor="w", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_SM))

        content_container = ctk.CTkFrame(top, fg_color="transparent")
        content_container.pack(fill="both", expand=True, padx=SPACE_XL, pady=SPACE_MD)

        # ── VISTA 1: SELECCIÓN Y BACKUP PRE-RESET ──
        frame_paso1 = ctk.CTkFrame(content_container, fg_color="transparent")
        frame_paso1.pack(fill="both", expand=True)

        # Tarjeta de advertencia visual
        warn_card = ctk.CTkFrame(frame_paso1, fg_color=RESET_CARD, border_width=1, border_color=RESET_CARD_BORDER, corner_radius=R_MD)
        warn_card.pack(fill="x", pady=(SPACE_NONE, SPACE_MD))
        w_row = ctk.CTkFrame(warn_card, fg_color="transparent")
        w_row.pack(fill="x", padx=SPACE_LG, pady=SPACE_MD)
        ctk.CTkLabel(w_row, text=ICON_WARNING, font=FONT_ICON_LG, text_color=RESET_TITLE).pack(side="left", padx=(SPACE_NONE, SPACE_MD), anchor="n")
        ctk.CTkLabel(w_row, text=self.t("reset_step1_msg"), font=FONT_BODY_S,
                     text_color=RESET_TEXT, justify="left", wraplength=440).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(frame_paso1, text=self.t("backup_select_items"), font=FONT_BODY,
                     text_color=TEXT_M, justify="center", wraplength=480).pack(fill="x", pady=SPACE_XL)

        # Botones del Paso 1
        bot_bar1 = ctk.CTkFrame(top, fg_color=SURFACE_LOWEST, height=54, corner_radius=0)
        bot_bar1.pack(fill="x", side="bottom")
        bot_bar1.pack_propagate(False)

        btn_cancel1 = ctk.CTkButton(bot_bar1, text=self.t("btn_cancel"), font=FONT_BODY,
                                    fg_color=BG_CARD2, hover_color=BORDER_C, height=32, width=80,
                                    command=top.destroy)
        btn_cancel1.pack(side="left", padx=14, pady=10)
        # ── VISTA 2: CONFIRMACIÓN CRÍTICA FINAL ──
        frame_paso2 = ctk.CTkFrame(content_container, fg_color="transparent")
        
        def mostrar_vista_confirmacion_final():
            frame_paso1.pack_forget()
            bot_bar1.pack_forget()
            lbl_hdr_sub.configure(text=self.t("step_final_confirm_title"))

            frame_paso2.pack(fill="both", expand=True)

            card_critica = ctk.CTkFrame(frame_paso2, fg_color=RESET_CRITICAL, border_width=2, border_color=RESET_CRITICAL_BORDER, corner_radius=R_LG)
            card_critica.pack(fill="both", expand=True, pady=(10, 16))

            ctk.CTkLabel(card_critica, text=ICON_WARNING, font=FONT_ICON_HERO, text_color=RESET_TITLE).pack(pady=(28, 8))
            ctk.CTkLabel(card_critica, text=self.t("reset_step3_title"), font=FONT_TITLE_M, text_color=RESET_TITLE).pack(pady=(0, 12))
            ctk.CTkLabel(card_critica, text=self.t("reset_step3_msg"), font=FONT_BODY,
                         text_color=RESET_TEXT, justify="center", wraplength=460).pack(padx=24, pady=(0, 20))

            bot_bar2 = ctk.CTkFrame(top, fg_color=BG_SIDE, height=54, corner_radius=0)
            bot_bar2.pack(fill="x", side="bottom")
            bot_bar2.pack_propagate(False)

            ctk.CTkButton(bot_bar2, text=self.t("btn_cancel"), font=FONT_BODY,
                          fg_color=BG_CARD2, hover_color=BORDER_C, height=36, width=95,
                          corner_radius=R_FULL, command=top.destroy).pack(side="left", padx=14, pady=10)

            ctk.CTkButton(bot_bar2, text=self.t("btn_wipe_all_confirm"), font=FONT_LABEL_L,
                          fg_color=DANGER, hover_color=DANGER_H, height=36, corner_radius=R_FULL,
                          command=lambda: ejecutar_borrado_definitivo(bot_bar2)).pack(side="right", padx=14, pady=10)

        def ejecutar_borrado_definitivo(bot_bar2):
            if hasattr(self, "sound"): self.sound.play("click")
            frame_paso2.pack_forget()
            bot_bar2.pack_forget()

            frame_wiping = ctk.CTkFrame(content_container, fg_color=BG_CARD, corner_radius=12)
            frame_wiping.pack(fill="both", expand=True, pady=20)

            lbl_w_icon = ctk.CTkLabel(frame_wiping, text=ICON_CLEANING, font=FONT_ICON_HERO, text_color=DANGER)
            lbl_w_icon.pack(pady=(36, 10))
            lbl_w_txt = ctk.CTkLabel(frame_wiping, text=self.t("wiping_data_status"), font=FONT_BODY, text_color=TEXT_MAIN, justify="center")
            lbl_w_txt.pack(pady=(0, 16))

            p_ind = ctk.CTkProgressBar(frame_wiping, progress_color="#ff4444", mode="indeterminate")
            p_ind.pack(fill="x", padx=40, pady=(0, 20))
            p_ind.start()

            def hilo_wipe():
                try:
                    for item in ["profiles", "mods", "versions", "assets", "libraries", "runtime", "skins", "wardrobe"]:
                        p = os.path.join(MINECRAFT_DIR, item)
                        if os.path.exists(p):
                            try: shutil.rmtree(p, ignore_errors=True)
                            except Exception: pass

                    cfg_file = os.path.join(MINECRAFT_DIR, "config.json")
                    if os.path.exists(cfg_file):
                        try: os.remove(cfg_file)
                        except Exception: pass

                    self.config_data = {
                        "language": self.lang,
                        "active_profile": "",
                        "profiles": {},
                        "last_version": "",
                        "launcher_fullscreen": False,
                        "auto_dependencias": False,
                        "ui_sounds": True,
                        "onboarding_completed": False,
                        "onboarding_step": 1,
                        "minecraft_dir": MINECRAFT_DIR
                    }
                    guardar_configuracion(self.config_data)

                    os.makedirs(os.path.join(MINECRAFT_DIR, "profiles"), exist_ok=True)
                    os.makedirs(os.path.join(MINECRAFT_DIR, "mods"), exist_ok=True)
                    os.makedirs(os.path.join(MINECRAFT_DIR, "skins"), exist_ok=True)

                    if hasattr(self, "_mod_cache"):
                        self._mod_cache.clear()

                    def finish_wipe():
                        p_ind.stop()
                        p_ind.pack_forget()
                        lbl_w_icon.configure(text=ICON_CHECK)
                        lbl_w_txt.configure(text=f"{self.t('success_title')}\n\n{self.t('reset_completed_msg')}", font=FONT_SECTION)
                        if hasattr(self, "sound"): self.sound.play("success")

                        bot_success = ctk.CTkFrame(top, fg_color=BG_SIDE, height=54, corner_radius=0)
                        bot_success.pack(fill="x", side="bottom")
                        bot_success.pack_propagate(False)

                        def cerrar_y_recargar():
                            top.destroy()
                            self._iniciar_onboarding()

                        ctk.CTkButton(bot_success, text=self.t("btn_ok"), font=FONT_SECTION,
                                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                                      height=34, width=100, command=cerrar_y_recargar).pack(side="right", padx=14, pady=10)

                    top.after(500, finish_wipe)

                except Exception as ex:
                    def error_wipe(e_msg):
                        p_ind.stop()
                        lbl_w_icon.configure(text=ICON_CLOSE)
                        lbl_w_txt.configure(text=f"Error:\n{e_msg}")
                        bot_err = ctk.CTkFrame(top, fg_color=BG_SIDE, height=54, corner_radius=0)
                        bot_err.pack(fill="x", side="bottom")
                        bot_err.pack_propagate(False)
                        ctk.CTkButton(bot_err, text=self.t("btn_close"), font=FONT_BODY,
                                      fg_color=BG_CARD2, hover_color=BORDER_C, height=32, width=80,
                                      command=top.destroy).pack(side="right", padx=14, pady=10)
                    top.after(0, lambda em=str(ex): error_wipe(em))

            threading.Thread(target=hilo_wipe, daemon=True).start()

        def ejecutar_respaldo_unificado():
            # El restablecimiento usa exactamente el mismo selector y formato
            # que el backup normal; después de exportar vuelve a este asistente.
            self.exportar_backup_selectivo(on_success=mostrar_vista_confirmacion_final)

        ctk.CTkButton(bot_bar1, text=self.t("btn_continue_no_backup"), font=FONT_BODY,
                      fg_color=BG_CARD2, hover_color=BORDER_C, text_color=DANGER, height=36,
                      corner_radius=R_FULL, command=mostrar_vista_confirmacion_final).pack(side="left", padx=6, pady=10)

        ctk.CTkButton(bot_bar1, text=self.t("btn_export_and_continue"), font=FONT_LABEL_L,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T, height=36,
                      corner_radius=R_FULL, command=ejecutar_respaldo_unificado).pack(side="right", padx=14, pady=10)

    def _calcular_tamano_dir(self, ruta):
        cache_key = os.path.normcase(os.path.abspath(ruta))
        ahora = time.monotonic()
        cached = self._size_cache.get(cache_key)
        if cached and ahora - cached[0] < 3.0:
            return cached[1]

        total = 0
        if os.path.exists(ruta):
            for root, _, files in os.walk(ruta):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except Exception:
                        pass
        self._size_cache[cache_key] = (ahora, total)
        return total

    def _formatear_tamano(self, bytes_val):
        b = float(bytes_val)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if b < 1024.0:
                return f"{b:.2f} {unit}"
            b /= 1024.0
        return f"{b:.2f} TB"

    def _abrir_ventana_desglose(self):
        if hasattr(self, "sound"): self.sound.play("click")
        top = ctk.CTkToplevel(self.root)
        top.title(self.t("breakdown_title"))
        top.geometry("500x440")
        top.resizable(False, False)
        top.grab_set()
        top.configure(fg_color=SURFACE_HIGHEST)
        animar_entrada_modal(top)

        hdr = ctk.CTkFrame(top, fg_color=SURFACE_LOWEST, height=48, corner_radius=0)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text=self.t('breakdown_title'), font=FONT_TITLE_S, text_color=TEXT_MAIN).pack(side="left", padx=SPACE_LG)

        ctk.CTkButton(hdr, text=self.t("storage_refresh"), font=FONT_CAPTION, fg_color=SURFACE_HIGH,
                      hover_color=BORDER_C, height=28, width=130, corner_radius=R_FULL,
                      command=self._actualizar_espacio_almacenamiento).pack(side="right", padx=SPACE_LG)

        content_f = ctk.CTkFrame(top, fg_color="transparent")
        content_f.pack(fill="both", expand=True, padx=SPACE_XL, pady=SPACE_MD)

        tot_card = ctk.CTkFrame(content_f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        tot_card.pack(fill="x", pady=(SPACE_NONE, SPACE_MD))

        ctk.CTkLabel(tot_card, text=self.t("storage_total"), font=FONT_CAPTION_B, text_color=TEXT_M).pack(anchor="w", padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))
        self.lbl_modal_storage_total = ctk.CTkLabel(tot_card, text=getattr(self, "_last_s_total", self.t("storage_calculating")),
                                                    font=FONT_TITLE_M, text_color=ACCENT)
        self.lbl_modal_storage_total.pack(anchor="w", padx=SPACE_LG, pady=(SPACE_NONE, SPACE_MD))

        items_f = ctk.CTkFrame(content_f, fg_color=SURFACE_CONTAINER, corner_radius=R_MD)
        items_f.pack(fill="both", expand=True, pady=(SPACE_NONE, SPACE_MD))

        def crear_fila(parent, icon, titulo_key, var_name):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=SPACE_LG, pady=SPACE_XS)
            ctk.CTkLabel(row, text=icon, font=FONT_ICON_MD, text_color=ACCENT, width=24).pack(side="left", padx=(0, SPACE_SM))
            ctk.CTkLabel(row, text=self.t(titulo_key), font=FONT_BODY, text_color=TEXT_MAIN).pack(side="left")
            lbl = ctk.CTkLabel(row, text=getattr(self, f"_last_s_{var_name}", "..."), font=FONT_SECTION, text_color="#4ec9b0")
            lbl.pack(side="right")
            setattr(self, f"lbl_modal_{var_name}", lbl)

        crear_fila(items_f, ICON_GAMEPAD, "storage_mc", "mc")
        crear_fila(items_f, ICON_EXTENSION, "storage_mods", "mods")
        crear_fila(items_f, ICON_FOLDER_OPEN, "storage_perfiles", "perfiles")
        crear_fila(items_f, ICON_CAMERA, "storage_capturas", "capturas")
        crear_fila(items_f, ICON_PERSON, "storage_skins", "skins")

        bot = ctk.CTkFrame(top, fg_color=SURFACE_LOWEST, height=48, corner_radius=0)
        bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)

        ctk.CTkButton(bot, text=self.t("btn_close"), font=FONT_SECTION,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                      height=32, width=90, corner_radius=R_FULL,
                      command=lambda: (hasattr(self, "sound") and self.sound.play("click"), top.destroy())).pack(side="right", padx=SPACE_LG, pady=SPACE_SM)

        self._actualizar_espacio_almacenamiento()

    def _actualizar_espacio_almacenamiento(self):
        if hasattr(self, "lbl_storage_total"):
            self.lbl_storage_total.configure(text=self.t("storage_calculating"))
        if hasattr(self, "lbl_modal_storage_total"):
            self.lbl_modal_storage_total.configure(text=self.t("storage_calculating"))
        threading.Thread(target=self._hilo_calcular_espacio, daemon=True).start()

    def _hilo_calcular_espacio(self):
        try:
            s_total = self._calcular_tamano_dir(MINECRAFT_DIR)
            s_mc = (self._calcular_tamano_dir(os.path.join(MINECRAFT_DIR, "versions")) +
                    self._calcular_tamano_dir(os.path.join(MINECRAFT_DIR, "libraries")) +
                    self._calcular_tamano_dir(os.path.join(MINECRAFT_DIR, "assets")) +
                    self._calcular_tamano_dir(os.path.join(MINECRAFT_DIR, "runtime")))
            s_mods = self._calcular_tamano_dir(os.path.join(MINECRAFT_DIR, "mods"))
            s_perfiles = self._calcular_tamano_dir(os.path.join(MINECRAFT_DIR, "profiles"))

            s_capturas = 0
            prof_dir = os.path.join(MINECRAFT_DIR, "profiles")
            if os.path.exists(prof_dir):
                for p in os.listdir(prof_dir):
                    s_capturas += self._calcular_tamano_dir(os.path.join(prof_dir, p, "screenshots"))

            s_skins = (self._calcular_tamano_dir(os.path.join(MINECRAFT_DIR, "skins")) +
                       self._calcular_tamano_dir(self._dir_armario()))

            self._last_s_total = self._formatear_tamano(s_total)
            self._last_s_mc = self._formatear_tamano(s_mc)
            self._last_s_mods = self._formatear_tamano(s_mods)
            self._last_s_perfiles = self._formatear_tamano(s_perfiles)
            self._last_s_capturas = self._formatear_tamano(s_capturas)
            self._last_s_skins = self._formatear_tamano(s_skins)

            def aplicar():
                if hasattr(self, "lbl_storage_total"):
                    self.lbl_storage_total.configure(text=self._last_s_total)
                if hasattr(self, "lbl_modal_storage_total"):
                    self.lbl_modal_storage_total.configure(text=self._last_s_total)
                if hasattr(self, "lbl_modal_mc"):
                    self.lbl_modal_mc.configure(text=self._last_s_mc)
                if hasattr(self, "lbl_modal_mods"):
                    self.lbl_modal_mods.configure(text=self._last_s_mods)
                if hasattr(self, "lbl_modal_perfiles"):
                    self.lbl_modal_perfiles.configure(text=self._last_s_perfiles)
                if hasattr(self, "lbl_modal_capturas"):
                    self.lbl_modal_capturas.configure(text=self._last_s_capturas)
                if hasattr(self, "lbl_modal_skins"):
                    self.lbl_modal_skins.configure(text=self._last_s_skins)

            self.root.after(0, aplicar)
        except Exception as e:
            print("Error calculando espacio:", e)

    def toggle_launcher_fullscreen(self, val=None):
        if val is not None:
            self.is_launcher_fs = val
        else:
            self.is_launcher_fs = not self.is_launcher_fs
        try:
            self.root.attributes("-fullscreen", self.is_launcher_fs)
        except Exception:
            pass
        self.config_data["launcher_fullscreen"] = self.is_launcher_fs
        guardar_configuracion(self.config_data)
        if hasattr(self, "launcher_fs_var"):
            self.launcher_fs_var.set(self.is_launcher_fs)

    def exit_launcher_fullscreen(self):
        if self.is_launcher_fs:
            self.toggle_launcher_fullscreen(False)

    # ──────────────────────────────────────────────
    # GESTIÓN DE PERFILES
    # ──────────────────────────────────────────────
    def al_cambiar_perfil(self, nombre):
        if hasattr(self, "sound"): self.sound.play("select")
        self.config_data["active_profile"] = nombre
        self.lbl_perfil_nombre.configure(text=nombre)
        guardar_configuracion(self.config_data)
        self._actualizar_avatar_perfil(nombre)

        p_ver = self.config_data.get("profiles", {}).get(nombre, {}).get("last_version", "")
        if p_ver and hasattr(self, "combo_version") and p_ver in self.combo_version.cget("values"):
            self.combo_version.set(p_ver)

        if self.vista_actual in ("mods", "jugar"):
            self.actualizar_lista_slots_ui()
        elif self.vista_actual == "skins":
            self._actualizar_preview_skin()
            self._actualizar_vista_armario()
        self._actualizar_resumen_jugar()

    def crear_perfil(self):
        d = ctk.CTkInputDialog(text=self.t("alert_new_profile_prompt"), title=self.t("alert_new_profile_title"))
        nombre = d.get_input()
        if not nombre: return
        nombre = nombre.strip()
        if not nombre: return
        if nombre in self.config_data["profiles"]:
            messagebox.showwarning(self.t("alert_wait"), self.t("alert_profile_exists")); return
        self.config_data["profiles"][nombre] = {"selected_slots": {}}
        self.config_data["active_profile"] = nombre
        guardar_configuracion(self.config_data)
        self._sync_sidebar_perfil(nombre)
        if hasattr(self, "sound"): self.sound.play("success")
        messagebox.showinfo(self.t("success_title"), self.t("alert_created", nombre))

    def renombrar_perfil(self):
        actual = self.config_data["active_profile"]
        d = ctk.CTkInputDialog(text=self.t("alert_rename_prompt", actual), title=self.t("alert_rename_title"))
        nuevo = d.get_input()
        if not nuevo: return
        nuevo = nuevo.strip()
        if not nuevo or nuevo == actual: return
        if nuevo in self.config_data["profiles"]:
            messagebox.showwarning(self.t("alert_wait"), self.t("alert_profile_exists")); return
        self.config_data["profiles"][nuevo] = self.config_data["profiles"].pop(actual)
        self.config_data["active_profile"] = nuevo
        guardar_configuracion(self.config_data)
        old_d = os.path.join(MINECRAFT_DIR, "profiles", actual)
        new_d = os.path.join(MINECRAFT_DIR, "profiles", nuevo)
        if os.path.exists(old_d):
            try: os.rename(old_d, new_d)
            except Exception: pass
        self._sync_sidebar_perfil(nuevo)
        if hasattr(self, "sound"): self.sound.play("success")

    def eliminar_perfil(self):
        if hasattr(self, "sound"): self.sound.play("click")
        actual = self.config_data["active_profile"]
        if len(self.config_data["profiles"]) <= 1:
            messagebox.showwarning(self.t("alert_wait"), self.t("alert_delete_profile_confirm", actual)); return
        if not messagebox.askyesno(self.t("confirm_title"), self.t("alert_delete_profile_confirm", actual)):
            return
        d = os.path.join(MINECRAFT_DIR, "profiles", actual)
        if os.path.exists(d):
            try: shutil.rmtree(d)
            except Exception as e:
                messagebox.showerror("Error", str(e)); return
        self.config_data["profiles"].pop(actual, None)
        restante = sorted(self.config_data["profiles"].keys())[0]
        self.config_data["active_profile"] = restante
        guardar_configuracion(self.config_data)
        self._sync_sidebar_perfil(restante)

    # ──────────────────────────────────────────────
    # SLOTS DE MODS
    # ──────────────────────────────────────────────
    def _obtener_slots(self):
        ver = self.combo_version.get()
        if ver in [self.t("loading_vers"), self.t("no_results"), ""]:
            return ["Default"]
        ver_s = "".join(c for c in ver if c.isalnum() or c in ".-_")
        ruta  = os.path.join(MINECRAFT_DIR, "mods", ver_s)
        os.makedirs(ruta, exist_ok=True)
        subs = [x for x in os.listdir(ruta) if os.path.isdir(os.path.join(ruta, x))]
        if not subs:
            os.makedirs(os.path.join(ruta, "Default"), exist_ok=True)
            subs = ["Default"]
        return sorted(subs)

    def actualizar_lista_slots_ui(self, sel=None):
        slots = self._obtener_slots()
        perfil  = self.config_data["active_profile"]
        version = self.combo_version.get()
        guardado = self.config_data["profiles"].get(perfil, {}).get("selected_slots", {}).get(version)
        if sel and sel in slots:
            seleccionado = sel
        elif guardado and guardado in slots:
            seleccionado = guardado
        else:
            seleccionado = slots[0]
        if hasattr(self, "combo_slot"):
            self.combo_slot.configure(values=slots)
            self.combo_slot.set(seleccionado)
        if hasattr(self, "combo_slot_jugar"):
            self.combo_slot_jugar.configure(values=slots)
            self.combo_slot_jugar.set(seleccionado)
            self._actualizar_estado_slot_jugar()
            self._actualizar_resumen_jugar()
        if hasattr(self, "scrollable_mods"):
            self.actualizar_lista_mods()

    def _actualizar_estado_slot_jugar(self):
        if not hasattr(self, "combo_slot_jugar"):
            return
        self.combo_slot_jugar.configure(state="readonly" if self.fabric_var.get() else "disabled")

    def _actualizar_resumen_jugar(self):
        if not hasattr(self, "lbl_play_summary"):
            return
        perfil = self.config_data.get("active_profile", "Jugador")
        version = self.combo_version.get() if hasattr(self, "combo_version") else "-"
        mods = self.fabric_var.get() if hasattr(self, "fabric_var") else False
        modo = "Mods" if mods else "Vanilla"
        slot = self.combo_slot_jugar.get() if hasattr(self, "combo_slot_jugar") else "Default"
        self.lbl_play_summary.configure(text=self.t("play_summary", perfil, f"{version} · {modo}", slot))

    def _al_cambiar_slot_desde_jugar(self, nombre):
        if not nombre:
            return
        if hasattr(self, "combo_slot"):
            self.combo_slot.set(nombre)
        self.al_cambiar_slot(nombre)

    def al_cambiar_slot(self, nombre):
        if hasattr(self, "sound"): self.sound.play("select")
        perfil  = self.config_data["active_profile"]
        version = self.combo_version.get()
        self.config_data["profiles"].setdefault(perfil, {}).setdefault("selected_slots", {})[version] = nombre
        guardar_configuracion(self.config_data)
        if hasattr(self, "combo_slot_jugar") and self.combo_slot_jugar.get() != nombre:
            self.combo_slot_jugar.set(nombre)
        self._actualizar_resumen_jugar()
        if hasattr(self, "scrollable_mods"):
            self.actualizar_lista_mods()

    def al_cambiar_version(self, ver=None):
        if hasattr(self, "sound"): self.sound.play("select")
        if ver is None:
            ver = self.combo_version.get()
        if ver and ver not in [self.t("loading_vers"), self.t("no_results"), ""]:
            perfil = self.config_data.get("active_profile", "Jugador")
            self.config_data["last_version"] = ver
            self.config_data.setdefault("profiles", {}).setdefault(perfil, {})["last_version"] = ver
            guardar_configuracion(self.config_data)

            instaladas = self._obtener_versiones_instaladas_set()
            if ver not in instaladas:
                if messagebox.askyesno(self.t("ver_not_installed_title"), self.t("ver_not_installed_msg", ver)):
                    self.mostrar_vista("versiones")
                    self._iniciar_instalacion_version_gestor(ver)

        self.actualizar_lista_slots_ui()
        self._actualizar_resumen_jugar()

    def crear_slot(self):
        ver = self.combo_version.get()
        if ver in [self.t("loading_vers"), self.t("no_results"), ""]: return
        d = ctk.CTkInputDialog(text=self.t("alert_new_slot_prompt"), title=self.t("alert_new_slot_title"))
        nombre = d.get_input()
        if not nombre: return
        nombre = "".join(c for c in nombre.strip() if c.isalnum() or c in " .-_").strip()
        if not nombre: return
        ver_s = "".join(c for c in ver if c.isalnum() or c in ".-_")
        ruta  = os.path.join(MINECRAFT_DIR, "mods", ver_s, nombre)
        if os.path.exists(ruta):
            messagebox.showwarning(self.t("alert_wait"), self.t("alert_slot_exists")); return
        try:
            os.makedirs(ruta)
            self.actualizar_lista_slots_ui(nombre)
            self.al_cambiar_slot(nombre)
            if hasattr(self, "sound"): self.sound.play("success")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def renombrar_slot(self):
        ver    = self.combo_version.get()
        actual = self.combo_slot.get()
        if actual == "Default":
            messagebox.showwarning(self.t("alert_wait"), self.t("cannot_rename_default_slot")); return
        d = ctk.CTkInputDialog(text=self.t("rename_slot_prompt", actual), title=self.t("rename_slot_title"))
        nuevo = d.get_input()
        if not nuevo: return
        nuevo = "".join(c for c in nuevo.strip() if c.isalnum() or c in " .-_").strip()
        if not nuevo or nuevo == actual: return
        ver_s = "".join(c for c in ver if c.isalnum() or c in ".-_")
        base  = os.path.join(MINECRAFT_DIR, "mods", ver_s)
        if os.path.exists(os.path.join(base, nuevo)):
            messagebox.showwarning(self.t("alert_wait"), self.t("alert_slot_exists")); return
        try:
            os.rename(os.path.join(base, actual), os.path.join(base, nuevo))
            for pd in self.config_data["profiles"].values():
                if pd.get("selected_slots", {}).get(ver) == actual:
                    pd["selected_slots"][ver] = nuevo
            guardar_configuracion(self.config_data)
            self.actualizar_lista_slots_ui(nuevo)
            if hasattr(self, "sound"): self.sound.play("success")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def eliminar_slot(self):
        if hasattr(self, "sound"): self.sound.play("click")
        ver    = self.combo_version.get()
        actual = self.combo_slot.get()
        if actual == "Default":
            messagebox.showwarning(self.t("alert_wait"), self.t("cannot_delete_default_slot")); return
        if not messagebox.askyesno(self.t("confirm_title"), self.t("alert_delete_slot_confirm", actual)):
            return
        ver_s = "".join(c for c in ver if c.isalnum() or c in ".-_")
        try:
            shutil.rmtree(os.path.join(MINECRAFT_DIR, "mods", ver_s, actual))
            for pd in self.config_data["profiles"].values():
                if pd.get("selected_slots", {}).get(ver) == actual:
                    pd["selected_slots"][ver] = "Default"
            guardar_configuracion(self.config_data)
            self.actualizar_lista_slots_ui("Default")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _mods_dir(self):
        ver  = self.combo_version.get()
        slot = self.combo_slot.get() if hasattr(self, "combo_slot") else "Default"
        slot = slot or "Default"
        if ver in [self.t("loading_vers"), self.t("no_results"), ""]:
            return os.path.join(MINECRAFT_DIR, "mods")
        ver_s = "".join(c for c in ver if c.isalnum() or c in ".-_")
        ruta  = os.path.join(MINECRAFT_DIR, "mods", ver_s, slot)
        os.makedirs(ruta, exist_ok=True)
        return ruta

    # ──────────────────────────────────────────────
    # MODS
    # ──────────────────────────────────────────────
    def _obtener_info_mod(self, jar_path):
        if not hasattr(self, "_mod_cache"):
            self._mod_cache = {}

        try:
            mtime = os.path.getmtime(jar_path)
        except Exception:
            mtime = 0

        if jar_path in self._mod_cache:
            cached_mtime, cached_info = self._mod_cache[jar_path]
            if cached_mtime == mtime:
                return cached_info

        mods_dir = os.path.dirname(jar_path)
        filename = os.path.basename(jar_path)
        meta_modrinth = self._obtener_mod_meta(mods_dir, filename)

        info = {
            "name": meta_modrinth.get("title", filename),
            "version": "",
            "icon": None,
            "filename": filename,
            "mod_id": meta_modrinth.get("project_id", "") or meta_modrinth.get("slug", ""),
            "project_id": meta_modrinth.get("project_id", ""),
            "slug": meta_modrinth.get("slug", ""),
            "depends": {},
            "provides": [],
            "activo": not filename.endswith(".disabled"),
        }

        try:
            with zipfile.ZipFile(jar_path, 'r') as zf:
                namelist = zf.namelist()
                icon_path = None

                meta_file = None
                if "fabric.mod.json" in namelist:
                    meta_file = "fabric.mod.json"
                elif "quilt.mod.json" in namelist:
                    meta_file = "quilt.mod.json"

                if meta_file:
                    try:
                        with zf.open(meta_file) as mf:
                            data = json.load(mf)

                        if meta_file == "quilt.mod.json":
                            ql = data.get("quilt_loader", {})
                            meta = ql.get("metadata", {})
                            info["name"]    = meta.get("name", info["name"])
                            info["mod_id"]  = ql.get("id", info["mod_id"])
                            ver = str(ql.get("version", "")).strip()
                            raw_deps = ql.get("depends", [])
                            icon_raw = meta.get("icon")
                        else:
                            info["name"]    = data.get("name", info["name"])
                            info["mod_id"]  = data.get("id", info["mod_id"])
                            ver = str(data.get("version", "")).strip()
                            raw_deps = data.get("depends", {})
                            icon_raw = data.get("icon")

                        provides_raw = data.get("provides", [])
                        if isinstance(provides_raw, list):
                            info["provides"] = [str(p).lower() for p in provides_raw]
                        elif isinstance(provides_raw, str):
                            info["provides"] = [provides_raw.lower()]

                        info["version"] = f"v{ver}" if ver and not ver.startswith("v") else ver

                        if isinstance(raw_deps, dict):
                            info["depends"] = raw_deps
                        elif isinstance(raw_deps, list):
                            for dep in raw_deps:
                                if isinstance(dep, dict) and "id" in dep:
                                    info["depends"][dep["id"]] = dep.get("versions", "*")
                                elif isinstance(dep, str):
                                    info["depends"][dep] = "*"

                        if isinstance(icon_raw, dict):
                            icon_path = list(icon_raw.values())[-1] if icon_raw else None
                        elif isinstance(icon_raw, str):
                            icon_path = icon_raw
                    except Exception:
                        pass
                else:
                    toml_path = next((f for f in namelist if f.endswith("mods.toml")), None)
                    if toml_path:
                        try:
                            with zf.open(toml_path) as tf:
                                content = tf.read().decode("utf-8", errors="ignore")
                                for line in content.splitlines():
                                    line_s = line.strip()
                                    if line_s.startswith("displayName"):
                                        parts = line_s.split("=", 1)
                                        if len(parts) == 2:
                                            info["name"] = parts[1].strip().strip('"\'')
                                    elif line_s.startswith("modId"):
                                        parts = line_s.split("=", 1)
                                        if len(parts) == 2:
                                            info["mod_id"] = parts[1].strip().strip('"\'')
                                    elif line_s.startswith("version"):
                                        parts = line_s.split("=", 1)
                                        if len(parts) == 2:
                                            info["version"] = parts[1].strip().strip('"\'')
                                    elif line_s.startswith("logoFile"):
                                        parts = line_s.split("=", 1)
                                        if len(parts) == 2:
                                            icon_path = parts[1].strip().strip('"\'')
                        except Exception:
                            pass
                    elif "mcmod.info" in namelist:
                        try:
                            with zf.open("mcmod.info") as mf:
                                data = json.load(mf)
                                if isinstance(data, list) and data:
                                    m = data[0]
                                    info["name"] = m.get("name", info["name"])
                                    info["mod_id"] = m.get("modid", info["mod_id"])
                                    info["version"] = m.get("version", "")
                                    icon_path = m.get("logoFile")
                        except Exception:
                            pass

                if icon_path:
                    icon_path = icon_path.lstrip("/")
                    if icon_path in namelist:
                        try:
                            with zf.open(icon_path) as img_f:
                                img = Image.open(io.BytesIO(img_f.read())).convert("RGBA")
                                info["icon"] = ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))
                        except Exception:
                            pass
        except Exception:
            pass

        if info["icon"] is None and meta_modrinth.get("icon_url"):
            icon_url = meta_modrinth["icon_url"]
            try:
                if not hasattr(self, "_icon_img_cache"): self._icon_img_cache = {}
                if icon_url in self._icon_img_cache:
                    info["icon"] = self._icon_img_cache[icon_url]
                else:
                    r = requests.get(icon_url, timeout=3)
                    if r.status_code == 200:
                        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))
                        self._icon_img_cache[icon_url] = ctk_img
                        info["icon"] = ctk_img
            except Exception:
                pass

        if (info["name"] == filename or not info["name"]) and meta_modrinth.get("title"):
            info["name"] = meta_modrinth["title"]

        self._mod_cache[jar_path] = (mtime, info)
        return info

    def actualizar_lista_mods(self):
        for w in self.scrollable_mods.winfo_children():
            w.destroy()
        mods_dir = self._mods_dir()
        if not os.path.exists(mods_dir):
            ctk.CTkLabel(self.scrollable_mods, text="No hay mods instalados.",
                         font=FONT_BODY_I, text_color=TEXT_M).pack(pady=30)
            return

        archivos = sorted([f for f in os.listdir(mods_dir)
                           if (f.endswith(".jar") or f.endswith(".jar.disabled"))
                           and not ("customskinloader" in f.lower() or "fabrictailor" in f.lower())])
        if not archivos:
            ctk.CTkLabel(self.scrollable_mods, text="No hay mods instalados.",
                         font=FONT_BODY_I, text_color=TEXT_M).pack(pady=30)
            return

        installed_ids = set()
        all_infos = {}
        for fn in archivos:
            inf = self._obtener_info_mod(os.path.join(mods_dir, fn))
            all_infos[fn] = inf
            if inf.get("mod_id"):
                m_id = inf["mod_id"].lower()
                installed_ids.add(m_id)
                installed_ids.add(m_id.replace("-", "").replace("_", ""))
                installed_ids.add(m_id.replace("_", "-"))
            if inf.get("slug"):
                s_id = inf["slug"].lower()
                installed_ids.add(s_id)
                installed_ids.add(s_id.replace("-", "").replace("_", ""))
                installed_ids.add(s_id.replace("_", "-"))
            if inf.get("project_id"):
                installed_ids.add(inf["project_id"].lower())
            if inf.get("name"):
                name = inf["name"].lower()
                installed_ids.add(name)
                installed_ids.add(name.replace("'", "").replace("’", "").replace(" ", "").replace("-", "").replace("_", ""))

            installed_ids.add(fn.lower())
            norm_fn = fn.lower().replace("-", "").replace("_", "")
            installed_ids.add(norm_fn)
            if fn.endswith(".jar"):
                base = fn[:-4].lower()
                installed_ids.add(base)
                installed_ids.add(base.replace("-", "").replace("_", ""))
            elif fn.endswith(".jar.disabled"):
                base = fn[:-13].lower()
                installed_ids.add(base)
                installed_ids.add(base.replace("-", "").replace("_", ""))

            for prov in inf.get("provides", []):
                prov_l = prov.lower()
                installed_ids.add(prov_l)
                installed_ids.add(prov_l.replace("-", "").replace("_", ""))

        SYSTEM_IDS = {"minecraft", "java", "fabricloader", "fabric-loader", "quilt_loader",
                      "quilt-loader", "fabric", "forge", "architectury"}

        has_fabric_api = ("fabric-api" in installed_ids or "fabric" in installed_ids or "fabricapi" in installed_ids)
        has_quilt_api  = ("quilt-api" in installed_ids or "quilt_api" in installed_ids or "quiltapi" in installed_ids)

        for jar in archivos:
            jar_path = os.path.join(mods_dir, jar)
            info = all_infos[jar]
            activo = info["activo"]

            deps_faltantes = []
            for dep_id in info.get("depends", {}):
                d_low = dep_id.lower()
                d_norm = d_low.replace("-", "").replace("_", "")
                if d_low in installed_ids or d_norm in installed_ids or d_low in SYSTEM_IDS:
                    continue
                if has_fabric_api and (d_low.startswith("fabric-") or d_low.startswith("fabric_") or d_norm.startswith("fabric")):
                    continue
                if has_quilt_api and (d_low.startswith("quilt-") or d_low.startswith("quilt_") or d_norm.startswith("quilt")):
                    continue
                deps_faltantes.append(dep_id)

            card = ctk.CTkFrame(self.scrollable_mods,
                                fg_color=BG_CARD2 if activo else "#1a1a2a",
                                corner_radius=8)
            card.pack(fill="x", pady=3, padx=4)

            sw_var = tk.BooleanVar(value=activo)
            ctk.CTkCheckBox(card, text="", variable=sw_var, width=22, height=22,
                          checkbox_width=18, checkbox_height=18, border_width=2,
                          fg_color=ACCENT, hover_color=ACCENT_H,
                          command=lambda n=jar, v=sw_var: self._toggle_mod(n, v)).pack(
                              side="left", padx=(8, 0), pady=8)

            if info["icon"]:
                ctk.CTkLabel(card, image=info["icon"], text="").pack(side="left", padx=(4, 4), pady=6)
            else:
                ctk.CTkLabel(card, text=ICON_PACKAGE, font=FONT_ICON_MD, text_color=ACCENT).pack(side="left", padx=(6, 4), pady=6)

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=4, pady=6)

            lbl_col = TEXT_MAIN if activo else TEXT_M
            ctk.CTkLabel(info_frame, text=info["name"], font=FONT_SECTION,
                         anchor="w", text_color=lbl_col).pack(anchor="w")

            sub_text = info["filename"]
            if info["version"]:
                sub_text = f"{info['version']}  •  {info['filename']}"
            ctk.CTkLabel(info_frame, text=sub_text, font=FONT_CAPTION_S,
                         anchor="w", text_color=TEXT_M).pack(anchor="w")

            if deps_faltantes:
                dep_btn = ctk.CTkButton(info_frame, text="Hay dependencias faltantes", font=FONT_LABEL_S,
                                        fg_color=WARNING, hover_color=WARNING_H, text_color="#ffcc66",
                                        height=22, corner_radius=R_SM,
                                        command=lambda deps=deps_faltantes: self._iniciar_dialogo_deps_faltantes(deps))
                dep_btn.pack(anchor="w", pady=(3, 0))

            ctk.CTkButton(card, text=ICON_CLOSE, font=FONT_ICON_SM, width=28, height=28, fg_color="transparent",
                          text_color=DANGER, hover_color=DANGER_SOFT_H, corner_radius=R_FULL,
                          command=lambda n=jar: self._eliminar_mod(n)).pack(side="right", padx=6, pady=4)

    def añadir_mods(self):
        if hasattr(self, "sound"): self.sound.play("click")
        archivos = filedialog.askopenfilenames(title=self.t("add_mods"), filetypes=[("Java Mods (*.jar)", "*.jar")])
        if not archivos: return
        mods_dir = self._mods_dir()
        err = 0
        for src in archivos:
            try: shutil.copy(src, os.path.join(mods_dir, os.path.basename(src)))
            except Exception: err += 1
        if hasattr(self, "_mod_cache"):
            self._mod_cache.clear()
        self.actualizar_lista_mods()
        ok = len(archivos) - err
        msg = self.t("mods_installed_count", ok, len(archivos))
        if err: messagebox.showwarning(self.t("alert_wait"), msg)
        else:   messagebox.showinfo(self.t("success_title"), msg)

    def _eliminar_mod(self, nombre):
        if hasattr(self, "sound"): self.sound.play("click")
        if messagebox.askyesno(self.t("confirm_title"), self.t("delete_mod_confirm", nombre)):
            ruta = os.path.join(self._mods_dir(), nombre)
            try:
                if os.path.exists(ruta): os.remove(ruta)
                if hasattr(self, "_mod_cache"):
                    self._mod_cache.pop(ruta, None)
                self.actualizar_lista_mods()
                if self.vista_actual == "modrinth":
                    self.iniciar_busqueda_modrinth()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def abrir_carpeta_mods(self):
        if hasattr(self, "sound"): self.sound.play("click")
        try: os.startfile(self._mods_dir())
        except Exception as e: messagebox.showerror("Error", str(e))

    def _toggle_mod(self, filename, sw_var):
        if hasattr(self, "sound"): self.sound.play("click")
        mods_dir = self._mods_dir()
        src = os.path.join(mods_dir, filename)
        if filename.endswith(".jar.disabled"):
            dst = os.path.join(mods_dir, filename[:-len(".disabled")])
        else:
            dst = os.path.join(mods_dir, filename + ".disabled")
        try:
            if os.path.exists(src):
                os.rename(src, dst)
            if hasattr(self, "_mod_cache"):
                self._mod_cache.pop(src, None)
                self._mod_cache.pop(dst, None)
            self.root.after(50, self.actualizar_lista_mods)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            sw_var.set(not sw_var.get())

    def vaciar_slot(self):
        if hasattr(self, "sound"): self.sound.play("click")
        slot = self.combo_slot.get()
        if not messagebox.askyesno(self.t("empty_slot_title"), self.t("empty_slot_confirm", slot)):
            return
        mods_dir = self._mods_dir()
        eliminados = 0
        for fn in os.listdir(mods_dir):
            if fn.endswith(".jar") or fn.endswith(".jar.disabled"):
                try:
                    os.remove(os.path.join(mods_dir, fn))
                    eliminados += 1
                except Exception:
                    pass
        if hasattr(self, "_mod_cache"):
            self._mod_cache.clear()
        self.actualizar_lista_mods()
        messagebox.showinfo(self.t("empty_slot_title"), self.t("empty_slot_success", eliminados, slot))

    def exportar_backup_selectivo(self, on_success=None):
        """Exporta perfiles y slots elegidos en un único formato de backup."""
        if hasattr(self, "sound"): self.sound.play("click")
        perfiles = sorted(self.config_data.get("profiles", {}).keys())
        slots = []
        mods_root = os.path.join(MINECRAFT_DIR, "mods")
        if os.path.isdir(mods_root):
            for version in sorted(os.listdir(mods_root)):
                version_root = os.path.join(mods_root, version)
                if not os.path.isdir(version_root):
                    continue
                for slot in sorted(os.listdir(version_root)):
                    slot_root = os.path.join(version_root, slot)
                    if os.path.isdir(slot_root):
                        slots.append((version, slot))
        if not perfiles and not slots:
            messagebox.showwarning(self.t("alert_wait"), self.t("no_backup_items"))
            return

        top = ctk.CTkToplevel(self.root)
        top.title(self.t("selective_backup"))
        top.geometry("580x650")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()
        top.configure(fg_color=BG_DARK)
        animar_entrada_modal(top)
        ctk.CTkLabel(top, text=self.t("selective_backup"), font=FONT_TITLE_M,
                     text_color=TEXT_MAIN).pack(anchor="w", padx=22, pady=(18, 2))
        ctk.CTkLabel(top, text=self.t("backup_select_items"), font=FONT_CAPTION,
                     text_color=TEXT_M).pack(anchor="w", padx=22, pady=(0, 10))

        select_all = tk.BooleanVar(value=True)
        checks = {}
        scroll = ctk.CTkScrollableFrame(top, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        def group_title(text):
            ctk.CTkLabel(scroll, text=text, font=FONT_SECTION,
                         text_color=ACCENT, anchor="w").pack(fill="x", pady=(8, 4))

        _updating_all = False
        def actualizar_seleccionar_todos(*_):
            if _updating_all:
                return
            select_all.set(bool(checks) and all(var.get() for var in checks.values()))

        group_title(self.t("backup_profiles_group"))
        for profile in perfiles:
            var = tk.BooleanVar(value=True)
            checks[("profile", profile)] = var
            var.trace_add("write", actualizar_seleccionar_todos)
            ctk.CTkCheckBox(scroll, text=profile, variable=var, font=FONT_BODY,
                            checkbox_width=18, checkbox_height=18, border_width=2,
                            fg_color=ACCENT, hover_color=ACCENT_H).pack(fill="x", padx=8, pady=3)

        if slots:
            group_title(self.t("backup_slots_group"))
            for version, slot in slots:
                var = tk.BooleanVar(value=True)
                checks[("slot", version, slot)] = var
                var.trace_add("write", actualizar_seleccionar_todos)
                ctk.CTkCheckBox(scroll, text=f"{slot}  ·  Minecraft {version}", variable=var,
                                font=FONT_BODY, checkbox_width=18, checkbox_height=18,
                                border_width=2, fg_color=ACCENT, hover_color=ACCENT_H).pack(fill="x", padx=8, pady=3)

        def toggle_all():
            nonlocal _updating_all
            _updating_all = True
            target = select_all.get()
            try:
                for var in checks.values():
                    var.set(target)
            finally:
                _updating_all = False
                select_all.set(target)

        footer = ctk.CTkFrame(top, fg_color=BG_SIDE, height=58)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        ctk.CTkCheckBox(footer, text=self.t("select_all"), variable=select_all,
                        font=FONT_BODY, checkbox_width=18, checkbox_height=18,
                        border_width=2, fg_color=ACCENT, hover_color=ACCENT_H,
                        command=toggle_all).pack(side="left", padx=18, pady=14)

        def exportar():
            selected_profiles = [k[1] for k, v in checks.items() if k[0] == "profile" and v.get()]
            selected_slots = [(k[1], k[2]) for k, v in checks.items() if k[0] == "slot" and v.get()]
            if not selected_profiles and not selected_slots:
                messagebox.showwarning(self.t("alert_wait"), self.t("no_backup_items"))
                return
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = filedialog.asksaveasfilename(
                title=self.t("selective_backup"), defaultextension=".zip",
                initialfile=f"backup_selectivo_{timestamp}.zip",
                filetypes=[(self.t("zip_files"), "*.zip")])
            if not dest:
                return
            top.destroy()

            top_prog = ctk.CTkToplevel(self.root)
            top_prog.title(self.t("selective_backup"))
            top_prog.geometry("480x240")
            top_prog.resizable(False, False)
            top_prog.transient(self.root)
            top_prog.grab_set()
            top_prog.configure(fg_color=BG_DARK)
            animar_entrada_modal(top_prog)

            hdr = ctk.CTkFrame(top_prog, fg_color=BG_SIDE, height=44, corner_radius=0)
            hdr.pack(fill="x", side="top")
            hdr.pack_propagate(False)
            ctk.CTkLabel(hdr, text=self.t('selective_backup'), font=FONT_SECTION, text_color=TEXT_MAIN).pack(side="left", padx=16)

            content = ctk.CTkFrame(top_prog, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=22, pady=16)

            lbl_st = ctk.CTkLabel(content, text=self.t("reading_backup_zip"), font=FONT_BODY, text_color=TEXT_M, anchor="w")
            lbl_st.pack(fill="x", pady=(0, 6))

            p_bar = ctk.CTkProgressBar(content, progress_color=ACCENT, height=10)
            p_bar.pack(fill="x", pady=(0, 4))
            p_bar.set(0)

            lbl_pct = ctk.CTkLabel(content, text="0%", font=FONT_CAPTION_B, text_color=ACCENT, anchor="e")
            lbl_pct.pack(fill="x", pady=(0, 8))

            cancel_export = [False]
            def cancelar():
                cancel_export[0] = True
                btn_cancel.configure(state="disabled", text=self.t("install_cancelling"))

            btn_cancel = ctk.CTkButton(content, text=self.t("btn_cancel_export"), font=FONT_SECTION,
                                       fg_color=DANGER, hover_color=DANGER_H, text_color=ACCENT_T, height=34,
                                       command=cancelar)
            btn_cancel.pack(fill="x")
            top_prog.protocol("WM_DELETE_WINDOW", cancelar)

            def hilo_crear_zip():
                try:
                    meta = {
                        "version_launcher": "SimpleLauncher_v3",
                        "type": "selective_unified_backup",
                        "profiles": {p: self.config_data.get("profiles", {}).get(p, {}) for p in selected_profiles},
                        "slots": [{"version": v, "slot": s} for v, s in selected_slots]
                    }
                    archivos_a_escribir = []
                    for profile in selected_profiles:
                        root_profile = os.path.join(MINECRAFT_DIR, "profiles", profile)
                        if os.path.isdir(root_profile):
                            for root_dir, _, files in os.walk(root_profile):
                                for filename in files:
                                    path = os.path.join(root_dir, filename)
                                    rel = os.path.relpath(path, root_profile)
                                    archivos_a_escribir.append((path, os.path.join("profiles", profile, "game", rel), filename))

                    for version, slot in selected_slots:
                        root_slot = os.path.join(MINECRAFT_DIR, "mods", version, slot)
                        if os.path.isdir(root_slot):
                            for root_dir, _, files in os.walk(root_slot):
                                for filename in files:
                                    if not (filename.endswith(".jar") or filename.endswith(".jar.disabled")):
                                        continue
                                    path = os.path.join(root_dir, filename)
                                    rel = os.path.relpath(path, root_slot)
                                    archivos_a_escribir.append((path, os.path.join("mods", version, slot, rel), filename))

                    total = len(archivos_a_escribir)
                    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr("backup_meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
                        for idx, (path, arcname, fname) in enumerate(archivos_a_escribir):
                            if cancel_export[0]:
                                raise ExportCancelledException("Cancelado")
                            zf.write(path, arcname)
                            pct = min((idx + 1) / max(total, 1), 1.0)
                            self.root.after(0, lambda p=pct, fn=fname: [
                                p_bar.set(p),
                                lbl_pct.configure(text=f"{int(p * 100)}%"),
                                lbl_st.configure(text=self.t("exporting_file", fn[:45]))
                            ])

                    if hasattr(self, "sound"): self.sound.play("success")
                    def final_ok():
                        top_prog.destroy()
                        messagebox.showinfo(self.t("success_title"), self.t("backup_total_success", len(selected_profiles), len(selected_slots), dest))
                        if on_success:
                            on_success()
                    self.root.after(0, final_ok)

                except ExportCancelledException:
                    if os.path.exists(dest):
                        try: os.remove(dest)
                        except OSError: pass
                    self.root.after(0, lambda: [
                        top_prog.destroy(),
                        messagebox.showinfo(self.t("confirm_title"), self.t("export_cancelled"))
                    ])
                except Exception as e:
                    if os.path.exists(dest):
                        try: os.remove(dest)
                        except OSError: pass
                    self.root.after(0, lambda err=e: [
                        top_prog.destroy(),
                        messagebox.showerror(self.t("error_exporting"), str(err))
                    ])

            threading.Thread(target=hilo_crear_zip, daemon=True).start()

        ctk.CTkButton(footer, text=self.t("btn_close"), font=FONT_BODY,
                      fg_color=BG_CARD2, hover_color=BORDER_C, height=32,
                      command=top.destroy).pack(side="right", padx=(6, 18), pady=13)
        ctk.CTkButton(footer, text=self.t("btn_export_selected"), font=FONT_SECTION,
                      fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                      height=32, command=exportar).pack(side="right", pady=13)

    def exportar_backup_completo(self):
        """Exporta todos los perfiles y ranuras sin pasar por Restablecimiento Total."""
        if hasattr(self, "sound"): self.sound.play("click")
        perfiles = sorted(self.config_data.get("profiles", {}).keys())
        slots = []
        mods_root = os.path.join(MINECRAFT_DIR, "mods")
        if os.path.isdir(mods_root):
            for version in sorted(os.listdir(mods_root)):
                version_root = os.path.join(mods_root, version)
                if not os.path.isdir(version_root):
                    continue
                for slot in sorted(os.listdir(version_root)):
                    if os.path.isdir(os.path.join(version_root, slot)):
                        slots.append((version, slot))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = filedialog.asksaveasfilename(
            title=self.t("full_backup"), defaultextension=".zip",
            initialfile=f"backup_completo_{timestamp}.zip",
            filetypes=[(self.t("zip_files"), "*.zip")])
        if not dest:
            return

        top = ctk.CTkToplevel(self.root)
        top.title(self.t("full_backup"))
        top.geometry("480x220")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()
        top.configure(fg_color=BG_DARK)
        animar_entrada_modal(top)
        ctk.CTkLabel(top, text=self.t("full_backup"), font=FONT_SECTION,
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(18, 4))
        lbl_backup = ctk.CTkLabel(top, text=self.t("reading_backup_zip"), font=FONT_CAPTION,
                                  text_color=TEXT_M, anchor="w")
        lbl_backup.pack(fill="x", padx=20, pady=(0, 8))
        p_backup = ctk.CTkProgressBar(top, progress_color=ACCENT, height=8)
        p_backup.pack(fill="x", padx=20, pady=(0, 14))
        p_backup.set(0)
        self._cancel_full_backup = False

        def cancelar_backup():
            self._cancel_full_backup = True
            btn_cancel.configure(state="disabled", text=self.t("install_cancelling"))

        btn_cancel = ctk.CTkButton(top, text=self.t("btn_cancel_export"), font=FONT_SECTION,
                                   fg_color=DANGER, hover_color=DANGER_H, text_color="white",
                                   height=34, command=cancelar_backup)
        btn_cancel.pack(fill="x", padx=20)
        top.protocol("WM_DELETE_WINDOW", cancelar_backup)

        def crear_zip():
            try:
                meta_data = {
                    "version_launcher": "SimpleLauncher_v2",
                    "type": "pre_reset_unified_backup",
                    "profiles": {p: self.config_data.get("profiles", {}).get(p, {}) for p in perfiles},
                    "slots": [{"version": v, "slot": s} for v, s in slots]
                }
                archivos_perfil = {}
                archivos_slot = {}
                total_archivos = 0
                for p_name in perfiles:
                    p_root = os.path.join(MINECRAFT_DIR, "profiles", p_name)
                    archivos = []
                    if os.path.isdir(p_root):
                        for root_dir, _, files in os.walk(p_root):
                            archivos.extend(os.path.join(root_dir, f) for f in files)
                    archivos_perfil[p_name] = archivos
                    total_archivos += len(archivos)
                for version, slot in slots:
                    slot_root = os.path.join(MINECRAFT_DIR, "mods", version, slot)
                    archivos = []
                    if os.path.isdir(slot_root):
                        for root_dir, _, files in os.walk(slot_root):
                            archivos.extend(os.path.join(root_dir, f) for f in files
                                            if f.endswith(".jar") or f.endswith(".jar.disabled"))
                    archivos_slot[(version, slot)] = archivos
                    total_archivos += len(archivos)

                procesados = 0
                with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("backup_meta.json", json.dumps(meta_data, ensure_ascii=False, indent=2))
                    zf.writestr("slot_backup_meta.json", json.dumps(meta_data, ensure_ascii=False, indent=2))

                    for p_name in perfiles:
                        p_root = os.path.join(MINECRAFT_DIR, "profiles", p_name)
                        for filepath in archivos_perfil[p_name]:
                            if self._cancel_full_backup:
                                raise ExportCancelledException("Cancelado")
                            rel = os.path.relpath(filepath, p_root)
                            zf.write(filepath, os.path.join("profiles", p_name, "game", rel))
                            procesados += 1
                            pct = procesados / max(total_archivos, 1)
                            top.after(0, lambda p=pct, f=rel: (p_backup.set(p), lbl_backup.configure(text=f[:70])))

                    for version, slot in slots:
                        slot_root = os.path.join(MINECRAFT_DIR, "mods", version, slot)
                        for filepath in archivos_slot[(version, slot)]:
                            if self._cancel_full_backup:
                                raise ExportCancelledException("Cancelado")
                            rel = os.path.relpath(filepath, slot_root)
                            zf.write(filepath, os.path.join("mods", version, slot, rel))
                            procesados += 1
                            pct = procesados / max(total_archivos, 1)
                            top.after(0, lambda p=pct, f=rel: (p_backup.set(p), lbl_backup.configure(text=f[:70])))

                self.root.after(0, lambda: [top.destroy(), messagebox.showinfo(
                    self.t("success_title"),
                    self.t("backup_total_success", len(perfiles), len(slots), dest))])
            except ExportCancelledException:
                try:
                    if os.path.exists(dest): os.remove(dest)
                except Exception:
                    pass
                self.root.after(0, lambda: [top.destroy(), messagebox.showinfo(
                    self.t("confirm_title"), self.t("export_cancelled"))])
            except Exception as e:
                try:
                    if os.path.exists(dest):
                        os.remove(dest)
                except Exception:
                    pass
                self.root.after(0, lambda err=e: [top.destroy(), messagebox.showerror(
                    self.t("error_exporting"), str(err))])

        threading.Thread(target=crear_zip, daemon=True).start()

    def exportar_slot(self, on_success=None):
        """Abre ventana modal para seleccionar y exportar múltiples slots de mods con barra de progreso y cancelación."""
        if hasattr(self, "sound"): self.sound.play("click")

        # Escanear todos los slots disponibles organizados por version
        mods_base = os.path.join(MINECRAFT_DIR, "mods")
        slots_encontrados = [] # [ (ver_name, slot_name, slot_path, num_mods, size_bytes) ]

        if os.path.exists(mods_base):
            for vd in sorted(os.listdir(mods_base)):
                vp = os.path.join(mods_base, vd)
                if not os.path.isdir(vp): continue
                for sd in sorted(os.listdir(vp)):
                    sp = os.path.join(vp, sd)
                    if os.path.isdir(sp):
                        jars = [x for x in os.listdir(sp) if x.endswith(".jar") or x.endswith(".jar.disabled")]
                        if jars:
                            s_size = self._calcular_tamano_dir(sp)
                            slots_encontrados.append((vd, sd, sp, len(jars), s_size))

        if not slots_encontrados:
            messagebox.showwarning(self.t("alert_wait"), self.t("no_slots_found"))
            return

        top = ctk.CTkToplevel(self.root)
        top.title(self.t("export_slots_title"))
        top.geometry("520x500")
        top.resizable(False, False)
        top.grab_set()
        top.configure(fg_color=BG_DARK)
        animar_entrada_modal(top)

        hdr = ctk.CTkFrame(top, fg_color=BG_SIDE, height=52, corner_radius=0)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text=self.t('export_slots_title'), font=FONT_SECTION, text_color=TEXT_MAIN).pack(anchor="w", padx=18, pady=(8, 1))
        ctk.CTkLabel(hdr, text=self.t("export_slots_sub"), font=FONT_CAPTION, text_color=TEXT_M).pack(anchor="w", padx=18, pady=(0, 6))

        content_f = ctk.CTkFrame(top, fg_color="transparent")
        content_f.pack(fill="both", expand=True, padx=20, pady=12)

        frame_seleccion = ctk.CTkFrame(content_f, fg_color="transparent")
        frame_seleccion.pack(fill="both", expand=True)

        sel_all_var = tk.BooleanVar(value=True)
        check_vars = {} # (ver, slot): BooleanVar

        _updating_slots = False
        def actualizar_sel_all_slots(*_):
            if _updating_slots: return
            sel_all_var.set(bool(check_vars) and all(v.get() for v in check_vars.values()))

        def toggle_all():
            nonlocal _updating_slots
            _updating_slots = True
            target = sel_all_var.get()
            try:
                for var in check_vars.values():
                    var.set(target)
            finally:
                _updating_slots = False
                sel_all_var.set(target)

        bar_all = ctk.CTkFrame(frame_seleccion, fg_color=BG_CARD, corner_radius=8, height=36)
        bar_all.pack(fill="x", pady=(0, 8))
        bar_all.pack_propagate(False)

        ctk.CTkCheckBox(bar_all, text=self.t("select_all"), variable=sel_all_var,
                        font=FONT_SECTION, text_color=TEXT_MAIN,
                        fg_color=ACCENT, hover_color=ACCENT_H, checkmark_color=ACCENT_T,
                        command=toggle_all).pack(side="left", padx=14, pady=6)

        scroll_s = ctk.CTkScrollableFrame(frame_seleccion, fg_color="transparent")
        scroll_s.pack(fill="both", expand=True, pady=(0, 10))

        cur_ver = self.combo_version.get()
        cur_slot = self.combo_slot.get() if hasattr(self, "combo_slot") else ""

        for vd, sd, sp, n_mods, s_size in slots_encontrados:
            s_var = tk.BooleanVar(value=True)
            check_vars[(vd, sd)] = s_var
            s_var.trace_add("write", actualizar_sel_all_slots)

            card = ctk.CTkFrame(scroll_s, fg_color=BG_CARD, corner_radius=8)
            card.pack(fill="x", pady=3)

            c_left = ctk.CTkFrame(card, fg_color="transparent")
            c_left.pack(side="left", fill="both", expand=True, padx=12, pady=8)

            es_activo = (vd == cur_ver and sd == cur_slot)
            chk_txt = f"MC {vd}  •  {sd}" + (f"  ({self.t('active_tag')})" if es_activo else "")
            chk = ctk.CTkCheckBox(c_left, text=chk_txt, variable=s_var,
                                  font=(FONT_LABEL_S if es_activo else FONT_BODY_S),
                                  text_color=TEXT_MAIN, fg_color=ACCENT, hover_color=ACCENT_H, checkmark_color=ACCENT_T)
            chk.pack(side="left")

            s_str = self._formatear_tamano(s_size)
            ctk.CTkLabel(card, text=f"{n_mods} mod(s)  •  {s_str}", font=FONT_CAPTION, text_color=TEXT_M).pack(side="right", padx=14, pady=8)

        # Frame de Progreso y Bloqueo (Oculto al inicio)
        frame_progreso = ctk.CTkFrame(content_f, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=ACCENT)
        lbl_prog_title = ctk.CTkLabel(frame_progreso, text="", font=FONT_SECTION, text_color=TEXT_MAIN)
        lbl_prog_title.pack(anchor="w", padx=16, pady=(16, 2))

        lbl_prog_file = ctk.CTkLabel(frame_progreso, text="", font=FONT_CAPTION, text_color=TEXT_M, anchor="w")
        lbl_prog_file.pack(anchor="w", padx=16, pady=(0, 10))

        prog_bar = ctk.CTkProgressBar(frame_progreso, progress_color=ACCENT, height=8)
        prog_bar.pack(fill="x", padx=16, pady=(0, 14))
        prog_bar.set(0)

        btn_cancelar = ctk.CTkButton(frame_progreso, text=self.t("btn_cancel_export"),
                                     font=FONT_SECTION, fg_color=DANGER,
                                     hover_color=DANGER_H, height=32, width=150)
        btn_cancelar.pack(pady=(0, 16))

        # Footer
        bot_bar = ctk.CTkFrame(top, fg_color=BG_SIDE, height=52, corner_radius=0)
        bot_bar.pack(fill="x", side="bottom")
        bot_bar.pack_propagate(False)

        btn_close = ctk.CTkButton(bot_bar, text=self.t("btn_close"), font=FONT_BODY,
                                  fg_color=BG_CARD2, hover_color=BORDER_C, height=32, width=90,
                                  command=top.destroy)
        btn_close.pack(side="left", padx=18, pady=10)

        self._cancel_export_slot = False

        def iniciar_exportacion_slots():
            seleccionados = [(vd, sd) for (vd, sd), var in check_vars.items() if var.get()]
            if not seleccionados:
                messagebox.showwarning(self.t("alert_wait"), self.t("no_slots_selected"))
                return

            if len(seleccionados) == 1:
                vd_s, sd_s = seleccionados[0]
                def_name = f"slot_{sd_s}_{vd_s}.zip"
            else:
                def_name = f"backup_{len(seleccionados)}_slots.zip"

            dest = filedialog.asksaveasfilename(
                title=self.t("export_slots_title"), defaultextension=".zip",
                initialfile=def_name, filetypes=[(self.t("slot_zip_file"), "*.zip"), (self.t("zip_files"), "*.zip")])
            if not dest: return

            if hasattr(self, "sound"): self.sound.play("click")
            self._cancel_export_slot = False

            frame_seleccion.pack_forget()
            bot_bar.pack_forget()
            frame_progreso.pack(fill="both", expand=True, pady=10)
            lbl_prog_title.configure(text=self.t('reading_modpack'))

            def cancelar_op():
                self._cancel_export_slot = True
                btn_cancelar.configure(state="disabled", text=self.t("install_cancelling"))

            btn_cancelar.configure(command=cancelar_op, state="normal", text=self.t("btn_cancel_export"))

            threading.Thread(target=hilo_exportar_slots, args=(dest, seleccionados), daemon=True).start()

        def hilo_exportar_slots(dest_zip, slots_a_exportar):
            try:
                # Contar archivos totales
                total_archivos = 0
                archivos_por_slot = {}
                for vd, sd in slots_a_exportar:
                    s_path = os.path.join(MINECRAFT_DIR, "mods", vd, sd)
                    files = []
                    if os.path.exists(s_path):
                        for root, _, fnames in os.walk(s_path):
                            for fn in fnames:
                                if fn.endswith(".jar") or fn.endswith(".jar.disabled"):
                                    files.append(os.path.join(root, fn))
                    archivos_por_slot[(vd, sd)] = files
                    total_archivos += len(files)

                meta_data = {
                    "version_launcher": "SimpleLauncher_v2",
                    "type": "slots_backup",
                    "slots": [{"version": vd, "slot": sd} for vd, sd in slots_a_exportar]
                }

                procesados = 0
                with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Guardar meta
                    zf.writestr("slot_backup_meta.json", json.dumps(meta_data, indent=2))

                    for (vd, sd), s_files in archivos_por_slot.items():
                        s_path = os.path.join(MINECRAFT_DIR, "mods", vd, sd)
                        for fp in s_files:
                            if self._cancel_export_slot:
                                raise ExportCancelledException("Cancelado")

                            rel = os.path.relpath(fp, s_path)
                            arcname = os.path.join("mods", vd, sd, rel)
                            zf.write(fp, arcname)

                            # Si solo se exporta 1 slot, incluir a la raiz para compatibilidad legacy
                            if len(slots_a_exportar) == 1:
                                zf.write(fp, rel)

                            procesados += 1
                            if total_archivos > 0:
                                p_pct = min(procesados / total_archivos, 1.0)
                                top.after(0, lambda pct=p_pct, fn=rel: (
                                    prog_bar.set(pct),
                                    lbl_prog_file.configure(text=self.t("exporting_file", fn[:55]))
                                ))

                if hasattr(self, "sound"): self.sound.play("success")
                def _al_finalizar():
                    top.destroy()
                    messagebox.showinfo(self.t("success_title"), self.t("slots_exported_success", len(slots_a_exportar), dest_zip))
                    if on_success:
                        on_success()
                top.after(0, _al_finalizar)

            except ExportCancelledException:
                try:
                    if os.path.exists(dest_zip): os.remove(dest_zip)
                except Exception: pass
                top.after(0, lambda: [
                    top.destroy(),
                    messagebox.showinfo(self.t("confirm_title"), self.t("export_cancelled"))
                ])
            except Exception as e:
                try:
                    if os.path.exists(dest_zip): os.remove(dest_zip)
                except Exception: pass
                top.after(0, lambda err=e: [
                    top.destroy(),
                    messagebox.showerror(self.t("error_exporting"), str(err))
                ])

        btn_export = ctk.CTkButton(bot_bar, text=self.t("btn_export_selected"), font=FONT_SECTION,
                                   fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                                   height=32, command=iniciar_exportacion_slots)
        btn_export.pack(side="right", padx=18, pady=10)

    def importar_slot(self, on_success=None):
        """Importa ranuras de mods (individuales o múltiples) desde un archivo ZIP con barra de progreso."""
        if hasattr(self, "sound"): self.sound.play("click")
        src = filedialog.askopenfilename(
            title=self.t("import_slots_title"), filetypes=[(self.t("slot_zip_file"), "*.zip"), (self.t("zip_files"), "*.zip")])
        if not src: return

        try:
            with zipfile.ZipFile(src, "r") as zf:
                namelist = zf.namelist()

                # Caso A: Backup multi-slot o con metadatos
                if "slot_backup_meta.json" in namelist or any(m.startswith("mods/") for m in namelist):
                    extract_list = []
                    for member in namelist:
                        if member.startswith("mods/") and not member.endswith("/"):
                            parts = member.split("/")
                            if len(parts) >= 4: # mods/version/slot/file.jar
                                vd = parts[1]
                                sd = parts[2]
                                fn = "/".join(parts[3:])
                                extract_list.append((member, vd, sd, fn))

                    if not extract_list:
                        messagebox.showwarning(self.t("alert_wait"), self.t("no_jars_in_zip"))
                        return

                    self._mostrar_modal_progreso_importacion(
                        titulo=self.t("importing_slots_title"),
                        zip_path=src,
                        items=extract_list,
                        is_slot=True,
                        on_success=on_success
                    )
                    return

                # Caso B: ZIP individual tradicional
                jars = [m for m in namelist if (m.endswith(".jar") or m.endswith(".jar.disabled")) and not m.startswith("__")]
                if not jars:
                    messagebox.showwarning(self.t("alert_wait"), self.t("no_jars_in_zip"))
                    return

                ver = self.combo_version.get()
                if ver in [self.t("loading_vers"), self.t("no_results"), ""]:
                    messagebox.showwarning(self.t("alert_wait"), self.t("alert_select_ver"))
                    return

                defecto = os.path.splitext(os.path.basename(src))[0].replace("slot_", "")
                d = ctk.CTkInputDialog(text=self.t("import_slot_prompt"), title=self.t("import_slot_title"))
                nombre = d.get_input()
                if not nombre: return
                nombre = "".join(c for c in nombre.strip() if c.isalnum() or c in " .-_").strip() or defecto

                ver_s = "".join(c for c in ver if c.isalnum() or c in ".-_")
                extract_list = [(m, ver_s, nombre, os.path.basename(m)) for m in jars]

                self._mostrar_modal_progreso_importacion(
                    titulo=self.t("importing_slots_title"),
                    zip_path=src,
                    items=extract_list,
                    is_slot=True,
                    target_slot_name=nombre,
                    on_success=on_success
                )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ──────────────────────────────────────────────
    # EXPORTACIÓN E IMPORTACIÓN DE PERFILES
    # ──────────────────────────────────────────────
    def exportar_perfil(self, on_success=None):
        """Abre ventana modal para seleccionar perfiles a exportar con barra de progreso y cancelación."""
        if hasattr(self, "sound"): self.sound.play("click")
        top = ctk.CTkToplevel(self.root)
        top.title(self.t("export_profiles_title"))
        top.geometry("500x490")
        top.resizable(False, False)
        top.grab_set()
        top.configure(fg_color=BG_DARK)
        animar_entrada_modal(top)

        # Header
        hdr = ctk.CTkFrame(top, fg_color=BG_SIDE, height=52, corner_radius=0)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text=self.t('export_profiles_title'), font=FONT_SECTION, text_color=TEXT_MAIN).pack(anchor="w", padx=18, pady=(8, 1))
        ctk.CTkLabel(hdr, text=self.t("export_profiles_sub"), font=FONT_CAPTION, text_color=TEXT_M).pack(anchor="w", padx=18, pady=(0, 6))

        content_f = ctk.CTkFrame(top, fg_color="transparent")
        content_f.pack(fill="both", expand=True, padx=20, pady=12)

        # Frame de Selección de Perfiles
        frame_seleccion = ctk.CTkFrame(content_f, fg_color="transparent")
        frame_seleccion.pack(fill="both", expand=True)

        # Fila Seleccionar Todos
        sel_all_var = tk.BooleanVar(value=True)
        check_vars = {}

        _updating_profs = False
        def actualizar_sel_all_profs(*_):
            if _updating_profs: return
            sel_all_var.set(bool(check_vars) and all(v.get() for v in check_vars.values()))

        def toggle_all():
            nonlocal _updating_profs
            _updating_profs = True
            target = sel_all_var.get()
            try:
                for var in check_vars.values():
                    var.set(target)
            finally:
                _updating_profs = False
                sel_all_var.set(target)

        bar_all = ctk.CTkFrame(frame_seleccion, fg_color=BG_CARD, corner_radius=8, height=36)
        bar_all.pack(fill="x", pady=(0, 8))
        bar_all.pack_propagate(False)

        ctk.CTkCheckBox(bar_all, text=self.t("select_all"), variable=sel_all_var,
                        font=FONT_SECTION, text_color=TEXT_MAIN,
                        fg_color=ACCENT, hover_color=ACCENT_H, checkmark_color=ACCENT_T,
                        command=toggle_all).pack(side="left", padx=14, pady=6)

        # Lista de perfiles con tamaño
        scroll_p = ctk.CTkScrollableFrame(frame_seleccion, fg_color="transparent")
        scroll_p.pack(fill="both", expand=True, pady=(0, 10))

        perfiles_disponibles = sorted(self.config_data.get("profiles", {}).keys())
        active_prof = self.config_data.get("active_profile", "")

        for p_name in perfiles_disponibles:
            p_var = tk.BooleanVar(value=True)
            check_vars[p_name] = p_var
            p_var.trace_add("write", actualizar_sel_all_profs)

            card = ctk.CTkFrame(scroll_p, fg_color=BG_CARD, corner_radius=8)
            card.pack(fill="x", pady=3)

            c_left = ctk.CTkFrame(card, fg_color="transparent")
            c_left.pack(side="left", fill="both", expand=True, padx=12, pady=8)

            chk_txt = f"{p_name}  ({self.t('active_tag')})" if p_name == active_prof else p_name
            chk = ctk.CTkCheckBox(c_left, text=chk_txt, variable=p_var,
                                  font=(FONT_LABEL_S if p_name == active_prof else FONT_BODY_S),
                                  text_color=TEXT_MAIN, fg_color=ACCENT, hover_color=ACCENT_H, checkmark_color=ACCENT_T)
            chk.pack(side="left")

            # Tamaño
            p_dir = os.path.join(MINECRAFT_DIR, "profiles", p_name)
            s_bytes = self._calcular_tamano_dir(p_dir)
            s_str = self._formatear_tamano(s_bytes)

            ctk.CTkLabel(card, text=s_str, font=FONT_CAPTION, text_color=TEXT_M).pack(side="right", padx=14, pady=8)

        # Frame de Progreso y Bloqueo (Oculto al inicio)
        frame_progreso = ctk.CTkFrame(content_f, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=ACCENT)

        lbl_prog_title = ctk.CTkLabel(frame_progreso, text="", font=FONT_SECTION, text_color=TEXT_MAIN)
        lbl_prog_title.pack(anchor="w", padx=16, pady=(16, 2))

        lbl_prog_file = ctk.CTkLabel(frame_progreso, text="", font=FONT_CAPTION, text_color=TEXT_M, anchor="w")
        lbl_prog_file.pack(anchor="w", padx=16, pady=(0, 10))

        prog_bar = ctk.CTkProgressBar(frame_progreso, progress_color=ACCENT, height=8)
        prog_bar.pack(fill="x", padx=16, pady=(0, 14))
        prog_bar.set(0)

        btn_cancelar = ctk.CTkButton(frame_progreso, text=self.t("btn_cancel_export"),
                                     font=FONT_SECTION, fg_color=DANGER,
                                     hover_color=DANGER_H, height=32, width=150)
        btn_cancelar.pack(pady=(0, 16))

        # Botones inferiores (Footer)
        bot_bar = ctk.CTkFrame(top, fg_color=BG_SIDE, height=52, corner_radius=0)
        bot_bar.pack(fill="x", side="bottom")
        bot_bar.pack_propagate(False)

        btn_close = ctk.CTkButton(bot_bar, text=self.t("btn_close"), font=FONT_BODY,
                                  fg_color=BG_CARD2, hover_color=BORDER_C, height=32, width=90,
                                  command=top.destroy)
        btn_close.pack(side="left", padx=18, pady=10)

        self._cancel_export_perfil = False

        def iniciar_exportacion():
            seleccionados = [p for p, var in check_vars.items() if var.get()]
            if not seleccionados:
                messagebox.showwarning(self.t("alert_wait"), self.t("no_profiles_selected"))
                return

            if len(seleccionados) == 1:
                def_name = f"{self.t('profile_prefix')}_{seleccionados[0]}.zip"
            else:
                def_name = f"backup_{len(seleccionados)}_{self.t('profiles_suffix')}.zip"

            dest = filedialog.asksaveasfilename(
                title=self.t("export_profiles_title"), defaultextension=".zip",
                initialfile=def_name, filetypes=[(self.t("zip_files"), "*.zip")])
            if not dest: return

            if hasattr(self, "sound"): self.sound.play("click")
            self._cancel_export_perfil = False

            # Bloquear interfaz del diálogo: ocultar selección y footer, mostrar progreso
            frame_seleccion.pack_forget()
            bot_bar.pack_forget()
            frame_progreso.pack(fill="both", expand=True, pady=20)

            btn_cancelar.configure(state="normal", text=self.t("btn_cancel_export"),
                                   command=solicitar_cancelacion)

            threading.Thread(target=hilo_exportar, args=(seleccionados, dest), daemon=True).start()

        def solicitar_cancelacion():
            if hasattr(self, "sound"): self.sound.play("click")
            self._cancel_export_perfil = True
            btn_cancelar.configure(state="disabled", text="...")
            lbl_prog_file.configure(text=self.t("cancelling_export"))

        def hilo_exportar(perfiles, dest_zip):
            try:
                # 1. Contar total de archivos para porcentaje preciso
                total_archivos = 0
                lista_trabajo = []
                for p in perfiles:
                    p_dir = os.path.join(MINECRAFT_DIR, "profiles", p)
                    p_files = []
                    if os.path.exists(p_dir):
                        for rp, _, files in os.walk(p_dir):
                            for f_item in files:
                                p_files.append(os.path.join(rp, f_item))
                    total_archivos += len(p_files)
                    lista_trabajo.append((p, p_dir, p_files))

                procesados = 0
                is_multi = len(perfiles) > 1

                with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Metadatos del backup
                    backup_meta = {
                        "version": 2,
                        "profiles": {p: self.config_data.get("profiles", {}).get(p, {}) for p in perfiles}
                    }
                    zf.writestr("backup_meta.json", json.dumps(backup_meta, ensure_ascii=False, indent=2))

                    # Para compatibilidad con backups de 1 solo perfil
                    if not is_multi:
                        solo_p = perfiles[0]
                        p_meta = {"nombre": solo_p, "datos": self.config_data.get("profiles", {}).get(solo_p, {})}
                        zf.writestr("perfil_meta.json", json.dumps(p_meta, ensure_ascii=False, indent=2))

                    for idx, (p_nombre, p_dir, p_files) in enumerate(lista_trabajo, start=1):
                        if self._cancel_export_perfil:
                            raise ExportCancelledException("Cancelado")

                        top.after(0, lambda p=p_nombre, i=idx, tot=len(perfiles):
                                  lbl_prog_title.configure(text=self.t("compressing_profile", p, i, tot)))

                        for fp in p_files:
                            if self._cancel_export_perfil:
                                raise ExportCancelledException("Cancelado")

                            rel = os.path.relpath(fp, p_dir)
                            if is_multi:
                                arcname = os.path.join("profiles", p_nombre, "game", rel)
                            else:
                                arcname = os.path.join("game", rel)

                            zf.write(fp, arcname)
                            procesados += 1

                            if total_archivos > 0:
                                p_pct = min(procesados / total_archivos, 1.0)
                                top.after(0, lambda pct=p_pct, fn=rel: (
                                    prog_bar.set(pct),
                                    lbl_prog_file.configure(text=self.t("exporting_file", fn[:55]))
                                ))

                # Éxito
                if hasattr(self, "sound"): self.sound.play("success")
                def _al_finalizar_exito():
                    top.destroy()
                    messagebox.showinfo(self.t("success_title"), self.t("profiles_exported_success", len(perfiles), dest_zip))
                    if on_success:
                        on_success()
                top.after(0, _al_finalizar_exito)

            except ExportCancelledException:
                try:
                    if os.path.exists(dest_zip):
                        os.remove(dest_zip)
                except Exception: pass
                top.after(0, lambda: [
                    top.destroy(),
                    messagebox.showinfo(self.t("confirm_title"), self.t("export_cancelled"))
                ])
            except Exception as e:
                try:
                    if os.path.exists(dest_zip):
                        os.remove(dest_zip)
                except Exception: pass
                top.after(0, lambda err=e: [
                    top.destroy(),
                    messagebox.showerror(self.t("error_exporting"), str(err))
                ])

        btn_export = ctk.CTkButton(bot_bar, text=self.t("btn_export_selected"), font=FONT_SECTION,
                                   fg_color=ACCENT, hover_color=ACCENT_H, text_color=ACCENT_T,
                                   height=32, command=iniciar_exportacion)
        btn_export.pack(side="right", padx=18, pady=10)

    def importar_perfil(self, on_success=None):
        """Importa perfiles individuales o múltiples desde un backup .zip con barra de progreso y cancelación."""
        if hasattr(self, "sound"): self.sound.play("click")
        src = filedialog.askopenfilename(
            title=self.t("import_profile"), filetypes=[(self.t("profile_zip_file"), "*.zip"), (self.t("zip_files"), "*.zip")])
        if not src: return

        try:
            with zipfile.ZipFile(src, "r") as zf:
                namelist = zf.namelist()

                # Caso 1: Backup multi-perfil o V2
                if "backup_meta.json" in namelist:
                    with zf.open("backup_meta.json") as bf:
                        b_meta = json.load(bf)
                    profs_to_import = b_meta.get("profiles", {})
                    renames = {}
                    for p_nombre in profs_to_import.keys():
                        nombre_final = p_nombre
                        if nombre_final in self.config_data.get("profiles", {}):
                            d = ctk.CTkInputDialog(
                                text=self.t("alert_profile_exists_rename", nombre_final),
                                title=self.t("import_profile"))
                            nuevo = d.get_input()
                            if nuevo and nuevo.strip():
                                nombre_final = nuevo.strip()
                        renames[p_nombre] = nombre_final

                    extract_list = []
                    for member in namelist:
                        if member == "backup_meta.json" or member.endswith("/"): continue
                        prefix_multi = "profiles/"
                        prefix_single = "game/"
                        if member.startswith(prefix_multi):
                            parts = member.split("/")
                            if len(parts) >= 4 and parts[2] == "game":
                                orig_p = parts[1]
                                if orig_p in renames:
                                    final_p = renames[orig_p]
                                    rel = "/".join(parts[3:])
                                    dest = os.path.join(MINECRAFT_DIR, "profiles", final_p, rel)
                                    extract_list.append((member, dest))
                        elif len(profs_to_import) == 1 and member.startswith(prefix_single):
                            orig_p = list(profs_to_import.keys())[0]
                            final_p = renames[orig_p]
                            rel = member[len(prefix_single):]
                            dest = os.path.join(MINECRAFT_DIR, "profiles", final_p, rel)
                            extract_list.append((member, dest))

                    for slot_info in b_meta.get("slots", []):
                        if not isinstance(slot_info, dict):
                            continue
                        version = str(slot_info.get("version", ""))
                        slot = str(slot_info.get("slot", ""))
                        if not version or not slot:
                            continue
                        prefix_slot = f"mods/{version}/{slot}/"
                        for member in namelist:
                            if member.startswith(prefix_slot) and not member.endswith("/"):
                                rel = member[len(prefix_slot):]
                                dest = os.path.join(MINECRAFT_DIR, "mods", version, slot, rel)
                                extract_list.append(("general_slot", member, dest))

                    self._mostrar_modal_progreso_importacion(
                        titulo=self.t("importing_profile_title"),
                        zip_path=src,
                        items=extract_list,
                        is_profile=True,
                        is_general=True,
                        profile_meta_map={renames[k]: v for k, v in profs_to_import.items()},
                        on_success=on_success
                    )
                    return

                # Caso 2: Backup clásico V1 con perfil_meta.json
                elif "perfil_meta.json" in namelist:
                    with zf.open("perfil_meta.json") as mf:
                        meta = json.load(mf)
                    nombre = meta.get("nombre", "Importado")
                    p_datos = meta.get("datos", {"selected_slots": {}})

                    if nombre in self.config_data.get("profiles", {}):
                        d = ctk.CTkInputDialog(
                            text=self.t("alert_profile_exists_rename", nombre),
                            title=self.t("import_profile"))
                        nuevo = d.get_input()
                        if nuevo and nuevo.strip():
                            nombre = nuevo.strip()

                    extract_list = []
                    for member in namelist:
                        if member.startswith("game/") and len(member) > 5 and not member.endswith("/"):
                            rel = member[5:]
                            dest = os.path.join(MINECRAFT_DIR, "profiles", nombre, rel)
                            extract_list.append((member, dest))

                    self._mostrar_modal_progreso_importacion(
                        titulo=self.t("importing_profile_title"),
                        zip_path=src,
                        items=extract_list,
                        is_profile=True,
                        profile_meta_map={nombre: p_datos},
                        on_success=on_success
                    )
                else:
                    messagebox.showerror(self.t("alert_wait"), self.t("invalid_profile_zip"))

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _mostrar_modal_progreso_importacion(self, titulo, zip_path, items, is_slot=False, is_profile=False, is_general=False, profile_meta_map=None, target_slot_name=None, on_success=None):
        """Muestra ventana modal de progreso para la importación asíncrona de archivos ZIP."""
        top = ctk.CTkToplevel(self.root)
        top.title(titulo)
        top.geometry("480x250")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()
        top.configure(fg_color=BG_DARK)
        animar_entrada_modal(top)

        hdr = ctk.CTkFrame(top, fg_color=BG_SIDE, height=44, corner_radius=0)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=titulo, font=FONT_SECTION, text_color=TEXT_MAIN).pack(side="left", padx=16)

        content = ctk.CTkFrame(top, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=22, pady=16)

        lbl_st = ctk.CTkLabel(content, text=self.t("reading_backup_zip"), font=FONT_BODY, text_color=TEXT_M, anchor="w")
        lbl_st.pack(fill="x", pady=(0, 6))

        p_bar = ctk.CTkProgressBar(content, progress_color=ACCENT, height=10)
        p_bar.pack(fill="x", pady=(0, 4))
        p_bar.set(0)

        lbl_pct = ctk.CTkLabel(content, text="0%", font=FONT_CAPTION_B, text_color=ACCENT, anchor="e")
        lbl_pct.pack(fill="x", pady=(0, 8))

        self._cancel_import_op = False

        def cancelar():
            self._cancel_import_op = True
            btn_cancel.configure(state="disabled", text=self.t("install_cancelling"))

        btn_cancel = ctk.CTkButton(content, text=self.t("btn_cancel_install"), font=FONT_SECTION,
                                   fg_color=DANGER, hover_color=DANGER_H, text_color="white", height=34,
                                   command=cancelar)
        btn_cancel.pack(fill="x")

        def hilo_import():
            total = len(items)
            created_files = []
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for i, item in enumerate(items):
                        if self._cancel_import_op:
                            raise ExportCancelledException("Cancelado")

                        if is_general and item[0] == "general_slot":
                            _, member, dest = item
                        elif is_slot:
                            member, vd, sd, fn = item
                            dest = os.path.join(MINECRAFT_DIR, "mods", vd, sd, fn)
                        else:
                            member, dest = item

                        dest = validar_ruta_dentro_de(MINECRAFT_DIR, dest)
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with zf.open(member) as sf, open(dest, "wb") as df:
                            df.write(sf.read())
                        created_files.append(dest)

                        pct = min((i + 1) / max(total, 1), 1.0)
                        fn_display = os.path.basename(dest)
                        top.after(0, lambda p=pct, f=fn_display: [
                            p_bar.set(p),
                            lbl_pct.configure(text=f"{int(p * 100)}%"),
                            lbl_st.configure(text=self.t("importing_file", f[:45]))
                        ])

                if is_profile and profile_meta_map:
                    for p_nom in profile_meta_map:
                        self._migrar_wardrobe_a_armario(
                            os.path.join(MINECRAFT_DIR, "profiles", p_nom)
                        )

                # Guardar configuraciones
                if is_profile and profile_meta_map:
                    for p_nom, p_dat in profile_meta_map.items():
                        self.config_data["profiles"][p_nom] = p_dat
                        self.config_data["active_profile"] = p_nom
                    guardar_configuracion(self.config_data)
                    self.root.after(0, lambda: self._sync_sidebar_perfil(self.config_data["active_profile"]))

                if is_slot:
                    if target_slot_name:
                        self.root.after(0, lambda: self.actualizar_lista_slots_ui(target_slot_name))
                    else:
                        self.root.after(0, self.actualizar_lista_slots_ui)
                if is_general:
                    self.root.after(0, self.actualizar_lista_modpacks)

                if hasattr(self, "sound"): self.sound.play("success")
                def _al_completar():
                    top.destroy()
                    if is_general:
                        n_slots = sum(1 for item in items if item[0] == "general_slot")
                        msg = self.t("profiles_imported_count", len(profile_meta_map or {}))
                        msg += f"\n{self.t('slots_imported_count', n_slots)}"
                    elif is_profile:
                        msg = self.t("profiles_imported_count", len(profile_meta_map or [1]))
                    else:
                        msg = self.t("slots_imported_count", len(items))
                    messagebox.showinfo(self.t("success_title"), msg)
                    if on_success:
                        on_success()

                top.after(0, _al_completar)

            except ExportCancelledException:
                for f in created_files:
                    try:
                        if os.path.exists(f): os.remove(f)
                    except Exception: pass
                top.after(0, lambda: [
                    top.destroy(),
                    messagebox.showinfo(self.t("confirm_title"), self.t("import_cancelled"))
                ])
            except Exception as e:
                for f in created_files:
                    try:
                        if os.path.exists(f): os.remove(f)
                    except Exception: pass
                top.after(0, lambda err=e: [
                    top.destroy(),
                    messagebox.showerror("Error", str(err))
                ])

        threading.Thread(target=hilo_import, daemon=True).start()

    def _guardar_ui_sounds(self):
        val = self.ui_sounds_var.get()
        self.config_data["ui_sounds"] = val
        guardar_configuracion(self.config_data)
        if hasattr(self, "sound"):
            self.sound.set_enabled(val)
            if val:
                self.sound.play("click")

    def _guardar_auto_dep(self):
        if hasattr(self, "sound"): self.sound.play("click")
        self.config_data["auto_dependencias"] = self.auto_dep_var.get()
        guardar_configuracion(self.config_data)

    def _buscar_dependencia(self, dep_id):
        self.mostrar_vista("modrinth")
        self.entry_modrinth.delete(0, "end")
        self.entry_modrinth.insert(0, dep_id)
        self.iniciar_busqueda_modrinth()

    # ──────────────────────────────────────────────
    # MODPACKS
    # ──────────────────────────────────────────────
    def actualizar_lista_modpacks(self):
        for w in self.scrollable_modpacks.winfo_children():
            w.destroy()
        base = os.path.join(MINECRAFT_DIR, "mods")
        packs = []
        if os.path.exists(base):
            for vd in sorted(os.listdir(base)):
                vp = os.path.join(base, vd)
                if not os.path.isdir(vp): continue
                for sd in sorted(os.listdir(vp)):
                    if sd == "Default": continue
                    sp = os.path.join(vp, sd)
                    if os.path.isdir(sp):
                        n_mods = len([x for x in os.listdir(sp) if x.endswith(".jar")])
                        packs.append((vd, sd, n_mods))
        if not packs:
            ctk.CTkLabel(self.scrollable_modpacks,
                         text=self.t("no_modpacks_installed"),
                         font=FONT_BODY, text_color=TEXT_M, justify="center").pack(pady=40)
            return
        for version, slot, n in packs:
            card = ctk.CTkFrame(self.scrollable_modpacks, fg_color=BG_CARD2, corner_radius=10)
            card.pack(fill="x", pady=4, padx=4)
            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True, padx=14, pady=10)
            title_row = ctk.CTkFrame(left, fg_color="transparent")
            title_row.pack(anchor="w", fill="x")
            ctk.CTkLabel(title_row, text=slot, font=FONT_SECTION, text_color=TEXT_MAIN, anchor="w").pack(side="left")
            if self.config_data.get("modpack_slots", {}).get(f"{version}|{slot}"):
                ctk.CTkLabel(title_row, text=self.t("modpack_tag"), font=FONT_CAPTION_B,
                             fg_color=ACCENT, text_color=ACCENT_T, corner_radius=6).pack(side="left", padx=8)
            ctk.CTkLabel(left, text=f"MC {version}  •  {n} mod(s)",
                         font=FONT_CAPTION, text_color=TEXT_M, anchor="w").pack(anchor="w")
            ctk.CTkButton(card, text=ICON_CLOSE, width=30, height=30, fg_color="transparent",
                          text_color=DANGER, hover_color=DANGER_SOFT_H,
                          command=lambda v=version, s=slot: self._eliminar_modpack(v, s)).pack(side="right", padx=10)

    def instalar_modpack(self):
        if hasattr(self, "sound"): self.sound.play("click")
        ruta = filedialog.askopenfilename(
            title=self.t("select_modpack_title"),
            filetypes=[(self.t("modpack_filter"), "*.mrpack *.zip"), ("Modrinth (.mrpack)", "*.mrpack"), ("ZIP", "*.zip")]
        )
        if not ruta: return

        if ruta.lower().endswith(".mrpack"):
            try:
                with zipfile.ZipFile(ruta, "r") as zf:
                    with zf.open("modrinth.index.json") as fj:
                        index = json.load(fj)
                nombre_pack = index.get("name", os.path.splitext(os.path.basename(ruta))[0])
                dependencias = index.get("dependencies", {})
                mc_ver = dependencias.get("minecraft", "desconocida")
            except (KeyError, OSError, ValueError, zipfile.BadZipFile):
                messagebox.showerror("Error", self.t("modpack_invalid_manifest"))
                return
            instaladas = self._obtener_versiones_instaladas_set()
            if mc_ver in instaladas:
                if not messagebox.askyesno(self.t("confirm_title"), self.t("modpack_install_confirm", nombre_pack, mc_ver)):
                    return
            else:
                if not messagebox.askyesno(self.t("confirm_title"), self.t("modpack_install_version_confirm", mc_ver)):
                    return
            threading.Thread(target=self._instalar_mrpack, args=(ruta,), daemon=True).start()
        elif ruta.lower().endswith(".zip"):
            defecto = os.path.splitext(os.path.basename(ruta))[0]
            d = ctk.CTkInputDialog(text=self.t("install_zip_prompt"), title=self.t("install_zip_title"))
            nombre = d.get_input()
            if not nombre: return
            nombre = "".join(c for c in nombre.strip() if c.isalnum() or c in " .-_").strip() or defecto
            threading.Thread(target=self._instalar_zip, args=(ruta, nombre), daemon=True).start()

    def _mp_status(self, txt, prog=None):
        self.root.after(0, lambda: self.lbl_modpack_status.configure(text=txt))
        if prog is not None:
            self.root.after(0, lambda: self.progress_modpack.set(prog))

    def _instalar_mrpack(self, ruta):
        archivos_creados = []
        try:
            self._mp_status(self.t("reading_modpack"), 0.05)
            with zipfile.ZipFile(ruta, "r") as zf:
                with zf.open("modrinth.index.json") as fj:
                    index = json.load(fj)

            nombre_pack = index.get("name", os.path.splitext(os.path.basename(ruta))[0])
            dependencias = index.get("dependencies", {})
            mc_ver       = dependencias.get("minecraft", self.combo_version.get())
            fabric_req   = dependencias.get("fabric-loader")
            loader_kind  = "fabric" if fabric_req else None
            if dependencias.get("forge") or dependencias.get("quilt-loader"):
                raise RuntimeError("Este modpack requiere Forge o Quilt; este launcher solo puede preparar modpacks Fabric.")
            files       = [f for f in index.get("files", [])
                           if f.get("env", {}).get("client", "required") != "unsupported"]

            ver_s     = "".join(c for c in mc_ver if c.isalnum() or c in ".-_")
            slot_name = "".join(c for c in nombre_pack if c.isalnum() or c in " .-_").strip()
            slot_path = os.path.join(MINECRAFT_DIR, "mods", ver_s, slot_name)
            os.makedirs(slot_path, exist_ok=True)

            # Verificar si la versión base ya está instalada para evitar descargas redundantes
            instaladas = self._obtener_versiones_instaladas_set()
            if mc_ver not in instaladas:
                self._mp_status(f"Minecraft {mc_ver}", 0.06)
                minecraft_launcher_lib.install.install_minecraft_version(mc_ver, MINECRAFT_DIR)
            else:
                self._mp_status(f"Minecraft {mc_ver} (OK)", 0.06)

            # El manifiesto puede exigir un loader concreto.
            if loader_kind == "fabric":
                loader_version = str(fabric_req).strip()
                fabric_ver_id = f"fabric-loader-{loader_version}-{mc_ver}"
                if fabric_ver_id not in instaladas:
                    self._mp_status(f"Fabric Loader {loader_version}", 0.08)
                    minecraft_launcher_lib.fabric.install_fabric(
                        mc_ver, MINECRAFT_DIR, loader_version, java=self._java(mc_ver))
                else:
                    self._mp_status(f"Fabric Loader {loader_version} (OK)", 0.08)

            total = len(files)
            self._mp_status(self.t("downloading_n_mods", total), 0.1)

            for i, fi in enumerate(files):
                urls = fi.get("downloads", [])
                if not urls:
                    if fi.get("env", {}).get("client", "required") == "required":
                        raise RuntimeError(f"El modpack no proporciona descarga para {fi.get('path', 'un archivo')}.")
                    continue
                fname = os.path.basename(fi["path"])
                destino = os.path.join(slot_path, fname)
                ultimo_error = None
                for url in urls:
                    try:
                        r = requests.get(url, stream=True, timeout=30)
                        r.raise_for_status()
                        with open(destino, "wb") as out:
                            for chunk in r.iter_content(8192):
                                if chunk:
                                    out.write(chunk)
                        archivos_creados.append(destino)
                        ultimo_error = None
                        break
                    except (OSError, requests.RequestException) as dl_e:
                        ultimo_error = dl_e
                if ultimo_error is not None:
                    raise RuntimeError(f"No se pudo descargar {fname}: {ultimo_error}") from ultimo_error
                self._mp_status(f"{fname[:40]}", 0.1 + 0.75 * ((i + 1) / max(total, 1)))

            self._mp_status(self.t("extracting_overrides"), 0.88)
            perfil   = self.config_data["active_profile"]
            game_dir = os.path.join(MINECRAFT_DIR, "profiles", perfil)
            with zipfile.ZipFile(ruta, "r") as zf:
                for member in zf.namelist():
                    for prefix in ("overrides/", "client-overrides/"):
                        if member.startswith(prefix) and len(member) > len(prefix):
                            rel  = member[len(prefix):]
                            dest = os.path.join(game_dir, rel)
                            if member.endswith("/"):
                                os.makedirs(dest, exist_ok=True)
                            else:
                                os.makedirs(os.path.dirname(dest), exist_ok=True)
                                with zf.open(member) as src, open(dest, "wb") as dst:
                                    dst.write(src.read())

            vlist = [v["id"] for v in self.todas_las_versiones]
            if mc_ver in vlist:
                self.root.after(0, lambda: self.combo_version.set(mc_ver))

            if loader_kind:
                self.config_data.setdefault("modpack_loaders", {})[f"{ver_s}|{slot_name}"] = {
                    "type": loader_kind,
                    "version": str(fabric_req).strip()
                }
            self.config_data.setdefault("modpack_slots", {})[f"{ver_s}|{slot_name}"] = True
            guardar_configuracion(self.config_data)

            self._mp_status(self.t("modpack_installed_status", nombre_pack), 1.0)
            self.root.after(0, lambda: self.sound.play("success"))
            self.root.after(0, self.actualizar_lista_modpacks)
            self.root.after(0, lambda: self.actualizar_lista_slots_ui(slot_name))
            self.root.after(0, lambda: messagebox.showinfo(
                self.t("success_title"),
                self.t("modpack_installed_msg", nombre_pack, mc_ver, slot_name)))
        except Exception as e:
            for archivo in archivos_creados:
                try:
                    if os.path.isfile(archivo):
                        os.remove(archivo)
                except OSError:
                    pass
            self._mp_status(f"Error: {str(e)[:60]}", 0)
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _instalar_zip(self, ruta, slot_name):
        try:
            self._mp_status(self.t("reading_zip"), 0.1)
            ver   = self.combo_version.get()
            ver_s = "".join(c for c in ver if c.isalnum() or c in ".-_")
            slot_path = os.path.join(MINECRAFT_DIR, "mods", ver_s, slot_name)
            os.makedirs(slot_path, exist_ok=True)

            with zipfile.ZipFile(ruta, "r") as zf:
                jars = [m for m in zf.namelist() if m.endswith(".jar") and not m.startswith("__")]
                if not jars:
                    self._mp_status(self.t("no_jars_in_zip_status"), 0)
                    self.root.after(0, lambda: messagebox.showwarning(self.t("alert_wait"), self.t("no_jars_in_zip")))
                    return
                for i, member in enumerate(jars):
                    fname = os.path.basename(member)
                    with zf.open(member) as src, open(os.path.join(slot_path, fname), "wb") as dst:
                        dst.write(src.read())
                    self._mp_status(f"{fname[:40]}", 0.1 + 0.85 * ((i + 1) / len(jars)))

            self._mp_status(self.t("zip_installed_status", len(jars), slot_name), 1.0)
            self.config_data.setdefault("modpack_slots", {})[f"{ver_s}|{slot_name}"] = True
            guardar_configuracion(self.config_data)
            self.root.after(0, lambda: self.sound.play("success"))
            self.root.after(0, self.actualizar_lista_modpacks)
            self.root.after(0, lambda: self.actualizar_lista_slots_ui(slot_name))
            self.root.after(0, lambda: messagebox.showinfo(self.t("success_title"), self.t("zip_installed_msg", len(jars), slot_name)))
        except Exception as e:
            self._mp_status(f"Error: {str(e)[:60]}", 0)
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _eliminar_modpack(self, ver_dir, slot):
        if hasattr(self, "sound"): self.sound.play("click")
        if messagebox.askyesno(self.t("confirm_title"), self.t("delete_modpack_confirm", slot, ver_dir)):
            try:
                shutil.rmtree(os.path.join(MINECRAFT_DIR, "mods", ver_dir, slot))
                slot_key = f"{ver_dir}|{slot}"
                self.config_data.get("modpack_slots", {}).pop(slot_key, None)
                self.config_data.get("modpack_loaders", {}).pop(slot_key, None)
                guardar_configuracion(self.config_data)
                self.actualizar_lista_modpacks()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ──────────────────────────────────────────────
    # ENLACES
    # ──────────────────────────────────────────────
    def abrir_fabric_api(self):
        self.mostrar_vista("modrinth")
        self.entry_modrinth.delete(0, "end")
        self.entry_modrinth.insert(0, "Fabric API")
        self.iniciar_busqueda_modrinth()

    def abrir_modmenu(self):
        self.mostrar_vista("modrinth")
        self.entry_modrinth.delete(0, "end")
        self.entry_modrinth.insert(0, "Mod Menu")
        self.iniciar_busqueda_modrinth()

    def abrir_modrinth(self):   self.mostrar_vista("modrinth")

    # ──────────────────────────────────────────────
    # CORE LAUNCHER
    # ──────────────────────────────────────────────
    def _actualizar_texto_ruta(self):
        self.entry_dir.configure(state="normal")
        self.entry_dir.delete(0, "end")
        self.entry_dir.insert(0, MINECRAFT_DIR)
        self.entry_dir.configure(state="disabled")

    def cambiar_directorio(self):
        if hasattr(self, "sound"): self.sound.play("click")
        global MINECRAFT_DIR, CONFIG_FILE, MODS_DIR
        nueva = filedialog.askdirectory(title=self.t("select_game_folder"), initialdir=MINECRAFT_DIR)
        if not nueva: return
        MINECRAFT_DIR = os.path.normpath(nueva)
        CONFIG_FILE   = os.path.join(MINECRAFT_DIR, "launcher_config.txt")
        MODS_DIR      = os.path.join(MINECRAFT_DIR, "mods")
        self.config_data["minecraft_dir"] = MINECRAFT_DIR
        guardar_configuracion(self.config_data)
        self._actualizar_texto_ruta()
        os.makedirs(MINECRAFT_DIR, exist_ok=True)
        if self.vista_actual == "mods": self.actualizar_lista_slots_ui()
        threading.Thread(target=self._descargar_versiones, daemon=True).start()
        messagebox.showinfo(self.t("dir_changed_title"), self.t("dir_changed_msg", MINECRAFT_DIR))

    def _leer_cache_versiones(self):
        try:
            if not VERSION_CACHE_FILE or not os.path.isfile(VERSION_CACHE_FILE):
                return None
            with open(VERSION_CACHE_FILE, encoding="utf-8") as archivo:
                cache = json.load(archivo)
            versiones = cache.get("versions", [])
            guardado = float(cache.get("saved_at", 0))
            if isinstance(versiones, list) and versiones:
                return versiones, (time.time() - guardado) <= VERSION_CACHE_TTL
        except (OSError, ValueError, TypeError):
            pass
        return None

    def _guardar_cache_versiones(self, versiones):
        if not VERSION_CACHE_FILE or not isinstance(versiones, list) or not versiones:
            return
        temporal = VERSION_CACHE_FILE + ".tmp"
        try:
            with open(temporal, "w", encoding="utf-8") as archivo:
                json.dump({"saved_at": time.time(), "versions": versiones}, archivo, ensure_ascii=False)
            os.replace(temporal, VERSION_CACHE_FILE)
        except (OSError, TypeError, ValueError):
            try:
                if os.path.exists(temporal):
                    os.remove(temporal)
            except OSError:
                pass

    def _descargar_versiones(self):
        cache = self._leer_cache_versiones()
        cache_disponible = bool(cache)
        if cache_disponible:
            self.todas_las_versiones = cache[0]
            self.root.after(0, self.aplicar_filtros)
            self.root.after(0, self._actualizar_lista_versiones_ui)
            self.root.after(0, self._actualizar_selector_version_onboarding)
            if cache[1]:
                return

        try:
            versiones_remotas = minecraft_launcher_lib.utils.get_version_list()
            if versiones_remotas:
                self.todas_las_versiones = versiones_remotas
                self._guardar_cache_versiones(versiones_remotas)
                try:
                    self.root.after(0, self.aplicar_filtros)
                    self.root.after(0, self._actualizar_lista_versiones_ui)
                    self.root.after(0, self._actualizar_selector_version_onboarding)
                except Exception:
                    pass
        except Exception as e:
            if not cache_disponible:
                try:
                    self.root.after(0, lambda: messagebox.showerror("Error", self.t("error_connecting_mojang", str(e))))
                except Exception:
                    pass

    def _actualizar_selector_version_onboarding(self):
        """Actualiza el selector del onboarding cuando termina la carga remota."""
        combo = getattr(self, "_ob_combo_ver", None)
        if combo is None:
            return
        try:
            if not combo.winfo_exists() or not self.todas_las_versiones:
                return
            releases = [v.get("id") for v in self.todas_las_versiones
                        if v.get("type") == "release" and v.get("id")]
            if not releases:
                return
            actual = combo.get().strip()
            combo.configure(values=releases)
            combo.set(actual if actual in releases else releases[0])
        except Exception:
            # El usuario puede haber cerrado o cambiado el onboarding mientras
            # terminaba la descarga; en ese caso no hay nada que actualizar.
            pass

    def aplicar_filtros(self):
        if not self.todas_las_versiones: return
        tipos = ["release"] + (["snapshot"] if (hasattr(self, "snapshots_var") and self.snapshots_var.get()) else [])
        mostrar_no_inst = self.show_uninstalled_var.get() if hasattr(self, "show_uninstalled_var") else False
        instaladas = self._obtener_versiones_instaladas_set()

        filtradas = []
        for v in self.todas_las_versiones:
            vid = v["id"]
            if v["type"] not in tipos: continue
            if hasattr(self, "vulkan_var") and self.vulkan_var.get():
                parts = vid.split("-")[0].split(".")
                try:
                    pi = [int(p) for p in parts if p.isdigit()]
                    ok = False
                    if pi:
                        if (len(pi) >= 2 and pi[0] == 1 and pi[1] >= 20) or (pi[0] >= 20):
                            ok = True
                    if not ok: continue
                except (ValueError, TypeError): continue

            if not mostrar_no_inst and vid not in instaladas:
                continue

            filtradas.append(vid)

        for local_id in sorted(instaladas):
            if local_id not in filtradas and not local_id.startswith("fabric-loader-"):
                filtradas.insert(0, local_id)

        lista = filtradas
        if lista:
            self.combo_version.configure(values=lista)
            perfil = self.config_data.get("active_profile", "Jugador")
            saved_ver = self.config_data.get("profiles", {}).get(perfil, {}).get("last_version", self.config_data.get("last_version", ""))
            if saved_ver and saved_ver in lista:
                self.combo_version.set(saved_ver)
            else:
                self.combo_version.set(lista[0])
        else:
            self.combo_version.configure(values=[self.t("no_results")])
            self.combo_version.set(self.t("no_results"))
        if self.vista_actual in ("mods", "jugar"):
            self.actualizar_lista_slots_ui()

    def _java(self, ver):
        try:
            info = minecraft_launcher_lib.runtime.get_version_runtime_information(ver, MINECRAFT_DIR)
            if info:
                exe = minecraft_launcher_lib.runtime.get_executable_path(info["name"], MINECRAFT_DIR)
                if exe and os.path.exists(exe): return exe
        except Exception: pass
        rt = os.path.join(MINECRAFT_DIR, "runtime")
        if os.path.exists(rt):
            for rp, _, fs in os.walk(rt):
                if "java.exe" in fs: return os.path.join(rp, "java.exe")
        return shutil.which("java") or "java"

    def iniciar_hilo_juego(self):
        if hasattr(self, "sound"): self.sound.play("click")
        self.btn_jugar.configure(state="disabled")
        threading.Thread(target=self._lanzar, daemon=True).start()

    def _lanzar(self):
        username = self.config_data["active_profile"]
        ver = self.combo_version.get()
        if ver in [self.t("loading_vers"), self.t("no_results"), ""]:
            self.root.after(0, lambda: messagebox.showwarning(self.t("alert_wait"), self.t("alert_select_ver")))
            self.root.after(0, lambda: self.btn_jugar.configure(state="normal"))
            return

        instaladas = self._obtener_versiones_instaladas_set()
        if ver not in instaladas:
            def redirigir():
                self.btn_jugar.configure(state="normal")
                if messagebox.askyesno(self.t("ver_not_installed_title"), self.t("ver_not_installed_msg", ver)):
                    self.mostrar_vista("versiones")
                    self._iniciar_instalacion_version_gestor(ver)
            self.root.after(0, redirigir)
            return

        self.max_progress = 0
        def st(t):    self.root.after(0, lambda: self.lbl_estado.configure(text=t))
        def sm(v):    self.max_progress = v; self.root.after(0, lambda: self.progress_bar.set(0))
        def sp(v):
            if self.max_progress > 0: self.root.after(0, lambda: self.progress_bar.set(v / self.max_progress))

        try:
            game_dir = os.path.join(MINECRAFT_DIR, "profiles", username)
            os.makedirs(game_dir, exist_ok=True)

            try:
                st(self.t("install_checking_java_short"))
                info = minecraft_launcher_lib.runtime.get_version_runtime_information(ver, MINECRAFT_DIR)
                if info and not minecraft_launcher_lib.runtime.get_executable_path(info["name"], MINECRAFT_DIR):
                    minecraft_launcher_lib.runtime.install_jvm_runtime(
                        info["name"], MINECRAFT_DIR, callback={"setStatus": st, "setMax": sm, "setProgress": sp})
            except Exception: pass

            st(self.t("install_checking_files", ver))
            minecraft_launcher_lib.install.install_minecraft_version(
                ver, MINECRAFT_DIR, callback={"setStatus": st, "setMax": sm, "setProgress": sp})

            ver_final = ver

            slot_key = "".join(c for c in ver if c.isalnum() or c in ".-_") + "|" + (self.combo_slot.get() or "Default")
            loader_spec = self.config_data.get("modpack_loaders", {}).get(slot_key, {})
            fabric_enabled = self.fabric_var.get() or loader_spec.get("type") == "fabric"

            if fabric_enabled:
                st(self.t("install_checking_fabric"))
                try:
                    fv = loader_spec.get("version") or minecraft_launcher_lib.fabric.get_latest_loader_version()
                    if fv:
                        st(self.t("install_installing_fabric"))
                        minecraft_launcher_lib.fabric.install_fabric(
                            ver, MINECRAFT_DIR, fv, java=self._java(ver))
                        ver_final = f"fabric-loader-{fv}-{ver}"
                except Exception as fe:
                    raise RuntimeError(f"No se pudo instalar Fabric Loader para {ver}: {fe}") from fe

            if fabric_enabled:
                try:
                    mods_gen  = os.path.join(game_dir, "mods")
                    mods_slot = self._mods_dir()
                    os.makedirs(mods_gen, exist_ok=True)
                    for item in os.listdir(mods_gen):
                        if item.endswith(".jar"):
                            try: os.remove(os.path.join(mods_gen, item))
                            except Exception: pass
                    for item in os.listdir(mods_slot):
                        if item.endswith(".jar") and not item.endswith(".jar.disabled"):
                            shutil.copy(os.path.join(mods_slot, item), os.path.join(mods_gen, item))

                    self._asegurar_mod_skin(game_dir)
                except Exception as ms:
                    print("Error sync mods:", ms)

            self._sincronizar_skin_activa_con_juego(game_dir, username)

            options = {
                "username": username,
                "uuid": "00000000-0000-0000-0000-000000000000",
                "token": "00000000000000000000000000000000",
                "launcherName": "SimpleLauncher",
                "launcherVersion": "5.0",
                "gameDirectory": game_dir
            }

            st(self.t("game_running"))
            self.root.after(0, lambda: self.progress_bar.set(1.0))
            self.root.after(0, lambda: self.sound.play("success"))

            cmd = minecraft_launcher_lib.command.get_minecraft_command(ver_final, MINECRAFT_DIR, options)
            java_exe = self._java(ver)
            if java_exe and java_exe != "java" and os.path.exists(java_exe):
                cmd[0] = java_exe
            if self.fullscreen_var.get():
                cmd.append("--fullscreen")

            self.root.after(0, lambda: self._append_console_log(f"\n[Launcher] Starting Minecraft {ver_final}...\n"))

            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen(
                cmd,
                cwd=game_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=creation_flags
            )

            for line in iter(proc.stdout.readline, ""):
                if line:
                    self.root.after(0, lambda l=line: self._append_console_log(l))

            proc.stdout.close()
            ret_code = proc.wait()
            self.root.after(0, lambda: self._append_console_log(f"\n[Launcher] Game exited with code {ret_code}.\n"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(self.t("error_launching_title"), str(e)))
        finally:
            self.root.after(0, lambda: self.lbl_estado.configure(text=self.t("ready_to_launch")))
            self.root.after(0, lambda: self.progress_bar.set(0))
            self.root.after(0, lambda: self.btn_jugar.configure(state="normal"))


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    # Los botones sin color explícito también deben respetar el modo claro.
    ctk.ThemeManager.theme["CTkButton"]["text_color"] = TEXT_MAIN
    root = ctk.CTk()
    app = MinecraftLauncherApp(root)
    root.mainloop()


