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


if __name__ == "__main__":
    test_frames()
    print("OK test_frames")
