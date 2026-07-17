(function () {
  "use strict";
  var status = document.getElementById("connection-status");
  var requestId = "00000000-0000-4000-8000-000000000001";
  var connected = false;
  var retryTimer = null;
  var RETRY_INTERVAL_MS = 250;
  var MAX_RETRIES = 40;
  var retriesRemaining = MAX_RETRIES;

  function stopRetrying() {
    if (retryTimer !== null) {
      window.clearInterval(retryTimer);
      retryTimer = null;
    }
  }

  // Interpret a raw JSON response string produced by the Python dispatcher.
  // Returns true once a response for our request has been consumed so callers
  // can stop retrying.
  function handleResponse(raw) {
    if (!raw) { return false; }
    var response;
    try {
      response = JSON.parse(raw);
    } catch (error) {
      return false;
    }
    if (!response || response.request_id !== requestId) { return false; }
    connected = true;
    stopRetrying();
    if (response.ok) {
      status.textContent = "Add-in connected.";
    } else {
      status.textContent = "Add-in connection error: " + response.error.message;
    }
    return true;
  }

  function send(action, payload) {
    var request = { protocol_version: 1, request_id: requestId, action: action, payload: payload || {} };
    var result;
    try {
      result = adsk.fusionSendData("fmsm.request", JSON.stringify(request));
    } catch (error) {
      // ``adsk`` may not be injected yet on the very first tick; the retry
      // loop below will try again.
      return;
    }
    // The old (CEF) browser returns the add-in's returnData string
    // synchronously; the new (Qt) browser returns a Promise that resolves to
    // it.  Support both so the handshake completes on every Fusion build.
    if (result && typeof result.then === "function") {
      result.then(handleResponse);
    } else if (result) {
      handleResponse(result);
    }
  }

  // Python-initiated pushes (unused today) still arrive here; keep the handler
  // registered and returning a string per the Fusion palette contract.
  window.fusionJavaScriptHandler = { handle: function (action, data) {
    if (action === "fmsm.response") { handleResponse(data); }
    return "OK";
  }};

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

  pingAddin();
}());
