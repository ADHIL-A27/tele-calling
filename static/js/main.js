(function () {
  "use strict";

  function toggleSidebar() {
    var sidebar = document.getElementById("claySidebar");
    var overlay = document.getElementById("sidebarOverlay");
    if (!sidebar) return;
    sidebar.classList.toggle("is-open");
    if (overlay) overlay.classList.toggle("is-open");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var toggleBtn = document.getElementById("sidebarToggle");
    var overlay = document.getElementById("sidebarOverlay");
    if (toggleBtn) toggleBtn.addEventListener("click", toggleSidebar);
    if (overlay) overlay.addEventListener("click", toggleSidebar);

    document.querySelectorAll(".clay-dropdown").forEach(function (dropdown) {
      var btn = dropdown.querySelector("button");
      var menu = dropdown.querySelector(".clay-dropdown__menu");
      if (!btn || !menu) return;
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var isOpen = menu.classList.contains("is-open");
        document.querySelectorAll(".clay-dropdown__menu.is-open").forEach(function (m) {
          m.classList.remove("is-open");
        });
        menu.classList.toggle("is-open", !isOpen);
        btn.setAttribute("aria-expanded", String(!isOpen));
      });
    });

    document.addEventListener("click", function () {
      document.querySelectorAll(".clay-dropdown__menu.is-open").forEach(function (m) {
        m.classList.remove("is-open");
      });
    });

    document.querySelectorAll("[data-clay-modal-target]").forEach(function (trigger) {
      trigger.addEventListener("click", function () {
        var target = document.querySelector(trigger.getAttribute("data-clay-modal-target"));
        if (target) target.classList.add("is-open");
      });
    });

    document.querySelectorAll("[data-clay-modal-close]").forEach(function (closer) {
      closer.addEventListener("click", function () {
        var modal = closer.closest(".clay-modal-backdrop");
        if (modal) modal.classList.remove("is-open");
      });
    });
  });

  window.clayToast = function (message, variant) {
    var area = document.getElementById("toast-area");
    if (!area) return;
    var toast = document.createElement("div");
    toast.className = "clay-card clay-card--compact clay-card--flat";
    toast.style.borderLeft = "5px solid var(--clay-" + (variant || "info") + ")";
    toast.textContent = message;
    area.appendChild(toast);
    setTimeout(function () {
      toast.remove();
    }, 4000);
  };
})();
