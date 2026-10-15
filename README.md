# Attack Shark Battery Tray (Windows)

Shows the battery level of Attack Shark wireless mice (Xenta chipset, VID `1d57`) in the Windows system tray, and warns you before the battery runs out.

Windows has no built-in way to show this, and the official software shows no percentage.
The receiver does broadcast the level every ~2 s on a vendor HID channel, and this app listens to it.

> Windows counterpart of [Attack-Shark-Battery-KDE](https://gitlab.com/gabriel17166/Attack-Shark-Battery-KDE) (Linux) by Gabriel Marques Ferrarezi, who first documented the battery protocol.

**[Português abaixo](#português)**

## Install

1. Download `AttackSharkBattery.exe` from the [latest release](https://github.com/daeoxide/attackshark-battery-windows/releases/latest).
2. Run it. Choose your language and whether it should start with Windows.
3. The battery icon appears next to the clock. If you don't see it, click the **^** arrow in the taskbar, then drag the icon onto the taskbar.

It installs for your user only (no admin rights) into `%LOCALAPPDATA%\Programs\AttackSharkBattery`, with a Start menu shortcut.
**To update**, download and run the newer `.exe`. It replaces the installed copy and keeps your settings.
The app also tells you when a new version is out. **To uninstall**, use the tray menu or *Settings → Apps*.

Windows SmartScreen may warn about an unknown publisher, because the file is not code-signed.
Click **More info → Run anyway**. Releases are built by GitHub Actions from the tagged source, and each release lists the file's SHA-256.

## Features

- **Tray icon** showing the percentage, coloured by level:
  - green above 40%
  - yellow at 21–40%
  - red at the low-battery level or below
  - blue with a bolt when charging (cable or dock)
  - grey when the mouse is asleep, off or in Bluetooth mode
- **Notifications:**
  - low battery at 20%, repeated every 10 min until you plug it in
  - critical battery at 10%, with an alarm sound
  - charging that keeps cutting out (loose cable or dock contact)
  - optionally at 100% (off by default: the level is only approximate while charging)
- **Works over the 2.4G receiver and over the USB cable.**
- **English and Portuguese.**
- **Battery history** (`battery_log.csv`): every change of level or state. Useful for spotting a worn battery.
- **No drivers, no admin rights, and no hidapi.** Uses only Windows APIs through `ctypes`.

## Strictly read-only

The app **cannot** send anything to the mouse. You can verify this in [`attackshark_battery/hidread.py`](attackshark_battery/hidread.py):

- **Opened read-only.** The battery collection is opened with `GENERIC_READ` only, so Windows rejects any write on that handle with error 5.
  `tests/test_readonly.py` proves it on real hardware.
- **Nothing to write to anyway.** The battery collection has no output or feature reports.
  The configuration channel (feature-only collection) is never opened.
- **No device requests.** Enumeration uses only data Windows already holds: the CfgMgr32 interface list and the cached HID descriptor.
  The app never calls `HidD_GetFeature`, `HidD_Get*String` or `DeviceIoControl`.
- **No extra traffic.** `ReadFile` only copies input reports that the Windows HID driver polls anyway, whether or not the app is running.
- **Checked automatically.** A static test fails the build if any write-capable API appears in the code.

The only network access is the daily update check: one request to the GitHub releases API. It can be turned off with `check_updates`.

## Supported devices

The app listens to every product with the Xenta vendor ID `1d57` that has a battery-like HID collection, and only accepts frames in the exact battery format (`03 xx 40 state level`, repeated twice).

| VID:PID | Connection | Status |
|---|---|---|
| `1d57:fa60` | 2.4G receiver | tested (Attack Shark X11) |
| `1d57:fa55` | mouse on USB cable | tested (Attack Shark X11) |
| `1d57:2155` | mouse on USB cable | reported by the Linux project |
| other `1d57` PIDs | — | detected automatically, untested |

Tested so far on the **Attack Shark X11**. The Linux project confirms the same protocol on another model, with a different model byte (`0xE5` instead of `0x55`).
Attack Shark models built on other chipsets (other vendor IDs) are not supported.

**Does it work with your mouse?** Please tell us either way. Right-click the icon → **Report a problem** opens a GitHub issue with the diagnostics already filled in (device IDs and the last raw frames, nothing personal).
Add your mouse model. If the tooltip says *device found but no battery data*, that report is exactly what's needed to add support.

Full protocol notes: **[docs/PROTOCOL.md](docs/PROTOCOL.md)**.

## Settings

Right-click → **Advanced settings** opens `config.json` in Notepad. Changes apply as soon as you save.

```json
{
  "language": "en",
  "warn_percent": 20,
  "critical_percent": 10,
  "repeat_minutes": 10,
  "notify_full": false,
  "notify_bad_contact": true,
  "sleep_after_seconds": 30,
  "check_updates": true
}
```

| Key | Meaning |
|---|---|
| `language` | `en` or `pt` (also in the tray menu) |
| `warn_percent` / `critical_percent` | battery levels for the low and critical notifications |
| `repeat_minutes` | how often the low-battery notification repeats |
| `notify_full` | notify when the battery reads 100% while charging |
| `notify_bad_contact` | notify when charging keeps cutting out |
| `sleep_after_seconds` | silence after which the mouse counts as asleep or off (the icon turns grey) |
| `check_updates` | check GitHub once a day for a new version |

Settings and history live in `%LOCALAPPDATA%\AttackSharkBattery`.

## Run from source

Requires Python 3.10+ on Windows 10/11.

```powershell
git clone https://github.com/daeoxide/attackshark-battery-windows
cd attackshark-battery-windows
powershell -ExecutionPolicy Bypass -File install.ps1
```

`install.ps1` installs the dependencies, runs the read-only check and starts the app.
To do it by hand, run `pip install -r requirements.txt`, then `pythonw attackshark_battery_tray.pyw`.
When run from source, settings and history are kept in the project folder.

**Build the .exe:** run `pip install pyinstaller`, then `python tools/build_exe.py`. The output is `dist/AttackSharkBattery.exe`.

**Make a release:** bump `__version__` in `attackshark_battery/__init__.py`, add a section to `CHANGELOG.md`, merge it, then push a tag such as `v1.1.0`.
GitHub Actions builds, tests and publishes the release.

## Tools for mapping a new model

- `python tools/mapper.py [minutes]` records every frame from any `1d57` device to a CSV file.
- `pythonw tools/test_wizard.pyw` is a guided recording session, in Portuguese, written for the X11 (cable, 2.4G, dock, BT, sleep).
  See [docs/TEST-PLAN.md](docs/TEST-PLAN.md).
- `python -m pytest tests` runs the checks.

## Credits

- **Protocol discovery:** [Attack-Shark-Battery-KDE](https://gitlab.com/gabriel17166/Attack-Shark-Battery-KDE) by Gabriel Marques Ferrarezi (MIT).
  He found the `03 E5 40 ST NN` frame and the link-blink trap.
- **This project:** a Windows port written from scratch. It adds the `0x55` model byte, state `0x02`, the wired PID `fa55`, the HID collection map and the read-only guarantees.

MIT License.

---

## Português

Mostra a porcentagem da bateria do mouse sem fio Attack Shark (chipset Xenta, VID `1d57`) na bandeja do Windows e avisa antes de acabar.

**Instalar:**

1. Baixe o `AttackSharkBattery.exe` da [última versão](https://github.com/daeoxide/attackshark-battery-windows/releases/latest) e rode.
2. Escolha o idioma e se ele deve iniciar com o Windows.
3. O ícone aparece perto do relógio. Se não aparecer, clique na setinha **^** da barra de tarefas.

Ele é instalado só para o seu usuário (sem administrador), e você não precisa ter Python.
O Windows SmartScreen pode avisar sobre editor desconhecido, porque o arquivo não tem assinatura digital. Clique em **Mais informações → Executar assim mesmo**.

- **Atualizar:** baixe e rode o `.exe` mais novo. Ele substitui o instalado e mantém suas configurações. O app também avisa quando sai uma versão nova.
- **Desinstalar:** pelo menu do ícone ou em *Configurações → Aplicativos*.
- **Avisos:** bateria baixa (20%), crítica (10%, com alarme) e carregamento que fica caindo (cabo ou contato da dock).
- **Somente leitura:** o app nunca envia nada ao mouse. Veja a seção *Strictly read-only* acima.
- **Seu mouse funcionou ou não?** Clique com o botão direito no ícone e escolha **Relatar um problema**. Isso abre uma issue no GitHub com o diagnóstico já preenchido. Só falta dizer o modelo do mouse.
  Até agora o app foi testado no Attack Shark X11.
