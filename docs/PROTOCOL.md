# Attack Shark (Xenta 1d57) — battery channel protocol

Reverse-engineered by **passive observation only**: nothing was ever sent to the mouse
or the receiver. Builds on the work of
[Attack-Shark-Battery-KDE](https://gitlab.com/gabriel17166/Attack-Shark-Battery-KDE)
by Gabriel Marques Ferrarezi, which documented the `03 E5 40 ST NN` frame for Linux.

Status legend: ✅ confirmed by capture · 🟡 hypothesis · ❓ open

## Device tested

| Item | Value |
|---|---|
| Mouse | Attack Shark X11 (with magnetic charging dock) |
| Mode switch | `2.4G` · `OFF` (works wired over USB-C when OFF) · `BT` (BT1 / BT2) |
| OS | Windows 11 Pro 26200 |

## USB identities

| VID:PID | Product string | When it appears | Status |
|---|---|---|---|
| `1d57:fa60` | 2.4G Wireless Device | 2.4G receiver plugged in (always, even with the mouse off) | ✅ |
| `1d57:fa55` | USB Gaming Mouse | mouse connected by USB-C cable | ✅ (switch at OFF) |
| `1d57:2155` | — | wired mouse in the Linux project (different model/batch?) | reported upstream |

❓ Does `fa55` also appear with the cable plugged in while the switch is at 2.4G or BT?

## HID collections (identical layout on `fa60` and `fa55`)

Read from the descriptor cached by Windows (`HidP_GetCaps`), not from the device.

| Interface | Collection | Usage page / usage | Input | Output | Feature | Role |
|---|---|---|---|---|---|---|
| MI_00 | — | 0x01 / 0x06 Keyboard | 9 | 2 | 0 | macro keys |
| MI_01 | — | 0x01 / 0x02 Mouse | 8 | 0 | 0 | pointer |
| MI_02 | COL01 | 0x01 / 0x80 System Control | 2 | 0 | 0 | power keys |
| MI_02 | COL02 | 0x0C / 0x01 Consumer | 3 | 0 | 0 | media keys |
| MI_02 | **COL03** | **0x0A / 0x00** | **5** | 0 | 0 | **battery channel (push only)** ✅ |
| MI_02 | COL04 | 0x0B / 0x00 | 0 | 0 | 134 (`fa60`) / 262 (`fa55`) | configuration channel used by the vendor driver 🟡 |
| MI_03 | — | 0x01 / 0x06 Keyboard | 15 (`fa60`) / 8 (`fa55`) | 0 | 0 | — |

Notes:
- The battery collection has **no output and no feature reports**. It can only flow from device to host.
  Reading it cannot change any setting on the mouse.
- COL04 is feature-only. Opening it for reading fails with a read error, which is expected.
  This project **never opens it**. It is the path a configuration tool would use to write DPI, polling rate and similar settings.
- The usage pages 0x0A (Ordinal) and 0x0B (Telephony) are reused by the vendor as private channels.

## Battery frame

```
03 MM 40 ST NN
```

| Byte | Meaning | Status |
|---|---|---|
| 0 | Report ID `0x03` | ✅ |
| 1 | `0x55` on this X11; `0xE5` on the Linux project's mouse. Constant per device. Model or firmware marker? | ✅ value / ❓ meaning |
| 2 | Frame type: `0x40` = battery. `0x01` = link-blink frame (`03 MM 01 00 00`), which must be ignored | ✅ / reported upstream |
| 3 | State (table below) | partial |
| 4 | Level 0–100 (%) | ✅ |

Cadence: a frame arrives about every 2 s, but repeated frames are irregular (2–6 s apart) ✅.

### State byte

| ST | Seen when | Interpretation | Status |
|---|---|---|---|
| `01` | 2.4G, mouse in use, no cable or dock | on battery | ✅ |
| `03` | 2.4G on dock; wired (switch OFF) | external power, charging | ✅ |
| `02` | wired, switch OFF; alternates with `03` every 2–4 s | 🟡 external power, charge current paused (CV phase / trickle?) | 🟡 |

## Level accuracy (observed behaviour)

- During normal 2.4G use the level falls about 6%/h (84 → 76 over 78 min) ✅.
- Right after plugging or unplugging power the number jumps ✅. Examples: 72 → 100 within 1 min on cable;
  100 → 87 → 84 → 82 → 100 → 79 within ~80 s after removal.
  This suggests the level is derived from cell voltage, which jumps under charge voltage.
  It is also consistent with a worn cell (voltage sag under load) 🟡.
- On the dock, `03` (charging) was reported for only ~1 min and then reverted to `01`, even though the dock LED kept blinking.
  Possible poor pogo-pin contact ❓.

## Open questions → see [TEST-PLAN.md](TEST-PLAN.md)

1. Meaning of byte 1 (`55` vs `E5`).
2. Meaning of state `02`. Does `02`/`03` alternation also happen on the dock? Does `02` mean "full"?
3. What does the receiver `fa60` send in BT mode, with the switch at OFF and no cable, and while the mouse sleeps?
   Silence? Link-blink frames?
4. Does the cable carry data at the 2.4G and BT positions, or only power?
5. Does the dock (pogo pins) report `03` steadily once contact is good?
6. How long until the mouse sleeps in 2.4G mode, and does the receiver go silent?
7. Is there a full-charge state (a different ST, or `03` at 100)?
8. In BT mode, does Windows show the battery natively through the GATT Battery Service (0x180F)?
   Test by pairing BT with this PC.
