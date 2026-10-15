"""Mapeia os frames do mouse em cada modo (cabo, 2.4G, desligado, Bluetooth...).

Somente leitura (ver attackshark_battery/hidread.py). Grava em CSV cada mudanca de
dispositivos presentes e cada frame distinto recebido, com horario e contagem.
Uso:
  python tools/mapper.py [minutos] [saida.csv]   gravacao livre
Para o roteiro guiado com janela, use tools/test_wizard.pyw.
"""
import csv
import os
import sys
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from attackshark_battery.hidread import ReadOnlyHid, enumerate_interfaces  # noqa: E402

IDS = [(0x1D57, 0xFA60), (0x1D57, 0xFA55), (0x1D57, 0x2155), (0x3554, 0xFA09)]
SKIP = {(0x1, 0x2), (0x1, 0x6)}  # mouse/teclado: o Windows nao permite ler
NAMES = {0xFA60: "receptor 2.4G (Xenta)", 0xFA55: "mouse no cabo", 0x2155: "mouse no cabo (variante)",
         0xFA09: "receptor 2.4G (CompX)"}

args = sys.argv[1:]
minutes = float(args[0]) if args else 20
default_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "captures",
                           datetime.now().strftime("%Y-%m-%d_%H%M_") + "livre.csv")
out = args[1] if len(args) > 1 else default_out
lock = threading.Lock()
f = open(out, "w", newline="", encoding="utf-8")
w = csv.writer(f)
w.writerow(["hora", "evento", "dispositivo", "dados"])


def emit(evento, disp, dados=""):
    with lock:
        w.writerow([datetime.now().strftime("%H:%M:%S"), evento, disp, dados])
        f.flush()
        print(f"   [{evento}] {disp} {dados}", flush=True)


def tag(d):
    return f"{d['vendor_id']:04x}:{d['product_id']:04x}/MI{d['interface_number']:02d}/COL{d['collection']:02d}/up{d['usage_page']:04x}"


def listen(d, active):
    last, count = None, 0
    try:
        h = ReadOnlyHid(d["path"], d["input_len"])
        while True:
            r = h.read().hex(" ")
            if r != last:
                if last is not None:
                    emit("fim_repeticao", tag(d), f"{last} x{count}")
                emit("frame", tag(d), r)
                last, count = r, 0
            count += 1
    except OSError:
        if last is not None:
            emit("fim_repeticao", tag(d), f"{last} x{count}")
    finally:
        active.discard(d["path"])


active, present = set(), None
end = time.time() + minutes * 60
while time.time() < end:
    devs = [d for d in enumerate_interfaces(IDS)
            if (d["usage_page"], d["usage"]) not in SKIP and d["input_len"] > 0]
    now = sorted({f"{d['vendor_id']:04x}:{d['product_id']:04x} {NAMES.get(d['product_id'], '')}" for d in devs})
    if now != present:
        emit("dispositivos", "", " | ".join(now))
        present = now
    for d in devs:
        if d["path"] not in active:
            active.add(d["path"])
            threading.Thread(target=listen, args=(d, active), daemon=True).start()
    time.sleep(1)
emit("fim", "", "")
