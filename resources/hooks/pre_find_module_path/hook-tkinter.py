"""Permite empaquetar Tkinter en el runtime embebido del proyecto."""

def pre_find_module_path(hook_api):
    # El runtime incluye Tcl/Tk, pero PyInstaller no puede validarlo sin una
    # variable de entorno específica. Dejamos que use las rutas del análisis.
    return None
