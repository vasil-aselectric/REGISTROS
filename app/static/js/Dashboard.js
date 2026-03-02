(() => {
  const deviceId = document.body.dataset.deviceId || "equipo1";

  const els = {
    ts: document.getElementById("ts"),
    n: document.getElementById("n"),
    ph: document.getElementById("ph"),
    cloro: document.getElementById("cloro"),
    turbidez: document.getElementById("turbidez"),
    temperatura: document.getElementById("temperatura"),
    status: document.getElementById("status"),
    tbody: document.getElementById("tbody"),

    // Barra / contador visual
    rowProgress: document.getElementById("rowProgress"),
    rowCountdown: document.getElementById("rowCountdown"),
  };

  const fmt = (x) => (x === null || x === undefined) ? "--" : Number(x).toFixed(2);

  // Tu fila nueva llega 1 vez por minuto
  const ROW_PERIOD_MS = 60_000;

  // Cada cuánto consultamos al backend (para detectar fila nueva)
  const POLL_MS = 5_000;

  // Cada cuánto animamos la barra (fluido)
  const ANIM_MS = 200;

  // Guardamos el timestamp del último registro (minuto)
  let lastRowTs = null;

  // Momento (en ms) cuando detectamos "fila nueva"
  let lastRowDetectedAt = Date.now();

  function renderTable(rows) {
    els.tbody.innerHTML = "";
    for (const r of rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${r.ts}</td>
        <td>${fmt(r.ph)}</td>
        <td>${fmt(r.cloro)}</td>
        <td>${fmt(r.turbidez)}</td>
        <td>${fmt(r.temperatura)}</td>
        <td>${r.n}</td>
      `;
      els.tbody.appendChild(tr);
    }
  }

  async function fetchLatest() {
    const r = await fetch(`/api/v1/devices/${encodeURIComponent(deviceId)}/latest`, { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  }

  async function fetchRecent20() {
    const r = await fetch(`/api/v1/devices/${encodeURIComponent(deviceId)}/recent?limit=20`, { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  }

  function updateProgressBar() {
    if (!els.rowProgress || !els.rowCountdown) return;

    const now = Date.now();
    const elapsed = now - lastRowDetectedAt;

    // progreso de 0 a 1
    const p = Math.min(1, Math.max(0, elapsed / ROW_PERIOD_MS));

    // Queremos "se consume": 100% -> 0%
    const remainingMs = Math.max(0, ROW_PERIOD_MS - elapsed);
    const remainingSec = Math.ceil(remainingMs / 1000);

    els.rowCountdown.textContent = String(remainingSec);
    els.rowProgress.style.width = `${Math.round((1 - p) * 100)}%`;
  }

  async function poll() {
    try {
      const latest = await fetchLatest();

      // KPI
      els.ts.textContent = latest.ts;
      els.n.textContent = latest.n;
      els.ph.textContent = fmt(latest.ph);
      els.cloro.textContent = fmt(latest.cloro);
      els.turbidez.textContent = fmt(latest.turbidez);
      els.temperatura.textContent = fmt(latest.temperatura);

      // Si cambió el ts => llegó una fila nueva (nuevo minuto)
      if (lastRowTs === null) {
        lastRowTs = latest.ts;
        lastRowDetectedAt = Date.now(); // arrancamos barra desde aquí
        const rows = await fetchRecent20();
        renderTable(rows);
      } else if (latest.ts !== lastRowTs) {
        lastRowTs = latest.ts;
        lastRowDetectedAt = Date.now(); // reinicia barra
        const rows = await fetchRecent20();
        renderTable(rows);
      }

      els.status.textContent = "OK";
    } catch (e) {
      els.status.textContent = "ERROR: " + e.message;
    }
  }

  // Arranque
  poll();
  updateProgressBar();

  // Poll al backend cada 5s
  setInterval(poll, POLL_MS);

  // Animación de barra (suave)
  setInterval(updateProgressBar, ANIM_MS);
})();