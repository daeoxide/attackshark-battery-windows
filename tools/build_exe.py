"""Gera dist/AttackSharkBattery.exe (arquivo unico, roda sem Python instalado).

Uso: python tools/build_exe.py
Requer: pip install pyinstaller (alem do requirements.txt)
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD = os.path.join(ROOT, "build")


def make_ico(path):
    """Icone do .exe: bateria branca sobre quadrado verde."""
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 255, 255), radius=48, fill=(40, 170, 70))
    d.rounded_rectangle((44, 80, 196, 176), radius=14, outline="white", width=14)
    d.rectangle((196, 108, 216, 148), fill="white")
    d.rectangle((66, 102, 150, 154), fill="white")
    img.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def main():
    os.makedirs(BUILD, exist_ok=True)
    ico = os.path.join(BUILD, "icon.ico")
    make_ico(ico)
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", "AttackSharkBattery",
        "--icon", ico,
        "--hidden-import", "pystray._win32",
        "--distpath", os.path.join(ROOT, "dist"),
        "--workpath", os.path.join(BUILD, "work"),
        "--specpath", BUILD,
        os.path.join(ROOT, "x11_battery.pyw"),
    ], check=True, cwd=ROOT)
    print("\nPronto:", os.path.join(ROOT, "dist", "AttackSharkBattery.exe"))


if __name__ == "__main__":
    main()
