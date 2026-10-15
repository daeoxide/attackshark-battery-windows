# Test plan — mapping every mode

Run `pythonw tools/test_wizard.pyw`. It opens a window that shows one step at a time, with a countdown and a live readout of what the PC sees.
Each step and its answer note are written to the capture CSV in `docs/captures/`.

**Close the official Attack Shark app first.** It talks to the mouse through its configuration channel, so it could change what we observe.
The wizard checks that it is closed, and the last step reopens it for comparison.

Everything is passive: the tool only listens on the battery collection (input-only), opened read-only.

| # | Switch | Cable (USB-C to PC) | Dock | Action | Answers |
|---|---|---|---|---|---|
| 1 | OFF | plugged | — | idle | baseline wired; `02`/`03` alternation |
| 2 | 2.4G | plugged | — | move mouse | Does the cable carry data at 2.4G? Which PID appears? |
| 3 | BT | plugged | — | — | Same question for the BT position |
| 4 | 2.4G | — | — | move mouse | baseline `01` |
| 5 | 2.4G | — | — | **don't touch for 5 min** | Sleep timeout. Does the receiver go silent or send link frames? |
| 6 | 2.4G | — | — | move to wake it | wake-up behaviour, level jump? |
| 7 | 2.4G | — | on dock | check the contact is firm, wait **3 min** | Is `03` steady on the dock? Does `02` appear? |
| 8 | OFF | — | on dock | wait 2 min | Does the dock charge with the switch OFF? Does the receiver go silent? |
| 9 | OFF | — | — | — | Receiver behaviour with the mouse fully off |
| 10 | BT1 (paired to the other PC) | — | — | use it on the other PC | Does the receiver here go silent? |
| 11 | BT2 (paired to **this** PC) | — | — | optional | Does Windows show battery natively (Settings › Bluetooth)? |
| 12 | 2.4G | — | — | back to normal | sanity check |

Later, a long run: leave the tray app running for days. `battery_log.csv` then records a full discharge curve,
and a full charge on the dock, so we can check whether a "full" state exists.
