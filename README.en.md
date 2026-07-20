# husky_spike_esp32

**HuskyLens → ESP32 → LEGO SPIKE Prime: color tracking with SPIKE word blocks**

*[한국어 README](README.md) · English*

The ESP32 **emulates a LEGO SPIKE Color Sensor** over the LPF2 protocol. Vision data from a
HuskyLens AI camera (the detected color's ID and its X/Y position on screen) is mapped onto the
color sensor's **raw red / green / blue** values — so it can be read directly in SPIKE App 3
**word blocks**, with no extra software or plugins.

The result: a LEGO robot that sees a colored object and follows it, programmed entirely with
the Scratch-based word blocks kids already know.

**Every HuskyLens algorithm is supported** — the firmware detects the data type automatically.

**① Block algorithms** — color / object / object-tracking / face / tag recognition, classification

| Word block | Value it carries | Range |
|---|---|---|
| **color** | Detected ID | 0 ~ |
| **raw red** | Center X (left ↔ right) | 0 ~ 320 |
| **raw green** | Center Y (up ↕ down) | 0 ~ 240 |
| **raw blue** | Width W (larger = closer) | 0 ~ |

**② Arrow algorithm** — Line Tracking

| Word block | Value it carries | Range |
|---|---|---|
| **color** | 1 = line detected, 0 = none | 0 / 1 |
| **raw red** | Arrow origin X (right in front of the robot) | 0 ~ 320 |
| **raw green** | Arrow target X (where the line heads) | 0 ~ 320 |
| **raw blue** | Arrow target Y | 0 ~ 240 |

Nothing to configure on the ESP32 — **just switch the algorithm on the HuskyLens** and the meaning
of the values changes; only your SPIKE program needs to match.

---

## Hardware

- **NodeMCU ESP-32S** (classic ESP32 / WROOM) — has 3 UARTs, so LPF2 and the HuskyLens can run at the same time
- **HuskyLens** (DFRobot AI camera) — UART mode, Serial 9600
- **LEGO SPIKE Prime hub + SPIKE App 3**
- LPF2 breakout cable, jumper wires
- *(optional)* 3D-printed HuskyLens mount — see [`hardware/`](hardware/)

> ⚠️ The **ESP32-C3 is not suitable**: it has only one usable hardware UART, so LPF2 and the
> HuskyLens cannot both be served. Use a classic ESP32 (WROOM).

## Wiring

The signal wiring is the same for every setup. **What differs is where the power comes from** (see
*Powering it* below).

| Link | One side | Other side |
|---|---|---|
| SPIKE UART | Hub pin 5 (TX) / pin 6 (RX) | ESP32 **GPIO18 / GPIO19** |
| HuskyLens UART | HuskyLens T (green) / R (blue) | ESP32 **GPIO16 / GPIO17** |
| Ground (common) | Hub pin 3 | ESP32 GND + HuskyLens − |

The T/R lines must be **crossed** (HuskyLens T→GPIO16, R→GPIO17). LPF2 pin numbering differs
between cables, so check GND and power with a multimeter first. Logic is 3.3 V.

## Powering it (important)

**Recommended: power the ESP32 from USB and feed the HuskyLens from the 5V pin.**

![usb power](docs/usb_power.png)

The HuskyLens draws 320 mA or more at 3.3 V. Feeding the camera from the hub's pin 4 (3.3 V) leaves
almost no current margin, which can cause **high-pitched coil whine, voltage sag and reboots** (it
may still power up on the hub's 3.3 V, but barely). So it is best to power the camera separately.

| Method | Summary | Notes |
|---|---|---|
| ⭐ **USB power** | USB (power bank) → ESP32; feed HuskyLens + from the **5V/VIN pin**, − from ESP32 GND | Fewest parts, most stable. **Do NOT connect hub pin 4 (3.3 V)** ([docs/usb_power.png](docs/usb_power.png)) |
| Battery (single 18650) | A power-bank board with built-in boost + protection (e.g. **DFR0968**): USB 5 V out → ESP32 USB | Simplest for a mobile robot ([docs/dfr0968_power.png](docs/dfr0968_power.png)) |
| Battery (2S 18650) | 2×18650 in series (7.4 V) + **2S BMS** → **LM2596 down to 5 V** → ESP32 5V/VIN | If you have an LM2596 ([docs/bat18650_power.png](docs/bat18650_power.png)) |
| Separate 5 V | Power only the HuskyLens from an independent 5 V; **share GND only** | [docs/sep_power.png](docs/sep_power.png) |
| Hub 3.3 V + capacitor | Keep hub 3.3 V, add a **470–1000 µF** cap across the camera power pins | Stop-gap only ([docs/cap_diagram.png](docs/cap_diagram.png), [docs/full_wiring_cap.png](docs/full_wiring_cap.png)) |

In every method **all grounds must meet at one common point**, or UART will not work. Do not connect
a single 18650 directly — use a board/module with **5 V boost + protection** (the DFR0968 has boost
and over-charge/over-discharge protection built in, so one cell works directly). The firmware is the
same regardless of how you power it.

## Install

1. **Flash MicroPython and upload the firmware** (ESP32 connected over USB):
   ```bash
   python3 tools/install_firmware.py
   ```
   This downloads MicroPython (ESP32_GENERIC), flashes it, and uploads the three files from
   `firmware/`. To re-upload code only (keeping MicroPython):
   ```bash
   python3 tools/install_firmware.py --skip-flash
   ```

2. **Set up the HuskyLens**: Protocol Type = **Serial 9600**, algorithm = **Color Recognition**,
   then learn the target color (it becomes ID 1).

> If you upload manually, all three files — `main.py`, `lpf2.py`, `pupremote.py` — must be on the
> board. `lpf2.py` **must be the combo-mode patched version** (see *How it works* below).

## Reading the values

![mapping](docs/blocks_mapping.png)

Move the object left/right and **raw red (X)** changes; up/down changes **raw green (Y)**; bring it
closer and **raw blue (W)** grows.

## Tutorial: follow a colored ball

The working program — the robot turns left or right to keep the ball centered in the camera.
(Movement motors **A + E**, movement speed **15 %**, sensor on port **C**.)

![tracking](docs/redball_blocks.png)

- raw red (X) **< 120** → the ball is on the left → turn left (-100)
- raw red (X) **> 200** → the ball is on the right → turn right (100)
- in between (120–200) → centered → **stop moving**

Ideas to extend it: hold a distance using `raw blue` (W), react only to a specific `color` (ID), or
tilt the camera up/down with `raw green` (Y).

The same behavior as a SPIKE 3 **Python** program: [`examples/red_ball_tracker.py`](examples/red_ball_tracker.py).

**Going further — follow (with forward/back).** Beyond left/right steering, this example also keeps a
set distance using raw blue (W) to chase the object. Word blocks:
[`docs/follow_blocks.png`](docs/follow_blocks.png), Python:
[`examples/object_follower.py`](examples/object_follower.py).

![follow](docs/follow_blocks.png)

**Search + track + stop.** A three-way version: spin to search when nothing is visible, stop when the
object is very close. [`docs/smart_tracker_blocks.png`](docs/smart_tracker_blocks.png) /
[`examples/smart_color_tracker.py`](examples/smart_color_tracker.py).

## Line tracing

Switch the HuskyLens algorithm to **Line Tracking**, learn a line, and the same firmware turns the
robot into a line follower. Steering comes from **raw red** (the line position right in front of the
robot, centre = 160).

![line](docs/line_blocks.png)

The Python version [`examples/line_follower.py`](examples/line_follower.py) also adds
**raw green − raw red** (how the line curves ahead) for smoother cornering.

> If it steers the wrong way, swap the motor pair; if it wobbles, divide by a larger number
> (`÷2` → `÷3`). Make sure the sensor blocks all use **the port the ESP32 is plugged into**.

## How it works (combo mode)

SPIKE 3 reads several color-sensor values in one go using **combo mode** (a `0x5C` setup packet).
This hub requests six values in the order **color, reflection, R, G, B, 4th**. The firmware
(`lpf2.py`) parses that request packet and replies with the values **in exactly that order and
size**. That is why raw red (R) = X, raw green (G) = Y and raw blue (B) = W line up correctly.

The stock `lpf2` library does not handle combo mode — it returns empty values (65535) — so the
`lpf2.py` in this repository is a patched version that adds combo handling (`0x5C` / `0x4C` plus a
dynamic response).

## Repository layout

```
firmware/
  main.py          Main firmware (read HuskyLens → serve it as color-sensor values)
  lpf2.py          LPF2 library (patched: combo-mode support)
  pupremote.py     PUPRemote library
tools/
  install_firmware.py   Flashes MicroPython and uploads the firmware
examples/
  red_ball_tracker.py     SPIKE 3 Python tracker (left/right steering)
  object_follower.py      Follower (steering + forward/back)
  smart_color_tracker.py  Search + track + stop (three-way)
  line_follower.py        Line tracing (Line Tracking mode)
hardware/
  huskylens_lego_mount.stl   3D-printable HuskyLens mount for LEGO Technic
docs/
  usb_power.png         ⭐ recommended power wiring (USB)
  sep_power.png, cap_diagram.png, full_wiring_cap.png   power options
  redball_blocks.png, follow_blocks.png   word-block examples
  blocks_mapping.png, blocks_tracking.png, wiring.png
  guide (DOCX), elementary-school lesson book (DOCX/PDF, Korean)
```

## 3D-printed HuskyLens mount

`hardware/huskylens_lego_mount.stl` is a bracket that holds the HuskyLens and attaches to LEGO
Technic beams, so the camera can be mounted rigidly on the robot.

Suggested print settings: PLA, 0.2 mm layer height, ~20 % infill, no supports needed for most
orientations. Print the frame so the pin holes run along the print bed for the strongest fit.

## Troubleshooting

| Symptom | What to check |
|---|---|
| No color sensor appears on the port | LPF2 wiring (pin5↔GPIO18, pin6↔GPIO19, GND), firmware uploaded |
| Sensor appears then disappears | Use the latest `main.py` (it services the hub frequently enough) |
| Raw values read 65535 | `lpf2.py` must be the combo-patched version |
| Raw values read 512 / 60416 etc. | Use the latest `lpf2.py` + `main.py` (dynamic combo response) |
| Values flicker between 0 and the real value | Latest `main.py` (debounce + no unsolicited frames) |
| Values never change | HuskyLens Serial 9600, color learned, T→GPIO16 and R→GPIO17 crossed correctly |
| Odd values persist | Restart the sensor view in the SPIKE app (clears cached readings) |

## Related work — and how this project differs

The idea of emulating a color sensor is not new. Here is how this repository compares.

| Project | Approach | Word blocks | Board |
|---|---|---|---|
| [Anton's Mindstorms — HuskyLens with Block Code](https://www.antonsmindstorms.com/2025/07/26/huskylens-spike-prime-blocks/) (2025) | Color-sensor emulation + MicroBlocks | ✅ | Dedicated **LMS-ESP32** |
| [Anton's Mindstorms — Pybricks + HuskyLens](https://www.antonsmindstorms.com/2024/11/24/pybricks-huskylens-a-simple-spike-prime-camera-line-follower/) | Pybricks Python | ❌ | LMS-ESP32 |
| [ysard/MyOwnBricks](https://github.com/ysard/MyOwnBricks) | Arduino color-sensor emulation library | (no hub-connected example) | AVR / Arduino |
| [DanieleBenedettelli/HuskyLensSPIKE](https://github.com/DanieleBenedettelli/HuskyLensSPIKE) | MicroPython library on the hub itself | ❌ | No extra board |
| **This repository** | Color-sensor emulation + **MicroPython** | ✅ | **Generic NodeMCU ESP-32S** |

What is specific to this repository:

- **No dedicated board required** — any common NodeMCU ESP-32S (WROOM) works.
- **MicroPython with a combo-mode patch.** SPIKE App 3 reads color-sensor values through combo mode
  (`0x5C`). This firmware parses that request and answers with the values in exactly the same order and
  size. The published `lpf2.py` (antonvh/PUPRemote) does not handle combo mode, so word blocks read
  65535 — this patch is the core contribution here.
- A documented mapping of HuskyLens **ID / center X / center Y / width W** onto color, raw red, raw
  green and raw blue.
- Ships with a 3D-printable mount (STL), an automated installer, and a lesson book for young learners.

## License & credits

Released under **GPL-3.0** (see [LICENSE](LICENSE)). This project uses and builds on the following
GPL open-source work:

- [`lpf2.py`, `pupremote.py`](https://github.com/antonvh/PUPRemote) — © Anton's Mindstorms (GPL-3.0).
  The `lpf2.py` here is modified to add SPIKE 3 combo-mode support.
- The color-sensor mode structure and combo-mode behavior are based on
  [MyOwnBricks](https://github.com/ysard/MyOwnBricks) — © Ysard (GPL-3.0).
- HuskyLens: [DFRobot](https://wiki.dfrobot.com/HUSKYLENS_V1.0_SKU_SEN0305_SEN0336)
