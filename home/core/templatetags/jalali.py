"""تبدیل تاریخ میلادی به شمسی (جلالی) بدون وابستگی خارجی."""

from datetime import date, datetime

from django import template
from django.utils import timezone

register = template.Library()

G_DAYS_IN_MONTH = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1
    g_day_no = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
    g_day_no += G_DAYS_IN_MONTH[gm2] + gd2
    if gm > 2 and ((gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0):
        g_day_no += 1

    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    if j_day_no < 186:
        jm = 1 + j_day_no // 31
        jd = 1 + j_day_no % 31
    else:
        jm = 7 + (j_day_no - 186) // 30
        jd = 1 + (j_day_no - 186) % 30
    return jy, jm, jd


def _as_date(value):
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.date()
    if isinstance(value, date):
        return value
    return None


@register.filter
def jalali(value):
    d = _as_date(value)
    if not d:
        return "—"
    jy, jm, jd = gregorian_to_jalali(d.year, d.month, d.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d}"


@register.filter
def jalali_short(value):
    d = _as_date(value)
    if not d:
        return "—"
    jy, jm, jd = gregorian_to_jalali(d.year, d.month, d.day)
    return f"{jm:02d}/{jd:02d}"


@register.filter
def jalali_time(value):
    if not isinstance(value, datetime):
        return ""
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime("%H:%M")


@register.filter
def jalali_datetime(value):
    return f"{jalali(value)} {jalali_time(value)}".strip()
