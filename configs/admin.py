from django.contrib import admin
from .models import AppConfig

@admin.register(AppConfig)
class AppConfigAdmin(admin.ModelAdmin):
    list_display = ('config_key', 'platform', 'config_value', 'config_type', 'is_active', 'updated_at')
    list_filter = ('platform', 'config_type', 'is_active')
    search_fields = ('config_key', 'config_value', 'description')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Configuration Info', {
            'fields': ('config_key', 'config_value', 'config_type', 'description')
        }),
        ('Platform & Status', {
            'fields': ('platform', 'is_active')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
