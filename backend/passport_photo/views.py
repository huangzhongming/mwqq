from rest_framework import status, generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import Country, PhotoProcessingJob
from .serializers import CountrySerializer, PhotoUploadSerializer, PhotoProcessingJobSerializer
from .services import PassportPhotoProcessor
import threading
import uuid

class CountryListView(generics.ListAPIView):
    queryset = Country.objects.all().order_by('name')
    serializer_class = CountrySerializer

@api_view(['POST'])
def upload_photo(request):
    """Upload photo and start processing"""
    serializer = PhotoUploadSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        photo = serializer.validated_data['photo']
        country_id = serializer.validated_data['country_id']
        
        # Get country
        country = Country.objects.get(id=country_id)
        
        # Validate image
        processor = PassportPhotoProcessor()
        processor.validate_image(photo)
        
        # Create processing job
        job = PhotoProcessingJob.objects.create(
            country=country,
            original_photo=photo,
            status='pending'
        )
        
        # Start background processing
        thread = threading.Thread(
            target=process_photo_background,
            args=(job.id,)
        )
        thread.daemon = True
        thread.start()
        
        # Return job ID for tracking
        return Response({
            'job_id': job.id,
            'status': 'pending',
            'message': 'Photo uploaded successfully. Processing started.'
        }, status=status.HTTP_201_CREATED)
        
    except Country.DoesNotExist:
        return Response({'error': 'Country not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def job_status(request, job_id):
    """Get processing job status"""
    try:
        job = PhotoProcessingJob.objects.get(id=job_id)
        
        # Check if job is expired
        if timezone.now() > job.expires_at:
            job.delete()
            return Response({'error': 'Job expired'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = PhotoProcessingJobSerializer(job, context={'request': request})
        return Response(serializer.data)
        
    except PhotoProcessingJob.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)

def process_photo_background(job_id):
    """Background task to process photo"""
    try:
        job = PhotoProcessingJob.objects.get(id=job_id)
        job.status = 'processing'
        job.save()
        
        # Get country specifications
        country_specs = {
            'photo_width': job.country.photo_width,
            'photo_height': job.country.photo_height,
            'face_height_ratio': job.country.face_height_ratio,
        }
        
        # Process the photo
        processor = PassportPhotoProcessor()
        
        # Read original photo
        with job.original_photo.open('rb') as f:
            image_bytes = f.read()
        
        # Create passport photo
        processed_bytes = processor.create_passport_photo(image_bytes, country_specs)
        
        # Save processed photo
        filename = f"passport_{job.id}.jpg"
        job.processed_photo.save(
            filename,
            ContentFile(processed_bytes),
            save=False
        )
        
        job.status = 'completed'
        job.save()
        
    except Exception as e:
        try:
            job = PhotoProcessingJob.objects.get(id=job_id)
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
        except:
            pass