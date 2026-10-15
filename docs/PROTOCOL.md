# Attack Shark (Xenta 1d57) — battery channel protocol

Reverse-engineered by **passive observation only**: nothing was ever sent to the mouse
or the receiver. Builds on the work of
[Attack-Shark-Battery-KDE](https://gitlab.com/gabriel17166/Attack-Shark-Battery-KDE)
by Gabriel Marques Ferrarezi, which documented the `03 E5 40 ST NN` frame for Linux.

Status legend: ✅ confirmed by capture · 🟡 hypothesis · ❓ open

Main capture: [`captures/2026-10-14_2335_assistente.csv`](captures/2026-10-14_2335_assistente.csv).
It covers 13 guided steps, starts with the official software closed, and includes the user's notes for each step.

## Device tested

| Item | Value |
|---|---|
| Mouse | Attack Shark X11 (with magnetic charging dock) |
| Mode switch | `2.4G` · `OFF` · `BT` (BT1 / BT2 selected on the mouse) |
| Mouse LED on external power | purple = charging, green = powered, not charging (user observation) |
| OS | Windows 11 Pro 26200 |

## USB identities

| VID:PID | Product string | When it appears | Status |
|---|---|---|---|
| `1d57:fa60` | 2.4G Wireless Device | 2.4G receiver plugged in, whether or not the mouse is on | ✅ |
| `1d57:fa55` | USB Gaming Mouse | mouse on the USB-C cable, **whatever the switch position** (OFF, 2.4G or BT) | ✅ |
| `1d57:2155` | — | wired mouse in the Linux project (different model or batch?) | reported upstream |

✅ The **cable always wins**. At any switch position the mouse works wired and reports its battery through `fa55`.
The receiver `fa60` stays silent meanwhile.

## HID collections (identical layout on `fa60` and `fa55`)

Read from the descriptor cached by Windows (`HidP_GetCaps`), not from the device.

| Interface | Collection | Usage page / usage | Input | Output | Feature | Role |
|---|---|---|---|---|---|---|
| MI_00 | — | 0x01 / 0x06 Keyboard | 9 | 2 | 0 | macro keys |
| MI_01 | — | 0x01 / 0x02 Mouse | 8 | 0 | 0 | pointer |
| MI_02 | COL01 | 0x01 / 0x80 System Control | 2 | 0 | 0 | power keys |
| MI_02 | COL02 | 0x0C / 0x01 Consumer | 3 | 0 | 0 | media keys |
| MI_02 | **COL03** | **0x0A / 0x00** | **5** | 0 | 0 | **battery channel (push only)** ✅ |
| MI_02 | COL04 | 0x0B / 0x00 | 0 | 0 | 134 (`fa60`) / 262 (`fa55`) | configuration channel used by the vendor software 🟡 |
| MI_03 | — | 0x01 / 0x06 Keyboard | 15 (`fa60`) / 8 (`fa55`) | 0 | 0 | — |

Notes:
- The battery collection has **no output and no feature reports**. It can only flow from device to host.
- COL04 is feature-only, so reading it gives a read error. This project never opens it.
- The vendor reuses usage pages 0x0A (Ordinal) and 0x0B (Telephony) as private channels.

## Battery frame

```
03 MM 40 ST NN
```

| Byte | Meaning | Status |
|---|---|---|
| 0 | Report ID `0x03` | ✅ |
| 1 | `0x55` on this X11, `0xE5` on the Linux project's mouse. Constant per device. Model or firmware marker? | ✅ value / ❓ meaning |
| 2 | Frame type: `0x40` = battery. `0x01` = link-blink frame (`03 MM 01 00 00`, reported upstream, never seen here) | ✅ |
| 3 | State (table below) | ✅ |
| 4 | Level 0–100 (%) | ✅ |

Cadence: one frame **every 2 s**, sent whenever the mouse is powered and linked ✅.
That covers on battery, on cable and on the dock. Opening the official software does not change it ✅.

### State byte

| ST | Meaning | Evidence | Status |
|---|---|---|---|
| `01` | on battery | every wireless step | ✅ |
| `02` | external power, **not charging** (charge paused / topped-off) | matches the green LED. Dominant on cable at 85% and on the dock once settled | ✅ (LED match) |
| `03` | external power, **charging** | matches the purple LED | ✅ (LED match) |

On external power the mouse **alternates `02` and `03`** every 2–20 s, with `02` dominating. This looks like a charger in its top-off phase.
The same pattern shows on cable and on dock ✅.

### ⚠ Spurious "100%" frame on (re)connection

**Every time** the mouse links to the receiver, it sends one isolated `03 MM 40 01 64` frame ("on battery, 100%") ✅.
This happens when the mouse wakes, the switch passes through 2.4G, it is lifted from the dock, or dock contact bounces.
The real level follows 2 s later.

Seen 7 times in one session, always a single frame: 23:41:44, 23:49:14, 23:49:22, 23:49:43, 23:53:32, 23:56:36, 00:00:17 and 00:01:32.

**Handling:** only accept a `(state, level)` pair after it arrives **twice in a row**.
This is the counterpart of the "false zero" trap in the Linux project.

### Level accuracy

- **On battery:** monotonic and plausible. Right after charging it fell 97 → 90 in about 8 min,
  which is typical of voltage-based estimation (surface charge). Earlier it fell about 6%/h around 80% ✅.
- **On external power:** the level is **not a live measurement**. It stayed frozen at 85 on cable for 6 min, and at 92 or 100 on the dock.
  After removal it reads several points higher than before (85 on cable → 97 after unplugging) ✅.
  Treat it as approximate. The app labels it "aprox." and does not trust it for a "full" notification.
- The official software shows no number, only a bar. That bar looked like "80–90%" while this channel read 89% ✅ consistent.

### Sleep / off / Bluetooth

| Situation | Receiver `fa60` | Status |
|---|---|---|
| 2.4G untouched for 6 min | keeps sending every 2 s (no sleep within 6 min) | ✅ |
| 2.4G untouched ≥ 10 min / 30 min | sleep / deep sleep per the mouse settings (owner's config, factory default?). The tray app logs a `sem sinal` row when frames stop, to measure this | 🟡 |
| switch OFF, no cable, no dock | silent | ✅ |
| switch OFF **on the dock** | **keeps sending** (`02`/`03`, level 100): the radio stays up while externally powered | ✅ |
| BT (linked to another PC) | silent | ✅ |
| switching through positions | spurious `01 64` + one real frame | ✅ |

Silence means the mouse is off or in BT mode. It never means 0%.

### Dock contact

At the start of the dock step the stream flapped between `01` and `03` seven times in 30 s.
The user confirmed they had to press the mouse down for the LED to turn purple, which points to **poor pogo-pin contact** ✅.
The app detects this pattern (≥ 4 battery ↔ power changes within 60 s) and shows a notification.
Replaying the capture flags exactly that minute and nothing else.

## Other devices seen

`3554:fa09` is the owner's wireless **keyboard** receiver (CompX), not part of the mouse. Its vendor collection `ff02` sent
`13 0a 01 00 04 02 0X 00 … 2X` at irregular intervals (minutes), with byte 6 toggling between 00 and 01.
It is unrelated to any mouse event.

## Open questions

1. Meaning of byte 1 (`55` vs `E5`).
2. Is there a distinct "full" state, e.g. a constant `02` at a real 100%? This needs a long charge from low to full on the dock.
3. Does the receiver go silent at the 10 min sleep, or only at the 30 min deep sleep? The `sem sinal` rows in `battery_log.csv` will tell.
4. In BT mode paired with *this* PC, does Windows show the battery natively (GATT Battery Service 0x180F)?
5. Battery health: a full discharge curve from the history log, compared against the X11's rated runtime.
