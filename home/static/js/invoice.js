/* صفحه‌ی فاکتور فروش/خرید — سبد خرید، بارکد، صدا، F6..F9 */
(function () {
  "use strict";

  const root = document.getElementById("invoice-app");
  if (!root) return;

  const HS = window.HS;
  const mode = root.dataset.mode || "sell";
  const isBuy = mode === "buy";
  const state = {
    cart: [],
    invoiceId: root.dataset.invoiceId || "",
    submitUrl: root.dataset.submitUrl,
    productEditTemplate: root.dataset.productEditTemplate || "/product/__ID__/edit/",
    busy: false,
  };

  const els = {
    search: document.getElementById("product-search"),
    results: document.getElementById("search-results"),
    cartBody: document.getElementById("cart-body"),
    cartEmpty: document.getElementById("cart-empty"),
    cartTotal: document.getElementById("cart-total"),
    lineCount: document.getElementById("cart-line-count"),
    customer: document.getElementById("customer-input"),
    supplier: document.getElementById("supplier-input"),
    description: document.getElementById("description-input"),
    invoiceNumber: document.getElementById("invoice-number"),
    invoiceStatus: document.getElementById("invoice-status"),
    voiceBtn: document.getElementById("btn-voice"),
    voiceHint: document.getElementById("voice-hint"),
    modal: document.getElementById("product-modal"),
    productForm: document.getElementById("product-form"),
    productFormErrors: document.getElementById("product-form-errors"),
    productModalTitle: document.getElementById("product-modal-title"),
    productSubmit: document.getElementById("product-submit"),
    saveButtons: Array.from(document.querySelectorAll("[data-save-action]")),
  };

  const seeded = HS.readJSONScript("cart-seed", []);
  if (Array.isArray(seeded)) {
    state.cart = seeded.map(function (row) {
      return {
        product_id: Number(row.product_id),
        name: row.name || "کالا",
        serial_number: row.serial_number || "",
        unit: row.unit || "",
        count: Number(row.count || 0),
        quantity: Number(row.quantity || 1),
        unit_price: Number(row.unit_price || 0),
      };
    });
  }

  // ------------------------------------------------------------------
  // رندر سبد
  // ------------------------------------------------------------------
  function lineTotal(line) {
    return Number(line.unit_price || 0) * Number(line.quantity || 0);
  }

  function cartTotal() {
    return state.cart.reduce(function (sum, line) {
      return sum + lineTotal(line);
    }, 0);
  }

  function renderCart() {
    if (!els.cartBody) return;
    els.cartBody.innerHTML = "";

    state.cart.forEach(function (line, index) {
      const overStock = !isBuy && line.quantity > line.count;
      const tr = document.createElement("tr");
      if (overStock) tr.style.background = "#ffe3e1";
      tr.dataset.index = String(index);
      tr.dataset.productId = String(line.product_id);

      const nameCell = document.createElement("td");
      nameCell.innerHTML =
        "<strong>" +
        HS.escapeHtml(line.name) +
        "</strong>" +
        '<div class="text-xs muted mono">' +
        HS.escapeHtml(line.serial_number || "—") +
        (line.unit ? " · " + HS.escapeHtml(line.unit) : "") +
        "</div>" +
        (!isBuy
          ? '<div class="text-xs ' +
            (overStock ? "badge badge--danger" : "muted") +
            '">موجودی: ' +
            HS.formatNumber(line.count) +
            (overStock ? " — بیشتر از موجودی!" : "") +
            "</div>"
          : "");

      const qtyCell = document.createElement("td");
      qtyCell.innerHTML =
        '<div class="cart-qty">' +
        '<button type="button" class="icon-btn" data-step="-1" aria-label="کاهش">−</button>' +
        '<input type="number" inputmode="numeric" min="1" step="1" value="' +
        line.quantity +
        '" data-qty aria-label="تعداد">' +
        '<button type="button" class="icon-btn" data-step="1" aria-label="افزایش">+</button>' +
        "</div>";

      const priceCell = document.createElement("td");
      priceCell.className = "num";
      if (isBuy) {
        priceCell.innerHTML =
          '<input type="number" inputmode="decimal" min="0" step="0.01" dir="ltr" value="' +
          Number(line.unit_price || 0) +
          '" data-price aria-label="قیمت خرید" style="width:110px">';
      } else {
        priceCell.textContent = HS.formatMoney(line.unit_price);
      }

      const totalCell = document.createElement("td");
      totalCell.className = "num";
      totalCell.dataset.lineTotal = "1";
      totalCell.textContent = HS.formatMoney(lineTotal(line));

      const actionCell = document.createElement("td");
      actionCell.innerHTML =
        '<div class="row" style="gap:4px;flex-wrap:nowrap">' +
        '<button type="button" class="icon-btn" data-edit aria-label="ویرایش کالا">✎</button>' +
        '<button type="button" class="icon-btn icon-btn--danger" data-remove aria-label="حذف">✕</button>' +
        "</div>";

      tr.append(nameCell, qtyCell, priceCell, totalCell, actionCell);
      els.cartBody.appendChild(tr);
    });

    if (els.cartEmpty) els.cartEmpty.classList.toggle("hidden", state.cart.length > 0);
    document.getElementById("cart-table")?.classList.toggle("hidden", state.cart.length === 0);
    if (els.cartTotal) els.cartTotal.textContent = HS.formatMoney(cartTotal());
    if (els.lineCount) els.lineCount.textContent = HS.formatNumber(state.cart.length);
    updateButtons();
  }

  function updateButtons() {
    const empty = state.cart.length === 0;
    els.saveButtons.forEach(function (button) {
      button.disabled = empty || state.busy;
    });
  }

  // ------------------------------------------------------------------
  // افزودن/کاهش
  // ------------------------------------------------------------------
  function addToCart(product, quantity) {
    const qty = Math.max(1, parseInt(quantity || 1, 10) || 1);
    const id = Number(product.id);
    const existing = state.cart.find(function (line) {
      return Number(line.product_id) === id;
    });
    const stock = Number(product.count == null ? 0 : product.count);

    if (!isBuy && existing && existing.quantity + qty > stock) {
      HS.toast("موجودی «" + product.name + "» کافی نیست (موجودی: " + HS.formatNumber(stock) + ").", "warning");
      return;
    }
    if (!isBuy && !existing && qty > stock) {
      HS.toast("موجودی «" + product.name + "» کافی نیست (موجودی: " + HS.formatNumber(stock) + ").", "warning");
      return;
    }

    if (existing) {
      existing.quantity += qty;
      existing.count = stock || existing.count;
      existing.name = product.name || existing.name;
      existing.serial_number = product.serial_number || existing.serial_number;
      existing.unit = product.unit_label || existing.unit;
    } else {
      state.cart.push({
        product_id: id,
        name: product.name,
        serial_number: product.serial_number || product.barcode || "",
        unit: product.unit_label || "",
        count: stock,
        quantity: qty,
        unit_price: isBuy
          ? Number(product.price_for_company || 0)
          : Number(product.final_price || product.price_for_customer || 0),
      });
    }
    renderCart();
    HS.toast("«" + product.name + "» اضافه شد.", "success");
  }

  els.cartBody?.addEventListener("click", function (event) {
    const row = event.target.closest("tr[data-index]");
    if (!row) return;
    const index = Number(row.dataset.index);
    const line = state.cart[index];
    if (!line) return;

    if (event.target.closest("[data-remove]")) {
      state.cart.splice(index, 1);
      renderCart();
      return;
    }
    if (event.target.closest("[data-edit]")) {
      loadProduct(line.product_id).then(function (product) {
        if (product) openProductModal({ id: line.product_id, product: product, addAfterSave: false });
      });
      return;
    }
    const stepButton = event.target.closest("[data-step]");
    if (stepButton) {
      const step = Number(stepButton.dataset.step);
      const next = line.quantity + step;
      if (next < 1) {
        state.cart.splice(index, 1);
      } else if (!isBuy && next > line.count) {
        HS.toast("بیشتر از موجودی نمی‌توان اضافه کرد (موجودی: " + HS.formatNumber(line.count) + ").", "warning");
        return;
      } else {
        line.quantity = next;
      }
      renderCart();
    }
  });

  els.cartBody?.addEventListener("input", function (event) {
    const row = event.target.closest("tr[data-index]");
    if (!row) return;
    const index = Number(row.dataset.index);
    const line = state.cart[index];
    if (!line) return;

    if (event.target.matches("[data-qty]")) {
      let value = parseInt(event.target.value, 10);
      if (!Number.isFinite(value) || value < 1) value = 1;
      if (!isBuy && value > line.count) {
        value = line.count;
        HS.toast("حداکثر موجودی " + HS.formatNumber(line.count) + " است.", "warning");
      }
      line.quantity = value;
      event.target.value = value;
      const totalCell = row.querySelector("[data-line-total]");
      if (totalCell) totalCell.textContent = HS.formatMoney(lineTotal(line));
      if (els.cartTotal) els.cartTotal.textContent = HS.formatMoney(cartTotal());
    }

    if (event.target.matches("[data-price]")) {
      const value = parseFloat(event.target.value);
      line.unit_price = Number.isFinite(value) && value >= 0 ? value : 0;
      const totalCell = row.querySelector("[data-line-total]");
      if (totalCell) totalCell.textContent = HS.formatMoney(lineTotal(line));
      if (els.cartTotal) els.cartTotal.textContent = HS.formatMoney(cartTotal());
    }
  });

  // ------------------------------------------------------------------
  // جستجو / بارکد
  // ------------------------------------------------------------------
  let searchTimer = null;
  let searchItems = [];
  let searchActive = -1;

  function hideResults() {
    if (!els.results) return;
    els.results.classList.add("hidden");
    els.results.innerHTML = "";
    searchActive = -1;
  }

  function renderResults(items) {
    searchItems = items || [];
    searchActive = items && items.length ? 0 : -1;
    if (!els.results) return;
    if (!items || !items.length) {
      els.results.innerHTML = '<div class="search-empty">کالایی پیدا نشد. با دکمه‌ی «کالای جدید» بسازید.</div>';
      els.results.classList.remove("hidden");
      return;
    }
    els.results.innerHTML = items
      .map(function (product, index) {
        return (
          '<button type="button" class="search-result' +
          (index === 0 ? " is-active" : "") +
          '" data-result-index="' +
          index +
          '">' +
          "<span><strong>" +
          HS.escapeHtml(product.name) +
          '</strong><br><span class="text-xs muted mono">' +
          HS.escapeHtml(product.serial_number) +
          (product.tag ? " · " + HS.escapeHtml(product.tag) : "") +
          " · موجودی: " +
          HS.formatNumber(product.count) +
          "</span></span>" +
          '<span class="mono text-sm">' +
          HS.formatMoney(isBuy && product.price_for_company != null ? product.price_for_company : product.final_price) +
          "</span></button>"
        );
      })
      .join("");
    els.results.classList.remove("hidden");
  }

  async function searchProducts(query) {
    if (!query || query.trim().length < 1) {
      hideResults();
      return;
    }
    try {
      const data = await HS.fetchJSON(root.dataset.searchUrl + "?q=" + encodeURIComponent(query.trim()));
      renderResults(data.results || []);
    } catch (error) {
      HS.toast(error.message, "error");
    }
  }

  els.search?.addEventListener("input", function () {
    clearTimeout(searchTimer);
    const value = this.value.trim();
    if (!value) {
      hideResults();
      return;
    }
    searchTimer = setTimeout(function () {
      searchProducts(value);
    }, 180);
  });

  els.search?.addEventListener("keydown", async function (event) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!searchItems.length) return;
      searchActive = Math.min(searchActive + 1, searchItems.length - 1);
      updateSearchActive();
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      if (!searchItems.length) return;
      searchActive = Math.max(searchActive - 1, 0);
      updateSearchActive();
      return;
    }
    if (event.key !== "Enter") return;
    event.preventDefault();
    const query = this.value.trim();
    if (!query) return;

    try {
      const data = await HS.fetchJSON(root.dataset.searchUrl + "?q=" + encodeURIComponent(query));
      const exact = (data.results || []).find(function (product) {
        return String(product.serial_number).toLowerCase() === query.toLowerCase();
      });
      if (exact) {
        addToCart(exact, 1);
        this.value = "";
        hideResults();
        return;
      }
      if (searchActive >= 0 && searchItems[searchActive]) {
        addToCart(searchItems[searchActive], 1);
        this.value = "";
        hideResults();
        return;
      }
      // کالای ناشناس: اگر شبیه بارکد است در فیلد بارکد، وگرنه در فیلد نام قرار بگیرد.
      const looksLikeBarcode = /^\d{6,}$/.test(query);
      openProductModal(looksLikeBarcode ? { barcode: query } : { name: query });
      this.value = "";
      hideResults();
    } catch (error) {
      HS.toast(error.message, "error");
    }
  });

  function updateSearchActive() {
    if (!els.results) return;
    els.results.querySelectorAll("[data-result-index]").forEach(function (node, index) {
      node.classList.toggle("is-active", index === searchActive);
    });
  }

  els.results?.addEventListener("click", function (event) {
    const button = event.target.closest("[data-result-index]");
    if (!button) return;
    const product = searchItems[Number(button.dataset.resultIndex)];
    if (product) {
      addToCart(product, 1);
      if (els.search) {
        els.search.value = "";
        els.search.focus();
      }
      hideResults();
    }
  });

  document.addEventListener("click", function (event) {
    if (!event.target.closest(".search-box")) hideResults();
  });

  // ------------------------------------------------------------------
  // ساخت/ویرایش سریع کالا
  // ------------------------------------------------------------------
  let editingProductId = null;
  let addAfterSave = false;

  function setProductErrors(errors) {
    if (!els.productFormErrors) return;
    if (!errors || !Object.keys(errors).length) {
      els.productFormErrors.innerHTML = "";
      return;
    }
    const labels = {
      name: "نام", serial_number: "بارکد", tag: "دسته", unit: "واحد",
      price_for_company: "قیمت خرید", price_for_customer: "قیمت فروش",
      count: "موجودی", offer_value: "تخفیف", offer_type: "نوع تخفیف",
      is_active: "فعال", __all__: "",
    };
    const list = [];
    Object.keys(errors).forEach(function (field) {
      (errors[field] || []).forEach(function (message) {
        list.push((labels[field] || field) + ": " + message);
      });
    });
    els.productFormErrors.innerHTML =
      '<div class="msg msg--error mb-2">' + HS.escapeHtml(list.join(" | ")) + "</div>";
  }

  function fillProductForm(product) {
    const form = els.productForm;
    if (!form) return;
    form.elements.name.value = product.name || "";
    form.elements.serial_number.value = product.serial_number || "";
    form.elements.tag.value = product.tag || "";
    form.elements.unit.value = product.unit || "piece";
    form.elements.price_for_company.value = product.price_for_company != null ? product.price_for_company : 0;
    form.elements.price_for_customer.value = product.price_for_customer != null ? product.price_for_customer : 0;
    form.elements.count.value = product.count != null ? product.count : 0;
    form.elements.offer_value.value = product.offer_value != null ? product.offer_value : 0;
    form.elements.offer_type.value = product.offer_type || "percent";
    form.elements.is_active.checked = product.is_active !== false;
  }

  function openProductModal(options) {
    const opts = options || {};
    editingProductId = opts.id || null;
    addAfterSave = opts.addAfterSave !== false;
    setProductErrors({});
    if (els.productForm) {
      els.productForm.reset();
      els.productForm.elements.unit.value = "piece";
      els.productForm.elements.offer_type.value = "percent";
      els.productForm.elements.is_active.checked = true;
      els.productForm.action = root.dataset.productCreateUrl;
    }
    if (els.productModalTitle) {
      els.productModalTitle.textContent = editingProductId ? "ویرایش کالا" : "کالای جدید";
    }
    if (els.productSubmit) els.productSubmit.textContent = editingProductId ? "ذخیره تغییرات" : "ساخت و افزودن";

    if (editingProductId && els.productForm) {
      els.productForm.action = state.productEditTemplate.replace("/0/", "/" + editingProductId + "/");
    }
    if (editingProductId && opts.product) {
      fillProductForm(opts.product);
    } else if (editingProductId) {
      loadProduct(editingProductId).then(function (product) {
        if (product) fillProductForm(product);
      });
    } else if (opts.barcode && els.productForm) {
      els.productForm.elements.serial_number.value = opts.barcode;
    }
    if (opts.name && els.productForm) els.productForm.elements.name.value = opts.name;
    HS.openModal("product-modal");
  }

  async function loadProduct(id) {
    try {
      const data = await HS.fetchJSON("/product/" + id + "/json/");
      return data && data.product ? data.product : null;
    } catch (error) {
      HS.toast(error.message, "error");
      return null;
    }
  }

  document.querySelectorAll("[data-open-product]").forEach(function (button) {
    button.addEventListener("click", function () {
      openProductModal({});
    });
  });

  document.getElementById("btn-generate-barcode")?.addEventListener("click", async function () {
    try {
      const data = await HS.fetchJSON(root.dataset.newBarcodeUrl);
      els.productForm.elements.serial_number.value = data.barcode;
      HS.toast("بارکد ساخته شد.", "success");
    } catch (error) {
      HS.toast(error.message, "error");
    }
  });

  els.productForm?.addEventListener("submit", async function (event) {
    event.preventDefault();
    const form = els.productForm;
    const data = new FormData(form);
    data.set("respond_json", "1");
    try {
      if (els.productSubmit) els.productSubmit.disabled = true;
      const response = await HS.fetchJSON(form.action, {
        method: "POST",
        body: data,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const product = response.product;
      HS.closeModal("product-modal");
      HS.toast("کالا ذخیره شد.", "success");
      if (product) {
        const existing = state.cart.find(function (line) {
          return Number(line.product_id) === Number(product.id);
        });
        if (existing) {
          existing.name = product.name;
          existing.serial_number = product.serial_number;
          existing.unit = product.unit_label;
          existing.count = product.count;
          existing.unit_price = isBuy
            ? Number(product.price_for_company || existing.unit_price)
            : Number(product.final_price || existing.unit_price);
          renderCart();
        } else if (addAfterSave) {
          addToCart(product, 1);
        }
        if (els.search) els.search.focus();
      }
    } catch (error) {
      const errors = (error.data && error.data.errors) || {};
      setProductErrors(errors);
      HS.toast(error.message, "error");
    } finally {
      if (els.productSubmit) els.productSubmit.disabled = false;
    }
  });

  async function openProductForEditFromCart() {
    const query = els.search?.value.trim();
    if (query) {
      try {
        const data = await HS.fetchJSON(root.dataset.searchUrl + "?q=" + encodeURIComponent(query));
        const results = data.results || [];
        const exact = results.find(function (p) {
          return String(p.serial_number).toLowerCase() === query.toLowerCase();
        });
        if (exact) {
          openProductModal({ id: exact.id, product: exact, addAfterSave: false });
          return;
        }
        if (results.length) {
          openProductModal({ id: results[0].id, product: results[0], addAfterSave: false });
          return;
        }
      } catch (error) {
        /* ادامه: ساخت جدید */
      }
      const looksLikeBarcode = /^\d{6,}$/.test(query);
      openProductModal(looksLikeBarcode ? { barcode: query } : { name: query });
      return;
    }
    if (state.cart.length) {
      const line = state.cart[state.cart.length - 1];
      const product = await loadProduct(line.product_id);
      if (product) {
        openProductModal({ id: line.product_id, product: product, addAfterSave: false });
        return;
      }
    }
    openProductModal({});
  }

  // ------------------------------------------------------------------
  // صدا
  // ------------------------------------------------------------------
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let listening = false;

  function parseVoice(text) {
    const normalized = String(text || "")
      .translatePersianDigits()
      .replace(/[،,.]/g, " ");
    const words = {
      یک: 1, دو: 2, سه: 3, چهار: 4, پنج: 5, شش: 6, هفت: 7, هشت: 8, نه: 9, ده: 10,
      یازده: 11, دوازده: 12, پانزده: 15, بیست: 20, سی: 30, چهل: 40, پنجاه: 50, صد: 100,
    };
    let quantity = 1;
    let matchedWord = "";
    let rest = normalized;
    const numeric = normalized.match(/(\d+)\s*(?:عدد|تا|کیلو|بسته|عددى|تایی)?/);
    if (numeric) {
      quantity = parseInt(numeric[1], 10) || 1;
      rest = normalized.replace(numeric[0], " ");
    } else {
      Object.keys(words).some(function (word) {
        const regex = new RegExp("(?:^|\\s)" + word + "(?:\\s|$)");
        if (regex.test(normalized)) {
          quantity = words[word];
          matchedWord = word;
          rest = normalized.replace(regex, " ");
          return true;
        }
        return false;
      });
    }
    rest = rest
      .replace(/(?:اضافه|بزن|کن|به|فاکتور|جمع|تعداد|عدد|تا|کیلو|بسته|از|یک|لطفا|لطفاً)/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    return { quantity: quantity, name: rest || normalized.trim(), matchedWord: matchedWord };
  }

  // افزایش سازگاری: تابع تبدیل ارقام فارسی
  String.prototype.translatePersianDigits = function () {
    return this.replace(/[۰-۹]/g, function (d) {
      return String("۰۱۲۳۴۵۶۷۸۹".indexOf(d));
    }).replace(/[٠-٩]/g, function (d) {
      return String("٠١٢٣٤٥٦٧٨٩".indexOf(d));
    });
  };

  async function handleVoiceTranscript(transcript) {
    const parsed = parseVoice(transcript);
    if (!parsed.name) {
      HS.toast("نام کالا تشخیص داده نشد؛ دوباره بگویید.", "warning");
      return;
    }
    try {
      const data = await HS.fetchJSON(root.dataset.searchUrl + "?q=" + encodeURIComponent(parsed.name));
      const results = data.results || [];
      if (results.length) {
        addToCart(results[0], parsed.quantity);
        HS.toast("«" + results[0].name + "» × " + parsed.quantity + " اضافه شد.", "success");
      } else {
        HS.toast("کالایی با نام «" + parsed.name + "» پیدا نشد؛ فرم ساخت باز شد.", "warning");
        openProductModal({ name: parsed.name });
      }
    } catch (error) {
      HS.toast(error.message, "error");
    }
  }

  if (!SpeechRecognition) {
    if (els.voiceBtn) {
      els.voiceBtn.disabled = true;
      els.voiceBtn.title = "مرورگر شما از تشخیص صدا پشتیبانی نمی‌کند.";
    }
    if (els.voiceHint) els.voiceHint.textContent = "مرورگر از میکروفن پشتیبانی نمی‌کند (Chrome/Edge لازم است).";
  } else {
    recognition = new SpeechRecognition();
    recognition.lang = "fa-IR";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    recognition.addEventListener("result", function (event) {
      const transcript = Array.from(event.results)
        .map(function (result) {
          return result[0].transcript;
        })
        .join(" ");
      if (els.voiceHint) els.voiceHint.textContent = "شنیده شد: " + transcript;
      handleVoiceTranscript(transcript);
    });
    recognition.addEventListener("error", function (event) {
      const messages = {
        "not-allowed": "اجازه‌ی میکروفن داده نشد.",
        "no-speech": "صدایی شنیده نشد.",
        network: "خطای شبکه در تشخیص صدا.",
      };
      HS.toast(messages[event.error] || "خطا در تشخیص صدا.", "error");
    });
    recognition.addEventListener("end", function () {
      listening = false;
      els.voiceBtn?.classList.remove("is-listening");
    });

    els.voiceBtn?.addEventListener("click", function () {
      if (listening) {
        recognition.stop();
        return;
      }
      try {
        recognition.start();
        listening = true;
        els.voiceBtn.classList.add("is-listening");
        if (els.voiceHint) els.voiceHint.textContent = "گوش می‌دهم… مثلاً «سه تا کاپوچینو»";
      } catch (error) {
        HS.toast("شروع ضبط ممکن نشد.", "error");
      }
    });
  }

  // ------------------------------------------------------------------
  // ذخیره / نهایی‌سازی / چاپ
  // ------------------------------------------------------------------
  function cartPayload() {
    return state.cart.map(function (line) {
      const row = { product_id: line.product_id, quantity: line.quantity };
      if (isBuy) row.unit_price = line.unit_price;
      return row;
    });
  }

  async function saveInvoice(action) {
    if (state.busy) return;
    if (!state.cart.length) {
      HS.toast("حداقل یک کالا اضافه کنید.", "warning");
      els.search?.focus();
      return;
    }
    state.busy = true;
    updateButtons();
    const payload = new URLSearchParams();
    payload.set("cart_json", JSON.stringify(cartPayload()));
    payload.set("description", els.description?.value || "");
    if (isBuy) {
      payload.set("supplier", els.supplier?.value || "");
    } else {
      payload.set("customer", els.customer?.value || "");
    }
    payload.set("action", action);
    payload.set("respond_json", "1");

    try {
      const data = await HS.fetchJSON(state.submitUrl, {
        method: "POST",
        body: payload,
        headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
      });

      if (data.edit_url) state.submitUrl = data.edit_url;
      if (data.id) state.invoiceId = data.id;
      if (els.invoiceNumber) els.invoiceNumber.textContent = data.number || "";
      if (els.invoiceStatus) {
        els.invoiceStatus.textContent = data.status_label || "";
        els.invoiceStatus.className =
          "badge " + (data.status === "draft" ? "badge--draft" : "badge--ok");
      }

      if (action === "draft") {
        if (data.edit_url && window.history.replaceState) {
          window.history.replaceState({}, "", data.edit_url);
        }
        HS.toast(data.message || "پیش‌نویس ذخیره شد.", "success");
        state.busy = false;
        updateButtons();
        return;
      }

      if (data.sync_error) {
        window.sessionStorage.setItem("sync-error", data.sync_error);
      }
      if (action === "print") {
        window.location.href = data.print_url;
      } else {
        window.location.href = data.preview_url;
      }
    } catch (error) {
      if (error.data && error.data.edit_url) {
        state.submitUrl = error.data.edit_url;
        state.invoiceId = error.data.id;
        if (window.history.replaceState) {
          window.history.replaceState({}, "", error.data.edit_url);
        }
        if (els.invoiceNumber) els.invoiceNumber.textContent = error.data.number || "";
        if (els.invoiceStatus) {
          els.invoiceStatus.textContent = error.data.status_label || "";
          els.invoiceStatus.className =
            "badge " + (error.data.status === "draft" ? "badge--draft" : "badge--ok");
        }
      }
      const errors = (error.data && error.data.errors) || null;
      if (errors && errors.length) {
        errors.forEach(function (message) {
          HS.toast(message, "error");
        });
      } else {
        HS.toast(error.message || "ثبت فاکتور ناموفق بود.", "error");
      }
      state.busy = false;
      updateButtons();
    }
  }

  els.saveButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      saveInvoice(button.dataset.saveAction);
    });
  });

  document.getElementById("btn-product")?.addEventListener("click", openProductForEditFromCart);

  document.addEventListener("keydown", function (event) {
    if (event.key === "F6") {
      event.preventDefault();
      saveInvoice("draft");
    } else if (event.key === "F7") {
      event.preventDefault();
      saveInvoice("finalize");
    } else if (event.key === "F8") {
      event.preventDefault();
      openProductForEditFromCart();
    } else if (event.key === "F9") {
      event.preventDefault();
      saveInvoice("print");
    }
  });

  // ------------------------------------------------------------------
  // شروع
  // ------------------------------------------------------------------
  renderCart();
  setTimeout(function () {
    els.search?.focus();
  }, 80);
})();
