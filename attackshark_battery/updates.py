"""Procura versao nova na pagina de releases do GitHub (so le; nada e baixado automaticamente)."""
import json
import re
import urllib.request

from . import REPO, __version__

API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"


def parse_version(text):
    """'v1.2.3' -> (1, 2, 3). Sufixos como '-beta' sao ignorados."""
    nums = [int(n) for n in re.findall(r"\d+", str(text).split("-")[0])[:3]]
    return tuple(nums + [0] * (3 - len(nums)))


def is_newer(candidate, current=__version__):
    return parse_version(candidate) > parse_version(current)


def latest_release(timeout=10):
    """(versao, url da pagina) da ultima release publicada."""
    req = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"AttackSharkBattery/{__version__}",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    return data["tag_name"].lstrip("v"), data.get("html_url") or RELEASES_URL
