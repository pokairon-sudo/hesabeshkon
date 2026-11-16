/* ابزارهای مشترک رابط بروتالیست */
(function () {
  "use strict";

  function readJSONScript(id, fallback) {
    const el = document.getElementById(id);
    if (!el) return fallback;
    try {
      return JSON.parse(el.textContent);
    } catch (error) {
      return fallback;
    }
  }

  const shop = readJSONScript("shop-config", {
    currencyUnit: "toman",
    currencyLabel: "تومان",
    usdRate: "0",
    showUsd: false,
  });

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^|;\\s*)" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[2]) : "";
  }

  const csrfToken =
    (document.querySelector('input[name="csrfmiddlewaretoken"]') || {}).value ||
    getCookie("csrftoken");

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function toNumber(value) {
    const n = Number(String(value == null ? 0 : value).replace(/,/g, ""));
    return Number.isFinite(n) ? n : 0;
  }

  function formatNumber(value) {
    const n = toNumber(value);
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(n);
  }

  function formatMoney(value, withUSD) {
    let display = toNumber(value);
    if (shop.currencyUnit === "rial") display *= 10;
    let text = formatNumber(display) + " " + shop.currencyLabel;
    const rate = toNumber(shop.usdRate);
    if (withUSD && shop.showUsd && rate > 0) {
      text += " ≈ $" + formatNumber(toNumber(value) / rate);
    }
    return text;
  }

  function formatUSD(value) {
    const rate = toNumber(shop.usdRate);
    if (!shop.showUsd || rate <= 0) return "";
    return "$" + formatNumber(toNumber(value) / rate);
  }

  function toast(message, type) {
    let box = document.getElementById("toasts");
    if (!box) {
      box = document.createElement("div");
      box.id = "toasts";
      document.body.appendChild(box);
    }
    const node = document.createElement("div");
    node.className = "toast toast--" + (type || "info");
    node.setAttribute("role", "status");
    node.textContent = message;
    box.appendChild(node);
    setTimeout(function () {
      node.style.opacity = "0";
      node.style.transform = "translateY(8px)";
      setTimeout(function () {
        node.remove();
      }, 180);
    }, 4200);
  }

  async function fetchJSON(url, options) {
    const opts = Object.assign({ method: "GET", headers: {} }, options || {});
    opts.headers = Object.assign({ "X-Requested-With": "XMLHttpRequest" }, opts.headers || {});
    if (opts.method && opts.method.toUpperCase() !== "GET") {
      opts.headers["X-CSRFToken"] = csrfToken;
    }
    const response = await fetch(url, opts);
    let data = null;
    try {
      data = await response.json();
    } catch (error) {
      data = null;
    }
    if (response.redirected) {
      const err = new Error("نشست شما منقضی شده است؛ صفحه را دوباره بارگذاری کنید.");
      err.status = 401;
      throw err;
    }
    if (!response.ok) {
      const message =
        (data && (data.errors || []).join(" ")) ||
        (data && data.error) ||
        "درخواست ناموفق بود (" + response.status + ").";
      const err = new Error(message);
      err.data = data;
      err.status = response.status;
      throw err;
    }
    if (data === null) {
      const err = new Error("پاسخ سرور نامعتبر بود؛ صفحه را دوباره بارگذاری کنید.");
      err.status = response.status;
      throw err;
    }
    return data;
  }

  function openModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    const focusable = modal.querySelector("input, select, textarea, button");
    if (focusable) setTimeout(() => focusable.focus(), 40);
  }

  function closeModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
  }

  function confirmDialog(message, onConfirm, options) {
    const opts = options || {};
    const id = "confirm-modal";
    let modal = document.getElementById(id);
    if (modal) modal.remove();
    modal = document.createElement("div");
    modal.id = id;
    modal.className = "brut-modal-backdrop open";
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.innerHTML =
      '<div class="brut-modal" style="width:min(460px,100%)">' +
      '<div class="brut-modal__head"><span class="brut-modal__title">' +
      escapeHtml(opts.title || "تأیید") +
      "</span></div>" +
      '<p class="mb-3" style="font-weight:700">' +
      escapeHtml(message) +
      "</p>" +
      '<div class="row" style="justify-content:flex-end">' +
      '<button type="button" class="brut-btn brut-btn--ghost" data-cancel>انصراف</button>' +
      '<button type="button" class="brut-btn brut-btn--danger" data-ok>' +
      escapeHtml(opts.okText || "بله، انجام بده") +
      "</button></div></div>";
    document.body.appendChild(modal);

    function close() {
      modal.remove();
      document.removeEventListener("keydown", onKey);
    }
    function onKey(event) {
      if (event.key === "Escape") close();
    }
    modal.querySelector("[data-cancel]").addEventListener("click", close);
    modal.querySelector("[data-ok]").addEventListener("click", function () {
      close();
      onConfirm();
    });
    modal.addEventListener("click", function (event) {
      if (event.target === modal) close();
    });
    document.addEventListener("keydown", onKey);
    setTimeout(() => modal.querySelector("[data-ok]").focus(), 30);
  }

  // تأییدیه‌ی فرم‌های حذف/ابطال
  document.addEventListener("submit", function (event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const message = form.getAttribute("data-confirm");
    if (!message || form.dataset.confirmed === "1") return;
    event.preventDefault();
    confirmDialog(message, function () {
      form.dataset.confirmed = "1";
      form.requestSubmit();
    });
  });

  // Escape برای بستن مودال‌ها
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      document.querySelectorAll(".brut-modal-backdrop.open").forEach(function (modal) {
        if (modal.id !== "confirm-modal") closeModal(modal.id);
      });
    }
  });

  // بستن مودال با کلیک روی پس‌زمینه و دکمه‌های [data-close-modal]
  document.addEventListener("click", function (event) {
    if (event.target.classList && event.target.classList.contains("brut-modal-backdrop")) {
      closeModal(event.target.id);
    }
    const closer = event.target.closest("[data-close-modal]");
    if (closer) closeModal(closer.getAttribute("data-close-modal"));
  });

  // نمایش ساعت/تاریخ سرور در هدر؟ خیر؛ فقط ابزارها.
  window.HS = {
    shop: shop,
    csrfToken: csrfToken,
    escapeHtml: escapeHtml,
    formatNumber: formatNumber,
    formatMoney: formatMoney,
    formatUSD: formatUSD,
    toNumber: toNumber,
    toast: toast,
    fetchJSON: fetchJSON,
    openModal: openModal,
    closeModal: closeModal,
    confirmDialog: confirmDialog,
    readJSONScript: readJSONScript,
  };
})();
