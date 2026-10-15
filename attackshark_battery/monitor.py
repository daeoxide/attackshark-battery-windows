"""Escuta o canal de bateria do receptor e do mouse no cabo, somente leitura."""
import threading
import time

from .hidread import ReadOnlyHid, enumerate_interfaces
from .protocol import BATTERY_USAGE_PAGE, PRODUCTS, VENDOR_ID, parse

RESCAN_SECONDS = 3
CONFIRM_FRAMES = 2        # um valor so vale quando chega repetido (filtra o "01 64" de reconexao)
FLAP_WINDOW = 60          # s
FLAP_THRESHOLD = 4        # trocas bateria<->energia nesse intervalo = mau contato na dock/cabo


class BatteryMonitor:
    """Mantem a ultima leitura valida. on_frame(frame, pid) e chamado a cada frame."""

    def __init__(self, on_frame=None):
        self.on_frame = on_frame
        self.lock = threading.Lock()
        self.frame = None
        self.source_pid = None
        self.last_seen = 0.0
        self.present = []          # pids com canal de bateria presentes agora
        self._pending = None       # (state, level) aguardando confirmacao
        self._pending_count = 0
        self._last_raw_power = None
        self._power_flips = []     # horarios das trocas bateria<->energia (frames crus)
        self._active = set()
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._scan_loop, daemon=True).start()

    def stop(self):
        self._stop.set()

    def flapping(self, now=None):
        """True se o contato de energia esta oscilando (ex.: mouse mal encaixado na dock)."""
        now = time.time() if now is None else now
        with self.lock:
            self._power_flips = [t for t in self._power_flips if now - t <= FLAP_WINDOW]
            return len(self._power_flips) >= FLAP_THRESHOLD

    def feed(self, f, pid, now=None):
        """Processa um frame ja decodificado. Retorna True se virou a leitura oficial.
        `now` permite reprocessar capturas com o horario original."""
        now = time.time() if now is None else now
        with self.lock:
            if self._last_raw_power is not None and f.on_power != self._last_raw_power:
                self._power_flips.append(now)
            self._last_raw_power = f.on_power
            key = (f.state, f.level)
            if key == self._pending:
                self._pending_count += 1
            else:
                self._pending, self._pending_count = key, 1
            if self._pending_count < CONFIRM_FRAMES:
                return False
            self.frame, self.source_pid, self.last_seen = f, pid, now
        if self.on_frame:
            self.on_frame(f, pid)
        return True

    def snapshot(self):
        with self.lock:
            return self.frame, self.source_pid, self.last_seen, list(self.present)

    def _scan_loop(self):
        ids = [(VENDOR_ID, pid) for pid in PRODUCTS]
        while not self._stop.is_set():
            try:
                devs = [d for d in enumerate_interfaces(ids)
                        if d["usage_page"] == BATTERY_USAGE_PAGE and d["input_len"] > 0]
            except OSError:
                devs = []
            with self.lock:
                self.present = sorted({d["product_id"] for d in devs})
            for d in devs:
                if d["path"] not in self._active:
                    self._active.add(d["path"])
                    threading.Thread(target=self._read_loop, args=(d,), daemon=True).start()
            self._stop.wait(RESCAN_SECONDS)

    def _read_loop(self, d):
        h = None
        try:
            h = ReadOnlyHid(d["path"], d["input_len"])
            while not self._stop.is_set():
                f = parse(h.read())
                if f is not None:
                    self.feed(f, d["product_id"])
        except OSError:
            pass  # dispositivo removido (cabo desconectado, receptor tirado)
        finally:
            if h:
                h.close()
            self._active.discard(d["path"])
