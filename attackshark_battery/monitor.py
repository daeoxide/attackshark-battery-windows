"""Escuta o canal de bateria do receptor e do mouse no cabo, somente leitura."""
import threading
import time

from .hidread import ReadOnlyHid, enumerate_interfaces
from .protocol import BATTERY_USAGE_PAGE, PRODUCTS, VENDOR_ID, parse

RESCAN_SECONDS = 3


class BatteryMonitor:
    """Mantem a ultima leitura valida. on_frame(frame, pid) e chamado a cada frame."""

    def __init__(self, on_frame=None):
        self.on_frame = on_frame
        self.lock = threading.Lock()
        self.frame = None
        self.source_pid = None
        self.last_seen = 0.0
        self.present = []          # pids com canal de bateria presentes agora
        self._active = set()
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._scan_loop, daemon=True).start()

    def stop(self):
        self._stop.set()

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
                if f is None:
                    continue
                with self.lock:
                    self.frame, self.source_pid, self.last_seen = f, d["product_id"], time.time()
                if self.on_frame:
                    self.on_frame(f, d["product_id"])
        except OSError:
            pass  # dispositivo removido (cabo desconectado, receptor tirado)
        finally:
            if h:
                h.close()
            self._active.discard(d["path"])
