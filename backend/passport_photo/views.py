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
        
        # Use the same logic as automatic mode for default rectangle
        target_width = country.photo_width
        target_height = country.photo_height
        face_height_ratio = country.face_height_ratio
        image_width = no_bg_image.width
        image_height = no_bg_image.height
        
        # Get detection method for proper positioning
        detection_method = face['method']
        
        # Use the same calculation as automatic mode
        positioning_data = processor.calculate_optimal_scale_and_position(
            face_bbox, 
            (image_width, image_height), 
            (target_width, target_height), 
            face_height_ratio,
            country.code,
            detection_method
        )
        
        scale = positioning_data['scale']
        target_head_center = positioning_data['target_head_center']
        face_center = positioning_data['face_center']
        
        # Calculate the cropping area that would be used in automatic mode
        scaled_img_width = image_width * scale
        scaled_img_height = image_height * scale
        
        # Calculate offset to center the head optimally
        offset_x = target_head_center[0] - (face_center[0] * scale)
        offset_y = target_head_center[1] - (face_center[1] * scale)
        
        # Calculate the crop area from the scaled and positioned image
        crop_left = max(0, -offset_x)
        crop_top = max(0, -offset_y)
        crop_right = min(scaled_img_width, crop_left + target_width)
        crop_bottom = min(scaled_img_height, crop_top + target_height)
        
        # Convert back to original image coordinates
        rect_left = crop_left / scale
        rect_top = crop_top / scale
        rect_right = crop_right / scale
        rect_bottom = crop_bottom / scale
        
        # Ensure rectangle stays within image bounds
        rect_left = max(0, min(image_width - target_width/scale, rect_left))
        rect_top = max(0, min(image_height - target_height/scale, rect_top))
        rect_right = min(image_width, rect_left + target_width/scale)
        rect_bottom = min(image_height, rect_top + target_height/scale)
        
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
        
        # Validate and get country
        try:
            country_id = int(country_id)
            if country_id <= 0:
                return Response({'error': 'Invalid country ID: must be positive'}, status=status.HTTP_400_BAD_REQUEST)
            country = Country.objects.get(id=country_id)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid country ID format'}, status=status.HTTP_400_BAD_REQUEST)
        except Country.DoesNotExist:
            return Response({'error': 'Country not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Validate and decode base64 image
        try:
            # Validate base64 string length (prevent DoS attacks)
            if len(image_data) > 50 * 1024 * 1024:  # 50MB limit for base64 string
                return Response({'error': 'Image data too large'}, status=status.HTTP_400_BAD_REQUEST)
                
            image_bytes = base64.b64decode(image_data)
            
            # Validate decoded image size
            if len(image_bytes) > 20 * 1024 * 1024:  # 20MB limit for decoded image
                return Response({'error': 'Image file too large'}, status=status.HTTP_400_BAD_REQUEST)
                
            image = Image.open(io.BytesIO(image_bytes))
            
            # Validate image dimensions
            if image.width > 10000 or image.height > 10000:
                return Response({'error': 'Image dimensions too large'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': 'Invalid image data'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate and extract selection coordinates
        try:
            sel_x = int(selection.get('x', 0))
            sel_y = int(selection.get('y', 0))
            sel_width = int(selection.get('width', 0))
            sel_height = int(selection.get('height', 0))
            
            # Validate selection bounds
            if sel_x < 0 or sel_y < 0 or sel_width <= 0 or sel_height <= 0:
                return Response({'error': 'Invalid selection coordinates: values must be positive'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Validate selection doesn't exceed image bounds
            if sel_x + sel_width > image.width or sel_y + sel_height > image.height:
                return Response({'error': 'Selection area exceeds image bounds'}, status=status.HTTP_400_BAD_REQUEST)
                
        except (ValueError, KeyError, TypeError) as e:
            return Response({'error': 'Invalid selection coordinates format'}, status=status.HTTP_400_BAD_REQUEST)
        
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
            # Note: DPI setting is metadata only, pixel dimensions determine actual resolution
            final_image.save(
                output,
                format='JPEG',
                quality=95,
                dpi=(300, 300)  # Metadata only - actual resolution determined by pixel dimensions
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