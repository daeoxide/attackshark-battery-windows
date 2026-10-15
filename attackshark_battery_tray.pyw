"""Attack Shark Battery - nivel da bateria do mouse na bandeja do Windows (somente leitura).

Uso: pythonw attackshark_battery_tray.pyw
Codigo do app: attackshark_battery/app.py. Protocolo: docs/PROTOCOL.md.
"""
import sys

from attackshark_battery.app import main

if __name__ == "__main__":
    main(sys.argv[1:])
