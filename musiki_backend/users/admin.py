from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

from django.utils import timezone
User = get_user_model()
from .models import PendingArtist


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_approved_artist', 'is_deleted', 'date_joined')
    list_filter = ('role', 'is_approved_artist', 'is_deleted', 'is_staff')
    search_fields = ('username', 'email')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Musiki', {
            'fields': ('role', 'bio', 'is_approved_artist', 'approved_at', 'is_deleted', 'deleted_at'),
        }),
    )


@admin.register(PendingArtist)
class PendingArtistAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'date_joined', 'is_approved_artist')
    list_editable = ('is_approved_artist',)
    
    # Detay sayfasına girildiğinde sadece ilgili alanları göster
    fieldsets = (
        (None, {'fields': ('username', 'email', 'bio')}),
        ('Onay Durumu', {'fields': ('is_approved_artist', 'approved_at', 'role')}),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role='artist', is_approved_artist=False)

    def save_model(self, request, obj, form, change):
        # Onay verildiğinde onaylanma tarihini otomatik ata
        if 'is_approved_artist' in form.changed_data and obj.is_approved_artist:
            obj.approved_at = timezone.now()
        super().save_model(request, obj, form, change)
