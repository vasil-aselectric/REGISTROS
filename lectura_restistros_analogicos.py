import time
import sqlite3
from datetime import datetime, timedelta

import minimalmodbus
import serial


# =========================
# CONFIG (NO TOCAR CONEXIÓN)
# =========================
PLC_COM = "COM5"
PLC_BAUD = 9600
PLC_SLAVE_ID = 1

SAMPLE_EVERY_SECONDS = 15 * 60  # 15 min
DB_PATH = "plc_analog_log.sqlite3"

# Canales: D1110..D1113  (AD0..AD3)
D_START = 1110
NUM_CHANNELS = 4


# =========================
# MODBUS / PLC
# =========================
def make_instrument() -> minimalmodbus.Instrument:
    inst = minimalmodbus.Instrument(PLC_COM, PLC_SLAVE_ID)
    inst.serial.baudrate = PLC_BAUD
    inst.serial.bytesize = 7
    inst.serial.parity = serial.PARITY_EVEN
    inst.serial.stopbits = 1
    inst.serial.timeout = 1
    inst.mode = minimalmodbus.MODE_ASCII
    inst.clear_buffers_before_each_transaction = True
    inst.debug = False
    return inst


def modbus_addr_for_D(d_number: int) -> int:
    # Tu mapeo probado: Dn -> 4096 + n  (ej: D50 -> 4146)
    return 4096 + d_number


def read_4_ai(inst: minimalmodbus.Instrument) -> dict:
    """
    Lee D1110..D1113 como Holding Registers (FC3).
    Retorna dict con llaves: ch0..ch3
    """
    values = {}
    for i in range(NUM_CHANNELS):
        d = D_START + i
        addr = modbus_addr_for_D(d)
        # read_register(registeraddress, number_of_decimals)
        raw = inst.read_register(addr, 0, functioncode=3, signed=False)
        values[f"ch{i}"] = raw
    return values


# =========================
# SQLITE
# =========================
def init_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")

        con.execute("""
        CREATE TABLE IF NOT EXISTS samples (
            ts_iso TEXT PRIMARY KEY,
            ch0 INTEGER NOT NULL,
            ch1 INTEGER NOT NULL,
            ch2 INTEGER NOT NULL,
            ch3 INTEGER NOT NULL
        );
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS daily_avg (
            day_iso TEXT PRIMARY KEY,   -- YYYY-MM-DD (día del promedio)
            avg_ch0 REAL NOT NULL,
            avg_ch1 REAL NOT NULL,
            avg_ch2 REAL NOT NULL,
            avg_ch3 REAL NOT NULL,
            samples_count INTEGER NOT NULL,
            computed_at_iso TEXT NOT NULL
        );
        """)


def insert_sample(db_path: str, ts: datetime, values: dict) -> None:
    ts_iso = ts.isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as con:
        con.execute(
            "INSERT OR REPLACE INTO samples(ts_iso, ch0, ch1, ch2, ch3) VALUES (?, ?, ?, ?, ?);",
            (ts_iso, values["ch0"], values["ch1"], values["ch2"], values["ch3"])
        )


def compute_daily_average(db_path: str, day: datetime.date) -> None:
    """
    Calcula promedio del día completo [day 00:00:00, day+1 00:00:00)
    y lo guarda en daily_avg. Si ya existe, no recalcula.
    """
    day_iso = day.isoformat()
    next_day = day + timedelta(days=1)

    with sqlite3.connect(db_path) as con:
        # ¿Ya existe?
        row = con.execute("SELECT 1 FROM daily_avg WHERE day_iso = ?;", (day_iso,)).fetchone()
        if row:
            return

        start_iso = datetime.combine(day, datetime.min.time()).isoformat(timespec="seconds")
        end_iso = datetime.combine(next_day, datetime.min.time()).isoformat(timespec="seconds")

        r = con.execute("""
            SELECT
                AVG(ch0) AS avg_ch0,
                AVG(ch1) AS avg_ch1,
                AVG(ch2) AS avg_ch2,
                AVG(ch3) AS avg_ch3,
                COUNT(*) AS n
            FROM samples
            WHERE ts_iso >= ? AND ts_iso < ?;
        """, (start_iso, end_iso)).fetchone()

        avg_ch0, avg_ch1, avg_ch2, avg_ch3, n = r
        if n == 0:
            # No hubo datos ese día, no guardamos promedio vacío
            return

        con.execute("""
            INSERT INTO daily_avg(day_iso, avg_ch0, avg_ch1, avg_ch2, avg_ch3, samples_count, computed_at_iso)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            day_iso, float(avg_ch0), float(avg_ch1), float(avg_ch2), float(avg_ch3),
            int(n), datetime.now().isoformat(timespec="seconds")
        ))


# =========================
# LOOP PRINCIPAL
# =========================
def main():
    init_db(DB_PATH)
    inst = make_instrument()

    # Para calcular promedios diarios: guardamos el "último día visto"
    last_day_seen = None

    while True:
        now = datetime.now()

        # Si cambió el día, calculamos el promedio del día anterior una vez
        if last_day_seen is None:
            last_day_seen = now.date()
        elif now.date() != last_day_seen:
            yesterday = last_day_seen
            compute_daily_average(DB_PATH, yesterday)
            last_day_seen = now.date()

        try:
            values = read_4_ai(inst)
            insert_sample(DB_PATH, now, values)
            print(f"[{now.isoformat(timespec='seconds')}] D1110..D1113 = {values}")
        except Exception as e:
            # No matamos el proceso; solo reportamos y seguimos
            print(f"[{now.isoformat(timespec='seconds')}] ERROR leyendo Modbus: {e}")

        time.sleep(SAMPLE_EVERY_SECONDS)


if __name__ == "__main__":
    main()