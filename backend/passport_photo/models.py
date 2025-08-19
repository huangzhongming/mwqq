from django.db import models
from django.utils import timezone
import uuid

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=3, unique=True)
    photo_width = models.IntegerField()  # in pixels
    photo_height = models.IntegerField()  # in pixels
    face_height_ratio = models.FloatField(default=0.7)  # face height as ratio of total height
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Countries"
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class PhotoProcessingJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    original_photo = models.ImageField(upload_to='uploads/original/')
    processed_photo = models.ImageField(upload_to='uploads/processed/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Job {self.id} - {self.status}"