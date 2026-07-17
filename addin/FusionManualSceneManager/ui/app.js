(function () {
  "use strict";
  var status = document.getElementById("connection-status");
  var requestId = "00000000-0000-4000-8000-000000000001";

  function send(action, payload) {
    var request = { protocol_version: 1, request_id: requestId, action: action, payload: payload || {} };
    adsk.fusionSendData("fmsm.request", JSON.stringify(request));
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
  send("system.ping", {});
}());
