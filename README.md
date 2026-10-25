# Simple Launcher

An open-source Minecraft launcher for Windows, focused on managing profiles, versions, mods, modpacks, skins, and backups.

## Estado

First public release, currently in development. The current interface uses Python, CustomTkinter, and `minecraft-launcher-lib`. The next major step is separating the launcher logic to support a future UI migration.

## Funciones actuales

- Minecraft version installation and launching.
- Profiles and mod slots.
- Fabric support.
- Mod exploration through Modrinth.
- Backup import and export.
- Skin and screenshot management.
- Adaptive themes, dynamic colors, and multiple languages.

## Estructura

```text
source/                  Current source code
resources/              Fonts, icons, sounds, and other resources
builds/                 Local builds
releases/               Local distribution files
MATERIAL3_PLAN.md        Visual design plan
```

Executables, builds, working backups, and generated files are excluded from version control through `.gitignore`.

## Desarrollo local

Requires Python 3.12 or compatible and Java to run Minecraft.

```powershell
cd source
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python launcher_gui.pyw
```

## Nota legal

Minecraft is owned by Mojang/Microsoft. Modrinth, Fabric, and the included dependencies retain their own trademarks and licenses. This project is not officially affiliated with them. Review third-party licenses before redistributing a build.

## Contribuir

Bug reports, feature requests, and improvements are welcome. For major changes, open an issue describing the problem or proposal first. Do not include executables, builds, personal backups, caches, or Minecraft data.

## Licencia

The project code is distributed under the MIT License. Third-party resources may have different licenses.

