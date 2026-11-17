# Neo-Brutalism UI/UX Transformation Plan - حساب‌شکن

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform حساب‌شکن from liquid glassmorphism to soft neo-brutalism design

**Architecture:** Complete CSS overhaul replacing glassmorphism (blur, transparency, gradients) with neo-brutalism (thick black borders, hard shadows, vibrant solid colors, geometric shapes). HTML structure remains unchanged; only styles and visual elements are modified.

**Tech Stack:** Django templates, Vanilla CSS, Vazirmatn font (preserved), RTL support

**Spec:** Design approved by user - Soft Neo-Brutalism style

## Global Constraints

- Preserve all Django template logic and functionality
- Maintain RTL (right-to-left) layout support for Persian language
- Keep all existing CSS utility classes for compatibility
- Use Vazirmatn font family (unchanged)
- All CSS variables must be redefined with neo-brutalist values
- Responsive design must be preserved
- Print styles must adapt to new design

## Review Focus

1. **Color contrast accessibility** - Ensure text remains readable on solid color backgrounds (no blur aid)
2. **RTL spacing consistency** - Hard shadows must offset correctly in RTL direction
3. **Mobile menu visibility** - Navigation must remain clear without glass backdrop
4. **Form input states** - Focus/hover states must be visible without glass effects
5. **Print output quality** - Invoice prints must look clean without dark backgrounds

---

## Task 1: Core CSS System - Neo-Brutalism Base Styles

**Files:**
- Modify: `/marimo/hesabeshkon/home/static/css/glassmorphism.css` (complete rewrite)

**Interfaces:**
- Consumes: None (base system)
- Produces: All CSS classes used by templates (`glass-*` prefixed classes, utility classes, component styles)

### Step 1: Rewrite CSS Variables & Theme

Replace current glassmorphism CSS variables with neo-brutalist palette:

```css
/* New neo-brutalist color palette */
:root {
  /* Background - light cream instead of dark */
  --bg-dark: #FFF9F0;
  --bg-gradient: linear-gradient(135deg, #FFF9F0 0%, #FFF5E6 100%);

  /* Solid vibrant colors (no transparency) */
  --primary: #FF6B6B;
  --primary-hover: #EE5A5A;
  --secondary: #4ECDC4;
  --secondary-hover: #3DBDB5;
  --accent: #FFE66D;
  --accent-hover: #EED95C;
  --info: #A78BFA;
  --success: #10B981;
  --success-hover: #059669;
  --warning: #F59E0B;
  --warning-hover: #D97706;
  --danger: #EF4444;
  --danger-hover: #DC2626;

  /* Text colors */
  --text-primary: #1A1A1A;
  --text-secondary: #374151;
  --text-muted: #6B7280;

  /* Borders & Shadows (hard, no blur) */
  --border-color: #000000;
  --border-width: 2px;
  --shadow-hard: 4px 4px 0px #000000;
  --shadow-hard-sm: 2px 2px 0px #000000;
  --shadow-hard-lg: 6px 6px 0px #000000;

  /* Radius (kept friendly but defined) */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* Transitions (snappy) */
  --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
```

- [ ] **Step 1: Update CSS variables in :root**
  - Replace all color gradients with solid colors
  - Change background from dark to light cream
  - Add hard shadow definitions (no blur)
  - Update border definitions (solid black)

**Expected:** CSS variables file is ready with neo-brutalist values

### Step 2: Rewrite Base & Background Styles

Replace animated glass background with static neo-brutalist background:

```css
/* Base styles */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Vazirmatn', 'Segoe UI', Tahoma, sans-serif;
  background: var(--bg-dark);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 100vh;
  overflow-x: hidden;
}

/* Remove animated background and orbs completely */
/* Replace with simple striped/grid pattern if desired */
.background-animate {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  background-image: 
    radial-gradient(circle at 20% 30%, rgba(255, 107, 107, 0.05) 0%, transparent 8%),
    radial-gradient(circle at 80% 70%, rgba(78, 205, 196, 0.05) 0%, transparent 8%);
}

/* Remove orb-1, orb-2, orb-3 animations */
.orb { display: none; }
```

- [ ] **Step 2: Update body and background styles**
  - Change background from dark gradient to light cream
  - Remove animated orb elements (or simplify)
  - Keep RTL support: `body[dir="rtl"] { text-align: right; }`

**Expected:** Page has light background, no floating animated orbs

### Step 3: Rewrite Glass Components to Neo-Brutalist Cards

Replace glassmorphism classes with neo-brutalist equivalents:

```css
/* Neo-brutalist card style (replaces .glass) */
.glass {
  background: #FFFFFF;
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-hard);
  transition: all var(--transition-normal);
}

.glass:hover {
  transform: translate(-2px, -2px);
  box-shadow: var(--shadow-hard-lg);
}

.glass-card {
  background: #FFFFFF;
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-hard);
  transition: all var(--transition-normal);
}

.glass-card:hover {
  transform: translate(-4px, -4px);
  box-shadow: var(--shadow-hard-lg);
}

/* Remove backdrop-filter: blur() - not supported in neo-brutalism */
```

- [ ] **Step 3: Rewrite .glass, .glass-card components**
  - Replace transparent background with solid white
  - Add thick black border (2px)
  - Add hard shadow (no blur)
  - Remove all backdrop-filter properties

**Expected:** Cards have solid white background, thick borders, hard shadows

### Step 4: Rewrite Buttons

Replace gradient glass buttons with solid neo-brutalist buttons:

```css
.glass-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: var(--primary);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-md);
  color: #FFFFFF;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  text-decoration: none;
}

.glass-btn:hover {
  background: var(--primary-hover);
  transform: translate(-2px, -2px);
  box-shadow: var(--shadow-hard-sm);
}

.glass-btn:active {
  transform: translate(0, 0);
  box-shadow: none;
}

.glass-btn-outline {
  background: #FFFFFF;
  color: var(--text-primary);
}

.glass-btn-outline:hover {
  background: var(--accent);
}

.glass-btn-success { background: var(--success); }
.glass-btn-success:hover { background: var(--success-hover); }

.glass-btn-danger { background: var(--danger); }
.glass-btn-danger:hover { background: var(--danger-hover); }
```

- [ ] **Step 4: Rewrite .glass-btn, .glass-btn-* variants**
  - Replace gradient backgrounds with solid colors
  - Add thick black borders
  - Remove opacity/hover fade effects
  - Add hard shadow on hover

**Expected:** Buttons have solid colors, thick borders, snappy hover states

### Step 5: Rewrite Form Inputs

Replace glass inputs with neo-brutalist inputs:

```css
.glass-input {
  width: 100%;
  padding: 0.875rem 1rem;
  background: #FFFFFF;
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 1rem;
  transition: all var(--transition-fast);
  outline: none;
}

.glass-input::placeholder {
  color: var(--text-muted);
}

.glass-input:focus {
  border-color: var(--primary);
  box-shadow: 4px 4px 0px var(--primary);
}

.glass-select {
  /* Similar to glass-input with custom arrow */
  background: #FFFFFF;
  border: var(--border-width) solid var(--border-color);
}
```

- [ ] **Step 5: Rewrite .glass-input, .glass-select**
  - Replace transparent background with white
  - Add thick black border
  - Change focus state to hard shadow (not glow)

**Expected:** Inputs have white background, thick borders, hard shadow on focus

### Step 6: Rewrite Navigation

Replace glass navbar with neo-brutalist navbar:

```css
.navbar {
  position: sticky;
  top: 1rem;
  z-index: 100;
  margin: 0 1rem 1.5rem;
  padding: 1rem 1.5rem;
  background: #FFFFFF;
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-hard);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.navbar-brand {
  font-size: 1.5rem;
  font-weight: 900;
  color: var(--primary);
}

.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius-md);
  border: 2px solid transparent;
  transition: all var(--transition-fast);
  font-weight: 500;
}

.nav-link:hover {
  background: var(--accent);
  color: var(--text-primary);
}

.nav-link.active {
  background: var(--primary);
  color: #FFFFFF;
  border-color: var(--border-color);
  box-shadow: var(--shadow-hard-sm);
}
```

- [ ] **Step 6: Rewrite .navbar, .nav-link**
  - Replace glass background with white
  - Add thick border and hard shadow
  - Change active state to solid color

**Expected:** Navigation bar has white background, thick borders, colorful active states

### Step 7: Rewrite Tables, Badges, and Widgets

```css
.glass-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.glass-table th {
  background: var(--accent);
  border-bottom: var(--border-width) solid var(--border-color);
  padding: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  text-transform: uppercase;
  font-size: 0.75rem;
}

.glass-table tbody tr {
  border-bottom: 1px solid var(--border-color);
}

.glass-table tbody tr:hover {
  background: rgba(255, 230, 109, 0.3);
}

.glass-badge {
  display: inline-flex;
  padding: 0.25rem 0.75rem;
  background: var(--info);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 600;
  color: #FFFFFF;
}

.glass-badge-success { background: var(--success); }
.glass-badge-warning { background: var(--warning); color: #000; }
.glass-badge-danger { background: var(--danger); }

.stat-card {
  background: #FFFFFF;
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-hard);
}
```

- [ ] **Step 7: Rewrite tables, badges, stat cards**
  - Apply neo-brutalist styling to all components
  - Use solid accent colors for table headers
  - Add hard shadows to stat cards

**Expected:** Tables, badges, and stat cards follow neo-brutalist style

### Step 8: Remove Glassmorphism-Specific Elements

Remove or update elements that don't work with neo-brutalism:

- [ ] **Step 8: Remove glassmorphism elements**
  - Remove `.orb` elements (floating colored orbs)
  - Remove `backdrop-filter: blur()` from all rules
  - Remove gradient backgrounds from `.text-gradient` - replace with solid color
  - Remove `shimmer` and `pulse` animations (or simplify)

**Expected:** No glassmorphism-specific visual effects remain

### Step 9: Update Text Gradient and Typography

```css
.text-gradient {
  /* Replace gradient with solid accent color */
  color: var(--primary);
  font-weight: 900;
}

.page-title {
  font-size: 1.75rem;
  font-weight: 900;
  color: var(--text-primary);
  text-shadow: 2px 2px 0px var(--accent);
}
```

- [ ] **Step 9: Update typography styles**
  - Replace gradient text with solid color + hard shadow
  - Increase font weights for bolder appearance

**Expected:** Headings have bold, solid colors with hard text shadows

### Step 10: Verify and Test

- [ ] **Step 10: Verify CSS compiles without errors**
  - Check for syntax errors
  - Ensure all classes used in templates exist

- [ ] **Step 11: Test all pages render correctly**
  - Login page
  - Dashboard
  - Invoice form
  - Product list
  - All modals and interactive elements

**Expected:** All pages render with neo-brutalist style without errors

---

## Task 2: Update Base Template

**Files:**
- Modify: `/marimo/hesabeshkon/home/templates/base/base.html`

### Step 1: Remove Orb Elements

- [ ] **Step 1: Remove floating orb divs from base.html**
  - Delete `<div class="orb orb-1"></div>`
  - Delete `<div class="orb orb-2"></div>`
  - Delete `<div class="orb orb-3"></div>`

**Expected:** Base template no longer renders floating orbs

### Step 2: Update Background Element

- [ ] **Step 2: Simplify animated background**
  - Change `.background-animate` to simpler static or subtle pattern

**Expected:** Background is simpler, neo-brutalist appropriate

---

## Task 3: Update Login Page Styles

**Files:**
- Modify: `/marimo/hesabeshkon/home/templates/accounts/login.html`

### Step 1: Update Login Card Styles

- [ ] **Step 1: Update inline styles in login.html to neo-brutalist**
  - Remove orb elements
  - Update `.login-card` with thick borders and hard shadows
  - Update `.login-logo-icon` with solid colors

**Expected:** Login page matches neo-brutalist design

---

## Task 4: Update Dashboard Styles

**Files:**
- Modify: `/marimo/hesabeshkon/home/templates/homepage/dashboard.html`

### Step 1: Update Dashboard Inline Styles

- [ ] **Step 1: Update inline styles in dashboard.html**
  - Ensure all styles match neo-brutalist system
  - Update chart containers, quick action buttons

**Expected:** Dashboard matches neo-brutalist design

---

## Task 5: Update Invoice Page Styles

**Files:**
- Modify: `/marimo/hesabeshkon/home/templates/faktor/invoice_sell.html`

### Step 1: Update Invoice Container Styles

- [ ] **Step 1: Update inline styles in invoice_sell.html**
  - Replace glass styles with neo-brutalist equivalents
  - Update summary card with hard shadows
  - Update cart items with thick borders

**Expected:** Invoice page matches neo-brutalist design

---

## Task 6: Update Product List Styles

**Files:**
- Modify: `/marimo/hesabeshkon/home/templates/product/product_list.html`

### Step 1: Update Product List Inline Styles

- [ ] **Step 1: Update inline styles in product_list.html**
  - Remove shimmer animation from product images
  - Update filter buttons with neo-brutalist style
  - Update action buttons with thick borders

**Expected:** Product list matches neo-brutalist design

---

## Completion Criteria

1. ✅ Main CSS file rewritten with neo-brutalist variables and styles
2. ✅ All `backdrop-filter: blur()` removed
3. ✅ All gradients replaced with solid colors
4. ✅ All components have thick black borders (2px)
5. ✅ All components have hard shadows (no blur)
6. ✅ Background changed from dark to light cream
7. ✅ Orbs and animated elements removed
8. ✅ All 6 pages render correctly with new styles
9. ✅ RTL layout preserved
10. ✅ Responsive design preserved
11. ✅ Accessibility maintained (color contrast)

---

## Notes

- The CSS file is large (1200+ lines). A complete rewrite is more efficient than incremental changes.
- All HTML templates keep their structure - only styles change.
- Font family (Vazirmatn) remains unchanged.
- Utility classes (`.mt-1`, `.mb-2`, etc.) remain unchanged for compatibility.
