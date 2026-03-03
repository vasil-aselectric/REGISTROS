/* app/static/js/Dashboard.es5.js */
/* ES5 compatible (HMI): simple, sin barra, sin countdown, sin animaciones */

(function () {
  function byId(id) { return document.getElementById(id); }

  function getDeviceId() {
    try {
      if (document.body && document.body.getAttribute) {
        var v = document.body.getAttribute("data-device-id");
        if (v) return v;
      }
    } catch (e) {}
    return "equipo1";
  }

  function fmt(x) {
    if (x === null || x === undefined) return "--";
    var n = Number(x);
    if (isNaN(n)) return "--";
    return n.toFixed(2);
  }

  function setStatus(text) {
    var el = byId("status");
    if (el) el.innerHTML = text;
  }

  function xhrJson(url, onOk, onErr) {
    // cache bust por si el HMI cachea agresivo
    var sep = url.indexOf("?") >= 0 ? "&" : "?";
    var full = url + sep + "_=" + String(new Date().getTime());

    var xhr = new XMLHttpRequest();
    xhr.open("GET", full, true);
    xhr.setRequestHeader("Cache-Control", "no-cache");
    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) return;
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          onOk(JSON.parse(xhr.responseText));
        } catch (e) {
          onErr("JSON parse: " + e.message);
        }
      } else {
        onErr("HTTP " + xhr.status);
      }
    };
    xhr.onerror = function () { onErr("Network error"); };
    try { xhr.send(null); } catch (e) { onErr("Send error: " + e.message); }
  }

  function renderLatest(latest) {
    var el;

    el = byId("ts"); if (el) el.innerHTML = latest.ts || "--";
    el = byId("n");  if (el) el.innerHTML = (latest.n !== undefined && latest.n !== null) ? String(latest.n) : "--";

    el = byId("ph"); if (el) el.innerHTML = fmt(latest.ph);
    el = byId("cloro"); if (el) el.innerHTML = fmt(latest.cloro);
    el = byId("turbidez"); if (el) el.innerHTML = fmt(latest.turbidez);
    el = byId("temperatura"); if (el) el.innerHTML = fmt(latest.temperatura);
  }

  function renderTable(rows) {
    var tbody = byId("tbody");
    if (!tbody) return;

    tbody.innerHTML = "";
    if (!rows || !rows.length) return;

    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" + (r.ts || "--") + "</td>" +
        "<td>" + fmt(r.ph) + "</td>" +
        "<td>" + fmt(r.cloro) + "</td>" +
        "<td>" + fmt(r.turbidez) + "</td>" +
        "<td>" + fmt(r.temperatura) + "</td>" +
        "<td>" + ((r.n !== undefined && r.n !== null) ? String(r.n) : "--") + "</td>";
      tbody.appendChild(tr);
    }
  }

  // -------------------------
  // API
  // -------------------------
  var deviceId = getDeviceId();
  var latestUrl = "/api/v1/devices/" + encodeURIComponent(deviceId) + "/latest";
  var recentUrl = "/api/v1/devices/" + encodeURIComponent(deviceId) + "/recent?limit=15";

  var lastTs = null;
  var inFlight = false;

  function pollOnce() {
    if (inFlight) return;
    inFlight = true;

    xhrJson(
      latestUrl,
      function (latest) {
        renderLatest(latest);

        // Tabla: solo repinta si cambia el ts (o primera carga)
        var ts = latest.ts || null;
        if (lastTs === null || (ts !== null && ts !== lastTs)) {
          lastTs = ts;

          xhrJson(
            recentUrl,
            function (rows) {
              renderTable(rows);
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

        setStatus("OK");
        inFlight = false;
      },
      function (err) {
        setStatus("ERROR (latest): " + err);
        inFlight = false;
      }
    );
  }

  setStatus("Conectando…");
  pollOnce();
  setInterval(pollOnce, 5000); // cada 5s
})();