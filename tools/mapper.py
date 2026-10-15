"""Mapeia os frames do mouse em cada modo (cabo, 2.4G, desligado, Bluetooth...).

Somente leitura (ver attackshark_battery/hidread.py). Grava em CSV cada mudanca de
dispositivos presentes e cada frame distinto recebido, com horario e contagem.
Uso:
  python tools/mapper.py [minutos] [saida.csv]   gravacao livre
  python tools/mapper.py --guided                 roteiro do docs/TEST-PLAN.md, Enter a cada etapa
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

STEPS = [
    "1  chave OFF  | cabo no PC          | parado",
    "2  chave 2.4G | cabo no PC          | mexa o mouse",
    "3  chave BT   | cabo no PC          | -",
    "4  chave 2.4G | sem cabo            | mexa o mouse",
    "5  chave 2.4G | sem cabo            | NAO TOQUE por 5 min",
    "6  chave 2.4G | sem cabo            | mexa para acordar",
    "7  chave 2.4G | na dock (encaixe firme) | espere 3 min",
    "8  chave OFF  | na dock             | espere 2 min",
    "9  chave OFF  | sem cabo, sem dock  | -",
    "10 chave BT1  | usando no outro PC  | -",
    "11 chave BT2  | pareado com ESTE PC (opcional) | veja Configuracoes > Bluetooth",
    "12 chave 2.4G | sem cabo            | uso normal",
]
guided = "--guided" in sys.argv
args = [a for a in sys.argv[1:] if a != "--guided"]
minutes = float(args[0]) if args else (180 if guided else 20)
default_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "captures",
                           datetime.now().strftime("%Y-%m-%d_%H%M_") + ("guiado" if guided else "livre") + ".csv")
out = args[1] if len(args) > 1 else default_out
lock = threading.Lock()
f = open(out, "w", newline="", encoding="utf-8")
w = csv.writer(f)
w.writerow(["hora", "evento", "dispositivo", "dados"])


def emit(evento, disp, dados=""):
    with lock:
        w.writerow([datetime.now().strftime("%H:%M:%S"), evento, disp, dados])
        f.flush()
        if not guided or evento in ("dispositivos", "etapa"):
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


def guide():
    print()
    print("Roteiro guiado. Coloque o mouse no estado indicado e aperte Enter.")
    print()
    for step in STEPS:
        input(f">>> {step}   [Enter quando estiver assim] ")
        emit("etapa", "", step)
    input("Fim do roteiro. Enter para encerrar a gravacao. ")
    emit("fim", "", "")
    os._exit(0)


if guided:
    threading.Thread(target=guide, daemon=True).start()

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
