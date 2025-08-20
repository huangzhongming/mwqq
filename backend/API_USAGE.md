# Passport Photo API Usage Guide

## 🚀 Quick Start

### 1. Start the Server

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source venv/bin/activate

# Start Django server
python manage.py runserver
```

**Server will be available at: http://localhost:8000**

---

## 📋 API Endpoints

### Get Available Countries

**GET** `/api/v1/countries/`

```bash
curl http://localhost:8000/api/v1/countries/
```

**Response:**
```json
[
  {
    "id": 7,
    "name": "Finland",
    "code": "FI",
    "photo_width": 500,
    "photo_height": 653,
    "face_height_ratio": 0.724
  },
  {
    "id": 1,
    "name": "United States", 
    "code": "US",
    "photo_width": 600,
    "photo_height": 600,
    "face_height_ratio": 0.7
  }
  // ... more countries
]
```

### Upload Photo for Processing

**POST** `/api/v1/upload/`

**Form Data:**
- `photo`: Image file (JPEG, PNG, WEBP)
- `country_id`: Country ID from countries endpoint

```bash
# Example: Upload photo for Finland passport
curl -X POST \
  -F "photo=@/path/to/your/photo.jpg" \
  -F "country_id=7" \
  http://localhost:8000/api/v1/upload/
```

**Response:**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "pending",
  "message": "Photo uploaded successfully. Processing started."
}
```

### Check Processing Status

**GET** `/api/v1/job/{job_id}/`

```bash
curl http://localhost:8000/api/v1/job/abc123-def456-ghi789/
```

**Response (Processing):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "processing",
  "message": "Your photo is being processed..."
}
```

**Response (Completed):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "completed",
  "result_url": "/media/processed/passport_abc123-def456-ghi789.jpg",
  "message": "Photo processed successfully!"
}
```

**Response (Failed):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "failed",
  "error": "No face detected in the image",
  "message": "Processing failed"
}
```

---

## 🖥️ Frontend Integration

### JavaScript Example

```javascript
// 1. Get available countries
async function getCountries() {
  const response = await fetch('/api/v1/countries/');
  return await response.json();
}

// 2. Upload photo
async function uploadPhoto(photoFile, countryId) {
  const formData = new FormData();
  formData.append('photo', photoFile);
  formData.append('country_id', countryId);
  
  const response = await fetch('/api/v1/upload/', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}

// 3. Check status and poll until complete
async function waitForProcessing(jobId) {
  while (true) {
    const response = await fetch(`/api/v1/job/${jobId}/`);
    const result = await response.json();
    
    if (result.status === 'completed') {
      return result;
    } else if (result.status === 'failed') {
      throw new Error(result.error);
    }
    
    // Wait 2 seconds before checking again
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}

// Complete workflow
async function processPassportPhoto(photoFile, countryId) {
  try {
    // Upload photo
    const uploadResult = await uploadPhoto(photoFile, countryId);
    console.log('Upload successful:', uploadResult.job_id);
    
    // Wait for processing
    const result = await waitForProcessing(uploadResult.job_id);
    console.log('Processing complete:', result.result_url);
    
    return result;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}
```

---

## 🔧 Troubleshooting

### Common Issues

1. **Request hangs indefinitely:**
   - Background removal models may be slow on first use
   - Try using a smaller test image first
   - Check server logs for initialization messages

2. **"No face detected" error:**
   - Ensure photo has a clear, visible face
   - Face should be well-lit and unobstructed
   - Try a different photo

3. **File upload fails:**
   - Check file size (max 10MB)
   - Supported formats: JPEG, PNG, WEBP
   - Ensure `country_id` is valid

4. **CORS errors (frontend):**
   - Server allows localhost:3000 by default
   - Update CORS settings if using different port

### Server Status Check

```bash
# Check if server is responding
curl -I http://localhost:8000/api/v1/countries/

# Should return: HTTP/1.1 200 OK
```

---

## 🎯 Example Workflow

```bash
# 1. Start server
source venv/bin/activate && python manage.py runserver

# 2. Get Finland country ID
curl http://localhost:8000/api/v1/countries/ | jq '.[] | select(.code=="FI")'

# 3. Upload photo
curl -X POST \
  -F "photo=@test_photo.jpg" \
  -F "country_id=7" \
  http://localhost:8000/api/v1/upload/

# 4. Check status (repeat until completed)
curl http://localhost:8000/api/v1/job/{JOB_ID}/

# 5. Download result
wget http://localhost:8000{RESULT_URL}
```

## 📁 File Locations

- **Uploaded photos**: `media/uploads/original/`
- **Processed photos**: `media/uploads/processed/`
- **Server logs**: Check terminal where `runserver` is running