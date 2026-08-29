from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import IdentityVerification, IdentityVerificationAnalysis, IdentityVerificationEvent, User


@admin.register(User)
class FasthomeUserAdmin(UserAdmin):
    """Administration du compte utilisateur Fasthome.

    Le modèle User de Fasthome n'utilise pas le champ Django ``username``.
    On définit donc les fieldsets explicitement au lieu d'hériter de
    UserAdmin.fieldsets, qui ajoute automatiquement ``username``.
    """

    ordering = ('-created_at',)
    list_display = (
        'fasthome_id', 'email', 'phone', 'last_name', 'first_name',
        'is_certified', 'is_staff', 'can_review_kyc',
    )
    search_fields = ('fasthome_id', 'email', 'phone', 'last_name', 'first_name')
    readonly_fields = ('fasthome_id',)

    fieldsets = (
        (None, {'fields': ('password',)}),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'postname', 'email', 'phone',
                       'birth_date', 'sex', 'profession', 'profile_photo')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Dates importantes', {
            'fields': ('last_login', 'date_joined')
        }),
        ('Fasthome', {
            'fields': (
                'fasthome_id', 'is_phone_verified', 'is_email_verified',
                'is_certified', 'can_review_kyc',
            )
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'phone', 'last_name', 'first_name',
                'postname', 'birth_date', 'sex', 'profession',
                'password1', 'password2',
            ),
        }),
    )


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'assigned_reviewer', 'document_type', 'status', 'facial_status', 'submitted_at', 'verified_at')
    list_filter = ('status', 'facial_status', 'document_type')
    search_fields = ('user__fasthome_id', 'user__email', 'assigned_reviewer__email')
    autocomplete_fields = ('assigned_reviewer',)


@admin.register(IdentityVerificationAnalysis)
class IdentityVerificationAnalysisAdmin(admin.ModelAdmin):
    list_display = ('verification', 'decision', 'confidence_score', 'ocr_engine', 'expiry_ok', 'processed_at')
    list_filter = ('decision', 'ocr_engine', 'expiry_ok')
    search_fields = ('verification__user__fasthome_id', 'verification__user__email', 'extracted_name')
    readonly_fields = [field.name for field in IdentityVerificationAnalysis._meta.fields]


@admin.register(IdentityVerificationEvent)
class IdentityVerificationEventAdmin(admin.ModelAdmin):
    list_display = ('verification', 'event_type', 'actor', 'from_status', 'to_status', 'created_at')
    list_filter = ('event_type', 'to_status', 'to_facial_status')
    search_fields = ('verification__user__fasthome_id', 'actor__email', 'reason')
    readonly_fields = [field.name for field in IdentityVerificationEvent._meta.fields]
