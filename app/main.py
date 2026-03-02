from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from .database import SessionLocal
from .models import MinuteAvg

from typing import List

from fastapi.staticfiles import StaticFiles

app = FastAPI(title="PLC Telemetry MVP (Lee SQLite local)")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/dashboard-hmi", response_class=HTMLResponse)
def dashboard_hmi(device_id: str = Query("equipo1")):
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard HMI {device_id}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 12px; }}
    .container {{ max-width: 1000px; margin: 0 auto; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 10px; margin-bottom: 10px; }}
    .row {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .kpi {{ min-width: 140px; }}
    .label {{ color: #555; font-size: 13px; }}
    .value {{ font-size: 22px; font-weight: bold; }}
    .muted {{ color: #777; font-size: 13px; }}

    /* tabla: compatible + evita romper layout */
    .table-wrap {{ overflow-x: auto; }}
    table {{ border-collapse: collapse; width: 100%; min-width: 900px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 14px; }}
    th {{ background: #f5f5f5; text-align: left; }}

    /* progreso: sin transition (HMI-friendly) */
    .progress-box {{ position: fixed; top: 12px; right: 12px; width: 40vw; max-width: 220px; min-width: 160px; }}
    .progress-bar {{ height: 10px; border: 1px solid #ddd; border-radius: 999px; overflow: hidden; background: #f5f5f5; }}
    #rowProgress {{ height: 100%; width: 100%; background: #4caf50; }}
  </style>
</head>

<body data-device-id="{device_id}">
  <div class="container">
    <h2>Equipo: <span id="device">{device_id}</span> <span class="muted">(HMI)</span></h2>

    <div class="progress-box">
      <div style="font-size: 12px; color: #555; margin-bottom: 6px;">
        Próxima fila en: <span id="rowCountdown">--</span>s
      </div>
      <div class="progress-bar">
        <div id="rowProgress"></div>
      </div>
    </div>

    <div class="card">
      <div class="muted">
        Última actualización: <span id="ts">--</span> | Nº tomas=<span id="n">--</span>
      </div>

      <div class="row" style="margin-top: 10px;">
        <div class="kpi"><div class="label">pH</div><div class="value" id="ph">--</div></div>
        <div class="kpi"><div class="label">Cloro Libre</div><div class="value" id="cloro">--</div></div>
        <div class="kpi"><div class="label">Turbidez</div><div class="value" id="turbidez">--</div></div>
        <div class="kpi"><div class="label">Temperatura</div><div class="value" id="temperatura">--</div></div>
      </div>
    </div>

    <div class="card">
      <div class="muted">Histórico (últimos 20 registros)</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>pH</th>
              <th>Cloro Libre</th>
              <th>Turbidez</th>
              <th>Temperatura</th>
              <th>Nº tomas</th>
            </tr>
          </thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </div>

    <div class="muted" id="status">Conectando…</div>

    <script src="/static/js/Dashboard.es5.js"></script>
  </div>
</body>
</html>
"""

@app.get("/api/v1/devices/{device_id}/latest")
def latest(device_id: str):
    db = SessionLocal()
    try:
        rows = (
            db.query(MinuteAvg)
            .order_by(MinuteAvg.minute_iso.desc())
            .limit(20)
            .all()
        )

        if not rows:
            raise HTTPException(status_code=404, detail="No data")

        # calcular media global de esos 20 registros
        avg_ph = sum(r.avg_ch0 for r in rows) / len(rows)
        avg_cloro = sum(r.avg_ch1 for r in rows) / len(rows)
        avg_turbidez = sum(r.avg_ch2 for r in rows) / len(rows)
        avg_temp = sum(r.avg_ch3 for r in rows) / len(rows)

        latest_ts = rows[0].minute_iso + ":00"

        return {
            "device_id": device_id,
            "ts": latest_ts,
            "ph": avg_ph,
            "cloro": avg_cloro,
            "turbidez": avg_turbidez,
            "temperatura": avg_temp,
            "n": len(rows),  # ahora será máximo 20
        }

    finally:
        db.close()
    # En esta fase demo, device_id no se usa porque tu tabla minute_avg no tiene columna device_id.
    db = SessionLocal()
    try:
        row = db.query(MinuteAvg).order_by(MinuteAvg.minute_iso.desc()).first()
        if not row:
            raise HTTPException(status_code=404, detail="No data")

        return {
    "device_id": device_id,
    "ts": row.minute_iso + ":00",
    "ph": row.avg_ch0,
    "cloro": row.avg_ch1,
    "turbidez": row.avg_ch2,
    "temperatura": row.avg_ch3,
    "n": row.samples_count,
}
    finally:
        db.close()



@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(device_id: str = Query("equipo1")):
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard {device_id}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 16px; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 12px; margin-bottom: 12px; }}
    .row {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    .kpi {{ min-width: 160px; }}
    .label {{ color: #555; font-size: 13px; }}
    .value {{ font-size: 24px; font-weight: bold; }}
    .muted {{ color: #777; font-size: 13px; }}

    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 14px; }}
    th {{ background: #f5f5f5; text-align: left; }}
  </style>
</head>

<body data-device-id="{device_id}">
  <h2>Equipo: <span id="device">{device_id}</span></h2>

<div style="position: fixed; top: 12px; right: 12px; width: 220px;">
  <div style="font-size: 12px; color: #555; margin-bottom: 6px;">
    Próxima fila en: <span id="rowCountdown">--</span>s
  </div>
  <div style="height: 10px; border: 1px solid #ddd; border-radius: 999px; overflow: hidden; background: #f5f5f5;">
    <div id="rowProgress"
         style="height: 100%; width: 100%; background: #4caf50; transition: width 0.2s linear;"></div>
  </div>
</div>

  <div class="card">
    <div class="muted">
      Última actualización: <span id="ts">--</span> | Nº tomas=<span id="n">--</span>
    </div>

    <div class="row" style="margin-top: 10px;">
      <div class="kpi"><div class="label">pH</div><div class="value" id="ph">--</div></div>
      <div class="kpi"><div class="label">Cloro Libre</div><div class="value" id="cloro">--</div></div>
      <div class="kpi"><div class="label">Turbidez</div><div class="value" id="turbidez">--</div></div>
      <div class="kpi"><div class="label">Temperatura</div><div class="value" id="temperatura">--</div></div>
    </div>
  </div>

  <div class="card">
    <div class="muted">Histórico (últimos 20 registros)</div>
    <table>
      <thead>
        <tr>
          <th>Timestamp</th>
          <th>pH</th>
          <th>Cloro Libre</th>
          <th>Turbidez</th>
          <th>Temperatura</th>
          <th>Nº tomas</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>

  <div class="muted" id="status">Conectando…</div>

  <script src="/static/js/Dashboard.js"></script>
</body>
</html>
"""
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard {device_id}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 16px; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 12px; margin-bottom: 12px; }}
    .row {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    .kpi {{ min-width: 140px; }}
    .label {{ color: #555; font-size: 13px; }}
    .value {{ font-size: 24px; font-weight: bold; }}
    .muted {{ color: #777; font-size: 13px; }}

    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 14px; }}
    th {{ background: #f5f5f5; text-align: left; }}
  </style>
</head>
<body data-device-id="{device_id}">
  <h2>Equipo: <span id="device">{device_id}</span></h2>

  <div class="card">
    <div class="muted">Última actualización: <span id="ts">--</span> | n=<span id="n">--</span></div>
    <div class="row" style="margin-top: 10px;">
      <div class="kpi"><div class="label">CH0</div><div class="value" id="ch0">--</div></div>
      <div class="kpi"><div class="label">CH1</div><div class="value" id="ch1">--</div></div>
      <div class="kpi"><div class="label">CH2</div><div class="value" id="ch2">--</div></div>
      <div class="kpi"><div class="label">CH3</div><div class="value" id="ch3">--</div></div>
    </div>
  </div>

  <div class="card">
    <div class="muted">Histórico (últimos registros)</div>
    <table>
      <thead>
        <tr>
          <th>Timestamp</th>
          <th>CH0</th>
          <th>CH1</th>
          <th>CH2</th>
          <th>CH3</th>
          <th>n</th>
        </tr>
      </thead>
      <tbody id="tbody">
      </tbody>
    </table>
  </div>

  <div class="muted" id="status">Conectando…</div>

  <script src="/static/js/Dashboard.js"></script>
</body>
</html>
"""
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard {device_id}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 16px; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 12px; margin-bottom: 12px; }}
    .row {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    .kpi {{ min-width: 140px; }}
    .label {{ color: #555; font-size: 13px; }}
    .value {{ font-size: 24px; font-weight: bold; }}
    .muted {{ color: #777; font-size: 13px; }}
  </style>
</head>
<body>
  <h2>Equipo: <span id="device">{device_id}</span></h2>

  <div class="card">
    <div class="muted">Última actualización: <span id="ts">--</span> | n=<span id="n">--</span></div>
    <div class="row" style="margin-top: 10px;">
      <div class="kpi"><div class="label">CH0</div><div class="value" id="ch0">--</div></div>
      <div class="kpi"><div class="label">CH1</div><div class="value" id="ch1">--</div></div>
      <div class="kpi"><div class="label">CH2</div><div class="value" id="ch2">--</div></div>
      <div class="kpi"><div class="label">CH3</div><div class="value" id="ch3">--</div></div>
    </div>
  </div>

  <div class="muted" id="status">Conectando…</div>

  <script>
    const deviceId = "{device_id}";
    const els = {{
      ts: document.getElementById("ts"),
      n: document.getElementById("n"),
      ch0: document.getElementById("ch0"),
      ch1: document.getElementById("ch1"),
      ch2: document.getElementById("ch2"),
      ch3: document.getElementById("ch3"),
      status: document.getElementById("status"),
    }};
    const fmt = (x) => (x === null || x === undefined) ? "--" : Number(x).toFixed(2);

    async function refresh() {{
      try {{
        const r = await fetch(`/api/v1/devices/${{encodeURIComponent(deviceId)}}/latest`, {{ cache: "no-store" }});
        if (!r.ok) throw new Error("HTTP " + r.status);
        const d = await r.json();
        els.ts.textContent = d.ts;
        els.n.textContent = d.n;
        els.ch0.textContent = fmt(d.ch0);
        els.ch1.textContent = fmt(d.ch1);
        els.ch2.textContent = fmt(d.ch2);
        els.ch3.textContent = fmt(d.ch3);
        els.status.textContent = "OK";
      }} catch (e) {{
        els.status.textContent = "ERROR: " + e.message;
      }}
    }}
    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>
"""


@app.get("/api/v1/devices/{device_id}/recent")
def recent(device_id: str, limit: int = 20):
    db = SessionLocal()
    try:
        rows = (
            db.query(MinuteAvg)
            .order_by(MinuteAvg.minute_iso.desc())  # más nuevo primero
            .limit(limit)
            .all()
        )

        return [
            {
                "ts": r.minute_iso + ":00",
                "ph": r.avg_ch0,
                "cloro": r.avg_ch1,
                "turbidez": r.avg_ch2,
                "temperatura": r.avg_ch3,
                "n": r.samples_count,
            }
            for r in rows
        ]
    finally:
        db.close()
    # device_id aún no filtra (tu tabla no lo tiene), pero dejamos la ruta igual
    db = SessionLocal()
    try:
        rows = (
            db.query(MinuteAvg)
            .order_by(MinuteAvg.minute_iso.desc())
            .limit(limit)
            .all()
        )
        # devolvemos en orden ASC para pintar bonito la tabla (viejo -> nuevo)
        rows = list(reversed(rows))

        return [
            {
                "ts": r.minute_iso + ":00",
                "ch0": r.avg_ch0,
                "ch1": r.avg_ch1,
                "ch2": r.avg_ch2,
                "ch3": r.avg_ch3,
                "n": r.samples_count,
            }
            for r in rows
        ]
    finally:
        db.close()

@app.get("/")
def root():
    return {"ok": True, "hint": "Visita /dashboard?device_id=equipo1"}