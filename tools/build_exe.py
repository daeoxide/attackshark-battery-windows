"""Gera dist/AttackSharkBattery.exe (arquivo unico, roda sem Python instalado).

Uso: python tools/build_exe.py
Requer: pip install -r requirements.txt pyinstaller
"""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD = os.path.join(ROOT, "build")
sys.path.insert(0, ROOT)
from attackshark_battery import APP_NAME, REPO, __version__  # noqa: E402
from attackshark_battery.icons import app_icon  # noqa: E402

VERSION_INFO = """VSVersionInfo(
  ffi=FixedFileInfo(filevers={v4}, prodvers={v4}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'github.com/{repo}'),
      StringStruct('FileDescription', '{name}'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('InternalName', 'AttackSharkBattery'),
      StringStruct('LegalCopyright', 'MIT License'),
      StringStruct('OriginalFilename', 'AttackSharkBattery.exe'),
      StringStruct('ProductName', '{name}'),
      StringStruct('ProductVersion', '{v}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main():
    os.makedirs(BUILD, exist_ok=True)
    ico = os.path.join(BUILD, "icon.ico")
    app_icon(256).save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    nums = tuple(int(n) for n in __version__.split("."))
    version_file = os.path.join(BUILD, "version_info.txt")
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(VERSION_INFO.format(v4=nums + (0,) * (4 - len(nums)), v=__version__, name=APP_NAME, repo=REPO))
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", "AttackSharkBattery",
        "--icon", ico,
        "--version-file", version_file,
        "--hidden-import", "pystray._win32",
        "--distpath", os.path.join(ROOT, "dist"),
        "--workpath", os.path.join(BUILD, "work"),
        "--specpath", BUILD,
        os.path.join(ROOT, "attackshark_battery_tray.pyw"),
    ], check=True, cwd=ROOT)
    print("\nPronto:", os.path.join(ROOT, "dist", "AttackSharkBattery.exe"), __version__)


if __name__ == "__main__":
    main()
