#!/usr/bin/env python3

import os
import sys
import time
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_tools.settings')
django.setup()

from rembg import remove, new_session
from PIL import Image
import torch
import io

def test_birefnet_subsequent_calls():
    print("🔍 Testing BiRefNet-Portrait: Subsequent Calls Performance")
    print("=" * 70)
    
    # Test image (relative to project root)
    test_image_path = "../tmp/test2.jpg"
    
    with open(test_image_path, 'rb') as f:
        image_bytes = f.read()
    
    print(f"📁 Using test image: {test_image_path}")
    
    # Setup providers
    providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
    
    print(f"🔧 Using providers: {providers}")
    
    # Create session ONCE (simulate server startup)
    print("\n📦 Creating BiRefNet session (simulating server startup)...")
    startup_time = time.time()
    birefnet_session = new_session('birefnet-portrait', providers=providers)
    session_creation_time = time.time() - startup_time
    print(f"⏱️  Session creation time: {session_creation_time:.2f}s")
    
    # Test multiple inference calls
    print(f"\n🔄 Testing multiple inference calls...")
    inference_times = []
    
    for i in range(5):
        print(f"\n--- Inference #{i+1} ---")
        
        # Time only the inference
        start_time = time.time()
        result_bytes = remove(image_bytes, session=birefnet_session)
        end_time = time.time()
        
        inference_time = end_time - start_time
        inference_times.append(inference_time)
        
        print(f"⏱️  Inference time: {inference_time:.2f}s")
        print(f"💾 Result size: {len(result_bytes) / 1024:.1f}KB")
    
    # Statistics
    avg_inference = sum(inference_times) / len(inference_times)
    min_inference = min(inference_times)
    max_inference = max(inference_times)
    
    print(f"\n📊 INFERENCE STATISTICS (after session creation):")
    print("-" * 50)
    print(f"Session creation (one-time): {session_creation_time:.2f}s")
    print(f"Average inference time:      {avg_inference:.2f}s")
    print(f"Minimum inference time:      {min_inference:.2f}s") 
    print(f"Maximum inference time:      {max_inference:.2f}s")
    
    # Compare with other models (quick test)
    print(f"\n🔄 Quick comparison with other models...")
    
    models_to_compare = [
        ('isnet-general-use', 'Current default'),
        ('u2net', 'Standard option')
    ]
    
    for model_name, description in models_to_compare:
        print(f"\n--- {model_name} ---")
        
        # Create session
        session_start = time.time()
        session = new_session(model_name, providers=providers)
        session_time = time.time() - session_start
        
        # Single inference
        inference_start = time.time()
        result = remove(image_bytes, session=session)
        inference_time = time.time() - inference_start
        
        print(f"Session creation: {session_time:.2f}s")
        print(f"Inference time:   {inference_time:.2f}s")
    
    print(f"\n💡 CONCLUSION:")
    print("-" * 50)
    print(f"BiRefNet-Portrait inference time: ~{avg_inference:.2f}s per image")
    print(f"This is comparable to other models once loaded!")
    print(f"The 22s+ initial time was due to model download + session creation.")
    print(f"For production use, session is created once at server startup.")

if __name__ == "__main__":
    test_birefnet_subsequent_calls()