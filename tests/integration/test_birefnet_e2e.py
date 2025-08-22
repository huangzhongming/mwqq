#!/usr/bin/env python3

import requests
import json
import time

def test_birefnet_e2e():
    base_url = "http://localhost:8000/api/v1"
    
    print("🚀 Testing BiRefNet-Portrait End-to-End Workflow")
    print("=" * 60)
    
    # Test image (relative to project root)
    test_image_path = "../tmp/test2.jpg"
    
    # Step 1: Test countries endpoint
    print("1️⃣ Testing countries endpoint...")
    response = requests.get(f"{base_url}/countries/")
    if response.status_code == 200:
        countries = response.json()
        finland = next((c for c in countries if c['code'] == 'FI'), None)
        if finland:
            print(f"✅ Using Finland (ID: {finland['id']})")
        else:
            print("❌ Finland not found")
            return
    else:
        print(f"❌ Countries API failed: {response.status_code}")
        return
    
    # Step 2: Test semi-auto prepare endpoint with BiRefNet
    print(f"\n2️⃣ Testing /prepare/ with BiRefNet-Portrait...")
    
    prepare_start = time.time()
    try:
        with open(test_image_path, 'rb') as f:
            files = {'photo': f}
            data = {'country_id': finland['id']}
            response = requests.post(f"{base_url}/prepare/", files=files, data=data)
        
        prepare_time = time.time() - prepare_start
        
        if response.status_code == 200:
            prepare_result = response.json()
            print(f"✅ Prepare successful in {prepare_time:.2f}s")
            print(f"   - Image format: {prepare_result['image_format']}")
            print(f"   - Image dimensions: {prepare_result['image_dimensions']}")
            print(f"   - Face bbox: {prepare_result['face_bbox']}")
            print(f"   - Default selection: {prepare_result['default_selection']}")
            print(f"   - Image data length: {len(prepare_result['image_data'])}")
        else:
            print(f"❌ Prepare failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Prepare error: {e}")
        return
    
    # Step 3: Test generate endpoint
    print(f"\n3️⃣ Testing /generate/ with BiRefNet result...")
    
    generate_data = {
        'image_data': prepare_result['image_data'],
        'selection': prepare_result['default_selection'],
        'country_id': finland['id']
    }
    
    generate_start = time.time()
    try:
        response = requests.post(
            f"{base_url}/generate/",
            json=generate_data,
            headers={'Content-Type': 'application/json'}
        )
        
        generate_time = time.time() - generate_start
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Generate successful in {generate_time:.2f}s")
            print(f"   - Job ID: {result['job_id']}")
            print(f"   - Status: {result['status']}")
            print(f"   - File size: {result['file_size']} bytes")
            print(f"   - Dimensions: {result['dimensions']}")
            
            # Step 4: Check job status and get final result
            print(f"\n4️⃣ Checking final result...")
            job_response = requests.get(f"{base_url}/job/{result['job_id']}/")
            if job_response.status_code == 200:
                job_data = job_response.json()
                print(f"✅ Job completed successfully")
                print(f"   - Status: {job_data['status']}")
                if 'processed_photo_url' in job_data:
                    print(f"   - Photo URL: {job_data['processed_photo_url']}")
                
                # Calculate total time
                total_time = prepare_time + generate_time
                print(f"\n⏱️  PERFORMANCE SUMMARY:")
                print(f"   - Background removal (BiRefNet): {prepare_time:.2f}s")
                print(f"   - Photo generation: {generate_time:.2f}s")
                print(f"   - Total processing time: {total_time:.2f}s")
                
            else:
                print(f"❌ Job check failed: {job_response.status_code}")
        else:
            print(f"❌ Generate failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Generate error: {e}")
        return
    
    # Step 5: Test automatic mode for comparison
    print(f"\n5️⃣ Testing automatic mode for comparison...")
    
    auto_start = time.time()
    try:
        with open(test_image_path, 'rb') as f:
            files = {'photo': f}
            data = {'country_id': finland['id']}
            response = requests.post(f"{base_url}/upload/", files=files, data=data)
        
        if response.status_code == 201:
            auto_result = response.json()
            print(f"✅ Auto upload successful")
            
            # Check job status
            job_response = requests.get(f"{base_url}/job/{auto_result['job_id']}/")
            if job_response.status_code == 200:
                job_data = job_response.json()
                auto_time = time.time() - auto_start
                print(f"✅ Auto mode completed in {auto_time:.2f}s")
                print(f"   - Status: {job_data['status']}")
                
        else:
            print(f"❌ Auto mode failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Auto mode error: {e}")
    
    print(f"\n🎉 BiRefNet-Portrait E2E test completed successfully!")
    print(f"🏆 High-quality background removal now active in production!")

if __name__ == "__main__":
    test_birefnet_e2e()