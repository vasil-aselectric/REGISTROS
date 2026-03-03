# app/conexion.py
import minimalmodbus
import serial

# CONFIG (NO TOCAR)
PLC_COM = "COM8"
PLC_BAUD = 38400
PLC_SLAVE_ID = 1

D_START = 1110
NUM_CHANNELS = 4


def make_instrument() -> minimalmodbus.Instrument:
    inst = minimalmodbus.Instrument(PLC_COM, PLC_SLAVE_ID)
    inst.serial.baudrate = PLC_BAUD
    inst.serial.bytesize = 8
    inst.serial.parity = serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout = 3
    inst.mode = minimalmodbus.MODE_RTU
    inst.clear_buffers_before_each_transaction = True
    inst.debug = False
    return inst


def modbus_addr_for_D(d_number: int) -> int:
    # Dn -> 4096 + n  (ej: D50 -> 4146)
    return 4096 + d_number


def read_4_ai(inst: minimalmodbus.Instrument, d_start: int = D_START, n: int = NUM_CHANNELS) -> dict:
    values = {}
    for i in range(n):
        d = d_start + i
        addr = modbus_addr_for_D(d)
        raw = inst.read_register(addr, 0, functioncode=3, signed=False)
        values[f"ch{i}"] = int(raw)
    return values


def write_D(inst: minimalmodbus.Instrument, d_number: int, value: int) -> None:
    """
    Escribe un registro Dxxxx usando el mismo esquema de direccionamiento.
    Usamos functioncode=16 por compatibilidad.
    """
    addr = modbus_addr_for_D(d_number)
    inst.write_register(addr, int(value), number_of_decimals=0, functioncode=16, signed=False)