import minimalmodbus
import serial

# Configuración
PLC_COM = 'COM8'
PLC_BAUD = 38400
PLC_SLAVE_ID = 1

instrument = minimalmodbus.Instrument(PLC_COM, PLC_SLAVE_ID)
instrument.serial.baudrate = PLC_BAUD
instrument.serial.bytesize = 8
instrument.serial.parity   = serial.PARITY_NONE
instrument.serial.stopbits = 1
instrument.serial.timeout  = 1
instrument.mode = minimalmodbus.MODE_RTU
instrument.clear_buffers_before_each_transaction = True
instrument.debug = False  # para ver la comunicación
Type_register = input("Ingrese el tipo de registro (D, M, etc.): ")
plc_address = int(input("Ingrese la dirección del registro (número): "))
registers_to_read = 4096 + plc_address

if Type_register.upper() == 'D':
    registers_to_read = 4096 + plc_address
elif Type_register.upper() == 'M':
    registers_to_read = 2048 + plc_address
elif Type_register.upper() == 'X':
    registers_to_read = 1024 + plc_address
elif Type_register.upper() == 'Y':
    registers_to_read = 1025 + plc_address

    
try:
    if Type_register.upper() == 'Y':
        # Para Y usamos read_bit (Function Code 1)
        valor_registro_plc = instrument.read_bit(registers_to_read, functioncode=1)
    else:
        # Para registros D usamos read_register
        valor_registro_plc = instrument.read_register(registers_to_read, 0)
        
    print(f"{Type_register}{plc_address} = {valor_registro_plc}")

except Exception as e:
    print(f"Error leyendo {Type_register}{plc_address}: {e}")


