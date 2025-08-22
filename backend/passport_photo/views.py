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
import base64
import json
from PIL import Image
import io

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

@api_view(['POST'])
def prepare_photo(request):
    """Upload photo, remove background, and detect face for manual selection"""
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
        
        # Read photo bytes
        photo.seek(0)
        image_bytes = photo.read()
        
        # Remove background
        no_bg_bytes = processor.remove_background(image_bytes)
        no_bg_image = Image.open(io.BytesIO(no_bg_bytes))
        
        # Detect face
        faces = processor.detect_face(no_bg_image)
        
        if not faces:
            return Response({'error': 'No face detected in the image'}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(faces) > 1:
            return Response({'error': 'Multiple faces detected. Please upload a photo with only one person.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the best face
        face = max(faces, key=lambda x: x['confidence'])
        face_bbox = face['bbox']
        
        # Convert background-removed image to base64
        bg_removed_buffer = io.BytesIO()
        if no_bg_image.mode == 'RGBA':
            no_bg_image.save(bg_removed_buffer, format='PNG')
        else:
            no_bg_image.save(bg_removed_buffer, format='JPEG', quality=85)
        bg_removed_buffer.seek(0)
        
        bg_removed_base64 = base64.b64encode(bg_removed_buffer.getvalue()).decode('utf-8')
        
        # Calculate default rectangle position and size based on country requirements
        target_width = country.photo_width
        target_height = country.photo_height
        face_height_ratio = country.face_height_ratio
        
        # Calculate default rectangle size (same aspect ratio as target)
        aspect_ratio = target_width / target_height
        image_width = no_bg_image.width
        image_height = no_bg_image.height
        
        # Default rectangle size - make it reasonably sized
        default_rect_height = min(image_height * 0.8, image_width * 0.8 / aspect_ratio)
        default_rect_width = default_rect_height * aspect_ratio
        
        # Position rectangle based on detected face
        x1, y1, x2, y2 = face_bbox
        face_center_x = (x1 + x2) / 2
        face_center_y = (y1 + y2) / 2
        
        # Position rectangle with face center at the appropriate position
        # For passport photos, face should be in upper portion
        rect_center_x = face_center_x
        rect_center_y = face_center_y - (default_rect_height * 0.1)  # Slightly higher than face center
        
        # Ensure rectangle stays within image bounds
        rect_left = max(0, rect_center_x - default_rect_width / 2)
        rect_top = max(0, rect_center_y - default_rect_height / 2)
        rect_right = min(image_width, rect_left + default_rect_width)
        rect_bottom = min(image_height, rect_top + default_rect_height)
        
        # Adjust if rectangle goes out of bounds
        if rect_right - rect_left < default_rect_width:
            rect_left = max(0, rect_right - default_rect_width)
        if rect_bottom - rect_top < default_rect_height:
            rect_top = max(0, rect_bottom - default_rect_height)
        
        return Response({
            'image_data': bg_removed_base64,
            'image_format': 'PNG' if no_bg_image.mode == 'RGBA' else 'JPEG',
            'image_dimensions': {
                'width': image_width,
                'height': image_height
            },
            'face_bbox': face_bbox,
            'default_selection': {
                'x': int(rect_left),
                'y': int(rect_top),
                'width': int(rect_right - rect_left),
                'height': int(rect_bottom - rect_top)
            },
            'target_dimensions': {
                'width': target_width,
                'height': target_height
            },
            'country': {
                'id': country.id,
                'name': country.name,
                'code': country.code
            }
        })
        
    except Country.DoesNotExist:
        return Response({'error': 'Country not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def generate_photo(request):
    """Generate final passport photo from selected area"""
    try:
        # Get request data
        image_data = request.data.get('image_data')
        selection = request.data.get('selection')
        country_id = request.data.get('country_id')
        
        if not all([image_data, selection, country_id]):
            return Response({'error': 'Missing required fields: image_data, selection, country_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get country
        country = Country.objects.get(id=country_id)
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            return Response({'error': 'Invalid image data'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract selection coordinates
        sel_x = int(selection['x'])
        sel_y = int(selection['y'])
        sel_width = int(selection['width'])
        sel_height = int(selection['height'])
        
        # Crop the selected area
        cropped_image = image.crop((sel_x, sel_y, sel_x + sel_width, sel_y + sel_height))
        
        # Convert RGBA to RGB if needed (for JPEG compatibility)
        if cropped_image.mode == 'RGBA':
            # Create white background
            rgb_image = Image.new('RGB', cropped_image.size, (255, 255, 255))
            rgb_image.paste(cropped_image, mask=cropped_image.split()[3])
            cropped_image = rgb_image
        elif cropped_image.mode != 'RGB':
            cropped_image = cropped_image.convert('RGB')
        
        # Resize to target dimensions
        target_width = country.photo_width
        target_height = country.photo_height
        final_image = cropped_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Enhance image quality
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Sharpness(final_image)
        final_image = enhancer.enhance(1.1)
        
        contrast_enhancer = ImageEnhance.Contrast(final_image)
        final_image = contrast_enhancer.enhance(1.05)
        
        # Convert to bytes
        output = io.BytesIO()
        
        if country.code == 'FI':
            # Finnish requirements: exactly 500x653 pixels, max 250KB
            quality = 95
            while quality > 60:
                output.seek(0)
                output.truncate()
                
                final_image.save(
                    output,
                    format='JPEG',
                    quality=quality,
                    optimize=True
                )
                
                file_size = output.tell()
                if file_size <= 250 * 1024:  # 250KB limit
                    break
                
                quality -= 5
        else:
            # Standard output for other countries
            final_image.save(
                output,
                format='JPEG',
                quality=95,
                dpi=(300, 300)
            )
        
        output.seek(0)
        processed_bytes = output.getvalue()
        
        # Create processing job for tracking
        job = PhotoProcessingJob.objects.create(
            country=country,
            status='completed'
        )
        
        # Save processed photo
        filename = f"passport_{job.id}.jpg"
        job.processed_photo.save(
            filename,
            ContentFile(processed_bytes),
            save=False
        )
        job.save()
        
        return Response({
            'job_id': job.id,
            'status': 'completed',
            'message': 'Photo generated successfully',
            'file_size': len(processed_bytes),
            'dimensions': f"{target_width}×{target_height}"
        }, status=status.HTTP_201_CREATED)
        
    except Country.DoesNotExist:
        return Response({'error': 'Country not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
            'country_code': job.country.code,
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