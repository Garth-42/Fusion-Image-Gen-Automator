(function () {
  "use strict";
  var status = document.getElementById("connection-status");
  function send(action, payload) {
    var request = { protocol_version: 1, request_id: "00000000-0000-4000-8000-000000000001", action: action, payload: payload || {} };
    adsk.fusionSendData("fmsm.request", JSON.stringify(request));
  }
  window.fusionJavaScriptHandler = { handle: function (action, data) {
    if (action !== "fmsm.response") { return; }
    var response = JSON.parse(data);
    status.textContent = response.ok ? "Add-in connected." : "Add-in connection error: " + response.error.message;
  }};
  send("system.ping", {});
}());
