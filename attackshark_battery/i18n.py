"""Textos da interface em ingles e portugues.

Regras para os textos (tests/test_app.py confere): sem aspas duplas, $ ou crase,
porque as notificacoes passam por um script do PowerShell (winotify).
"""
import ctypes

LANGUAGES = {"en": "English", "pt": "Português"}

STRINGS = {
    "en": {
        # dica do icone (tooltip, max. 127 caracteres)
        "tip_starting": "Mouse: starting...",
        "tip_no_device": "Mouse: no Attack Shark receiver or cable found",
        "tip_waiting": "Mouse: waiting for data (move the mouse)",
        "tip_no_data": "Mouse: device found but no battery data. Your model may not be supported - see Report a problem",
        "tip_asleep": "Mouse: {pct}% (last reading {minutes} min ago - asleep, off or in Bluetooth mode)",
        "tip_level": "Mouse: {pct}%{approx} - {state}",
        "approx": " (approx.)",
        "state_battery": "on battery",
        "state_powered": "plugged in, not charging",
        "state_charging": "charging",
        "state_unknown": "unknown state ({code})",
        # notificacoes
        "n_low_title": "Mouse battery low: {pct}%",
        "n_low_msg": "Plug in the charger soon.",
        "n_crit_title": "Mouse battery critical: {pct}%",
        "n_crit_msg": "Charge it now. The mouse may turn off soon.",
        "n_full_title": "Mouse charged",
        "n_full_msg": "The battery reads 100%.",
        "n_flap_title": "Charging keeps cutting out",
        "n_flap_msg": "The mouse keeps switching between battery and external power. Check the cable or the charging dock contacts.",
        "n_update_title": "Update available: {version}",
        "n_update_msg": "Click to open the download page.",
        "n_uptodate_title": "Attack Shark Battery is up to date",
        "n_uptodate_msg": "You have the latest version ({version}).",
        "n_update_failed": "Could not check for updates. Check your internet connection.",
        "n_installed_title": "Attack Shark Battery {version} installed",
        "n_updated_title": "Attack Shark Battery updated to {version}",
        "n_installed_msg": "The battery icon is next to the clock. If you do not see it, click the ^ arrow in the taskbar.",
        "n_running_title": "Attack Shark Battery is already running",
        "n_running_msg": "Look for the battery icon next to the clock (or under the ^ arrow in the taskbar).",
        # menu
        "m_history": "Battery history",
        "m_settings": "Advanced settings",
        "m_language": "Language / Idioma",
        "m_startup": "Start with Windows",
        "m_updates": "Check for updates",
        "m_report": "Report a problem",
        "m_uninstall": "Uninstall",
        "m_quit": "Quit",
        # instalacao
        "newer_installed": "A newer version ({version}) is already installed. Starting it instead.",
        "close_running": "Could not close the running copy of Attack Shark Battery. Quit it from the tray icon and run this file again.",
        "install_failed": "Could not install Attack Shark Battery:\n{error}",
        "u_confirm": "Uninstall Attack Shark Battery?",
        "u_delete_data": "Also delete your settings and battery history?",
        "u_done": "Attack Shark Battery was uninstalled.",
    },
    "pt": {
        "tip_starting": "Mouse: iniciando...",
        "tip_no_device": "Mouse: nenhum receptor ou cabo Attack Shark encontrado",
        "tip_waiting": "Mouse: aguardando dados (mexa o mouse)",
        "tip_no_data": "Mouse: dispositivo encontrado, mas sem dados de bateria. Seu modelo pode não ser compatível - veja Relatar um problema",
        "tip_asleep": "Mouse: {pct}% (última leitura há {minutes} min - dormindo, desligado ou em Bluetooth)",
        "tip_level": "Mouse: {pct}%{approx} - {state}",
        "approx": " (aprox.)",
        "state_battery": "na bateria",
        "state_powered": "conectado, sem carregar",
        "state_charging": "carregando",
        "state_unknown": "estado desconhecido ({code})",
        "n_low_title": "Bateria do mouse baixa: {pct}%",
        "n_low_msg": "Conecte o carregador em breve.",
        "n_crit_title": "Bateria do mouse crítica: {pct}%",
        "n_crit_msg": "Carregue agora. O mouse pode desligar em breve.",
        "n_full_title": "Mouse carregado",
        "n_full_msg": "A bateria indica 100%.",
        "n_flap_title": "O carregamento fica caindo",
        "n_flap_msg": "O mouse fica alternando entre bateria e energia externa. Confira o cabo ou os contatos da dock de carga.",
        "n_update_title": "Atualização disponível: {version}",
        "n_update_msg": "Clique para abrir a página de download.",
        "n_uptodate_title": "Attack Shark Battery está atualizado",
        "n_uptodate_msg": "Você tem a versão mais recente ({version}).",
        "n_update_failed": "Não foi possível procurar atualizações. Confira sua conexão com a internet.",
        "n_installed_title": "Attack Shark Battery {version} instalado",
        "n_updated_title": "Attack Shark Battery atualizado para {version}",
        "n_installed_msg": "O ícone da bateria fica perto do relógio. Se não aparecer, clique na setinha ^ da barra de tarefas.",
        "n_running_title": "Attack Shark Battery já está aberto",
        "n_running_msg": "Procure o ícone da bateria perto do relógio (ou na setinha ^ da barra de tarefas).",
        "m_history": "Histórico da bateria",
        "m_settings": "Configurações avançadas",
        "m_language": "Language / Idioma",
        "m_startup": "Iniciar com o Windows",
        "m_updates": "Procurar atualizações",
        "m_report": "Relatar um problema",
        "m_uninstall": "Desinstalar",
        "m_quit": "Sair",
        "newer_installed": "Uma versão mais nova ({version}) já está instalada. Ela será aberta no lugar desta.",
        "close_running": "Não foi possível fechar o Attack Shark Battery que está aberto. Feche pelo ícone da bandeja e rode este arquivo de novo.",
        "install_failed": "Não foi possível instalar o Attack Shark Battery:\n{error}",
        "u_confirm": "Desinstalar o Attack Shark Battery?",
        "u_delete_data": "Apagar também suas configurações e o histórico da bateria?",
        "u_done": "O Attack Shark Battery foi desinstalado.",
    },
}

_lang = "en"


def detect():
    """Idioma sugerido a partir do idioma do Windows."""
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except (AttributeError, OSError):
        return "en"
    return "pt" if lang_id & 0x3FF == 0x16 else "en"   # LANG_PORTUGUESE (pt-BR e pt-PT)


def set_language(code):
    global _lang
    _lang = code if code in STRINGS else "en"


def get_language():
    return _lang


def t(key, **kw):
    s = STRINGS[_lang].get(key) or STRINGS["en"][key]
    return s.format(**kw) if kw else s


def state_name(code):
    """Nome traduzido de Frame.state_code."""
    if code.startswith("unknown_"):
        return t("state_unknown", code=code[len("unknown_"):])
    return t("state_" + code)
