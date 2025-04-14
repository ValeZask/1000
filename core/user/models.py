from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone
import random
import string


class MyUserManager(BaseUserManager):
    def create_user(self, email, phone_number, username, password=None):
        user = self.model(
            email=email,
            phone_number=phone_number,
            username=username,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone_number, username, password=None):
        user = self.create_user(
            email=email,
            phone_number=phone_number,
            username=username,
        )
        user.is_admin = True
        user.set_password(password)
        user.save(using=self._db)
        return user


class MyUser(AbstractBaseUser):
    username = models.CharField(max_length=223, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=14)
    address = models.CharField(max_length=220, blank=True, null=True)
    cover = models.ImageField(upload_to='user_cover', blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)

    objects = MyUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone_number']

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        """Does the user have a specific permission?"""
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        """Does the user have permissions to view the app `app_label`?"""
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        """Is the user a member of staff?"""
        # Simplest possible answer: All admins are staff
        return self.is_admin

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class PasswordResetCode(models.Model):
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE)
    code = models.CharField(max_length=6, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices(string.digits, k=6))
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=15)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Reset code for {self.user.email}"

    class Meta:
        verbose_name = 'Код сброса пароля'
        verbose_name_plural = 'Коды сброса пароля'
