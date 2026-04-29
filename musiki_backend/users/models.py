from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from common.models import SoftDeleteModel, SoftDeleteManager


class UserManager(BaseUserManager, SoftDeleteManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError('Username zorunludur')
        email = self.normalize_email(email) if email else ''
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser, SoftDeleteModel):
    class Role(models.TextChoices):
        LISTENER = 'listener', 'Dinleyici'
        ARTIST = 'artist', 'Sanatçı'
        ADMIN = 'admin', 'Yönetici'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.LISTENER,
    )
    bio = models.TextField(blank=True, default='')
    is_approved_artist = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class PendingArtist(User):
    class Meta:
        proxy = True
        verbose_name = 'Onay Bekleyen Sanatçı'
        verbose_name_plural = 'Onay Bekleyen Sanatçılar'
