(function () {
  "use strict";
  var status = document.getElementById("connection-status");
  var requestId = "00000000-0000-4000-8000-000000000001";
  var connected = false;
  var retryTimer = null;
  var RETRY_INTERVAL_MS = 250;
  var MAX_RETRIES = 40;
  var retriesRemaining = MAX_RETRIES;

  function send(action, payload) {
    var request = { protocol_version: 1, request_id: requestId, action: action, payload: payload || {} };
    adsk.fusionSendData("fmsm.request", JSON.stringify(request));
  }

  function stopRetrying() {
    if (retryTimer !== null) {
      window.clearInterval(retryTimer);
      retryTimer = null;
    }
  }

  // A palette document can load before Python has attached incomingFromHTML.
  // Retry the idempotent ping until a response arrives so that startup ordering
  // cannot leave the visible palette permanently stuck on its connecting state.
  function pingAddin() {
    send("system.ping");
    retryTimer = window.setInterval(function () {
      if (connected) {
        stopRetrying();
        return;
      }
      if (retriesRemaining <= 0) {
        stopRetrying();
        status.textContent = "Add-in did not respond. Restart the add-in from Fusion's Scripts and Add-Ins dialog.";
        return;
      }
      retriesRemaining -= 1;
      send("system.ping");
    }, RETRY_INTERVAL_MS);
  }

  window.fusionJavaScriptHandler = { handle: function (action, data) {
    if (action !== "fmsm.response") { return; }
    var response = JSON.parse(data);
    if (response.request_id !== requestId) { return; }
    connected = true;
    stopRetrying();
    if (response.ok) {
      status.textContent = "Add-in connected.";
      return;
    }
    status.textContent = "Add-in connection error: " + response.error.message;
  }};

  pingAddin();
}());
