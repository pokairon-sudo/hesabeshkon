/**
 * Liquid Glassmorphism UI Interactions
 * حساب‌شکن - Interactive Components
 */

// ===========================
// Toast Notifications
// ===========================
class ToastManager {
  constructor() {
    this.container = null;
    this.init();
  }

  init() {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    this.container = container;
  }

  show(message, type = 'success', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${this.getIcon(type)}</span>
      <span class="toast-message">${message}</span>
    `;

    this.container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'slideOut 0.3s ease forwards';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  getIcon(type) {
    const icons = {
      success: '✓',
      error: '✕',
      warning: '⚠',
      info: 'ℹ'
    };
    return icons[type] || icons.info;
  }

  success(message) { this.show(message, 'success'); }
  error(message) { this.show(message, 'error'); }
  warning(message) { this.show(message, 'warning'); }
  info(message) { this.show(message, 'info'); }
}

// Global toast instance
const toast = new ToastManager();

// ===========================
// Modal System
// ===========================
class ModalManager {
  constructor() {
    this.overlay = null;
    this.init();
  }

  init() {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal">
        <div class="modal-header">
          <h2 class="modal-title"></h2>
          <button class="modal-close">×</button>
        </div>
        <div class="modal-body"></div>
        <div class="modal-footer"></div>
      </div>
    `;
    document.body.appendChild(overlay);
    this.overlay = overlay;

    // Close button click
    overlay.querySelector('.modal-close').addEventListener('click', () => this.close());

    // Overlay click to close
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this.close();
    });

    // ESC key to close
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.close();
    });
  }

  open(title, content, actions = []) {
    this.overlay.querySelector('.modal-title').textContent = title;
    this.overlay.querySelector('.modal-body').innerHTML = content;

    const footer = this.overlay.querySelector('.modal-footer');
    footer.innerHTML = '';
    actions.forEach(action => {
      const btn = document.createElement('button');
      btn.className = `glass-btn glass-btn-${action.type || 'outline'}`;
      btn.textContent = action.label;
      if (action.onClick) btn.addEventListener('click', action.onClick);
      footer.appendChild(btn);
    });

    this.overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  close() {
    this.overlay.classList.remove('active');
    document.body.style.overflow = '';
  }
}

const modal = new ModalManager();

// ===========================
// Mobile Menu Toggle
// ===========================
function initMobileMenu() {
  const toggle = document.querySelector('.mobile-menu-toggle');
  const nav = document.querySelector('.navbar-nav');

  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      nav.classList.toggle('active');
      toggle.textContent = nav.classList.contains('active') ? '✕' : '☰';
    });
  }
}

// ===========================
// Invoice Cart Manager
// ===========================
class InvoiceCart {
  constructor() {
    this.items = [];
    this.init();
  }

  init() {
    // Load from session if exists
    const saved = sessionStorage.getItem('invoice_cart');
    if (saved) {
      try {
        this.items = JSON.parse(saved);
        this.render();
      } catch (e) {
        console.error('Failed to load cart:', e);
      }
    }

    // Search input handler
    const searchInput = document.querySelector('.search-bar input');
    if (searchInput) {
      searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          this.searchAndAdd(searchInput.value);
          searchInput.value = '';
        }
      });
    }

    // Voice input
    const voiceBtn = document.querySelector('.voice-input-btn');
    if (voiceBtn && 'webkitSpeechRecognition' in window) {
      this.initVoiceInput();
    }
  }

  initVoiceInput() {
    const recognition = new webkitSpeechRecognition();
    recognition.lang = 'fa-IR';
    recognition.continuous = false;

    const voiceBtn = document.querySelector('.voice-input-btn');
    if (voiceBtn) {
      voiceBtn.addEventListener('click', () => {
        recognition.start();
        voiceBtn.classList.add('pulse');
      });

      recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        this.parseVoiceCommand(text);
        voiceBtn.classList.remove('pulse');
      };

      recognition.onerror = () => {
        toast.error('خطا در تشخیص صدا');
        voiceBtn.classList.remove('pulse');
      };

      recognition.onend = () => {
        voiceBtn.classList.remove('pulse');
      };
    }
  }

  parseVoiceCommand(text) {
    // Parse Persian voice commands like "سه تا کاپوچینو"
    const patterns = [
      { regex: /(\d+)\s*(تایی|عدد|عدد تا)?\s*(.+)/, multi: 1 },
      { regex: /(.+)/, multi: 1 }
    ];

    for (const pattern of patterns) {
      const match = text.match(pattern.regex);
      if (match) {
        const qty = match[1] ? this.persianToNumber(match[1]) : pattern.multi;
        const productName = match[3] || match[1];
        this.searchAndAdd(productName, qty);
        break;
      }
    }
  }

  persianToNumber(text) {
    const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
    const englishDigits = '0123456789';
    let result = text;
    for (let i = 0; i < 10; i++) {
      result = result.replace(new RegExp(persianDigits[i], 'g'), englishDigits[i]);
    }
    return parseInt(result) || 1;
  }

  searchAndAdd(query, quantity = 1) {
    // Search products API
    fetch(`/api/products/search/?q=${encodeURIComponent(query)}`)
      .then(res => res.json())
      .then(data => {
        if (data.products && data.products.length > 0) {
          this.addItem(data.products[0], quantity);
          toast.success(`کالا اضافه شد: ${data.products[0].name}`);
        } else {
          toast.warning('کالا یافت نشد');
        }
      })
      .catch(() => {
        toast.error('خطا در جستجو');
      });
  }

  addItem(product, quantity = 1) {
    const existing = this.items.find(item => item.id === product.id);
    if (existing) {
      existing.quantity += quantity;
    } else {
      this.items.push({
        id: product.id,
        name: product.name,
        price: product.price,
        quantity: quantity
      });
    }
    this.save();
    this.render();
  }

  removeItem(productId) {
    this.items = this.items.filter(item => item.id !== productId);
    this.save();
    this.render();
  }

  updateQuantity(productId, quantity) {
    if (quantity <= 0) {
      this.removeItem(productId);
      return;
    }
    const item = this.items.find(item => item.id === productId);
    if (item) {
      item.quantity = quantity;
      this.save();
      this.render();
    }
  }

  getTotal() {
    return this.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  }

  save() {
    sessionStorage.setItem('invoice_cart', JSON.stringify(this.items));
  }

  clear() {
    this.items = [];
    sessionStorage.removeItem('invoice_cart');
    this.render();
  }

  render() {
    const cartContainer = document.querySelector('.invoice-cart-items');
    const summaryContainer = document.querySelector('.invoice-summary');

    if (!cartContainer) return;

    if (this.items.length === 0) {
      cartContainer.innerHTML = `
        <div class="empty-cart">
          <div class="empty-cart-icon">🛒</div>
          <p>سبد خرید خالی است</p>
          <p class="empty-hint">کالاها را جستجو و اضافه کنید</p>
        </div>
      `;
      return;
    }

    cartContainer.innerHTML = this.items.map(item => `
      <div class="invoice-item" data-id="${item.id}">
        <div class="invoice-item-info">
          <div class="invoice-item-name">${item.name}</div>
          <div class="invoice-item-price">${this.formatPrice(item.price)} تومان</div>
        </div>
        <div class="invoice-item-qty">
          <button class="qty-btn" onclick="invoiceCart.updateQuantity(${item.id}, ${item.quantity - 1})">-</button>
          <input type="number" class="qty-input" value="${item.quantity}" readonly>
          <button class="qty-btn" onclick="invoiceCart.updateQuantity(${item.id}, ${item.quantity + 1})">+</button>
        </div>
        <button class="invoice-remove" onclick="invoiceCart.removeItem(${item.id})">✕</button>
      </div>
    `).join('');

    // Update summary
    if (summaryContainer) {
      const subtotal = this.getTotal();
      const discount = 0; // Could be calculated
      const total = subtotal - discount;

      summaryContainer.innerHTML = `
        <h3 class="modal-title mb-3">خلاصه فاکتور</h3>
        <div class="summary-row">
          <span class="summary-label">جمع کل</span>
          <span class="summary-value">${this.formatPrice(subtotal)}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">تخفیف</span>
          <span class="summary-value">${this.formatPrice(discount)}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">مبلغ قابل پرداخت</span>
          <span class="summary-value summary-total text-gradient">${this.formatPrice(total)} تومان</span>
        </div>
        <div class="invoice-actions">
          <button class="glass-btn glass-btn-outline" onclick="invoiceCart.saveDraft()">
            <span>💾 ذخیره پیش‌نویس</span>
          </button>
          <button class="glass-btn glass-btn-primary" onclick="invoiceCart.finalize()">
            <span>✓ نهایی‌سازی (F7)</span>
          </button>
          <button class="glass-btn glass-btn-success" onclick="invoiceCart.finalizeAndPrint()">
            <span>🖨 نهایی و چاپ (F9)</span>
          </button>
        </div>
      `;
    }
  }

  formatPrice(price) {
    return price.toLocaleString('fa-IR');
  }

  saveDraft() {
    // Save to API
    fetch('/api/invoice/draft/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: this.items })
    })
    .then(res => res.json())
    .then(data => {
      toast.success('پیش‌نویس ذخیره شد');
    })
    .catch(() => {
      toast.error('خطا در ذخیره پیش‌نویس');
    });
  }

  finalize() {
    if (this.items.length === 0) {
      toast.error('سبد خرید خالی است');
      return;
    }

    fetch('/api/invoice/finalize/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: this.items })
    })
    .then(res => res.json())
    .then(data => {
      toast.success('فاکتور نهایی شد');
      this.clear();
      setTimeout(() => window.location.href = '/faktor/sell/', 1000);
    })
    .catch(() => {
      toast.error('خطا در نهایی‌سازی');
    });
  }

  finalizeAndPrint() {
    this.finalize();
    setTimeout(() => window.print(), 500);
  }
}

// Global invoice cart instance
let invoiceCart = null;
document.addEventListener('DOMContentLoaded', () => {
  if (document.querySelector('.invoice-cart')) {
    invoiceCart = new InvoiceCart();
  }
});

// ===========================
// Keyboard Shortcuts
// ===========================
function initKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // F6 - Save draft
    if (e.key === 'F6' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      if (invoiceCart) invoiceCart.saveDraft();
    }

    // F7 - Finalize
    if (e.key === 'F7' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      if (invoiceCart) invoiceCart.finalize();
    }

    // F8 - New product
    if (e.key === 'F8' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      window.location.href = '/product/create/';
    }

    // F9 - Finalize and print
    if (e.key === 'F9' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      if (invoiceCart) invoiceCart.finalizeAndPrint();
    }
  });
}

// ===========================
// Product Card Animations
// ===========================
function initProductCards() {
  const cards = document.querySelectorAll('.product-card');

  cards.forEach((card, index) => {
    card.style.animationDelay = `${index * 0.1}s`;
    card.classList.add('fade-in');
  });
}

// ===========================
// Animated Count Up
// ===========================
function animateValue(element, start, end, duration) {
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);

    // Ease out quart
    const easeProgress = 1 - Math.pow(1 - progress, 4);

    const current = Math.floor(easeProgress * (end - start) + start);
    element.textContent = current.toLocaleString('fa-IR');

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

function initStatAnimations() {
  const statValues = document.querySelectorAll('.stat-value');

  statValues.forEach(stat => {
    const text = stat.textContent.replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/,/g, '');
    const value = parseInt(text) || 0;
    const originalText = stat.dataset.original || stat.textContent;

    // Animate on scroll/visibility
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateValue(stat, 0, value, 1500);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });

    observer.observe(stat);
  });
}

// ===========================
// Search Autocomplete
// ===========================
class SearchAutocomplete {
  constructor(inputSelector, suggestionsSelector) {
    this.input = document.querySelector(inputSelector);
    this.suggestionsContainer = document.querySelector(suggestionsSelector);
    this.selectedProducts = [];
    this.init();
  }

  init() {
    if (!this.input) return;

    let debounce;

    this.input.addEventListener('input', (e) => {
      clearTimeout(debounce);
      const query = e.target.value.trim();

      if (query.length < 2) {
        this.hideSuggestions();
        return;
      }

      debounce = setTimeout(() => {
        this.search(query);
      }, 300);
    });

    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        this.selectFirst();
      }
    });

    document.addEventListener('click', (e) => {
      if (!this.input.contains(e.target) && !this.suggestionsContainer?.contains(e.target)) {
        this.hideSuggestions();
      }
    });
  }

  async search(query) {
    try {
      const res = await fetch(`/api/products/search/?q=${encodeURIComponent(query)}`);
      const data = await res.json();

      if (data.products && data.products.length > 0) {
        this.showSuggestions(data.products);
      } else {
        this.hideSuggestions();
      }
    } catch (error) {
      console.error('Search error:', error);
    }
  }

  showSuggestions(products) {
    this.suggestionsContainer.innerHTML = products.map((product, index) => `
      <div class="autocomplete-item" data-index="${index}">
        <span class="product-name">${product.name}</span>
        <span class="product-price">${product.price.toLocaleString('fa-IR')} تومان</span>
        <span class="product-stock">${product.stock} موجود</span>
      </div>
    `).join('');

    this.suggestionsContainer.style.display = 'block';

    this.suggestionsContainer.querySelectorAll('.autocomplete-item').forEach(item => {
      item.addEventListener('click', () => {
        const index = parseInt(item.dataset.index);
        this.selectProduct(products[index]);
      });
    });
  }

  hideSuggestions() {
    if (this.suggestionsContainer) {
      this.suggestionsContainer.style.display = 'none';
      this.suggestionsContainer.innerHTML = '';
    }
  }

  selectFirst() {
    const first = this.suggestionsContainer?.querySelector('.autocomplete-item');
    if (first) {
      const index = parseInt(first.dataset.index);
      this.selectProduct(products[index]);
    }
  }

  selectProduct(product) {
    this.input.value = product.name;
    this.hideSuggestions();

    // Add to cart
    if (invoiceCart) {
      invoiceCart.addItem(product, 1);
    }

    toast.success(`افزوده شد: ${product.name}`);
  }
}

// ===========================
// Initialize All
// ===========================
document.addEventListener('DOMContentLoaded', () => {
  initMobileMenu();
  initKeyboardShortcuts();
  initProductCards();
  initStatAnimations();

  // Initialize search autocomplete
  if (document.querySelector('.search-bar input')) {
    new SearchAutocomplete('.search-bar input', '.autocomplete-suggestions');
  }

  // Add missing CSS animation
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideOut {
      from { opacity: 1; transform: translateX(0); }
      to { opacity: 0; transform: translateX(-100%); }
    }
    .empty-cart {
      text-align: center;
      padding: 3rem 1rem;
      color: var(--text-muted);
    }
    .empty-cart-icon {
      font-size: 4rem;
      margin-bottom: 1rem;
      opacity: 0.5;
    }
    .autocomplete-suggestions {
      display: none;
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      margin-top: 0.5rem;
      background: var(--glass-bg);
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border);
      border-radius: var(--radius-md);
      overflow: hidden;
      z-index: 100;
    }
    .autocomplete-item {
      padding: 0.75rem 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      transition: background 0.15s;
    }
    .autocomplete-item:hover {
      background: var(--glass-bg-hover);
    }
  `;
  document.head.appendChild(style);
});

// ===========================
// Dark/Light Mode (Future Enhancement)
// ===========================
function toggleTheme() {
  const isDark = document.body.classList.toggle('light-mode');
  localStorage.setItem('theme', isDark ? 'light' : 'dark');
}

// ===========================
// Export for use in templates
// ===========================
window.Toast = toast;
window.Modal = modal;
window.InvoiceCart = InvoiceCart;
window.animateValue = animateValue;
