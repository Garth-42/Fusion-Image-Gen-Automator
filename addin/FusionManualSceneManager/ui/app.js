(function () {
  "use strict";
  var status = document.getElementById("connection-status");
  var requestId = "00000000-0000-4000-8000-000000000001";
  var attempts = 0;
  var maximumAttempts = 20;
  var retryDelayMilliseconds = 250;

  function send(action, payload) {
    var request = { protocol_version: 1, request_id: requestId, action: action, payload: payload || {} };
    adsk.fusionSendData("fmsm.request", JSON.stringify(request));
  }

  function pingAddin() {
    attempts += 1;
    send("system.ping", {});
    if (attempts < maximumAttempts) {
      window.setTimeout(pingAddin, retryDelayMilliseconds);
    }
  }

  window.fusionJavaScriptHandler = { handle: function (action, data) {
    if (action !== "fmsm.response") { return; }
    var response = JSON.parse(data);
    if (response.request_id !== requestId) { return; }
    if (response.ok) {
      status.textContent = "Add-in connected.";
      return;
    }
    status.textContent = "Add-in connection error: " + response.error.message;
  }};
  // A palette document can load before Python has attached incomingFromHTML.
  // Retry the idempotent ping briefly so that startup ordering cannot leave the
  // visible palette permanently stuck on its connecting state.
  pingAddin();
}());
