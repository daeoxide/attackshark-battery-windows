"""Instalacao por usuario (sem admin) do .exe, atualizacao e desinstalacao.

O .exe baixado se copia para %LOCALAPPDATA%\\Programs\\AttackSharkBattery e passa a rodar de la.
Rodar um .exe mais novo fecha a copia aberta, substitui o arquivo instalado e reabre;
rodar um mais velho so abre a versao instalada. Config e historico ficam em
%LOCALAPPDATA%\\AttackSharkBattery e sobrevivem a atualizacoes.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import winreg

from . import APP_NAME, REPO, __version__, settings, winsys
from .i18n import t
from .updates import parse_version

EXE_NAME = "AttackSharkBattery.exe"
_LOCAL = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
_PROGRAMS = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
INSTALL_DIR = os.path.join(_LOCAL, "Programs", "AttackSharkBattery")
INSTALLED_EXE = os.path.join(INSTALL_DIR, EXE_NAME)
START_MENU_LNK = os.path.join(_PROGRAMS, f"{APP_NAME}.lnk")
STARTUP_LNK = os.path.join(_PROGRAMS, "Startup", f"{APP_NAME}.lnk")   # mesmo nome da v1.0.0
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AttackSharkBattery"


def _same(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def is_installed_copy():
    return _same(sys.executable, INSTALLED_EXE)


def installed_version():
    """Versao instalada, '0' se o arquivo existe sem registro, ou None se nao ha instalacao."""
    if not os.path.exists(INSTALLED_EXE):
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
            return str(winreg.QueryValueEx(k, "DisplayVersion")[0])
    except OSError:
        return "0"


# ---------- inicio com o Windows ----------

def launch_target():
    """(alvo, argumentos) para iniciar este app: o .exe instalado, ou pythonw + script."""
    if settings.FROZEN:
        return (INSTALLED_EXE if os.path.exists(INSTALLED_EXE) else sys.executable), ""
    script = os.path.abspath(sys.argv[0])
    return winsys.pythonw(), f'"{script}"'


def startup_enabled(item=None):
    return os.path.exists(STARTUP_LNK)


def set_startup(enabled):
    if not enabled:
        winsys.remove_file(STARTUP_LNK)
        return
    target, args = launch_target()
    workdir = os.path.dirname(target) if settings.FROZEN else settings.SOURCE_ROOT
    winsys.create_shortcut(STARTUP_LNK, target, args, workdir)


# ---------- instalar / atualizar ----------

def _copy_self():
    os.makedirs(INSTALL_DIR, exist_ok=True)
    tmp = INSTALLED_EXE + ".new"
    shutil.copy2(sys.executable, tmp)
    for _ in range(20):            # o processo antigo pode demorar a soltar o arquivo
        try:
            os.replace(tmp, INSTALLED_EXE)
            return
        except PermissionError:
            time.sleep(0.5)
    os.replace(tmp, INSTALLED_EXE)


def _register():
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
        for name, value in (("DisplayName", APP_NAME),
                            ("DisplayVersion", __version__),
                            ("Publisher", f"github.com/{REPO}"),
                            ("DisplayIcon", INSTALLED_EXE),
                            ("InstallLocation", INSTALL_DIR),
                            ("URLInfoAbout", f"https://github.com/{REPO}"),
                            ("UninstallString", f'"{INSTALLED_EXE}" --uninstall'),
                            ("QuietUninstallString", f'"{INSTALLED_EXE}" --uninstall --quiet')):
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
        for name in ("NoModify", "NoRepair"):
            winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, 1)
        size_kb = os.path.getsize(INSTALLED_EXE) // 1024
        winreg.SetValueEx(k, "EstimatedSize", 0, winreg.REG_DWORD, size_kb)


def install_or_update():
    """Chamado quando o .exe roda fora da pasta de instalacao (ex.: Downloads)."""
    current = installed_version()
    if current is not None and parse_version(current) > parse_version(__version__):
        winsys.message(t("newer_installed", version=current))
        winsys.launch(INSTALLED_EXE)
        return
    if current is not None and parse_version(current) == parse_version(__version__):
        winsys.launch(INSTALLED_EXE)       # mesma versao: so abre (se ja estiver aberta, ela avisa)
        return
    if not winsys.close_running_instance(EXE_NAME):
        winsys.message(t("close_running"), winsys.MB_OK | winsys.MB_ICONWARNING)
        return
    try:
        _copy_self()
        _register()
        winsys.create_shortcut(START_MENU_LNK, INSTALLED_EXE)
        if startup_enabled():              # ex.: atalho da v1.0.0 apontando para Downloads
            winsys.create_shortcut(STARTUP_LNK, INSTALLED_EXE)
    except OSError as e:
        winsys.message(t("install_failed", error=e), winsys.MB_OK | winsys.MB_ICONWARNING)
        return
    winsys.launch(INSTALLED_EXE, "--updated" if current is not None else "--installed")


# ---------- desinstalar ----------

def request_uninstall():
    """Item do menu: o desinstalador roda em outro processo, que fecha este."""
    winsys.launch(INSTALLED_EXE if os.path.exists(INSTALLED_EXE) else sys.executable, "--uninstall")


def uninstall(quiet=False):
    if not quiet and winsys.message(t("u_confirm"), winsys.MB_YESNO | winsys.MB_ICONQUESTION) != winsys.IDYES:
        return
    winsys.close_running_instance(EXE_NAME)
    delete_data = (settings.FROZEN and not quiet and winsys.message(
        t("u_delete_data"), winsys.MB_YESNO | winsys.MB_ICONQUESTION | winsys.MB_DEFBUTTON2) == winsys.IDYES)
    for lnk in (STARTUP_LNK, START_MENU_LNK):
        winsys.remove_file(lnk)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        pass
    winsys.unregister_app_id()
    if not quiet:
        winsys.message(t("u_done"))
    # este .exe ainda esta em uso: um cmd separado apaga as pastas depois que ele fechar
    targets = [INSTALL_DIR] + ([settings.DATA_DIR] if delete_data else [])
    cmd = " & ".join(f'for /l %i in (1,1,15) do @if exist "{p}" (ping -n 2 127.0.0.1 >nul & rmdir /s /q "{p}")'
                     for p in targets)
    subprocess.Popen(f"cmd /c {cmd}", cwd=tempfile.gettempdir(), env=winsys.clean_env(),
                     creationflags=winsys.CREATE_NO_WINDOW, close_fds=True)
