"""Garante que o projeto nunca envia dados ao mouse.

1) Estatico: nenhum arquivo do projeto referencia APIs que escrevem no dispositivo
   ou que geram requisicoes a ele.
2) Em tempo de execucao (se o mouse/receptor estiver conectado): o handle aberto
   pelo projeto nao tem permissao de escrita - o Windows recusa WriteFile.
"""
import ctypes
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FORBIDDEN = [
    r"\bWriteFile\b", r"GENERIC_WRITE", r"HidD_Set\w+", r"HidD_GetFeature", r"HidD_GetInputReport",
    r"HidD_Get\w*String", r"send_feature_report", r"get_feature_report", r"DeviceIoControl",
    r"\bimport hid\b", r"\bhid\.device\b",
]
SOURCES = [p for p in ROOT.rglob("*.py*") if "tests" not in p.parts and p.suffix in (".py", ".pyw")]


def code_only(text):
    """Remove docstrings e comentarios (que citam as APIs proibidas para explica-las)."""
    text = re.sub(r'"""(?:.|\n)*?"""', "", text)
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def test_no_write_apis():
    hits = []
    for p in SOURCES:
        code = code_only(p.read_text(encoding="utf-8"))
        for pat in FORBIDDEN:
            for m in re.finditer(pat, code):
                hits.append(f"{p.relative_to(ROOT)}: {m.group(0)}")
    assert not hits, "APIs proibidas encontradas:\n" + "\n".join(hits)


def test_handle_is_read_only():
    from attackshark_battery.hidread import ReadOnlyHid, enumerate_interfaces
    from attackshark_battery.protocol import BATTERY_USAGE_PAGE, PRODUCTS, VENDOR_ID
    devs = [d for d in enumerate_interfaces([(VENDOR_ID, p) for p in PRODUCTS])
            if d["usage_page"] == BATTERY_USAGE_PAGE]
    if not devs:
        print("  (mouse/receptor ausente - teste de handle pulado)")
        return
    h = ReadOnlyHid(devs[0]["path"], devs[0]["input_len"])
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        n = ctypes.c_ulong()
        # Esta e a UNICA escrita do projeto, e existe para provar que e impossivel.
        ok = k32.WriteFile(h._h, b"\x00" * 8, 8, ctypes.byref(n), None)
        assert not ok and ctypes.get_last_error() == 5, "handle deveria negar escrita (erro 5)"
    finally:
        h.close()


if __name__ == "__main__":
    for t in (test_no_write_apis, test_handle_is_read_only):
        t()
        print("OK", t.__name__)
