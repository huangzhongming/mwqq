#!/usr/bin/env python3

import os
import sys
import time
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_tools.settings')
django.setup()

from passport_photo.services import PassportPhotoProcessor
from rembg import remove, new_session
from PIL import Image
import torch

def test_rembg_performance():
    print("🔍 Testing rembg Background Removal Performance")
    print("=" * 60)
    
    # Check GPU availability
    print(f"🖥️  CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"🎮 GPU Count: {torch.cuda.device_count()}")
        print(f"🎯 Current GPU: {torch.cuda.get_device_name(0)}")
    
    # Test image (relative to project root)
    test_image_path = "../tmp/test2.jpg"
    
    if not os.path.exists(test_image_path):
        print(f"❌ Test image not found: {test_image_path}")
        return
    
    print(f"📁 Using test image: {test_image_path}")
    
    # Load image
    with open(test_image_path, 'rb') as f:
        image_bytes = f.read()
    
    original_image = Image.open(test_image_path)
    print(f"📐 Original image size: {original_image.size}")
    
    # Test 1: Current processor (default)
    print("\n1️⃣ Testing current PassportPhotoProcessor...")
    processor = PassportPhotoProcessor()
    
    start_time = time.time()
    try:
        no_bg_bytes = processor.remove_background(image_bytes)
        end_time = time.time()
        print(f"✅ Current method: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"❌ Current method failed: {e}")
        return
    
    # Test 2: Default rembg (CPU)
    print("\n2️⃣ Testing default rembg (CPU)...")
    start_time = time.time()
    try:
        cpu_result = remove(image_bytes)
        end_time = time.time()
        print(f"✅ Default rembg (CPU): {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"❌ Default rembg failed: {e}")
    
    # Test 3: Try GPU-enabled session (if available)
    print("\n3️⃣ Testing rembg with potential GPU acceleration...")
    
    # Try different providers that might support GPU
    providers = ['CPUExecutionProvider']
    if torch.cuda.is_available():
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
    
    print(f"🔧 Available providers: {providers}")
    
    try:
        # Create session with specific providers
        start_time = time.time()
        session = new_session('u2net', providers=providers)
        gpu_result = remove(image_bytes, session=session)
        end_time = time.time()
        print(f"✅ rembg with providers {providers}: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"❌ GPU rembg failed: {e}")
    
    # Test 4: Test isnet-general-use model (current config)
    print("\n4️⃣ Testing isnet-general-use model...")
    start_time = time.time()
    try:
        isnet_session = new_session('isnet-general-use', providers=providers)
        isnet_result = remove(image_bytes, session=isnet_session)
        end_time = time.time()
        print(f"✅ isnet-general-use: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"❌ isnet-general-use failed: {e}")
    
    print("\n🎉 Performance test completed!")
    print("\n💡 Tips for GPU acceleration:")
    print("   - Ensure onnxruntime-gpu is installed")
    print("   - Use providers=['CUDAExecutionProvider', 'CPUExecutionProvider']")
    print("   - Consider birefnet-portrait for best quality (if GPU available)")

if __name__ == "__main__":
    test_rembg_performance()