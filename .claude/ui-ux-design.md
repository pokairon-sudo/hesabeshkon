# UI/UX Design Skill

Comprehensive design guidance for building modern, accessible, and beautiful user interfaces.

---

## Core Design Principles

### 1. Visual Hierarchy
- Use size, color, and spacing to guide attention
- Establish clear information architecture
- Apply the 8px grid system for consistent spacing

### 2. Accessibility First
- Maintain WCAG 2.1 AA contrast ratios (4.5:1 for text, 3:1 for large text)
- Support keyboard navigation and focus states
- Use semantic HTML and ARIA labels appropriately
- Design for reduced motion preferences

### 3. Consistency
- Use design tokens for colors, typography, and spacing
- Maintain consistent component patterns
- Establish and follow a style guide

---

## Tailwind CSS Utility Reference

### Layout
```
flex, flex-col, flex-row, flex-wrap
grid, grid-cols-1 md:grid-cols-2 lg:grid-cols-3
justify-start | center | end | between | around
items-start | center | end | stretch
gap-0 | gap-1 | gap-2 | gap-4 | gap-6 | gap-8
```

### Spacing (8px scale)
```
p-1(4px) | p-2(8px) | p-3(12px) | p-4(16px) | p-6(24px) | p-8(32px)
m-1(4px) | m-2(8px) | m-3(12px) | m-4(16px) | m-6(24px) | m-8(32px)
```

### Typography
```
text-xs(12px) | text-sm(14px) | text-base(16px) | text-lg(18px) | text-xl(20px) | text-2xl(24px)
font-normal | font-medium | font-semibold | font-bold
text-gray-500 | text-gray-700 | text-gray-900
leading-tight | leading-normal | leading-relaxed
```

### Colors (with opacity modifiers)
```
bg-white | bg-gray-100 | bg-gray-500 | bg-gray-900
bg-blue-500 | bg-green-500 | bg-red-500 | bg-purple-500
text-current | text-white | text-black
bg-opacity-50 | bg-opacity-75 | bg-opacity-100
```

### Effects
```
shadow-sm | shadow | shadow-md | shadow-lg | shadow-xl
rounded-sm | rounded | rounded-md | rounded-lg | rounded-xl | rounded-full
opacity-0 | opacity-25 | opacity-50 | opacity-75 | opacity-100
blur-sm | blur | blur-md | blur-lg
```

### Transitions & Animations
```
transition-all | transition-colors | transition-transform
duration-150 | duration-200 | duration-300 | duration-500
ease-in | ease-out | ease-in-out | linear
animate-pulse | animate-bounce | animate-spin
```

---

## Component Patterns

### Button Variants

```html
<!-- Primary Button -->
<button class="bg-blue-600 hover:bg-blue-700 text-white font-medium
               py-2 px-4 rounded-lg transition-colors duration-200
               focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
  Primary Action
</button>

<!-- Secondary Button -->
<button class="bg-gray-100 hover:bg-gray-200 text-gray-900 font-medium
               py-2 px-4 rounded-lg transition-colors duration-200
               focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2">
  Secondary Action
</button>

<!-- Ghost Button -->
<button class="bg-transparent hover:bg-gray-100 text-gray-700 font-medium
               py-2 px-4 rounded-lg transition-colors duration-200
               focus:outline-none focus:ring-2 focus:ring-gray-500">
  Ghost Action
</button>

<!-- Danger Button -->
<button class="bg-red-600 hover:bg-red-700 text-white font-medium
               py-2 px-4 rounded-lg transition-colors duration-200
               focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2">
  Delete
</button>
```

### Card Component

```html
<div class="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300">
  <img src="..." alt="..." class="w-full h-48 object-cover" />
  <div class="p-6">
    <h3 class="text-xl font-semibold text-gray-900 mb-2">Card Title</h3>
    <p class="text-gray-600 mb-4">Card description text goes here...</p>
    <div class="flex justify-between items-center">
      <span class="text-sm text-gray-500">Metadata</span>
      <button class="text-blue-600 hover:text-blue-700 font-medium">
        Learn More
      </button>
    </div>
  </div>
</div>
```

### Form Elements

```html
<!-- Input Field -->
<div class="space-y-2">
  <label class="block text-sm font-medium text-gray-700">Email</label>
  <input type="email"
         class="w-full px-4 py-2 border border-gray-300 rounded-lg
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                placeholder-gray-400"
         placeholder="Enter your email" />
  <p class="text-xs text-gray-500">We'll never share your email.</p>
</div>

<!-- Checkbox -->
<label class="flex items-center space-x-2 cursor-pointer">
  <input type="checkbox"
         class="w-4 h-4 text-blue-600 border-gray-300 rounded
                focus:ring-blue-500" />
  <span class="text-sm text-gray-700">I agree to the terms</span>
</label>

<!-- Select Dropdown -->
<select class="w-full px-4 py-2 border border-gray-300 rounded-lg
               focus:outline-none focus:ring-2 focus:ring-blue-500
               bg-white">
  <option>Option 1</option>
  <option>Option 2</option>
  <option>Option 3</option>
</select>
```

### Navigation

```html
<!-- Responsive Navigation Bar -->
<nav class="bg-white shadow-sm">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16">
      <div class="flex items-center">
        <span class="text-xl font-bold text-gray-900">Logo</span>
        <div class="hidden md:ml-6 md:flex md:space-x-4">
          <a href="#" class="px-3 py-2 text-sm font-medium text-blue-600">Home</a>
          <a href="#" class="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900">About</a>
          <a href="#" class="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900">Contact</a>
        </div>
      </div>
    </div>
  </div>
</nav>
```

### Modal/Dialog

```html
<div class="fixed inset-0 z-50 overflow-y-auto">
  <div class="flex min-h-screen items-center justify-center p-4">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>

    <!-- Modal -->
    <div class="relative bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">Modal Title</h3>
      <p class="text-gray-600 mb-6">Modal content goes here...</p>
      <div class="flex justify-end space-x-3">
        <button class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg">Cancel</button>
        <button class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Confirm</button>
      </div>
    </div>
  </div>
</div>
```

---

## Color Systems

### Neutral Scale
```
gray-50    #fafafa   /* Backgrounds */
gray-100   #f5f5f5   /* Card backgrounds */
gray-200   #e5e5e5   /* Borders */
gray-300   #d4d4d4   /* Divider */
gray-400   #a3a3a3   /* Secondary text */
gray-500   #737373   /* Muted text */
gray-600   #525252   /* Body text */
gray-700   #404040   /* Headings */
gray-800   #262626   /* Strong text */
gray-900   #171717   /* Highest contrast */
```

### Semantic Colors
```
blue-500   #3b82f6   /* Primary actions */
green-500  #22c55e   /* Success states */
yellow-500 #eab308   /* Warning states */
red-500    #ef4444   /* Error states */
purple-500 #a855f7   /* Accents */
```

---

## Glass Morphism (Modern Additions)

```css
.glass-panel {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
}

/* Tailwind equivalent */
.glass-tailwind {
  @apply bg-white/10 backdrop-blur-md border border-white/20
         rounded-xl shadow-lg;
}
```

---

## Responsive Breakpoints

```
sm:  640px   /* Small devices */
md:  768px   /* Tablets */
lg:  1024px  /* Laptops */
xl:  1280px  /* Desktops */
2xl: 1536px  /* Large screens */
```

---

## Dark Mode Support

```html
<div class="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
  <button class="bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600">
    Dark Mode Button
  </button>
</div>
```

---

## Accessibility Checklist

- [ ] All interactive elements have visible focus states
- [ ] Color is not the only means of conveying information
- [ ] Images have descriptive alt text
- [ ] Form inputs have associated labels
- [ ] Interactive elements are keyboard navigable
- [ ] Sufficient color contrast (4.5:1 for text)
- [ ] Animations can be paused or reduced
- [ ] Touch targets are at least 44x44px

---

## Design Tools & Resources

- **Figma** - UI/UX design and prototyping
- **Tailwind Play** - https://play.tailwindcss.com/
- **Heroicons** - https://heroicons.com/
- **shadcn/ui** - https://ui.shadcn.com/
- **Material Design 3** - https://m3.material.io/
- **Color Contrast Checkers** - WebAIM Contrast Checker

---

## Usage

When you need UI/UX assistance, ask:

- "Create a responsive navigation component"
- "Design a login form with validation"
- "Create a dashboard layout"
- "Style a card grid with Tailwind"
- "Make this button accessible"
- "Create a dark mode color scheme"
- "Design a modal dialog component"
