# Attack Shark Battery Tray (Windows)

Shows the battery level of Attack Shark wireless mice (Xenta chipset, VID `1d57`) in the Windows system tray.
It also warns you before the battery runs out.

Windows has no built-in way to show this, and the official software shows no percentage.
The receiver does broadcast the level every ~2 s on a vendor HID channel, and this app listens to it.

> Windows counterpart of [Attack-Shark-Battery-KDE](https://gitlab.com/gabriel17166/Attack-Shark-Battery-KDE) (Linux) by Gabriel Marques Ferrarezi, who first documented the battery protocol.

*Português:* mostra a % de bateria do mouse Attack Shark na bandeja do Windows e avisa quando chegar em 20% / 10%.
É somente leitura: não envia nada ao mouse.

## Features

- **Tray icon** showing the percentage, coloured by level:
  - green above 40%
  - yellow at 21–40%
  - red at 20% or below
  - blue with a bolt when on cable or dock
  - grey when the mouse is asleep, off or in BT mode
- **Toast notifications:**
  - at 20%, repeated every 10 min until charging
  - at 10%, with an alarm sound
  - when the dock contact is bad (charging keeps switching on and off)
  - optionally at 100% (off by default: the level is approximate while on external power)
- **Works over the 2.4G receiver and over the USB-C cable.**
- **History file** (`battery_log.csv`): every change of level or state, with the raw frame. Useful for spotting a worn battery.
- **No drivers, no admin rights, and no hidapi.** Uses only Windows APIs through `ctypes`.

## Strictly read-only

The app **cannot** send anything to the mouse. You can verify this in [`attackshark_battery/hidread.py`](attackshark_battery/hidread.py):

- **Opened read-only.** The battery collection is opened with `GENERIC_READ` only, so Windows rejects any write on that handle with error 5.
  `tests/test_readonly.py` proves it on real hardware.
- **Nothing to write to anyway.** The battery collection has no output or feature reports.
  The configuration channel (feature-only collection `0x0B`) is never opened.
- **No device requests.** Enumeration uses only data Windows already holds: the CfgMgr32 interface list and the cached HID descriptor.
  The app never calls `HidD_GetFeature`, `HidD_Get*String` or `DeviceIoControl`.
- **No extra traffic.** `ReadFile` only copies input reports that the Windows HID driver polls anyway, whether or not the app is running.
- **Checked automatically.** A static test fails the build if any write-capable API appears in the code.

## Supported devices

| VID:PID | Connection |
|---|---|
| `1d57:fa60` | 2.4G receiver |
| `1d57:fa55` | mouse on USB-C cable (switch OFF) |
| `1d57:2155` | wired variant reported by the Linux project |

Tested on the **Attack Shark X11**. The battery frame's model byte is `0x55` on the X11 and `0xE5` on other models, and both are accepted.
Please open an issue with a capture from `tools/mapper.py` if your model behaves differently.

Full protocol notes: **[docs/PROTOCOL.md](docs/PROTOCOL.md)**.

## Install

### Option 1: download the .exe (no Python needed)

1. Download `AttackSharkBattery.exe` from the [latest release](https://github.com/daeoxide/attackshark-battery-windows/releases/latest).
2. Run it. The icon appears next to the clock.
3. Right-click the icon and tick **Iniciar com o Windows** to start it with Windows.

Windows SmartScreen may warn about an unknown publisher, because the file is not code-signed.
Click **More info → Run anyway**. You can also build the .exe yourself from source (see below).
Settings and history live in `%LOCALAPPDATA%\AttackSharkBattery`.

### Option 2: run from source

Requires Python 3.10+ on Windows 10/11.

```powershell
git clone https://github.com/daeoxide/attackshark-battery-windows
cd attackshark-battery-windows
powershell -ExecutionPolicy Bypass -File install.ps1
```

`install.ps1` installs the dependencies, runs the read-only check, adds a shortcut in `shell:startup` and starts the app.
To do it by hand instead, run `pip install -r requirements.txt` and then `pythonw x11_battery.pyw`.
Only one copy runs at a time.

To build the .exe yourself: `pip install pyinstaller`, then `python tools/build_exe.py`. The output is `dist/AttackSharkBattery.exe`.

Settings are in `config.json`, which is created on first run:

```json
{ "warn_percent": 20, "critical_percent": 10, "repeat_minutes": 10, "notify_full": true, "sleep_after_seconds": 30 }
```

## Tools

- `pythonw tools/test_wizard.pyw` opens a window that walks you through every mode (cable, 2.4G, dock, BT, sleep) and records all frames
  (see [docs/TEST-PLAN.md](docs/TEST-PLAN.md)). Captures go to `docs/captures/`.
- `python tools/mapper.py [minutes]` records freely from the console.
- `python tests/test_readonly.py` and `python tests/test_protocol.py` run the checks.

## Credits

- **Protocol discovery:** [Attack-Shark-Battery-KDE](https://gitlab.com/gabriel17166/Attack-Shark-Battery-KDE) by Gabriel Marques Ferrarezi (MIT).
  He found the `03 E5 40 ST NN` frame and the link-blink trap.
- **This project:** a Windows port written from scratch. It adds the `0x55` model byte, state `0x02`, the wired PID `fa55`, the HID collection map and the read-only guarantees.

MIT License.
