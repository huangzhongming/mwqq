from django.contrib import admin
from .models import Country, PhotoProcessingJob

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'photo_width', 'photo_height', 'face_height_ratio']
    list_filter = ['created_at']
    search_fields = ['name', 'code']
    ordering = ['name']

@admin.register(PhotoProcessingJob)
class PhotoProcessingJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'country', 'status', 'created_at', 'expires_at']
    list_filter = ['status', 'created_at', 'country']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']