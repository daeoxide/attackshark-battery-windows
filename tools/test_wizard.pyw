"""Assistente de testes: guia o mapeamento de todos os modos do mouse numa janela.

Somente leitura (attackshark_battery/hidread.py). Grava tudo em docs/captures/.
Uso: pythonw tools/test_wizard.pyw
"""
import csv
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from attackshark_battery.hidread import ReadOnlyHid, enumerate_interfaces  # noqa: E402
from attackshark_battery.protocol import parse  # noqa: E402

VENDORS = {0x1D57}  # todos os produtos Xenta, nao so os PIDs ja conhecidos
SKIP = {(0x1, 0x2), (0x1, 0x6)}  # mouse/teclado: o Windows nao permite ler
NAMES = {0xFA60: "Receptor 2.4G", 0xFA55: "Mouse no cabo", 0x2155: "Mouse no cabo (variante)"}
OFFICIAL_APP = "AttackShark.exe"

# (titulo, instrucao, segundos de espera, pergunta para anotar)
STEPS = [
    ("Feche o app oficial",
     "Feche o programa Attack Shark (inclusive o icone perto do relogio: botao direito > Sair).\n"
     "Ele conversa com o mouse e atrapalharia o teste.\n\n"
     "O status abaixo fica verde quando ele estiver fechado.",
     0, ""),
    ("Cabo, chave em OFF",
     "Chave do mouse em OFF.\nCabo USB-C ligado no PC.\nMexa o mouse de vez em quando.",
     60, "O mouse funcionou pelo cabo? Alguma luz acesa nele?"),
    ("Cabo, chave em 2.4G",
     "Mude a chave para 2.4G.\nDeixe o cabo ligado.\nMexa o mouse.",
     60, "O mouse funcionou? Alguma luz?"),
    ("Cabo, chave em BT",
     "Mude a chave para BT.\nDeixe o cabo ligado.",
     60, "O mouse funcionou neste PC? Alguma luz?"),
    ("Sem fio, 2.4G",
     "Tire o cabo.\nChave em 2.4G.\nUse o mouse normalmente.",
     60, "Funcionou normal?"),
    ("2.4G parado (sono)",
     "NAO toque no mouse ate o tempo acabar.\nQueremos ver quando ele dorme.",
     300, ""),
    ("Acordar",
     "Mexa o mouse para acordar.",
     30, "Acordou na hora ou demorou?"),
    ("Dock, chave em 2.4G",
     "Coloque o mouse na dock, chave em 2.4G.\nConfira se encaixou firme no ima.",
     180, "A dock piscou? A luz do MOUSE acendeu?"),
    ("Dock, chave em OFF",
     "Ainda na dock, mude a chave para OFF.",
     120, "A dock continua piscando? Alguma luz no mouse?"),
    ("Desligado, solto",
     "Tire da dock. Chave em OFF. Sem cabo.",
     60, ""),
    ("Bluetooth no outro PC",
     "Chave em BT, usando no outro PC (BT1).",
     60, "Funcionou no outro PC?"),
    ("Bluetooth neste PC (opcional)",
     "Se quiser: troque para BT2 e pareie com ESTE PC.\n"
     "Depois veja em Configuracoes > Bluetooth se aparece a bateria.\n"
     "Se nao quiser, clique em Pular.",
     60, "Apareceu % de bateria no Windows? Quanto?"),
    ("App oficial aberto (comparacao)",
     "Chave em 2.4G, sem cabo.\nAbra o programa Attack Shark de novo.\nMexa o mouse.",
     120, "Qual % o app oficial mostra?"),
]


class Recorder:
    def __init__(self, path):
        self.lock = threading.Lock()
        self.f = open(path, "w", newline="", encoding="utf-8")
        self.w = csv.writer(self.f)
        self.w.writerow(["hora", "evento", "dispositivo", "dados"])
        self.present = []
        self.last = None            # (Frame, pid, horario)
        self._active = set()
        self._stop = threading.Event()
        threading.Thread(target=self._scan, daemon=True).start()

    def emit(self, evento, disp="", dados=""):
        with self.lock:
            if self.f.closed:
                return
            self.w.writerow([datetime.now().strftime("%H:%M:%S"), evento, disp, dados])
            self.f.flush()

    def _scan(self):
        prev = None
        while not self._stop.is_set():
            try:
                devs = [d for d in enumerate_interfaces(vendors=VENDORS)
                        if (d["usage_page"], d["usage"]) not in SKIP and d["input_len"] > 0]
            except OSError:
                devs = []
            now = sorted({d["product_id"] for d in devs})
            if now != prev:
                self.emit("dispositivos", "", " | ".join(f"{p:04x} {NAMES.get(p, '')}" for p in now))
                prev = now
            self.present = now
            for d in devs:
                if d["path"] not in self._active:
                    self._active.add(d["path"])
                    threading.Thread(target=self._listen, args=(d,), daemon=True).start()
            self._stop.wait(1)

    def _listen(self, d):
        tag = f"{d['vendor_id']:04x}:{d['product_id']:04x}/MI{d['interface_number']:02d}" \
              f"/COL{d['collection']:02d}/up{d['usage_page']:04x}"
        try:
            h = ReadOnlyHid(d["path"], d["input_len"])
            while not self._stop.is_set():
                raw = h.read()
                self.emit("frame", tag, raw.hex(" "))  # todo frame, sem resumir
                f = parse(raw)
                if f is not None:
                    self.last = (f, d["product_id"], time.time())
        except OSError:
            self.emit("sumiu", tag)
        finally:
            self._active.discard(d["path"])

    def close(self):
        self._stop.set()
        self.emit("fim")
        with self.lock:
            self.f.close()


def official_app_running():
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {OFFICIAL_APP}", "/NH"],
                             capture_output=True, text=True, creationflags=0x08000000).stdout
        return OFFICIAL_APP.lower() in out.lower()
    except OSError:
        return False


class Wizard:
    def __init__(self, root):
        cap_dir = os.path.join(ROOT, "docs", "captures")
        os.makedirs(cap_dir, exist_ok=True)
        self.path = os.path.join(cap_dir, datetime.now().strftime("%Y-%m-%d_%H%M_assistente.csv"))
        self.rec = Recorder(self.path)
        self.root = root
        self.i = -1
        self.deadline = 0
        self.app_running = official_app_running()

        root.title("Teste do mouse Attack Shark")
        root.geometry("640x620")
        root.configure(padx=20, pady=16)
        big = ("Segoe UI", 20, "bold")
        mid = ("Segoe UI", 13)

        self.lbl_count = tk.Label(root, font=("Segoe UI", 10), fg="#666")
        self.lbl_count.pack(anchor="w")
        self.lbl_title = tk.Label(root, font=big, anchor="w")
        self.lbl_title.pack(fill="x")
        self.lbl_text = tk.Label(root, font=mid, justify="left", anchor="w", wraplength=590)
        self.lbl_text.pack(fill="x", pady=(8, 8))

        self.lbl_timer = tk.Label(root, font=("Segoe UI", 28, "bold"), fg="#1a6fd6")
        self.lbl_timer.pack()
        self.bar = ttk.Progressbar(root, length=590)
        self.bar.pack(pady=(0, 10))

        self.lbl_question = tk.Label(root, font=("Segoe UI", 11, "bold"), anchor="w")
        self.lbl_question.pack(fill="x")
        self.note = tk.Entry(root, font=mid)
        self.note.pack(fill="x", pady=(2, 12))

        btns = tk.Frame(root)
        btns.pack(fill="x")
        self.btn_next = tk.Button(btns, text="Proxima etapa  >", font=mid, width=18, command=self.next)
        self.btn_next.pack(side="right")
        tk.Button(btns, text="Pular", font=mid, command=lambda: self.next(skipped=True)).pack(side="right", padx=8)

        live = tk.LabelFrame(root, text=" O que o PC esta vendo agora ", font=("Segoe UI", 10), padx=10, pady=8)
        live.pack(fill="x", pady=(16, 0))
        self.lbl_app = tk.Label(live, font=("Segoe UI", 11), anchor="w")
        self.lbl_app.pack(fill="x")
        self.lbl_devs = tk.Label(live, font=("Segoe UI", 11), anchor="w")
        self.lbl_devs.pack(fill="x")
        self.lbl_batt = tk.Label(live, font=("Segoe UI", 15, "bold"), anchor="w")
        self.lbl_batt.pack(fill="x")

        root.protocol("WM_DELETE_WINDOW", self.quit)
        self.next()
        self.tick()
        self.poll_app()

    def next(self, skipped=False):
        if self.i >= 0:
            note = self.note.get().strip()
            title = STEPS[self.i][0]
            self.rec.emit("fim_etapa", title, ("PULADA " if skipped else "") + (f"nota: {note}" if note else ""))
        self.i += 1
        self.note.delete(0, "end")
        if self.i >= len(STEPS):
            self.finish()
            return
        title, text, secs, question = STEPS[self.i]
        self.rec.emit("etapa", title, text.replace("\n", " "))
        self.lbl_count.config(text=f"Etapa {self.i + 1} de {len(STEPS)}")
        self.lbl_title.config(text=title)
        self.lbl_text.config(text=text)
        self.lbl_question.config(text=question or "Algo estranho? (opcional)")
        self.secs = secs
        self.deadline = time.time() + secs

    def tick(self):
        if self.i < len(STEPS):
            left = max(0, int(self.deadline - time.time() + 0.99))
            if self.i == 0:
                ready = not self.app_running
                self.lbl_timer.config(text="")
                self.bar["value"] = 100 if ready else 0
            else:
                ready = left == 0
                self.lbl_timer.config(text="Pode avancar" if ready else f"Aguarde {left // 60}:{left % 60:02d}")
                self.bar["value"] = 100 * (1 - left / self.secs) if self.secs else 100
            self.btn_next.config(state="normal" if ready else "disabled",
                                 bg="#2e9e4f" if ready else "SystemButtonFace", fg="white" if ready else "black")

            self.lbl_app.config(text=("App oficial: ABERTO (interfere no teste)" if self.app_running
                                      else "App oficial: fechado  ✓"),
                                fg="#c62828" if self.app_running else "#2e7d32")
            devs = [NAMES.get(p, f"{p:04x}") for p in self.rec.present]
            self.lbl_devs.config(text="Conectado: " + (", ".join(devs) if devs else "nada"))
            if self.rec.last:
                f, pid, t = self.rec.last
                age = int(time.time() - t)
                silent = age > 10
                self.lbl_batt.config(
                    text=f"{f.level}%  ·  {f.state_code}  ·  via {NAMES.get(pid, hex(pid))}  ·  "
                         + (f"SEM SINAL ha {age}s" if silent else f"ha {age}s"),
                    fg="#999" if silent else "#222")
            else:
                self.lbl_batt.config(text="Aguardando sinal da bateria...", fg="#999")
        self.root.after(250, self.tick)

    def poll_app(self):
        def check():
            self.app_running = official_app_running()
        threading.Thread(target=check, daemon=True).start()
        self.root.after(3000, self.poll_app)

    def finish(self):
        self.rec.close()
        self.lbl_count.config(text="")
        self.lbl_title.config(text="Pronto! Obrigado.")
        self.lbl_text.config(text=f"Tudo foi gravado em:\n{os.path.normpath(self.path)}\n\n"
                                  "Pode fechar esta janela e anexar o arquivo numa issue no GitHub.")
        self.lbl_timer.config(text="")
        self.lbl_question.config(text="")
        self.note.pack_forget()
        self.btn_next.config(state="disabled")

    def quit(self):
        if self.i < len(STEPS):
            self.rec.emit("interrompido", STEPS[self.i][0] if self.i >= 0 else "")
            self.rec.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    Wizard(root)
    root.mainloop()
