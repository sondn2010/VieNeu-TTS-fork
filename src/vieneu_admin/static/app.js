/* VieNeu admin: small progressive enhancements (no eval, CSP-friendly). */
(function () {
  "use strict";

  // Swap HTML error responses (400/403/413/429/500/503) so validation messages show in place.
  document.addEventListener("htmx:beforeSwap", function (e) {
    var xhr = e.detail.xhr;
    var type = xhr.getResponseHeader("Content-Type") || "";
    if (xhr.status >= 400 && type.indexOf("text/html") === 0) {
      e.detail.shouldSwap = true;
      e.detail.isError = false;
    }
  });

  document.addEventListener("click", function (e) {
    var el = e.target.closest("[data-copy],[data-dismiss],[data-confirm]");
    if (!el) return;
    if (el.hasAttribute("data-confirm") && !window.confirm(el.getAttribute("data-confirm"))) {
      e.preventDefault();
      return;
    }
    if (el.hasAttribute("data-copy")) {
      var src = document.querySelector(el.getAttribute("data-copy"));
      if (src && navigator.clipboard) {
        navigator.clipboard.writeText(src.textContent.trim()).then(function () {
          el.textContent = "Copied";
        }, function () {
          el.textContent = "Select and copy manually";
        });
      }
    }
    if (el.hasAttribute("data-dismiss")) {
      var panel = document.querySelector(el.getAttribute("data-dismiss"));
      if (panel) panel.remove();
    }
  });

  // Character counter for the Script Lab textarea.
  document.addEventListener("input", function (e) {
    var sel = e.target.getAttribute && e.target.getAttribute("data-counter");
    if (!sel) return;
    var out = document.querySelector(sel);
    if (!out) return;
    var n = e.target.value.length;
    var maxRender = parseInt(out.getAttribute("data-max-render") || "0", 10);
    out.textContent = n.toLocaleString() + " characters" +
      (maxRender && n > maxRender ? " (too long for in-app audio)" : "");
  });
})();
