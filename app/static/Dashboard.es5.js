/* app/static/js/Dashboard.es5.js */
/* ES5 compatible (HMI-friendly): no async/await, no fetch, no template literals, no const/let */

(function () {
  // -------------------------
  // Helpers
  // -------------------------
  function getDeviceId() {
    try {
      // Preferimos data-device-id si existe
      if (document.body && document.body.getAttribute) {
        var v = document.body.getAttribute("data-device-id");
        if (v) return v;
      }
    } catch (e) {}
    return "equipo1";
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function fmt(x) {
    if (x === null || x === undefined) return "--";
    var n = Number(x);
    if (isNaN(n)) return "--";
    // 2 decimales como en el moderno
    return n.toFixed(2);
  }

  function xhrJson(url, onOk, onErr) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    // cache bust (algunos HMIs cachean agresivo)
    xhr.setRequestHeader("Cache-Control", "no-cache");
    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) return;
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          var data = JSON.parse(xhr.responseText);
          onOk(data);
        } catch (e) {
          onErr("JSON parse: " + e.message);
        }
      } else {
        onErr("HTTP " + xhr.status);
      }
    };
    xhr.onerror = function () {
      onErr("Network error");
    };
    try {
      xhr.send(null);
    } catch (e) {
      onErr("Send error: " + e.message);
    }
  }

  // -------------------------
  // DOM elements
  // -------------------------
  var deviceId = getDeviceId();

  var els = {
    ts: byId("ts"),
    n: byId("n"),
    ph: byId("ph"),
    cloro: byId("cloro"),
    turbidez: byId("turbidez"),
    temperatura: byId("temperatura"),
    status: byId("status"),
    tbody: byId("tbody"),

    rowProgress: byId("rowProgress"),
    rowCountdown: byId("rowCountdown")
  };

  // -------------------------
  // Config
  // -------------------------
  var ROW_PERIOD_MS = 60000;  // 1 minuto
  var POLL_MS = 5000;         // refresco KPI cada 5s
  var ANIM_MS = 500;          // update barra/contador (más suave y barato que 200ms)

  // Estado
  var lastRowTs = null;
  var lastRowDetectedAt = new Date().getTime();

  // -------------------------
  // UI
  // -------------------------
  function setStatus(text) {
    if (!els.status) return;
    els.status.innerHTML = text;
  }

  function renderTable(rows) {
    if (!els.tbody) return;

    // Vaciar
    els.tbody.innerHTML = "";

    if (!rows || !rows.length) return;

    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];

      var tr = document.createElement("tr");

      // sin template strings
      var html = ""
        + "<td>" + (r.ts || "--") + "</td>"
        + "<td>" + fmt(r.ph) + "</td>"
        + "<td>" + fmt(r.cloro) + "</td>"
        + "<td>" + fmt(r.turbidez) + "</td>"
        + "<td>" + fmt(r.temperatura) + "</td>"
        + "<td>" + (r.n !== undefined && r.n !== null ? String(r.n) : "--") + "</td>";

      tr.innerHTML = html;
      els.tbody.appendChild(tr);
    }
  }

  function updateProgressBar() {
    if (!els.rowProgress || !els.rowCountdown) return;

    var now = new Date().getTime();
    var elapsed = now - lastRowDetectedAt;

    if (elapsed < 0) elapsed = 0;
    if (elapsed > ROW_PERIOD_MS) elapsed = ROW_PERIOD_MS;

    var remainingMs = ROW_PERIOD_MS - elapsed;
    if (remainingMs < 0) remainingMs = 0;

    var remainingSec = Math.ceil(remainingMs / 1000);

    // contador
    els.rowCountdown.innerHTML = String(remainingSec);

    // “se consume”: 100% -> 0%
    var pct = Math.round((remainingMs / ROW_PERIOD_MS) * 100);
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;

    // OJO: no usamos transition (HMI-friendly)
    els.rowProgress.style.width = String(pct) + "%";
  }

  // -------------------------
  // API calls
  // -------------------------
  function fetchLatest(cbOk, cbErr) {
    var url = "/api/v1/devices/" + encodeURIComponent(deviceId) + "/latest";
    xhrJson(url, cbOk, cbErr);
  }

  function fetchRecent20(cbOk, cbErr) {
    var url = "/api/v1/devices/" + encodeURIComponent(deviceId) + "/recent?limit=20";
    xhrJson(url, cbOk, cbErr);
  }

  // -------------------------
  // Main loop
  // -------------------------
  var inFlight = false;

  function pollOnce() {
    if (inFlight) return; // evita solapes si el HMI va lento
    inFlight = true;

    fetchLatest(
      function (latest) {
        // KPI
        if (els.ts) els.ts.innerHTML = latest.ts || "--";
        if (els.n) els.n.innerHTML = (latest.n !== undefined && latest.n !== null) ? String(latest.n) : "--";
        if (els.ph) els.ph.innerHTML = fmt(latest.ph);
        if (els.cloro) els.cloro.innerHTML = fmt(latest.cloro);
        if (els.turbidez) els.turbidez.innerHTML = fmt(latest.turbidez);
        if (els.temperatura) els.temperatura.innerHTML = fmt(latest.temperatura);

        // Detectar cambio de minuto
        var ts = latest.ts || null;

        // Primera vez o cambió => reinicia barra y refresca tabla
        if (lastRowTs === null) {
          lastRowTs = ts;
          lastRowDetectedAt = new Date().getTime();

          fetchRecent20(
            function (rows) {
              renderTable(rows);
              setStatus("OK");
              inFlight = false;
            },
            function (err) {
              setStatus("ERROR (recent): " + err);
              inFlight = false;
            }
          );
          return;
        }

        if (ts !== null && ts !== lastRowTs) {
          lastRowTs = ts;
          lastRowDetectedAt = new Date().getTime();

          fetchRecent20(
            function (rows2) {
              renderTable(rows2);
              setStatus("OK");
              inFlight = false;
            },
            function (err2) {
              setStatus("ERROR (recent): " + err2);
              inFlight = false;
            }
          );
          return;
        }

        // Si no cambió minuto, no tocamos tabla
        setStatus("OK");
        inFlight = false;
      },
      function (err) {
        setStatus("ERROR (latest): " + err);
        inFlight = false;
      }
    );
  }

  // Arranque
  setStatus("Conectando…");
  pollOnce();
  updateProgressBar();

  // Poll de datos
  setInterval(pollOnce, POLL_MS);

  // Barra/contador
  setInterval(updateProgressBar, ANIM_MS);
})();