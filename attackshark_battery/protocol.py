"""Protocolo do canal de bateria dos mouses Attack Shark (chipset Xenta, VID 1d57).

O mouse/receptor publica, por conta propria e a cada ~2 s, um relatorio de entrada
de 5 bytes na colecao HID de usage page 0x000A (interface 02):

    03 MM 40 ST NN
    |  |  |  |  +-- nivel de bateria, 0..100 (%)
    |  |  |  +----- estado (ver STATES)
    |  |  +-------- tipo de frame: 0x40 = bateria
    |  +----------- varia por modelo/lote: 0xE5 (projeto Linux original), 0x55 (X11 testado)
    +-------------- report ID

Frames com byte 2 != 0x40 (ex.: 03 MM 01 00 00 quando o enlace pisca) nao sao bateria.
Toda vez que o mouse (re)conecta ao receptor ele manda um frame isolado 03 MM 40 01 64
("100% falso") antes do nivel real - por isso o monitor so aceita um valor repetido.
Detalhes e itens ainda em aberto: docs/PROTOCOL.md.
"""
from dataclasses import dataclass

REPORT_ID = 0x03
FRAME_BATTERY = 0x40
VENDOR_ID = 0x1D57
BATTERY_USAGE_PAGE = 0x000A

# pid -> descricao. O canal de bateria existe nos dois.
PRODUCTS = {
    0xFA60: "receptor 2.4G",
    0xFA55: "mouse no cabo (qualquer posicao da chave)",
    0x2155: "mouse no cabo (outra variante, visto no projeto Linux)",
}

STATE_BATTERY = 0x01
STATE_POWERED = 0x02      # energia externa, carga pausada (LED verde no mouse)
STATE_CHARGING = 0x03     # energia externa, carregando (LED roxo no mouse)

STATES = {
    STATE_BATTERY: "na bateria",
    STATE_POWERED: "na energia, carga pausada",
    STATE_CHARGING: "carregando",
}


@dataclass(frozen=True)
class Frame:
    model_byte: int
    state: int
    level: int
    raw: bytes

    @property
    def on_power(self):
        """Mouse recebendo energia externa (cabo ou dock)."""
        return self.state in (STATE_POWERED, STATE_CHARGING)

    @property
    def state_name(self):
        return STATES.get(self.state, f"desconhecido ({self.state:02x})")


def parse(data):
    """Frame de bateria valido, ou None. Estados desconhecidos sao aceitos
    (e registrados) para nao perder informacao de modelos diferentes."""
    if len(data) < 5 or data[0] != REPORT_ID or data[2] != FRAME_BATTERY or data[4] > 100:
        return None
    return Frame(model_byte=data[1], state=data[3], level=data[4], raw=bytes(data[:5]))
