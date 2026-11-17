---
name: glassMorphism
description: Generate glass morphism and liquid glass CSS effects for web components
---

# Glass Morphism Skill

## Overview
Helps implement glass morphism and liquid glass effects in web applications.

## Commands

### Generate Glass CSS
When asked for glass morphism CSS, provide:

```css
.glass-panel {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
}
```

### Liquid Glass CSS
For organic liquid glass effects:

```css
.liquid-glass {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.1) 0%,
    rgba(255, 255, 255, 0.05) 100%
  );
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 30px 20px 35px 25px / 25px 35px 20px 30px;
  box-shadow:
    0 8px 32px 0 rgba(0, 0, 0, 0.15),
    inset 0 0 20px rgba(255, 255, 255, 0.05);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
```

### Color Palettes

**Ocean Gradient:**
```css
background: linear-gradient(135deg, rgba(105, 240, 241, 0.15) 0%, rgba(75, 0, 212, 0.15) 100%);
```

**Sunset Gradient:**
```css
background: linear-gradient(135deg, rgba(255, 94, 148, 0.15) 0%, rgba(255, 159, 120, 0.15) 100%);
```

**Dark Glass:**
```css
.glass-dark {
  background: rgba(30, 30, 40, 0.6);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
}
```

### Tailwind CSS Equivalent
```html
<div class="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl shadow-lg">
  Content
</div>
```

## Usage Examples
- "Create a glass morphism navbar"
- "Make a glass card component"
- "Generate liquid glass CSS for a modal"
- "Convert this component to glass style"
