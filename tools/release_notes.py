"""Release notes for a tag: the CHANGELOG section, download steps and the .exe SHA-256.

Usage: python tools/release_notes.py v1.1.0 dist/AttackSharkBattery.exe
"""
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def changelog_section(version):
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^## \[?{re.escape(version)}\]?.*?$\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def main(tag, exe):
    version = tag.lstrip("v")
    sha = hashlib.sha256(pathlib.Path(exe).read_bytes()).hexdigest()
    print(f"""{changelog_section(version)}

### Install / update

Download **`AttackSharkBattery.exe`** below and run it. Python is not needed.
It installs itself for your user (no admin rights), asks for the language, and the battery icon appears next to the clock.
Running a newer `.exe` later updates the installed copy and keeps your settings.

The file is not code-signed, so Windows SmartScreen may warn about it: click *More info → Run anyway*.
It was built by GitHub Actions from the tagged source code.

SHA-256: `{sha}`
""")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:3])
