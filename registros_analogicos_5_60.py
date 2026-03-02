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

SAMPLE_EVERY_SECONDS = 5       # cada 5 s
REPORT_EVERY_SECONDS = 60      # informe cada 60 s (promedio del último minuto)

DB_PATH = "plc_analog_log_test_5s_60s.sqlite3"

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
    # Dn -> 4096 + n  (ej: D50 -> 4146)
    return 4096 + d_number


def read_4_ai(inst: minimalmodbus.Instrument) -> dict:
    values = {}
    for i in range(NUM_CHANNELS):
        d = D_START + i
        addr = modbus_addr_for_D(d)
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
        CREATE TABLE IF NOT EXISTS samples_5s (
            ts_iso TEXT PRIMARY KEY,
            ch0 INTEGER NOT NULL,
            ch1 INTEGER NOT NULL,
            ch2 INTEGER NOT NULL,
            ch3 INTEGER NOT NULL
        );
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS minute_avg (
            minute_iso TEXT PRIMARY KEY,   -- YYYY-MM-DDTHH:MM (minuto del promedio)
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
            "INSERT OR REPLACE INTO samples_5s(ts_iso, ch0, ch1, ch2, ch3) VALUES (?, ?, ?, ?, ?);",
            (ts_iso, values["ch0"], values["ch1"], values["ch2"], values["ch3"])
        )


def compute_minute_average(db_path: str, start_ts: datetime, end_ts: datetime) -> dict | None:
    """
    Calcula promedio en el intervalo [start_ts, end_ts)
    y lo guarda en minute_avg usando minute_iso = start_ts 'YYYY-MM-DDTHH:MM'
    """
    minute_iso = start_ts.strftime("%Y-%m-%dT%H:%M")

    with sqlite3.connect(db_path) as con:
        # Si ya existe ese minuto, no recalcula (evita duplicados si reinicias)
        row = con.execute("SELECT 1 FROM minute_avg WHERE minute_iso = ?;", (minute_iso,)).fetchone()
        if row:
            return None

        start_iso = start_ts.isoformat(timespec="seconds")
        end_iso = end_ts.isoformat(timespec="seconds")

        r = con.execute("""
            SELECT
                AVG(ch0) AS avg_ch0,
                AVG(ch1) AS avg_ch1,
                AVG(ch2) AS avg_ch2,
                AVG(ch3) AS avg_ch3,
                COUNT(*) AS n
            FROM samples_5s
            WHERE ts_iso >= ? AND ts_iso < ?;
        """, (start_iso, end_iso)).fetchone()

        avg_ch0, avg_ch1, avg_ch2, avg_ch3, n = r
        if n == 0:
            return None

        result = {
            "minute_iso": minute_iso,
            "avg_ch0": float(avg_ch0),
            "avg_ch1": float(avg_ch1),
            "avg_ch2": float(avg_ch2),
            "avg_ch3": float(avg_ch3),
            "samples_count": int(n),
        }

        con.execute("""
            INSERT INTO minute_avg(minute_iso, avg_ch0, avg_ch1, avg_ch2, avg_ch3, samples_count, computed_at_iso)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            minute_iso,
            result["avg_ch0"], result["avg_ch1"], result["avg_ch2"], result["avg_ch3"],
            result["samples_count"],
            datetime.now().isoformat(timespec="seconds")
        ))

        return result


# =========================
# LOOP PRINCIPAL
# =========================
def align_to_next_boundary(boundary_seconds: int) -> datetime:
    """
    Devuelve el datetime del próximo múltiplo de boundary_seconds (alineado).
    Ej: boundary=60 => próximo cambio de minuto.
    """
    now = datetime.now()
    # truncar a segundo
    now_ts = int(now.timestamp())
    next_ts = ((now_ts // boundary_seconds) + 1) * boundary_seconds
    return datetime.fromtimestamp(next_ts)


def main():
    init_db(DB_PATH)
    inst = make_instrument()

    # Ventana de reporte: alineada a minuto real (xx:xx:00)
    window_start = datetime.now()
    window_end = align_to_next_boundary(REPORT_EVERY_SECONDS)

    while True:
        now = datetime.now()

        # Si pasamos el final de ventana, calculamos promedio de esa ventana (puede ser 60s exactos)
        if now >= window_end:
            avg = compute_minute_average(DB_PATH, window_start, window_end)
            if avg:
                print(
                    f"[MINUTE AVG {avg['minute_iso']}] "
                    f"ch0={avg['avg_ch0']:.2f} ch1={avg['avg_ch1']:.2f} "
                    f"ch2={avg['avg_ch2']:.2f} ch3={avg['avg_ch3']:.2f} "
                    f"(n={avg['samples_count']})"
                )

            # avanzar ventana
            window_start = window_end
            window_end = window_end + timedelta(seconds=REPORT_EVERY_SECONDS)
            # si el PC estuvo parado y se saltó varios minutos, re-alinear al próximo minuto real:
            if window_end < now - timedelta(seconds=REPORT_EVERY_SECONDS * 2):
                window_start = now
                window_end = align_to_next_boundary(REPORT_EVERY_SECONDS)

        try:
            values = read_4_ai(inst)
            insert_sample(DB_PATH, now, values)
            print(f"[{now.isoformat(timespec='seconds')}] {values}")
        except Exception as e:
            print(f"[{now.isoformat(timespec='seconds')}] ERROR leyendo Modbus: {e}")

        time.sleep(SAMPLE_EVERY_SECONDS)


if __name__ == "__main__":
    main()