# Liquid Glassmorphism UI - حساب‌شکن

## نمای کلی

این سند توصیف‌کننده سیستم طراحی **Liquid Glassmorphism** جدید برای پروژه حساب‌شکن است. این طراحی مدرن‌ترین سبک UI با افکت‌های شیشه‌ای، گرادینت‌های شناور و انیمیشن‌های سیال است.

## فایل‌های ایجاد شده

### CSS
- `static/css/glassmorphism.css` - سیستم طراحی کامل شامل:
  - متغیرهای CSS برای رنگ‌ها، سایزها، انیمیشن‌ها
  - کامپوننت‌های Glass (کارت‌ها، دکمه‌ها، فرم‌ها)
  - استایل‌های جدول، مدال، Toast notifications
  - پشتیبانی از RTL برای فارسی
  - ریسپانسیو برای موبایل
  - انیمیشن‌های شناور و سیال

### JavaScript
- `static/js/glass-ui.js` - تعاملات شامل:
  - Toast notification system
  - Modal system
  - Mobile menu toggle
  - Invoice cart manager
  - Voice input (Web Speech API)
  - Keyboard shortcuts (F6-F9)
  - Search autocomplete
  - Animated counters

### Templates
| فایل | کاربرد |
|------|--------|
| `templates/base/base.html` | قالب پایه با ناوبری |
| `templates/accounts/login.html` | صفحه ورود |
| `templates/index.html` | داشبورد اصلی |
| `templates/product/list.html` | لیست کالاها |
| `templates/product/form.html` | فرم ایجاد/ویرایش کالا |
| `templates/core/settings.html` | تنظیمات فروشگاه |
| `templates/faktor/invoice_sell.html` | فاکتور فروش |

## ویژگی‌های طراحی

### 1. Glass Morphism
```css
.glass {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
}
```

### 2. Animated Background Orbs
سه کره رنگی با انیمیشن شناور در پس‌زمینه:
- بنفش (#667eea)
- صورتی (#f093fb)
- آبی (#4facfe)

### 3. Gradient Accents
- Primary: بنفش-آبی
- Success: سبز-فیروزه‌ای
- Warning: صورتی-زرد
- Danger: نارنجی-صورتی

### 4. Keyboard Shortcuts
| کلید | عملکرد |
|------|--------|
| F6 | ذخیره پیش‌نویس |
| F7 | نهایی‌سازی فاکتور |
| F8 | ساخت کالا جدید |
| F9 | نهایی و چاپ |

### 5. Voice Input
- پشتیبانی از تشخیص صدای فارسی
- دستوراتی مانند "سه تا کاپوچینو"
- فقط در Chrome/Edge با HTTPS

## کامپوننت‌ها

### Stat Cards
کارت‌های نمایش آمار با:
- آیکون گرادینت
- مقدار با انیمیشن
- برچسب وضعیت
- تغییر نسبت به دوره قبل

### Product Cards
کارت‌های کالا با:
- تصویر/آیکون
- قیمت فعلی و اصلی
- تخفیف
- موجودی
- دکمه‌های عملیات

### Tables
جدول‌های شیشه‌ای با:
- هدر ثابت
- hover effects
- ردیف‌های قابل کلیک
- pagination

### Forms
فرم‌های مدرن با:
- ورودی‌های شیشه‌ای
- toggle switches
- select با استایل سفارشی
- validation messages

## رنگ‌ها

| نام | مقدار | استفاده |
|-----|-------|---------|
| --glass-bg | rgba(255,255,255,0.08) | پس‌زمینه کارت‌ها |
| --primary-gradient | linear-gradient(135deg, #667eea, #764ba2) | دکمه‌های اصلی |
| --success-gradient | linear-gradient(135deg, #43e97b, #38f9d7) | تأیید/موفق |
| --warning-gradient | linear-gradient(135deg, #fa709a, #fee140) | هشدار |
| --danger-gradient | linear-gradient(135deg, #ff6a00, #ee1285) | خطا/حذف |

## انیمیشن‌ها

### Floating Orbs
```css
@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(50px, -50px) scale(1.1); }
  50% { transform: translate(-30px, 30px) scale(0.95); }
  75% { transform: translate(40px, 40px) scale(1.05); }
}
```

### Slide Up
ورود المان‌ها از پایین با delay برای هر کارت

### Shimmer
افکت برق روی تصاویر محصولات

## ریسپانسیو

- دسکتاپ: > 992px
- تبلت: 768px - 992px
- موبایل: < 768px

## نکات استقرار

1. فایل‌های استاتیک باید توسط Django جمع‌آوری شوند:
   ```bash
   python manage.py collectstatic
   ```

2. برای توسعه:
   ```bash
   python manage.py runserver
   ```

3. فونت Vazirmatn از Google Fonts بارگذاری می‌شود

## کارهای باقی‌مانده

- [ ] ایجاد template برای فاکتور خرید
- [ ] ایجاد template برای گزارش‌ها
- [ ] ایجاد template برای مدیریت کاربران
- [ ] ایجاد template برای پیش‌نویس‌ها
- [ ] افزودن نمودارهای واقعی با Chart.js
- [ ] ایجاد template برای چاپ فاکتور
- [ ] افزودن dark mode toggle

## تست

برای مشاهده تغییرات:
1. سرور را اجرا کنید
2. به صفحه لاگین بروید
3. با حساب مدیر وارد شوید
4. هر صفحه را بررسی کنید

## پشتیبانی

- مرورگرهای مدرن (Chrome, Firefox, Safari, Edge)
- پشتیبانی از CSS Variables
- پشتیبانی از backdrop-filter
