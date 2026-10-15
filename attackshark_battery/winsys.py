"""Integracao com o Windows: instancia unica, caixas de mensagem, atalhos e processos.
Nada aqui fala com o mouse."""
import ctypes
import os
import subprocess
import sys
import time
import winreg
from ctypes import wintypes

from . import APP_NAME

MUTEX_NAME = r"Local\AttackSharkBatteryTray"   # mesmo nome da v1.0.0: a atualizacao enxerga a versao antiga
QUIT_EVENT_NAME = r"Local\AttackSharkBatteryQuit"
APP_ID = APP_NAME                               # AppUserModelID das notificacoes
CREATE_NO_WINDOW = 0x08000000
SYNCHRONIZE = 0x00100000
EVENT_MODIFY_STATE = 0x0002
ERROR_ALREADY_EXISTS = 183
INFINITE = 0xFFFFFFFF

MB_OK, MB_YESNO = 0x0, 0x4
MB_ICONINFO, MB_ICONWARNING, MB_ICONQUESTION = 0x40, 0x30, 0x20
MB_DEFBUTTON2 = 0x100
MB_SETFOREGROUND, MB_TOPMOST = 0x10000, 0x40000
IDYES = 6

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
for _name, _args in (("CreateMutexW", [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]),
                     ("OpenMutexW", [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]),
                     ("CreateEventW", [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]),
                     ("OpenEventW", [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR])):
    getattr(_k32, _name).argtypes = _args
    getattr(_k32, _name).restype = wintypes.HANDLE
_k32.SetEvent.argtypes = _k32.ResetEvent.argtypes = _k32.CloseHandle.argtypes = [wintypes.HANDLE]
_k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_k32.WaitForSingleObject.restype = wintypes.DWORD
_user32 = ctypes.WinDLL("user32")
_user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]

_handles = []   # mantidos abertos ate o processo terminar


def acquire_single_instance():
    """True se esta e a unica copia rodando (mutex nomeado)."""
    h = _k32.CreateMutexW(None, False, MUTEX_NAME)
    already = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
    _handles.append(h)
    return not already


def instance_running():
    h = _k32.OpenMutexW(SYNCHRONIZE, False, MUTEX_NAME)
    if h:
        _k32.CloseHandle(h)
        return True
    return False


def on_quit_request(callback):
    """Chama callback() quando outra copia (instalador/desinstalador) pedir para fechar."""
    h = _k32.CreateEventW(None, False, False, QUIT_EVENT_NAME)
    if not h:
        return
    _k32.ResetEvent(h)   # sinal velho de um processo que ja saiu
    _handles.append(h)

    def wait():
        if _k32.WaitForSingleObject(h, INFINITE) == 0:
            callback()
    import threading
    threading.Thread(target=wait, daemon=True).start()


def _wait_gone(timeout):
    end = time.time() + timeout
    while instance_running():
        if time.time() > end:
            return False
        time.sleep(0.25)
    return True


def close_running_instance(exe_name):
    """Fecha a copia que esta na bandeja. Versoes >= 1.1 atendem o evento de saida;
    a 1.0.0 nao tinha esse evento, entao ela e encerrada pelo nome do executavel."""
    if not instance_running():
        return True
    h = _k32.OpenEventW(EVENT_MODIFY_STATE, False, QUIT_EVENT_NAME)
    if h:
        _k32.SetEvent(h)
        _k32.CloseHandle(h)
        if _wait_gone(8):
            return True
    # este processo e o pai dele (bootloader do PyInstaller) tem o mesmo nome: ficam de fora
    subprocess.run(["taskkill", "/F", "/IM", exe_name,
                    "/FI", f"PID ne {os.getpid()}", "/FI", f"PID ne {os.getppid()}"],
                   creationflags=CREATE_NO_WINDOW, capture_output=True, check=False)
    return _wait_gone(5)


def message(text, flags=MB_OK | MB_ICONINFO):
    return _user32.MessageBoxW(None, text, APP_NAME, flags | MB_SETFOREGROUND | MB_TOPMOST)


def clean_env():
    """Ambiente para iniciar outro .exe do PyInstaller sem herdar a pasta temporaria deste."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("_PYI", "_MEI"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def launch(exe, *args):
    subprocess.Popen([exe, *args], env=clean_env(), cwd=os.path.dirname(exe), close_fds=True)


def create_shortcut(lnk, target, args="", workdir=None):
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK);"
          "$s.TargetPath=$env:TGT;$s.Arguments=$env:ARGS;$s.WorkingDirectory=$env:WD;"
          "$s.IconLocation=$env:TGT;$s.Description=$env:DESC;$s.Save()")
    env = dict(clean_env(), LNK=lnk, TGT=target, ARGS=args, DESC=APP_NAME,
               WD=workdir or os.path.dirname(target))
    os.makedirs(os.path.dirname(lnk), exist_ok=True)
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], env=env,
                   creationflags=CREATE_NO_WINDOW, capture_output=True, check=False, timeout=60)
    return os.path.exists(lnk)


def remove_file(path):
    try:
        os.remove(path)
    except OSError:
        pass


def register_app_id(icon_path):
    """Nome e icone das notificacoes (registro do usuario, sem admin)."""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\AppUserModelId\{APP_ID}") as k:
            winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
            if os.path.exists(icon_path):
                winreg.SetValueEx(k, "IconUri", 0, winreg.REG_SZ, icon_path)
    except OSError:
        pass


def unregister_app_id():
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\AppUserModelId\{APP_ID}")
    except OSError:
        pass


def pythonw():
    exe = sys.executable
    candidate = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return candidate if os.path.exists(candidate) else exe
