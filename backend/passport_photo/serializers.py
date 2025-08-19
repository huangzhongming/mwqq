from rest_framework import serializers
from .models import Country, PhotoProcessingJob

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'code', 'photo_width', 'photo_height', 'face_height_ratio']

class PhotoUploadSerializer(serializers.Serializer):
    photo = serializers.ImageField()
    country_id = serializers.IntegerField()
    
    def validate_country_id(self, value):
        try:
            Country.objects.get(id=value)
            return value
        except Country.DoesNotExist:
            raise serializers.ValidationError("Invalid country ID")

class PhotoProcessingJobSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    processed_photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PhotoProcessingJob
        fields = ['id', 'country', 'status', 'error_message', 'created_at', 
                 'updated_at', 'processed_photo_url']
    
    def get_processed_photo_url(self, obj):
        if obj.processed_photo and obj.status == 'completed':
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.processed_photo.url)
        return None