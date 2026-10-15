import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from attackshark_battery.protocol import parse  # noqa: E402


def test_frames():
    f = parse(bytes.fromhex("035540 01 54".replace(" ", "")))
    assert (f.model_byte, f.state, f.level, f.on_power) == (0x55, 1, 84, False)
    assert parse(bytes.fromhex("03e5400364")).level == 100          # variante E5 (projeto Linux)
    assert parse(bytes.fromhex("0355400255")).on_power              # estado 02 no cabo
    assert parse(bytes.fromhex("03e5010000")) is None               # "falso zero" do enlace
    assert parse(bytes.fromhex("0355400165")) is None               # nivel > 100
    assert parse(bytes.fromhex("0255400150")) is None               # report ID errado
    assert parse(b"\x03\x55") is None


def test_monitor_filters_reconnect_frame_and_detects_flapping():
    from attackshark_battery.monitor import BatteryMonitor
    m = BatteryMonitor()
    seq = ["0355400164", "0355400161", "0355400161"]       # 100% falso de reconexao, depois 97 real
    accepted = [m.feed(parse(bytes.fromhex(h)), 0xFA60) for h in seq]
    assert accepted == [False, False, True] and m.frame.level == 97
    assert not m.flapping()
    # captura real da dock com mau contato (2026-10-14 23:49)
    for h in ["0355400157", "0355400355", "0355400164", "0355400153", "0355400353", "0355400164",
              "0355400356"]:
        m.feed(parse(bytes.fromhex(h)), 0xFA60)
    assert m.flapping()


if __name__ == "__main__":
    test_frames()
    print("OK test_frames")
    test_monitor_filters_reconnect_frame_and_detects_flapping()
    print("OK test_monitor_filters_reconnect_frame_and_detects_flapping")
