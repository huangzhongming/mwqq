#!/usr/bin/env python3

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_tools.settings')
django.setup()

from passport_photo.services import PassportPhotoProcessor
from PIL import Image, ImageDraw
import requests
import io

def test_face_detection_with_debug():
    print("🔍 Testing Face Detection with Debug Visualization")
    print("=" * 60)
    
    # Test image path (absolute, resolved relative to this script)
    test_image_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp", "test2.jpg"))
    
    if not os.path.exists(test_image_path):
        print(f"❌ Test image not found: {test_image_path}")
        return
    
    print(f"📁 Using test image: {test_image_path}")
    
    # Initialize processor
    processor = PassportPhotoProcessor()
    
    # Load original image
    with open(test_image_path, 'rb') as f:
        image_bytes = f.read()
    
    original_image = Image.open(test_image_path)
    print(f"📐 Original image size: {original_image.size}")
    
    # Step 1: Remove background
    print("\n1️⃣ Removing background...")
    try:
        no_bg_bytes = processor.remove_background(image_bytes)
        no_bg_image = Image.open(io.BytesIO(no_bg_bytes))
        print(f"✅ Background removed successfully")
        print(f"📐 Background-removed image size: {no_bg_image.size}")
        print(f"🎨 Image mode: {no_bg_image.mode}")
    except Exception as e:
        print(f"❌ Background removal failed: {e}")
        return
    
    # Step 2: Detect faces
    print("\n2️⃣ Detecting faces...")
    try:
        faces = processor.detect_face(no_bg_image)
        print(f"✅ Face detection completed")
        print(f"👥 Number of faces detected: {len(faces)}")
        
        if faces:
            for i, face in enumerate(faces):
                print(f"   Face {i+1}:")
                print(f"     - Confidence: {face['confidence']:.3f}")
                print(f"     - BBox: {face['bbox']}")
                print(f"     - Method: {face['method']}")
        else:
            print("❌ No faces detected!")
            
    except Exception as e:
        print(f"❌ Face detection failed: {e}")
        return
    
    # Step 3: Create debug visualization
    print("\n3️⃣ Creating debug visualization...")
    
    # Create a copy of the background-removed image for drawing
    debug_image = no_bg_image.copy()
    if debug_image.mode == 'RGBA':
        # Convert to RGB for drawing
        rgb_image = Image.new('RGB', debug_image.size, (255, 255, 255))
        rgb_image.paste(debug_image, mask=debug_image.split()[3])
        debug_image = rgb_image
    
    draw = ImageDraw.Draw(debug_image)
    
    # Draw face bounding boxes
    colors = ['red', 'blue', 'green', 'yellow', 'purple']
    for i, face in enumerate(faces):
        x1, y1, x2, y2 = face['bbox']
        color = colors[i % len(colors)]
        
        # Draw rectangle
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        
        # Draw confidence text
        text = f"{face['method']}: {face['confidence']:.2f}"
        draw.text((x1, y1-20), text, fill=color)
    
    # Save debug image
    debug_output_path = "../tmp/debug_face_detection.jpg"
    debug_image.save(debug_output_path, "JPEG", quality=95)
    print(f"💾 Debug image saved to: {debug_output_path}")
    
    # Step 4: Test the API endpoint
    print("\n4️⃣ Testing /prepare/ API endpoint...")
    
    try:
        # Test with Finland (country_id=3)
        with open(test_image_path, 'rb') as f:
            files = {'photo': f}
            data = {'country_id': 3}  # Finland
            response = requests.post('http://localhost:8000/api/v1/prepare/', files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API /prepare/ successful")
            print(f"   - Face bbox: {result['face_bbox']}")
            print(f"   - Default selection: {result['default_selection']}")
            print(f"   - Image dimensions: {result['image_dimensions']}")
            print(f"   - Target dimensions: {result['target_dimensions']}")
            
            # Draw the default selection rectangle on a separate debug image
            api_debug_image = no_bg_image.copy()
            if api_debug_image.mode == 'RGBA':
                rgb_image = Image.new('RGB', api_debug_image.size, (255, 255, 255))
                rgb_image.paste(api_debug_image, mask=api_debug_image.split()[3])
                api_debug_image = rgb_image
            
            draw = ImageDraw.Draw(api_debug_image)
            
            # Draw face bbox in red
            face_bbox = result['face_bbox']
            draw.rectangle(face_bbox, outline='red', width=2)
            draw.text((face_bbox[0], face_bbox[1]-20), 'Face Detection', fill='red')
            
            # Draw default selection in blue
            selection = result['default_selection']
            sel_coords = [
                selection['x'], 
                selection['y'], 
                selection['x'] + selection['width'], 
                selection['y'] + selection['height']
            ]
            draw.rectangle(sel_coords, outline='blue', width=3)
            draw.text((selection['x'], selection['y']-20), 'Default Selection', fill='blue')
            
            # Save API debug image
            api_debug_path = "../tmp/debug_api_selection.jpg"
            api_debug_image.save(api_debug_path, "JPEG", quality=95)
            print(f"💾 API debug image saved to: {api_debug_path}")
            
        else:
            print(f"❌ API /prepare/ failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ API test failed: {e}")
    
    print("\n🎉 Face detection debug test completed!")
    print(f"📂 Check debug images in ../tmp/")

if __name__ == "__main__":
    test_face_detection_with_debug()