"""Sistema de color, tipografía y forma del launcher — Material Design 3.

La paleta se genera a partir de un color semilla guardado por el usuario.
Los nombres siguen los roles de Material 3 para que cada vista use
superficies, textos y formas consistentes en modo claro y oscuro.
"""

import colorsys
import os
import sys


def _hex_rgb(value):
    value = str(value or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        value = "72c3cb"
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _hsl_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def _contrast_text(hex_color, hue=None):
    r, g, b = _hex_rgb(hex_color)
    luminance = (0.2126 * r) + (0.7152 * g) + (0.0722 * b)
    if hue is not None:
        return _hsl_hex(hue, 0.12, 0.96) if luminance < 0.48 else _hsl_hex(hue, 0.25, 0.08)
    return "#f4faf8" if luminance < 0.48 else "#0f1a18"


def text_on(surface_tuple, is_dark_mode=True, hue=None):
    bg = surface_tuple[1] if isinstance(surface_tuple, (tuple, list)) else surface_tuple
    return _contrast_text(bg, hue)


def generar_paleta(color_semilla="#72c3cb"):
    r, g, b = _hex_rgb(color_semilla)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    seed = _hsl_hex(h, s, l)
    s_tone = max(0.40, min(0.85, s))
    bg_dark = _hsl_hex(h, min(0.45, s_tone * 0.70), 0.11)
    bg_lowest = _hsl_hex(h, min(0.50, s_tone * 0.80), 0.08)
    bg_low = _hsl_hex(h, min(0.38, s_tone * 0.60), 0.16)
    bg_high = _hsl_hex(h, min(0.40, s_tone * 0.65), 0.22)
    bg_highest = _hsl_hex(h, min(0.42, s_tone * 0.70), 0.28)
    accent = seed if 0.38 <= l <= 0.68 else _hsl_hex(h, s_tone, max(0.46, min(0.60, l)))
    accent_h = _hsl_hex(h, s_tone, min(0.72, max(0.46, min(0.60, l)) + 0.08))
    accent_t = _contrast_text(accent, h)
    text_main = _hsl_hex(h, 0.12, 0.94)
    text_m = _hsl_hex(h, 0.18, 0.72)
    border_c = _hsl_hex(h, min(0.32, s_tone * 0.50), 0.28)
    card_sel = _hsl_hex(h, min(0.45, s_tone * 0.70), 0.26)
    return {
        "BG_DARK": (bg_dark, bg_dark), "BG_SIDE": (bg_lowest, bg_lowest),
        "BG_CARD": (bg_low, bg_low), "BG_CARD2": (bg_high, bg_high),
        "SURFACE": (bg_dark, bg_dark), "SURFACE_CONTAINER_LOWEST": (bg_lowest, bg_lowest),
        "SURFACE_LOWEST": (bg_lowest, bg_lowest), "SURFACE_CONTAINER_LOW": (bg_low, bg_low),
        "SURFACE_LOW": (bg_low, bg_low), "SURFACE_CONTAINER": (bg_low, bg_low),
        "SURFACE_CONTAINER_HIGH": (bg_high, bg_high), "SURFACE_HIGH": (bg_high, bg_high),
        "SURFACE_CONTAINER_HIGHEST": (bg_highest, bg_highest), "SURFACE_HIGHEST": (bg_highest, bg_highest),
        "ACCENT": (accent, accent), "ACCENT_H": (accent_h, accent_h), "ACCENT_T": (accent_t, accent_t),
        "TEXT_M": (text_m, text_m), "TEXT_MAIN": (text_main, text_main),
        "BORDER_C": (border_c, border_c), "CARD_SEL": (card_sel, card_sel), "_ACCENT_SEED": seed,
    }


_default_p = generar_paleta("#72c3cb")
for _name, _value in _default_p.items():
    if not _name.startswith("_"):
        globals()[_name] = _value

DANGER = ("#c24135", "#cf6679")
DANGER_H = ("#a83228", "#b04d62")
DANGER_SOFT = ("#f7d8d5", "#441414")
DANGER_SOFT_H = ("#efb8b3", "#6e1f1f")
WARNING = ("#a16207", "#e8b44a")
WARNING_H = ("#c0841a", "#c99030")
RESET_HEADER = ("#f5dedb", "#3d1414")
RESET_CARD = ("#f9e9e7", "#2b1818")
RESET_CARD_BORDER = ("#e5aaa4", "#772222")
RESET_CRITICAL = ("#fbe5e2", "#260e0e")
RESET_CRITICAL_BORDER = ("#d46b62", "#991b1b")
RESET_TITLE = ("#9f2d25", "#ff8888")
RESET_TEXT = ("#6f211b", "#ffd0d0")

SPACE_NONE, SPACE_XS, SPACE_SM, SPACE_MD = 0, 4, 8, 12
SPACE_LG, SPACE_XL, SPACE_2XL = 16, 24, 32
FONT_UI, FONT_MONO = "Nunito", "Consolas"
FONT_CODE = (FONT_MONO, 10, "normal")
FONT_DISPLAY = (FONT_UI, 36, "normal")
FONT_H1, FONT_H2, FONT_H3 = (FONT_UI, 28, "normal"), (FONT_UI, 24, "normal"), (FONT_UI, 20, "normal")
FONT_TITLE, FONT_TITLE_M, FONT_TITLE_S = (FONT_UI, 22, "normal"), (FONT_UI, 16, "bold"), (FONT_UI, 14, "bold")
FONT_BODY_L, FONT_BODY = (FONT_UI, 16, "normal"), (FONT_UI, 12, "normal")
FONT_BODY_S, FONT_BODY_I, FONT_BODY_M_I = (FONT_UI, 11, "normal"), (FONT_UI, 11, "italic"), (FONT_UI, 12, "italic")
FONT_LABEL_L, FONT_SECTION, FONT_LABEL_S = (FONT_UI, 14, "bold"), (FONT_UI, 12, "bold"), (FONT_UI, 11, "bold")
FONT_CAPTION, FONT_CAPTION_B, FONT_CAPTION_S = (FONT_UI, 10, "normal"), (FONT_UI, 10, "bold"), (FONT_UI, 9, "normal")
FONT_HINT_I = (FONT_UI, 9, "italic")

FONT_ICON_FAMILY = "Material Symbols Outlined"
ICON_SM, ICON_MD, ICON_LG, ICON_XL, ICON_HERO = 16, 20, 24, 32, 40
FONT_ICON_SM, FONT_ICON_MD = (FONT_ICON_FAMILY, ICON_SM), (FONT_ICON_FAMILY, ICON_MD)
FONT_ICON_LG, FONT_ICON_XL, FONT_ICON_HERO = (FONT_ICON_FAMILY, ICON_LG), (FONT_ICON_FAMILY, ICON_XL), (FONT_ICON_FAMILY, ICON_HERO)
ICON_ADD="\ue145"; ICON_EDIT="\ue3c9"; ICON_DELETE="\ue872"; ICON_CLOSE="\ue5cd"; ICON_FOLDER="\ue2c7"; ICON_FOLDER_OPEN="\ue2c8"
ICON_CAMERA="\ue412"; ICON_CLEANING="\ueb44"; ICON_SETTINGS="\ue8b8"; ICON_SEARCH="\ue8b6"; ICON_REFRESH="\ue5d5"; ICON_BOLT="\uea0b"
ICON_SAVE="\ue161"; ICON_CHECK="\ue5ca"; ICON_CHECK_CIRCLE="\ue86c"; ICON_WARNING="\ue002"; ICON_INFO="\ue88e"; ICON_PACKAGE="\ue1a1"
ICON_PERSON="\ue7fd"; ICON_ARROW_FORWARD="\ue5c8"; ICON_ARROW_BACK="\ue5c4"; ICON_PLAY="\ue037"; ICON_DOWNLOAD="\ue2c4"; ICON_CHART="\ue26b"
ICON_EXTENSION="\ue87b"; ICON_GAMEPAD="\ue338"; ICON_SPARKLE="\uea35"; ICON_ROCKET="\ueba3"; ICON_SHIELD="\ue8e8"; ICON_PALETTE="\ue40a"; ICON_CALENDAR="\ue935"

_icon_cache, _material_font_cache = {}, {}

def obtener_icono_ctk(glyph, color, size=20, font_path=None):
    import customtkinter as ctk
    from PIL import Image, ImageDraw, ImageFont
    color_l, color_d = color if isinstance(color, tuple) else (color, color)
    key = (glyph, color_l, color_d, size)
    if key in _icon_cache: return _icon_cache[key]
    if not font_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [os.path.join(getattr(sys, "_MEIPASS", base_dir), "MaterialSymbolsOutlined.ttf"), os.path.join(os.path.dirname(base_dir), "resources", "MaterialSymbolsOutlined.ttf"), os.path.join(base_dir, "MaterialSymbolsOutlined.ttf")]
        font_path = next((path for path in candidates if os.path.exists(path)), None)
    fonts = _material_font_cache.setdefault(font_path, {})
    if size not in fonts:
        try: fonts[size] = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        except Exception: fonts[size] = ImageFont.load_default()
    font = fonts[size]
    def render(c):
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0)); draw = ImageDraw.Draw(image); box = font.getbbox(glyph)
        w, h = box[2] - box[0], box[3] - box[1]; draw.text(((size-w)//2-box[0], (size-h)//2-box[1]), glyph, font=font, fill=c); return image
    result = ctk.CTkImage(light_image=render(color_l), dark_image=render(color_d), size=(size, size)); _icon_cache[key] = result; return result

R_NONE, R_XS, R_SM, R_MD, R_LG, R_XL, R_FULL = 0, 4, 8, 12, 16, 28, 200
DUR_MICRO, DUR_SHORT, DUR_MEDIUM, DUR_LONG, DUR_SKELETON = 100, 200, 300, 400, 500

def animar_entrada_modal(top, duracion=DUR_SHORT):
    try:
        top.attributes("-alpha", 0.0); steps = 6; interval = max(10, duracion // steps)
        def step(index=0):
            try:
                top.attributes("-alpha", min(1.0, (index + 1) / steps))
                if index + 1 < steps: top.after(interval, step, index + 1)
            except Exception: pass
        top.after(0, step)
    except Exception: pass

def animar_progreso(widget, valor_destino, duracion=DUR_SHORT):
    try: actual = float(widget.get())
    except Exception: actual = 0.0
    try:
        target = max(0.0, min(1.0, float(valor_destino))); steps = max(1, duracion // 20); delta = (target - actual) / steps
        def step(index=0, value=actual):
            try:
                value += delta; widget.set(value)
                if index + 1 < steps: widget.after(20, step, index + 1, value)
            except Exception: pass
        widget.after(0, step)
    except Exception: pass
