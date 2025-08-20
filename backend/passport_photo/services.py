import cv2
import numpy as np
from PIL import Image, ImageEnhance
from rembg import remove
from ultralytics import YOLO
import io
from django.core.files.base import ContentFile
from django.conf import settings

class PassportPhotoProcessor:
    def __init__(self):
        # Load YOLO model for face detection (using YOLOv8n for speed)
        try:
            self.face_model = YOLO('yolov8n-face.pt')
        except:
            # Fallback to standard YOLO if face model not available
            self.face_model = YOLO('yolov8n.pt')
    
    def remove_background(self, image_bytes):
        """Remove background from image using rembg"""
        try:
            # Remove background
            output = remove(image_bytes)
            return output
        except Exception as e:
            raise Exception(f"Background removal failed: {str(e)}")
    
    def detect_face(self, image):
        """Detect face using YOLO model"""
        try:
            # Convert PIL image to numpy array
            img_array = np.array(image)
            
            # Run inference
            results = self.face_model(img_array)
            
            faces = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        
                        # Filter by confidence
                        if confidence > 0.5:
                            faces.append({
                                'bbox': (int(x1), int(y1), int(x2), int(y2)),
                                'confidence': float(confidence)
                            })
            
            return faces
        except Exception as e:
            raise Exception(f"Face detection failed: {str(e)}")
    
    def calculate_optimal_scale_and_position(self, face_bbox, image_size, target_size, face_height_ratio, country_code=None):
        """Calculate optimal scaling and positioning for perfect head centering"""
        x1, y1, x2, y2 = face_bbox
        img_width, img_height = image_size
        target_width, target_height = target_size
        
        # Calculate face dimensions
        face_width = x2 - x1
        face_height = y2 - y1
        face_center_x = x1 + face_width / 2
        face_center_y = y1 + face_height / 2
        
        # Special handling for Finland's strict requirements
        if country_code == 'FI':
            return self._calculate_finnish_positioning(face_bbox, image_size, target_size)
        
        # Standard positioning for other countries
        target_face_height = target_height * face_height_ratio
        target_head_center_x = target_width / 2
        target_head_center_y = target_height * 0.35  # 35% from top
        
        # Calculate base scale from face height requirement
        base_scale = target_face_height / face_height
        
        # Calculate where face would be positioned with base scale
        scaled_face_center_x = face_center_x * base_scale
        scaled_face_center_y = face_center_y * base_scale
        scaled_img_width = img_width * base_scale
        scaled_img_height = img_height * base_scale
        
        # Calculate positioning offset to center the head
        offset_x = target_head_center_x - scaled_face_center_x
        offset_y = target_head_center_y - scaled_face_center_y
        
        # Check if the scaled image with optimal positioning fits in target
        final_left = offset_x
        final_top = offset_y
        final_right = offset_x + scaled_img_width
        final_bottom = offset_y + scaled_img_height
        
        # Adjust scale if image doesn't fit properly
        scale_adjustment = 1.0
        
        # If image extends beyond bounds significantly, adjust scale
        if final_right - final_left > target_width * 1.5 or final_bottom - final_top > target_height * 1.5:
            # Scale down to fit better
            width_scale = target_width * 1.2 / scaled_img_width
            height_scale = target_height * 1.2 / scaled_img_height
            scale_adjustment = min(width_scale, height_scale, 1.0)
        
        final_scale = base_scale * scale_adjustment
        
        return {
            'scale': final_scale,
            'target_head_center': (target_head_center_x, target_head_center_y),
            'face_center': (face_center_x, face_center_y)
        }
    
    def _calculate_finnish_positioning(self, face_bbox, image_size, target_size):
        """Calculate positioning specifically for Finnish passport requirements"""
        x1, y1, x2, y2 = face_bbox
        img_width, img_height = image_size
        target_width, target_height = target_size  # 500 x 653
        
        # Finnish specific requirements
        # Head size: 445-500 px (crown to chin), using upper range for better compliance
        # Top margin: 56-84 px (using optimal 70px)
        # Bottom margin: 96-124 px (using optimal 110px)
        
        face_width = x2 - x1
        face_height = y2 - y1
        face_center_x = x1 + face_width / 2
        face_center_y = y1 + face_height / 2
        
        # Target face height for Finland - use 485px (closer to max for better visibility)
        # The detected face is typically smaller than the full head, so we need to scale more
        target_face_height = 485  # Higher in the 445-500px range
        
        # Finnish positioning: center horizontally, optimal vertical placement
        target_head_center_x = target_width / 2  # 250px
        # Crown should be at ~70px from top, chin at ~555px from top
        # So face center should be at ~312.5px from top
        target_head_center_y = 70 + (target_face_height / 2)  # ~312.5px
        
        # Calculate scale based on face height - be more aggressive with scaling
        # YOLO face detection often underestimates the full head size
        base_scale = target_face_height / face_height
        
        # For Finnish requirements, we need to be less conservative
        # Remove the restrictive max_scale limits for better head size
        max_scale = min(
            (target_width * 1.2) / face_width,  # Allow wider faces
            (target_height * 1.0) / (face_height * 1.2)  # Less restrictive height limit
        )
        
        # Use the base scale more aggressively for Finnish compliance
        final_scale = min(base_scale * 1.15, max_scale)  # 15% boost for better head size
        
        return {
            'scale': final_scale,
            'target_head_center': (target_head_center_x, target_head_center_y),
            'face_center': (face_center_x, face_center_y)
        }
    
    def create_passport_photo(self, image_bytes, country_specs):
        """Process image to create passport photo with proper head centering and scaling"""
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Remove background
            no_bg_bytes = self.remove_background(image_bytes)
            no_bg_image = Image.open(io.BytesIO(no_bg_bytes))
            
            # Detect face
            faces = self.detect_face(image)
            
            if not faces:
                raise Exception("No face detected in the image")
            
            if len(faces) > 1:
                raise Exception("Multiple faces detected. Please upload a photo with only one person.")
            
            # Get the most confident face
            face = max(faces, key=lambda x: x['confidence'])
            face_bbox = face['bbox']
            
            # Calculate target dimensions
            target_width = country_specs['photo_width']
            target_height = country_specs['photo_height']
            face_height_ratio = country_specs['face_height_ratio']
            country_code = country_specs.get('country_code')
            
            # Calculate optimal scaling and positioning
            image_size = (no_bg_image.width, no_bg_image.height)
            target_size = (target_width, target_height)
            
            optimization = self.calculate_optimal_scale_and_position(
                face_bbox, image_size, target_size, face_height_ratio, country_code
            )
            
            scale = optimization['scale']
            target_head_center_x, target_head_center_y = optimization['target_head_center']
            face_center_x, face_center_y = optimization['face_center']
            
            # Get original image dimensions
            orig_width = no_bg_image.width
            orig_height = no_bg_image.height
            
            # Calculate scaled dimensions maintaining aspect ratio
            scaled_width = int(orig_width * scale)
            scaled_height = int(orig_height * scale)
            
            # Calculate where the face center will be after scaling
            scaled_face_center_x = face_center_x * scale
            scaled_face_center_y = face_center_y * scale
            
            # Create working image by resizing with proper scaling
            working_image = no_bg_image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
            
            # Recalculate scaled face center after resizing
            scaled_face_center_x = face_center_x * scale
            scaled_face_center_y = face_center_y * scale
            
            # Calculate where to position the image so the head is centered
            paste_x = int(target_head_center_x - scaled_face_center_x)
            paste_y = int(target_head_center_y - scaled_face_center_y)
            
            # Create final canvas
            final_image = Image.new('RGB', (target_width, target_height), 'white')
            
            # Smart cropping and positioning for perfect head centering
            if working_image.width <= target_width and working_image.height <= target_height:
                # Image fits entirely - simple paste
                if working_image.mode == 'RGBA':
                    final_image.paste(working_image, (paste_x, paste_y), mask=working_image.split()[3])
                else:
                    final_image.paste(working_image, (paste_x, paste_y))
            else:
                # Image is larger than canvas - need to crop intelligently
                # Calculate which part of the working image to use
                source_left = 0
                source_top = 0
                source_right = working_image.width
                source_bottom = working_image.height
                
                dest_left = paste_x
                dest_top = paste_y
                dest_right = paste_x + working_image.width
                dest_bottom = paste_y + working_image.height
                
                # Adjust source and destination if image extends beyond canvas
                if dest_left < 0:
                    source_left = -dest_left
                    dest_left = 0
                if dest_top < 0:
                    source_top = -dest_top
                    dest_top = 0
                if dest_right > target_width:
                    source_right = working_image.width - (dest_right - target_width)
                    dest_right = target_width
                if dest_bottom > target_height:
                    source_bottom = working_image.height - (dest_bottom - target_height)
                    dest_bottom = target_height
                
                # Crop the working image to fit the destination area
                if source_right > source_left and source_bottom > source_top:
                    cropped_image = working_image.crop((source_left, source_top, source_right, source_bottom))
                    
                    # Paste the cropped image
                    if cropped_image.mode == 'RGBA':
                        final_image.paste(cropped_image, (dest_left, dest_top), mask=cropped_image.split()[3])
                    else:
                        final_image.paste(cropped_image, (dest_left, dest_top))
            
            # Enhance image quality
            enhancer = ImageEnhance.Sharpness(final_image)
            final_image = enhancer.enhance(1.1)
            
            # Slight contrast enhancement for better photo quality
            contrast_enhancer = ImageEnhance.Contrast(final_image)
            final_image = contrast_enhancer.enhance(1.05)
            
            # Finnish-specific output requirements
            if country_code == 'FI':
                return self._create_finnish_output(final_image)
            
            # Convert to bytes for other countries
            output = io.BytesIO()
            final_image.save(
                output,
                format='JPEG',
                quality=settings.PASSPORT_PHOTO_SETTINGS['OUTPUT_QUALITY'],
                dpi=(settings.PASSPORT_PHOTO_SETTINGS['OUTPUT_DPI'], 
                     settings.PASSPORT_PHOTO_SETTINGS['OUTPUT_DPI'])
            )
            output.seek(0)
            
            return output.getvalue()
            
        except Exception as e:
            raise Exception(f"Photo processing failed: {str(e)}")
    
    def _create_finnish_output(self, image):
        """Create output specifically for Finnish passport requirements"""
        # Finnish requirements: exactly 500x653 pixels, max 250KB
        output = io.BytesIO()
        
        # Start with high quality and reduce if file size exceeds 250KB
        quality = 95
        while quality > 60:  # Don't go below reasonable quality
            output.seek(0)
            output.truncate()
            
            image.save(
                output,
                format='JPEG',
                quality=quality,
                optimize=True
            )
            
            file_size = output.tell()
            if file_size <= 250 * 1024:  # 250KB limit
                break
            
            quality -= 5
        
        output.seek(0)
        return output.getvalue()
    
    def validate_image(self, image_file):
        """Validate uploaded image"""
        # Check file size
        if image_file.size > settings.PASSPORT_PHOTO_SETTINGS['MAX_FILE_SIZE']:
            raise Exception("File size exceeds 10MB limit")
        
        try:
            # Check if it's a valid image
            image = Image.open(image_file)
            
            # Check format - PIL reports JPEG for both .jpg and .jpeg files
            allowed_formats = ['JPEG', 'PNG', 'WEBP']
            if image.format not in allowed_formats:
                raise Exception(f"Unsupported format. Allowed formats: JPEG, PNG, WEBP")
            
            # Check dimensions (minimum requirements)
            if image.width < 200 or image.height < 200:
                raise Exception("Image too small. Minimum 200x200 pixels required")
            
            return True
            
        except Exception as e:
            if "Unsupported format" in str(e) or "Image too small" in str(e):
                raise e
            raise Exception("Invalid image file")