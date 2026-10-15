"""Logica que roda em qualquer sistema: textos, configuracao, versoes e filtro do monitor."""
import json
import pathlib
import re
import string
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from attackshark_battery import __version__, i18n, settings, updates  # noqa: E402
from attackshark_battery.monitor import BatteryMonitor, is_battery_candidate  # noqa: E402
from attackshark_battery.protocol import STATES, parse  # noqa: E402


def fields(s):
    return {f for _, f, _, _ in string.Formatter().parse(s) if f}


def test_translations_complete_and_safe():
    en = i18n.STRINGS["en"]
    for lang, table in i18n.STRINGS.items():
        assert set(table) == set(en), f"{lang}: chaves diferentes de en: {set(table) ^ set(en)}"
        for key, s in table.items():
            assert fields(s) == fields(en[key]), f"{lang}.{key}: campos diferentes"
            # as notificacoes passam por um script do PowerShell (winotify)
            assert not re.search(r'["$`]', s), f"{lang}.{key}: aspas, $ ou crase"
            if key.startswith("tip_"):
                assert len(s) <= 127, f"{lang}.{key}: dica longa demais"
    for code in STATES.values():
        for lang in i18n.STRINGS:
            i18n.set_language(lang)
            assert i18n.state_name(code)
    assert "05" in i18n.state_name("unknown_05")
    i18n.set_language("en")


def test_config_validation(tmp_path):
    path = tmp_path / "config.json"
    original, settings.CONFIG_PATH = settings.CONFIG_PATH, str(path)
    try:
        _check_config(path)
    finally:
        settings.CONFIG_PATH = original


def _check_config(path):
    path.write_text(json.dumps({"warn_percent": "25", "critical_percent": 50, "repeat_minutes": -3,
                                "notify_full": "yes", "language": "xx", "extra": 1}))
    cfg = settings.load_config()
    assert cfg["warn_percent"] == 25
    assert cfg["critical_percent"] == 24           # nunca >= aviso
    assert cfg["repeat_minutes"] == 1
    assert cfg["notify_full"] is False             # tipo errado -> padrao
    assert cfg["language"] == ""
    saved = json.loads(path.read_text())
    assert saved["extra"] == 1 and "check_updates" in saved   # chaves novas acrescentadas, extras mantidas
    path.write_text("{ quebrado")
    assert settings.load_config() == settings.DEFAULTS
    assert path.read_text() == "{ quebrado"        # nao sobrescreve o arquivo do usuario


def test_versions():
    assert updates.parse_version("v1.2.3") == (1, 2, 3)
    assert updates.parse_version("1.2") == (1, 2, 0)
    assert updates.is_newer("v1.10.0", "1.9.9")
    assert not updates.is_newer("1.0.0", "1.0.0")
    assert not updates.is_newer("v1.0.0", __version__)


def test_candidate_collections():
    base = {"usage_page": 0x0A, "input_len": 5}
    assert is_battery_candidate(base)
    assert is_battery_candidate({**base, "usage_page": 0xFF01, "input_len": 33})
    assert not is_battery_candidate({**base, "usage_page": 0x0B, "input_len": 0})   # canal de configuracao
    assert not is_battery_candidate({**base, "usage_page": 0x0C, "input_len": 3})   # teclas de midia
    assert not is_battery_candidate({**base, "usage_page": 0x01})


def test_confirmation_is_per_device():
    m = BatteryMonitor()
    # dois dispositivos falando ao mesmo tempo nao podem impedir um ao outro de confirmar
    for a, b in [("0355400150", "03e5400140"), ("0355400150", "03e5400140")]:
        m.feed(parse(bytes.fromhex(a)), 0xFA60)
        m.feed(parse(bytes.fromhex(b)), 0x1234)
    assert m.frame.level == 0x40 and m.source_pid == 0x1234


if __name__ == "__main__":
    import tempfile
    for test in (test_translations_complete_and_safe, test_versions, test_candidate_collections,
                 test_confirmation_is_per_device):
        test()
        print("OK", test.__name__)
    with tempfile.TemporaryDirectory() as d:
        test_config_validation(pathlib.Path(d))
        print("OK test_config_validation")
