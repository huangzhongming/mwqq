import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
from rembg import remove, new_session
from ultralytics import YOLO
import io
from django.core.files.base import ContentFile
from django.conf import settings

class PassportPhotoProcessor:
    def __init__(self):
        # Load YapaLab YOLO-face model for accurate face detection
        model_path = settings.PASSPORT_PHOTO_SETTINGS.get('YOLO_FACE_MODEL_PATH', '/tmp/yolov8n-face.pt')
        
        try:
            # Try YapaLab face model first (most accurate)
            self.yolo_face_model = YOLO(model_path)
            print(f"✓ Loaded YapaLab YOLOv8n-face model from {model_path}")
        except Exception as e:
            print(f"Failed to load YapaLab face model from {model_path}: {e}")
            try:
                # Fallback to standard YOLO
                self.yolo_face_model = YOLO('yolov8n.pt')
                print("✓ Loaded standard YOLOv8n model as fallback")
            except Exception as e2:
                print(f"Failed to load any YOLO model: {e2}")
                self.yolo_face_model = None
        
        # Lazy load background removal session (initialize on first use)
        self.bg_removal_session = None
        self._bg_model = settings.PASSPORT_PHOTO_SETTINGS.get('BACKGROUND_REMOVAL_MODEL', 'u2net')
        self._bg_session_initialized = False
    
    def _initialize_bg_session(self):
        """Initialize background removal session on first use with GPU acceleration"""
        if not self._bg_session_initialized:
            self._bg_session_initialized = True
            
            # Setup GPU providers for acceleration
            import torch
            providers = ['CPUExecutionProvider']
            if torch.cuda.is_available():
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                print(f"🎮 GPU detected: {torch.cuda.get_device_name(0)}")
            
            try:
                print(f"🔄 Initializing {self._bg_model} background removal model with providers: {providers}")
                self.bg_removal_session = new_session(self._bg_model, providers=providers)
                print(f"✓ Loaded {self._bg_model} background removal model with GPU acceleration")
            except Exception as e:
                print(f"⚠️ Failed to load {self._bg_model} model with GPU, falling back to CPU: {e}")
                try:
                    self.bg_removal_session = new_session(self._bg_model, providers=['CPUExecutionProvider'])
                    print(f"✓ Loaded {self._bg_model} background removal model (CPU fallback)")
                except Exception as e2:
                    print(f"⚠️ Failed to load {self._bg_model} model, using default u2net: {e2}")
                    self.bg_removal_session = None
    
    def remove_background(self, image_bytes):
        """Remove background from image using configured rembg model with GPU acceleration"""
        try:
            # Initialize session on first use (lazy loading)
            self._initialize_bg_session()
            
            # Use configured background removal model
            if self.bg_removal_session:
                # Use specific model session with GPU acceleration
                output = remove(image_bytes, session=self.bg_removal_session)
            else:
                # Use default u2net model with GPU if available
                import torch
                if torch.cuda.is_available():
                    providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                    try:
                        u2net_session = new_session('u2net', providers=providers)
                        output = remove(image_bytes, session=u2net_session)
                    except:
                        # Fallback to default if GPU session fails
                        output = remove(image_bytes)
                else:
                    output = remove(image_bytes)
            return output
        except Exception as e:
            raise Exception(f"Background removal failed: {str(e)}")
    
    def detect_face(self, image):
        """Detect face using best available method: YapaLab YOLO-face > OpenCV Haar > YOLO person"""
        try:
            # Ensure image is RGB
            if image.mode == 'RGBA':
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[3])
                image = rgb_image
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Try YapaLab YOLO-face first (most accurate for faces)
            if self.yolo_face_model:
                try:
                    faces = self._detect_face_yolo_face(image)
                    if faces:
                        return faces
                    print('YapaLab YOLO-face found no faces, trying OpenCV...')
                except Exception as e:
                    print(f'YapaLab YOLO-face failed: {e}, trying OpenCV...')
            
            # Fallback to OpenCV Haar Cascade
            faces = self._detect_face_opencv(image)
            if faces:
                return faces
            print('OpenCV found no faces, falling back to YOLO person detection...')
            
            # Final fallback to YOLO person detection
            return self._detect_face_yolo_fallback(image)
            
        except Exception as e:
            print(f'All face detection methods failed: {e}')
            raise Exception(f"Face detection failed: {str(e)}")
    
    def _detect_face_yolo_face(self, image):
        """Detect face using YapaLab YOLO-face model (most accurate)"""
        try:
            # Ensure image is RGB (YOLO expects 3 channels, not RGBA)
            if image.mode == 'RGBA':
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[3])
                image = rgb_image
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert PIL image to numpy array
            img_array = np.array(image)
            
            # Run YapaLab YOLO-face inference
            results = self.yolo_face_model(img_array)
            
            faces = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        
                        # YOLO-face should have high confidence for actual faces
                        min_confidence = settings.PASSPORT_PHOTO_SETTINGS.get('FACE_DETECTION_CONFIDENCE', {}).get('YOLO_FACE', 0.3)
                        if confidence > min_confidence:
                            face_width = x2 - x1
                            face_height = y2 - y1
                            aspect_ratio = face_width / face_height
                            
                            # Validate face dimensions
                            if 0.5 <= aspect_ratio <= 2.0:  # Reasonable face aspect ratio
                                img_area = image.width * image.height
                                face_area = face_width * face_height
                                area_ratio = face_area / img_area
                                
                                if 0.005 <= area_ratio <= 0.8:  # Face should be reasonable size
                                    faces.append({
                                        'bbox': (int(x1), int(y1), int(x2), int(y2)),
                                        'confidence': float(confidence),
                                        'method': 'yolo_face'
                                    })
            
            # Sort by confidence and return the best face
            if faces:
                faces.sort(key=lambda x: x['confidence'], reverse=True)
                return faces[:1]  # Return only the most confident face
            
            return []
            
        except Exception as e:
            raise Exception(f"YOLO-face detection failed: {str(e)}")
    
    def _detect_face_opencv(self, image):
        """Detect face using OpenCV Haar Cascade"""
        try:
            # Convert PIL image to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Use OpenCV Haar Cascade for face detection
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            # Detect faces with different parameters for better accuracy
            opencv_faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(50, 50),  # Minimum face size
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            faces = []
            for (x, y, w, h) in opencv_faces:
                # Convert to our format
                x1, y1, x2, y2 = x, y, x + w, y + h
                
                # Calculate confidence equivalent (OpenCV doesn't provide confidence)
                face_area = w * h
                img_area = image.width * image.height
                area_ratio = face_area / img_area
                
                # Assign confidence based on face size and aspect ratio
                aspect_ratio = w / h
                confidence = min(0.95, 0.5 + area_ratio * 2)  # Higher confidence for larger faces
                
                # Validate face dimensions
                if 0.7 <= aspect_ratio <= 1.4:  # Face should be roughly square to slightly tall
                    if 0.01 <= area_ratio <= 0.5:  # Face should be reasonable size
                        faces.append({
                            'bbox': (int(x1), int(y1), int(x2), int(y2)),
                            'confidence': float(confidence),
                            'method': 'opencv_haar'
                        })
            
            # Filter out false positives - select the uppermost face (head should be at top)
            if len(faces) > 1:
                print(f'OpenCV found {len(faces)} faces, selecting the uppermost one...')
                faces.sort(key=lambda x: (x['bbox'][1], -x['confidence']))
                faces = faces[:1]  # Keep only the top face
            
            faces.sort(key=lambda x: x['confidence'], reverse=True)
            return faces
            
        except Exception as e:
            raise Exception(f"OpenCV face detection failed: {str(e)}")
    
    def _detect_face_yolo_fallback(self, image):
        """Fallback YOLO person detection with head estimation"""
        try:
            # Convert PIL image to numpy array
            img_array = np.array(image)
            
            # Run YOLO inference (using the fallback model)
            results = self.yolo_face_model(img_array)
            
            faces = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        
                        if confidence > 0.5:
                            face_width = x2 - x1
                            face_height = y2 - y1
                            aspect_ratio = face_width / face_height
                            
                            if 0.3 <= aspect_ratio <= 2.0:
                                img_area = image.width * image.height
                                face_area = face_width * face_height
                                area_ratio = face_area / img_area
                                
                                if area_ratio <= 0.8:
                                    faces.append({
                                        'bbox': (int(x1), int(y1), int(x2), int(y2)),
                                        'confidence': float(confidence),
                                        'method': 'yolo_person'
                                    })
            
            return faces
        except Exception as e:
            raise Exception(f"Face detection failed: {str(e)}")
    
    def calculate_optimal_scale_and_position(self, face_bbox, image_size, target_size, face_height_ratio, country_code=None, detection_method='opencv_haar'):
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
            return self._calculate_finnish_positioning(face_bbox, image_size, target_size, detection_method)
        
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
    
    def _calculate_finnish_positioning(self, face_bbox, image_size, target_size, detection_method='opencv_haar'):
        """Calculate positioning specifically for Finnish passport requirements"""
        x1, y1, x2, y2 = face_bbox
        img_width, img_height = image_size
        target_width, target_height = target_size  # 500 x 653
        
        # Finnish specific requirements
        # Head size: 445-500 px (crown to chin), using upper range for better compliance
        # Top margin: 56-84 px (using optimal 70px)
        # Bottom margin: 96-124 px (using optimal 110px)
        
        if detection_method == 'yolo_face':
            # YapaLab YOLO-face provides very precise face detection
            # Need to expand significantly to include full head for passport photos
            detected_width = x2 - x1
            detected_height = y2 - y1
            
            # Expand face detection to include full head (hair, forehead, chin, neck)
            # YOLO-face detects just facial features, so need more expansion
            head_expansion = settings.PASSPORT_PHOTO_SETTINGS.get('HEAD_EXPANSION', {}).get('YOLO_FACE', 1.4)
            face_width = detected_width * head_expansion
            face_height = detected_height * head_expansion
            
            # Center the expanded area on the detected face
            face_center_x = x1 + detected_width / 2
            face_center_y = y1 + detected_height / 2
            
        elif detection_method == 'opencv_haar':
            # OpenCV Haar Cascade provides accurate face detection
            # Use the detected face area directly with some expansion for full head
            detected_width = x2 - x1
            detected_height = y2 - y1
            
            # Expand face detection to include full head (hair, forehead, chin)
            # Haar cascade typically detects just the core face features
            head_expansion = settings.PASSPORT_PHOTO_SETTINGS.get('HEAD_EXPANSION', {}).get('OPENCV_HAAR', 1.3)
            face_width = detected_width * head_expansion
            face_height = detected_height * head_expansion
            
            # Center the expanded area on the detected face
            face_center_x = x1 + detected_width / 2
            face_center_y = y1 + detected_height / 2
            
        else:
            # YOLO person detection - estimate head area from full person
            person_width = x2 - x1
            person_height = y2 - y1
            
            # Estimate head area (typically top 25-30% of person detection)
            head_height_ratio = settings.PASSPORT_PHOTO_SETTINGS.get('HEAD_EXPANSION', {}).get('YOLO_PERSON', 0.28)
            estimated_head_height = person_height * head_height_ratio
            
            head_width_ratio = 0.75
            estimated_head_width = person_width * head_width_ratio
            
            # Position head in upper portion of person detection
            head_top = y1 + (person_height * 0.05)
            head_left = x1 + (person_width - estimated_head_width) / 2
            
            face_width = estimated_head_width
            face_height = estimated_head_height
            face_center_x = head_left + face_width / 2
            face_center_y = head_top + face_height / 2
        
        # Target face height for Finland - use near maximum for passport photo compliance
        # For passport photos, head should be very prominent
        target_face_height = 490  # Near maximum 500px for better head visibility
        
        # Finnish positioning: center horizontally, position for head-focused framing
        target_head_center_x = target_width / 2  # 250px
        # Position head higher in frame to minimize body visibility
        # Crown at ~60px from top, chin at ~550px from top
        target_head_center_y = 60 + (target_face_height / 2)  # ~305px - higher positioning
        
        # Calculate scale based on face height - be more aggressive with scaling
        # YOLO face detection often underestimates the full head size
        base_scale = target_face_height / face_height
        
        # For Finnish requirements, we need to be less conservative
        # Remove the restrictive max_scale limits for better head size
        max_scale = min(
            (target_width * 1.2) / face_width,  # Allow wider faces
            (target_height * 1.0) / (face_height * 1.2)  # Less restrictive height limit
        )
        
        # Use appropriate scale for estimated head area
        # Since we now have better head estimation, less aggressive scaling needed
        final_scale = min(base_scale * 1.2, max_scale)  # 20% boost for proper head size
        
        return {
            'scale': final_scale,
            'target_head_center': (target_head_center_x, target_head_center_y),
            'face_center': (face_center_x, face_center_y)
        }
    
    def create_passport_photo(self, image_bytes, country_specs):
        """Process image to create passport photo with proper head centering and scaling"""
        try:
            # Load and preprocess image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Handle EXIF orientation (important for camera photos)
            image = ImageOps.exif_transpose(image)
            
            # Handle large images - resize if too big for performance
            max_dimension = 3000  # Max width or height
            if max(image.size) > max_dimension:
                ratio = max_dimension / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                print(f"📏 Resized large image to {new_size[0]}×{new_size[1]} for processing")
            
            # Convert to RGB if needed (handle various formats)
            if image.mode in ('RGBA', 'LA'):
                # Create white background for transparent images
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    rgb_image.paste(image, mask=image.split()[3])
                else:  # LA mode
                    rgb_image.paste(image, mask=image.split()[1])
                image = rgb_image
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert back to bytes for background removal
            processed_bytes = io.BytesIO()
            image.save(processed_bytes, format='JPEG', quality=95)
            processed_bytes.seek(0)
            
            # Remove background
            no_bg_bytes = self.remove_background(processed_bytes.getvalue())
            no_bg_image = Image.open(io.BytesIO(no_bg_bytes))
            
            # Detect face on the background-removed image (properly oriented)
            faces = self.detect_face(no_bg_image)
            
            if not faces:
                raise Exception("No face detected in the image")
            
            if len(faces) > 1:
                raise Exception("Multiple faces detected. Please upload a photo with only one person.")
            
            # Get the most confident face
            face = max(faces, key=lambda x: x['confidence'])
            face_bbox = face['bbox']
            detection_method = face.get('method', 'opencv_haar')
            
            # Calculate target dimensions
            target_width = country_specs['photo_width']
            target_height = country_specs['photo_height']
            face_height_ratio = country_specs['face_height_ratio']
            country_code = country_specs.get('country_code')
            
            # Calculate optimal scaling and positioning
            image_size = (no_bg_image.width, no_bg_image.height)
            target_size = (target_width, target_height)
            
            optimization = self.calculate_optimal_scale_and_position(
                face_bbox, image_size, target_size, face_height_ratio, country_code, detection_method
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
            
            # Check format - PIL reports various formats including MPO for Sony cameras
            allowed_formats = ['JPEG', 'PNG', 'WEBP', 'MPO']
            if image.format not in allowed_formats:
                raise Exception(f"Unsupported format '{image.format}'. Allowed formats: JPEG, PNG, WEBP, MPO (Sony cameras)")
            
            # Check dimensions (minimum requirements)
            if image.width < 200 or image.height < 200:
                raise Exception("Image too small. Minimum 200x200 pixels required")
            
            return True
            
        except Exception as e:
            if "Unsupported format" in str(e) or "Image too small" in str(e):
                raise e
            raise Exception("Invalid image file")