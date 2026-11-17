from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import ManagedUserForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    add_form = ManagedUserForm
    ordering = ("username",)
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("username", "email", "phone")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("اطلاعات شخصی", {"fields": ("username", "phone")}),
        (
            "نقش و دسترسی",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "phone", "role", "password1", "password2", "is_active"),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        role = form.cleaned_data.get("role") if hasattr(form, "cleaned_data") else None
        if role:
            obj.assign_role(role)
