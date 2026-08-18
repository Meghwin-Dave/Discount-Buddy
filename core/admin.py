from django.contrib import admin
from .models import Banner

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_visible', 'priority', 'cta_url', 'is_active', 'created_at')
    list_filter = ('is_visible', 'is_active')
    search_fields = ('title', 'body', 'cta_url')
    fields = ('title', 'body', 'cta_url', 'image', 'priority', 'is_visible', 'is_active')
