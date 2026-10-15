"""Attack Shark - bateria do mouse na bandeja do Windows (somente leitura).

Protocolo: attackshark_battery/protocol.py e docs/PROTOCOL.md.
"""
import csv
import json
import os
import sys
import threading
import time
from datetime import datetime

import pystray
from PIL import Image, ImageDraw, ImageFont
from winotify import Notification, audio

from attackshark_battery.monitor import BatteryMonitor
from attackshark_battery.protocol import PRODUCTS

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
LOG_PATH = os.path.join(BASE, "battery_log.csv")
LOG_HEADER = ["data_hora", "percent", "estado", "fonte", "frame"]

DEFAULT_CONFIG = {
    "warn_percent": 20,
    "critical_percent": 10,
    "repeat_minutes": 10,
    "notify_full": True,
    "sleep_after_seconds": 30,
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
    except Exception:
        pass
    return cfg


cfg = load_config()
stop = threading.Event()
_log_lock = threading.Lock()
_last_logged = None


def log_frame(frame, pid):
    """Grava no CSV quando nivel, estado ou fonte mudam."""
    global _last_logged
    key = (frame.level, frame.state, pid)
    with _log_lock:
        if key == _last_logged:
            return
        _last_logged = key
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, encoding="utf-8") as f:
                if f.readline().strip() != ",".join(LOG_HEADER):
                    f.close()
                    os.replace(LOG_PATH, LOG_PATH.replace(".csv", "_v1.csv"))
        new = not os.path.exists(LOG_PATH)
        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(LOG_HEADER)
            w.writerow([datetime.now().isoformat(timespec="seconds"), frame.level,
                        frame.state_name, f"{pid:04x}", frame.raw.hex(" ")])


monitor = BatteryMonitor(on_frame=log_frame)


def color_for(pct, on_power, asleep):
    if asleep or pct is None:
        return (128, 128, 128)
    if on_power:
        return (40, 120, 230)
    if pct <= cfg["warn_percent"]:
        return (220, 40, 40)
    if pct <= 40:
        return (230, 180, 0)
    return (40, 170, 70)


def load_font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_BIG, FONT_SMALL = load_font(40), load_font(26)


def make_icon(pct, on_power, asleep):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 63, 63), radius=12, fill=color_for(pct, on_power, asleep))
    text = "?" if pct is None else str(pct)
    font = FONT_BIG if len(text) < 3 else FONT_SMALL
    d.text((32, 30), text, font=font, fill="white", anchor="mm")
    if on_power:
        d.polygon([(50, 2), (42, 16), (49, 16), (44, 28), (58, 12), (51, 12), (56, 2)],
                  fill=(255, 230, 0))
    return img


def tooltip(frame, pid, asleep, age, present):
    if not present and frame is None:
        return "Mouse: receptor/cabo nao encontrado"
    if frame is None:
        return "Mouse: aguardando leitura (mexa o mouse)"
    if asleep:
        return f"Mouse: {frame.level}% (ultima leitura ha {int(age // 60)} min - dormindo, BT ou desligado)"
    return f"Mouse: {frame.level}% - {frame.state_name} - via {PRODUCTS.get(pid, hex(pid))}"


def notify(title, msg, loud=False):
    try:
        n = Notification(app_id="Attack Shark Battery", title=title, msg=msg,
                         duration="long" if loud else "short")
        n.set_audio(audio.LoopingAlarm if loud else audio.Default, loop=False)
        n.show()
    except Exception:
        pass


def ui_loop(icon):
    last_warn = 0.0
    warned_level = None
    full_notified = False
    last_render = None
    while not stop.is_set():
        frame, pid, seen, present = monitor.snapshot()
        age = time.time() - seen if seen else 0
        asleep = frame is not None and age > cfg["sleep_after_seconds"]
        pct = frame.level if frame else None
        on_power = bool(frame and frame.on_power)

        render = (pct, on_power, asleep)
        if render != last_render:
            icon.icon = make_icon(pct, on_power, asleep)
            last_render = render
        icon.title = tooltip(frame, pid, asleep, age, present)[:127]

        if frame is not None and not asleep:
            now = time.time()
            if on_power:
                warned_level = None
                if pct >= 100 and cfg["notify_full"] and not full_notified:
                    notify("Mouse carregado", "Bateria em 100%. Pode tirar da dock/cabo.")
                    full_notified = True
            else:
                full_notified = False
                level = ("critical" if pct <= cfg["critical_percent"]
                         else "warn" if pct <= cfg["warn_percent"] else None)
                if level is None:
                    warned_level = None
                elif level != warned_level or now - last_warn >= cfg["repeat_minutes"] * 60:
                    if level == "critical":
                        notify(f"Mouse CRITICO: {pct}%",
                               "Coloque na dock AGORA. Abaixo disso ele pode nao funcionar nem no cabo.",
                               loud=True)
                    else:
                        notify(f"Mouse com {pct}% de bateria", "Coloque o mouse na dock para carregar.")
                    warned_level, last_warn = level, now
        stop.wait(2)


def open_path(path):
    return lambda icon, item: os.path.exists(path) and os.startfile(path)


def reload_config(icon, item):
    global cfg
    cfg = load_config()


def quit_app(icon, item):
    stop.set()
    monitor.stop()
    icon.stop()


def main():
    icon = pystray.Icon(
        "attackshark_battery", make_icon(None, False, False), "Mouse: iniciando...",
        menu=pystray.Menu(
            pystray.MenuItem("Abrir historico (CSV)", open_path(LOG_PATH)),
            pystray.MenuItem("Editar config", open_path(CONFIG_PATH)),
            pystray.MenuItem("Recarregar config", reload_config),
            pystray.MenuItem("Sair", quit_app),
        ))
    monitor.start()
    threading.Thread(target=ui_loop, args=(icon,), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    if "--test-notify" in sys.argv:
        notify("Mouse com 18% de bateria", "Teste de notificacao.")
        sys.exit()
    main()
