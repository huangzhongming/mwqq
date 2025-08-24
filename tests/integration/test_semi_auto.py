#!/usr/bin/env python3

import requests
import json
import base64

def test_semi_auto_workflow():
    base_url = "http://localhost:8000/api/v1"
    
    print("🚀 Testing Semi-Automatic Workflow")
    print("=" * 50)
    
    # Step 1: Test countries endpoint
    print("1️⃣ Testing countries endpoint...")
    response = requests.get(f"{base_url}/countries/")
    if response.status_code == 200:
        countries = response.json()
        print(f"✅ Found {len(countries)} countries")
        finland = None
        for country in countries:
            if country['code'] == 'FI':
                finland = country
                break
        if not finland:
            print("❌ Finland not found")
            return
        print(f"✅ Using Finland (ID: {finland['id']})")
    else:
        print(f"❌ Countries API failed: {response.status_code}")
        return
    
    # Step 2: Test prepare endpoint
    print("\n2️⃣ Testing prepare endpoint...")
    test_image_path = "tmp/test.png"
    
    try:
        with open(test_image_path, 'rb') as f:
            files = {'photo': f}
            data = {'country_id': finland['id']}
            response = requests.post(f"{base_url}/prepare/", files=files, data=data)
            
        if response.status_code == 200:
            prepare_result = response.json()
            print(f"✅ Prepare successful")
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
    print("\n3️⃣ Testing generate endpoint...")
    
    generate_data = {
        'image_data': prepare_result['image_data'],
        'selection': prepare_result['default_selection'],
        'country_id': finland['id']
    }
    
    try:
        response = requests.post(
            f"{base_url}/generate/",
            json=generate_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Generate successful")
            print(f"   - Job ID: {result['job_id']}")
            print(f"   - Status: {result['status']}")
            print(f"   - File size: {result['file_size']} bytes")
            print(f"   - Dimensions: {result['dimensions']}")
            
            # Step 4: Check job status
            print("\n4️⃣ Checking job status...")
            job_response = requests.get(f"{base_url}/job/{result['job_id']}/")
            if job_response.status_code == 200:
                job_data = job_response.json()
                print(f"✅ Job completed")
                print(f"   - Status: {job_data['status']}")
                if 'processed_photo_url' in job_data:
                    print(f"   - Photo URL: {job_data['processed_photo_url']}")
            else:
                print(f"❌ Job check failed: {job_response.status_code}")
        else:
            print(f"❌ Generate failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Generate error: {e}")
        return
    
    print("\n🎉 Semi-automatic workflow test completed successfully!")

if __name__ == "__main__":
    test_semi_auto_workflow()