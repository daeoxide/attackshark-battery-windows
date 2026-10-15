"""Icone de bandeja com o nivel da bateria, avisos e menu."""
import csv
import os
import platform
import subprocess
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime

from . import APP_NAME, REPO, __version__, i18n, installer, settings, updates, winsys
from .i18n import t

LOG_HEADER = ["timestamp", "percent", "state", "source_pid", "frame"]
NO_DATA_HINT_SECONDS = 120     # dispositivo presente e mudo por esse tempo: talvez modelo sem suporte
UPDATE_CHECK_SECONDS = 24 * 3600


class TrayApp:
    def __init__(self, cfg):
        from .monitor import BatteryMonitor
        self.cfg = cfg
        self.cfg_mtime = settings.config_mtime()
        self.stop = threading.Event()
        self.icon = None
        self._log_lock = threading.Lock()
        self._last_logged = None
        self.monitor = BatteryMonitor(on_frame=self.log_frame)

    # ---------- historico ----------

    def migrate_old_log(self):
        """Historico com outro cabecalho (versao antiga) e preservado com outro nome."""
        try:
            with open(settings.LOG_PATH, encoding="utf-8") as f:
                header = f.readline().strip()
        except OSError:
            return
        if header != ",".join(LOG_HEADER):
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.replace(settings.LOG_PATH, settings.LOG_PATH.replace(".csv", f"_old_{stamp}.csv"))

    def write_log(self, row):
        try:
            new = not os.path.exists(settings.LOG_PATH)
            with open(settings.LOG_PATH, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(LOG_HEADER)
                w.writerow([datetime.now().isoformat(timespec="seconds")] + row)
        except OSError:
            pass   # arquivo aberto e travado (ex.: Excel): perde-se uma linha, o app segue

    def log_frame(self, frame, pid):
        """Grava no CSV quando nivel, estado ou fonte mudam."""
        key = (frame.level, frame.state, pid)
        with self._log_lock:
            if key == self._last_logged:
                return
            self._last_logged = key
            self.write_log([frame.level, frame.state_code, f"{pid:04x}", frame.raw.hex(" ")])

    def log_silence(self):
        """Mouse parou de falar (dormiu, desligou ou foi para BT). Ajuda a medir o tempo de sono."""
        with self._log_lock:
            self._last_logged = None   # a proxima leitura e gravada mesmo se igual a anterior
            self.write_log(["", "no_signal", "", ""])

    # ---------- notificacoes ----------

    def notify(self, title, msg, loud=False, launch=""):
        try:
            from winotify import Notification, audio
            n = Notification(app_id=winsys.APP_ID, title=title, msg=msg, launch=launch,
                             icon=settings.ICON_PATH if os.path.exists(settings.ICON_PATH) else "",
                             duration="long" if loud else "short")
            n.set_audio(audio.LoopingAlarm if loud else audio.Default, loop=False)
            n.show()
        except Exception:
            pass

    # ---------- laco principal ----------

    def tooltip(self, frame, asleep, age, present, quiet_for):
        if frame is None:
            if not present:
                return t("tip_no_device")
            return t("tip_no_data") if quiet_for > NO_DATA_HINT_SECONDS else t("tip_waiting")
        if asleep:
            return t("tip_asleep", pct=frame.level, minutes=int(age // 60))
        return t("tip_level", pct=frame.level, approx=t("approx") if frame.on_power else "",
                 state=i18n.state_name(frame.state_code))

    def maybe_reload_config(self):
        mtime = settings.config_mtime()
        if mtime != self.cfg_mtime:
            self.cfg_mtime = mtime
            lang = self.cfg["language"]
            self.cfg = settings.load_config()
            if self.cfg["language"] != lang:
                self.apply_language(self.cfg["language"], save=False)

    def ui_loop(self):
        last_warn = 0.0
        warned_level = None
        full_notified = False
        last_render = None
        last_flap_notify = 0.0
        was_asleep = False
        present_since = None
        while not self.stop.is_set():
            try:
                self.maybe_reload_config()
                cfg = self.cfg
                now = time.time()
                if cfg["notify_bad_contact"] and self.monitor.flapping() and now - last_flap_notify > 300:
                    self.notify(t("n_flap_title"), t("n_flap_msg"))
                    last_flap_notify = now
                frame, pid, seen, present = self.monitor.snapshot()
                present_since = (present_since or now) if present else None
                age = now - seen if seen else 0
                asleep = frame is not None and age > cfg["sleep_after_seconds"]
                pct = frame.level if frame else None
                on_power = bool(frame and frame.on_power)
                if asleep and not was_asleep:
                    self.log_silence()
                was_asleep = asleep

                render = (pct, on_power, asleep, cfg["warn_percent"])
                if render != last_render:
                    from .icons import tray_icon
                    self.icon.icon = tray_icon(pct, on_power, asleep, cfg["warn_percent"])
                    last_render = render
                quiet_for = now - present_since if present_since else 0
                self.icon.title = self.tooltip(frame, asleep, age, present, quiet_for)[:127]

                if frame is not None and not asleep:
                    if on_power:
                        warned_level = None
                        if pct >= 100 and cfg["notify_full"] and not full_notified:
                            self.notify(t("n_full_title"), t("n_full_msg"))
                            full_notified = True
                    else:
                        full_notified = False
                        level = ("critical" if pct <= cfg["critical_percent"]
                                 else "warn" if pct <= cfg["warn_percent"] else None)
                        if level is None:
                            warned_level = None
                        elif level != warned_level or now - last_warn >= cfg["repeat_minutes"] * 60:
                            if level == "critical":
                                self.notify(t("n_crit_title", pct=pct), t("n_crit_msg"), loud=True)
                            else:
                                self.notify(t("n_low_title", pct=pct), t("n_low_msg"))
                            warned_level, last_warn = level, now
            except Exception:
                pass   # um erro inesperado nao pode congelar o icone
            self.stop.wait(2)

    # ---------- atualizacoes ----------

    def check_for_updates(self, manual=False):
        try:
            version, url = updates.latest_release()
        except Exception:
            if manual:
                self.notify(APP_NAME, t("n_update_failed"))
            return
        if updates.is_newer(version):
            state = settings.load_state()
            if manual or state.get("notified_version") != version:
                self.notify(t("n_update_title", version=version), t("n_update_msg"), launch=url)
                state["notified_version"] = version
                settings.save_state(state)
        elif manual:
            self.notify(t("n_uptodate_title"), t("n_uptodate_msg", version=__version__))

    def update_loop(self):
        if self.stop.wait(60):      # nao atrasa o inicio do Windows
            return
        while True:
            state = settings.load_state()
            if self.cfg["check_updates"] and time.time() - state.get("last_update_check", 0) >= UPDATE_CHECK_SECONDS:
                state["last_update_check"] = time.time()
                settings.save_state(state)
                self.check_for_updates()
            if self.stop.wait(3600):
                return

    # ---------- menu ----------

    def apply_language(self, code, save=True):
        i18n.set_language(code)
        if save:
            self.cfg["language"] = code
            settings.save_config(self.cfg)
            self.cfg_mtime = settings.config_mtime()
        if self.icon:
            self.icon.update_menu()

    def open_history(self, icon=None, item=None):
        try:
            os.startfile(settings.LOG_PATH if os.path.exists(settings.LOG_PATH) else settings.DATA_DIR)
        except OSError:   # sem programa associado a .csv
            subprocess.Popen(["explorer", "/select,", settings.LOG_PATH])

    def open_settings(self, icon=None, item=None):
        settings.load_config()   # garante que o arquivo existe com todas as chaves
        subprocess.Popen(["notepad.exe", settings.CONFIG_PATH])

    def diagnostics(self):
        frame, pid, seen, present = self.monitor.snapshot()
        with self.monitor.lock:
            devices = list(self.monitor.devices)
            recent = list(self.monitor.recent)
        lines = [
            f"- App: {APP_NAME} {__version__} ({'exe' if settings.FROZEN else 'source'})",
            f"- Windows: {platform.platform()}",
            "- Devices (VID:PID, interface, collection, usage page, input length):",
        ]
        lines += [f"  - {d['vendor_id']:04x}:{d['product_id']:04x} MI_{d['interface_number']:02d} "
                  f"COL{d['collection']:02d} page 0x{d['usage_page']:04X} in={d['input_len']}" for d in devices] or ["  - none"]
        lines.append(f"- Last reading: {frame.raw.hex(' ') if frame else 'none'}"
                     + (f" from {pid:04x}, {int(time.time() - seen)} s ago" if frame else ""))
        lines.append("- Recent frames:")
        lines += [f"  - {datetime.fromtimestamp(ts).strftime('%H:%M:%S')} {p:04x}: {raw.hex(' ')}"
                  for ts, p, raw in recent] or ["  - none"]
        return "\n".join(lines)

    def report_problem(self, icon=None, item=None):
        body = ("**Mouse model:** (e.g. Attack Shark X11)\n"
                "**Connection:** (2.4G receiver / USB cable / dock)\n"
                "**What happened:**\n\n\n"
                "### Diagnostics\n" + self.diagnostics())
        query = urllib.parse.urlencode({"title": "Problem: ", "body": body})
        webbrowser.open(f"https://github.com/{REPO}/issues/new?{query}")

    def toggle_startup(self, icon, item):
        installer.set_startup(not installer.startup_enabled())

    def quit(self, icon=None, item=None):
        self.stop.set()
        self.monitor.stop()
        if self.icon:
            self.icon.stop()

    def build_menu(self):
        import pystray
        item = pystray.MenuItem

        def text(key):
            return lambda _item: t(key)

        def lang_item(code, name):
            return item(name, lambda: self.apply_language(code),
                        checked=lambda _item: i18n.get_language() == code, radio=True)

        entries = [
            item(f"{APP_NAME} {__version__}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            item(text("m_history"), self.open_history),
            item(text("m_settings"), self.open_settings),
            item(text("m_language"), pystray.Menu(*[lang_item(c, n) for c, n in i18n.LANGUAGES.items()])),
            item(text("m_startup"), self.toggle_startup, checked=installer.startup_enabled),
            item(text("m_updates"), lambda: threading.Thread(target=self.check_for_updates,
                                                             args=(True,), daemon=True).start()),
            item(text("m_report"), self.report_problem),
            pystray.Menu.SEPARATOR,
        ]
        if settings.FROZEN and installer.is_installed_copy():
            entries.append(item(text("m_uninstall"), lambda: installer.request_uninstall()))
        entries.append(item(text("m_quit"), self.quit))
        return pystray.Menu(*entries)

    def run(self, just_installed=None):
        import pystray
        from .icons import tray_icon
        self.migrate_old_log()
        self.icon = pystray.Icon("attackshark_battery", tray_icon(None, False, False), t("tip_starting"),
                                 menu=self.build_menu())
        winsys.on_quit_request(self.quit)
        self.monitor.start()
        threading.Thread(target=self.ui_loop, daemon=True).start()
        threading.Thread(target=self.update_loop, daemon=True).start()
        if just_installed:
            title = "n_updated_title" if just_installed == "--updated" else "n_installed_title"
            self.notify(t(title, version=__version__), t("n_installed_msg"))
        self.icon.run()


def first_run_dialog(default_lang, startup_default):
    """Janela da primeira execucao: idioma e inicio com o Windows. Retorna (idioma, iniciar)."""
    import ctypes
    import tkinter as tk
    from tkinter import ttk
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    result = {"lang": default_lang, "startup": startup_default}
    root = tk.Tk()
    root.title(APP_NAME)
    root.resizable(False, False)
    root.attributes("-topmost", True)
    try:
        from PIL import ImageTk
        from .icons import app_icon
        root._icon = ImageTk.PhotoImage(app_icon(64))
        root.iconphoto(True, root._icon)
    except Exception:
        pass
    startup = tk.BooleanVar(value=startup_default)

    def pick(code):
        result.update(lang=code, startup=startup.get())
        root.destroy()

    frm = ttk.Frame(root, padding=24)
    frm.pack()
    ttk.Label(frm, text=APP_NAME, font=("Segoe UI", 13, "bold")).pack()
    ttk.Label(frm, text="Choose your language\nEscolha o idioma", justify="center").pack(pady=(8, 14))
    btns = ttk.Frame(frm)
    btns.pack()
    order = sorted(i18n.LANGUAGES, key=lambda c: c != default_lang)   # o idioma do Windows primeiro
    for code in order:
        b = ttk.Button(btns, text=i18n.LANGUAGES[code], width=14, command=lambda c=code: pick(c))
        b.pack(side="left", padx=6)
        if code == default_lang:
            b.focus_set()
    ttk.Checkbutton(frm, text="Start with Windows / Iniciar com o Windows", variable=startup).pack(pady=(18, 0))
    root.protocol("WM_DELETE_WINDOW", lambda: pick(default_lang))
    root.bind("<Return>", lambda e: pick(default_lang))
    root.update_idletasks()
    w, h = root.winfo_reqwidth(), root.winfo_reqheight()
    root.geometry(f"+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 2}")
    root.mainloop()
    return result["lang"], result["startup"]


def self_test():
    """Confere que tudo que o app usa esta presente (usado pela CI, inclusive no .exe)."""
    import tkinter
    import pystray  # noqa: F401
    import winotify  # noqa: F401
    from . import hidread, monitor, protocol  # noqa: F401
    from .icons import app_icon, tray_icon
    tkinter.Tcl()
    tray_icon(55, False, False)
    app_icon(32)
    for lang in i18n.STRINGS:
        i18n.set_language(lang)
        for key in i18n.STRINGS["en"]:
            t(key, pct=1, minutes=1, approx="", state="", version="1", code="00", error="")
    hidread.enumerate_interfaces([], vendors={protocol.VENDOR_ID})
    print("self-test OK", __version__)


def main(argv):
    if "--self-test" in argv:
        try:
            self_test()
        except BaseException:
            import traceback
            traceback.print_exc()
            os._exit(1)   # no .exe sem console, uma excecao abriria uma janela de erro e travaria a CI
        return
    cfg = settings.load_config()
    i18n.set_language(cfg["language"] or i18n.detect())

    if "--uninstall" in argv:
        installer.uninstall(quiet="--quiet" in argv)
        return
    if settings.FROZEN and not installer.is_installed_copy():
        installer.install_or_update()
        return
    if not winsys.acquire_single_instance():
        TrayApp(cfg).notify(t("n_running_title"), t("n_running_msg"))
        return

    os.makedirs(settings.DATA_DIR, exist_ok=True)
    if not cfg["language"]:
        lang, startup = first_run_dialog(i18n.detect(), installer.startup_enabled() or settings.FROZEN)
        cfg["language"] = lang
        settings.save_config(cfg)
        i18n.set_language(lang)
        installer.set_startup(startup)
    try:
        from .icons import app_icon
        app_icon(128).save(settings.ICON_PATH)
    except OSError:
        pass
    winsys.register_app_id(settings.ICON_PATH)

    if "--test-notify" in argv:
        TrayApp(cfg).notify(t("n_low_title", pct=18), t("n_low_msg"))
        return
    just_installed = next((a for a in argv if a in ("--installed", "--updated")), None)
    TrayApp(cfg).run(just_installed)
