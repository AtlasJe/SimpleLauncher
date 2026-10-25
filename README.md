# Simple Launcher

Launcher de Minecraft para Windows, enfocado en administrar perfiles, versiones, mods, modpacks, skins y copias de seguridad.

## Estado

Primera publicación pública, en desarrollo. La interfaz actual usa Python, CustomTkinter y `minecraft-launcher-lib`. El siguiente trabajo importante es separar la lógica del launcher para facilitar una futura migración visual.

## Funciones actuales

- Instalación y lanzamiento de versiones de Minecraft.
- Perfiles y slots de mods.
- Soporte para Fabric.
- Exploración de mods mediante Modrinth.
- Importación y exportación de backups.
- Gestión de skins y capturas.
- Temas adaptables, color dinámico y varios idiomas.

## Estructura

```text
source/                   Código fuente actual
resources/               Fuentes, iconos, sonidos y recursos
builds/                  Compilaciones locales
releases/                Archivos de distribución locales
MATERIAL3_PLAN.md         Plan visual
```

Los ejecutables, builds, backups de trabajo y archivos generados quedan fuera del control de versiones mediante `.gitignore`.

## Desarrollo local

Requiere Python 3.12 o compatible y Java para ejecutar Minecraft.

```powershell
cd source
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python launcher_gui.pyw
```

## Nota legal

Minecraft es propiedad de Mojang/Microsoft. Modrinth, Fabric y las dependencias utilizadas conservan sus propias marcas y licencias. Este proyecto no está afiliado oficialmente con ellos. Revisa las licencias de los recursos antes de redistribuir una compilación.

## Contribuir

Las propuestas de cambios, errores y mejoras son bienvenidas. Para cambios grandes, abre primero un issue describiendo el problema o la propuesta. No incluyas ejecutables, builds, backups personales, cachés ni datos de Minecraft.

## Licencia

El código de este proyecto se distribuye bajo la licencia MIT. Los recursos de terceros pueden tener licencias distintas.

