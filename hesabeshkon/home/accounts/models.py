#
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.core.validators import RegexValidator

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, phone=None):
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('The Username field must be set')

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, phone=phone)
        user.set_password(password)  # Hash the password
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, phone=None):
        user = self.create_user(username, email, password, phone)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(validators=[phone_regex], max_length=16, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    groups = models.ManyToManyField(Group, related_name='accounts_users', blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name='accounts_user_permissions', blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'  # Email will be the unique identifier
    REQUIRED_FIELDS = ['username']  # Required fields

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.email

    @property
    def is_staff_or_manager(self):
        """
        T3.1/T2.1: single source of truth for "can manage products/faktors" —
        used both here (so navbar links can check it directly in templates,
        since Django templates call zero-arg properties automatically) and
        by accounts.mixins.StaffGroupRequiredMixin, so the definition of
        "staff" never drifts between the nav and the actual permission check.
        """
        if self.is_staff or self.is_superuser:
            return True
        return self.groups.filter(name__in=["personal", "admin"]).exists()


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def add_user_to_customer_group(sender, instance, created, **kwargs):
    if created:
        customer_group, _ = Group.objects.get_or_create(name='customer')
        instance.groups.add(customer_group)
