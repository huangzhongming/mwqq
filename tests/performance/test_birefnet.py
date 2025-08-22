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

def test_birefnet_performance():
    print("🔍 Testing BiRefNet-Portrait Background Removal")
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
    
    # Setup providers
    providers = ['CPUExecutionProvider']
    if torch.cuda.is_available():
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
    
    print(f"🔧 Using providers: {providers}")
    
    # Test models in order of speed (fastest to slowest)
    models_to_test = [
        ('u2net', 'Fast, good quality'),
        ('isnet-general-use', 'Current default, very good quality'),
        ('birefnet-portrait', 'Best quality, slower - testing for production'),
        ('u2netp', 'Fastest, lower quality'),
    ]
    
    results = []
    
    for model_name, description in models_to_test:
        print(f"\n{'='*20} Testing {model_name} {'='*20}")
        print(f"📝 Description: {description}")
        
        try:
            # Test performance
            start_time = time.time()
            session = new_session(model_name, providers=providers)
            setup_time = time.time()
            
            result_bytes = remove(image_bytes, session=session)
            process_time = time.time()
            
            # Convert result to image for quality assessment
            result_image = Image.open(io.BytesIO(result_bytes))
            
            setup_duration = setup_time - start_time
            process_duration = process_time - setup_time
            total_duration = process_time - start_time
            
            print(f"⏱️  Setup time: {setup_duration:.2f}s")
            print(f"⏱️  Process time: {process_duration:.2f}s")
            print(f"⏱️  Total time: {total_duration:.2f}s")
            print(f"📐 Result size: {result_image.size}")
            print(f"🎨 Result mode: {result_image.mode}")
            print(f"💾 Result size: {len(result_bytes) / 1024:.1f}KB")
            
            # Save result for visual inspection
            output_path = f"../tmp/test_bg_removal_{model_name}.png"
            result_image.save(output_path, "PNG")
            print(f"💾 Saved result: {output_path}")
            
            results.append({
                'model': model_name,
                'description': description,
                'setup_time': setup_duration,
                'process_time': process_duration,
                'total_time': total_duration,
                'file_size': len(result_bytes),
                'success': True
            })
            
            print(f"✅ {model_name}: SUCCESS")
            
        except Exception as e:
            print(f"❌ {model_name}: FAILED - {e}")
            results.append({
                'model': model_name,
                'description': description,
                'success': False,
                'error': str(e)
            })
    
    # Performance summary
    print(f"\n{'='*60}")
    print("📊 PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    
    successful_results = [r for r in results if r['success']]
    
    if successful_results:
        # Sort by total time
        successful_results.sort(key=lambda x: x['total_time'])
        
        print(f"{'Model':<20} {'Setup':<8} {'Process':<8} {'Total':<8} {'Size':<8} {'Quality'}")
        print("-" * 70)
        
        for result in successful_results:
            model = result['model']
            setup = f"{result['setup_time']:.2f}s"
            process = f"{result['process_time']:.2f}s"
            total = f"{result['total_time']:.2f}s"
            size = f"{result['file_size']/1024:.0f}KB"
            
            # Quality rating based on model
            if 'birefnet' in model:
                quality = "🌟🌟🌟🌟🌟"
            elif 'isnet' in model:
                quality = "🌟🌟🌟🌟"
            elif model == 'u2net':
                quality = "🌟🌟🌟"
            else:
                quality = "🌟🌟"
            
            print(f"{model:<20} {setup:<8} {process:<8} {total:<8} {size:<8} {quality}")
    
    # Recommendation
    print(f"\n💡 RECOMMENDATIONS:")
    
    birefnet_result = next((r for r in successful_results if r['model'] == 'birefnet-portrait'), None)
    isnet_result = next((r for r in successful_results if r['model'] == 'isnet-general-use'), None)
    
    if birefnet_result and isnet_result:
        speed_diff = birefnet_result['total_time'] - isnet_result['total_time']
        speed_increase = (speed_diff / isnet_result['total_time']) * 100
        
        print(f"📈 BiRefNet-Portrait is {speed_increase:.1f}% slower than isnet-general-use")
        print(f"⏱️  Time difference: +{speed_diff:.2f} seconds")
        
        if birefnet_result['total_time'] < 5.0:  # Less than 5 seconds
            print(f"✅ RECOMMENDED: Switch to birefnet-portrait for best quality")
            print(f"   - Excellent quality for passport photos")
            print(f"   - Acceptable processing time ({birefnet_result['total_time']:.2f}s)")
        elif birefnet_result['total_time'] < 8.0:  # Less than 8 seconds
            print(f"⚠️  CONSIDER: birefnet-portrait trade-off")
            print(f"   - Best quality but slower ({birefnet_result['total_time']:.2f}s)")
            print(f"   - Good for premium service or batch processing")
        else:
            print(f"❌ NOT RECOMMENDED: birefnet-portrait too slow")
            print(f"   - Processing time too long ({birefnet_result['total_time']:.2f}s)")
            print(f"   - Stick with isnet-general-use")
    
    print(f"\n🎉 Testing completed! Check output images in ../tmp/")

if __name__ == "__main__":
    test_birefnet_performance()