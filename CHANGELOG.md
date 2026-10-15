# Changelog

## [1.1.0]

- **English and Portuguese.** The first run asks for the language, and it can be changed later in the tray menu (*Language / Idioma*).
- **Installs and updates itself.** The `.exe` installs for the current user only, so no admin rights are needed. It goes to `%LOCALAPPDATA%\Programs\AttackSharkBattery` and adds a Start menu shortcut and an entry in *Settings → Apps*.
  Running a newer `.exe` closes the old one, replaces it and keeps your settings and history. This includes upgrading from 1.0.0.
- **Update check:** once a day, the app checks GitHub for a new release and shows a notification. It never downloads anything by itself, and you can turn it off with `"check_updates": false`.
- **Generic notifications** that make sense with any charger, whether a cable or a dock.
- **Wider device support:** listens to every Xenta (`1d57`) product, not only the three known PIDs. If a device is found but sends no battery data, the tooltip says so.
- **Report a problem** in the menu opens a GitHub issue pre-filled with diagnostics: device IDs, HID collections and recent raw frames.
- Settings are validated, and edits to `config.json` apply without restarting. The settings file opens in Notepad.
- The history CSV uses language-neutral columns. An older log is kept under a new name and never overwritten.
- Uninstall from the tray menu or from *Settings → Apps*.
- Release builds are made by GitHub Actions from the tagged source, with a self-test of the `.exe`.

## [1.0.0]

- First release.
