# AI Passport Photo Processing System - Setup Instructions

A comprehensive AI-powered passport photo processing system with support for multiple countries, featuring advanced face detection using YapaLab YOLO-face model and Finnish passport compliance.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Backend Setup (Django + AI Models)

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration (see Configuration section below)

# Run database migrations
python manage.py makemigrations
python manage.py migrate

# Load sample country data (includes Finland)
python manage.py shell
```

**In Django shell, run:**
```python
from passport_photo.models import Country

countries_data = [
    {'name': 'United States', 'code': 'US', 'photo_width': 600, 'photo_height': 600, 'face_height_ratio': 0.7},
    {'name': 'United Kingdom', 'code': 'UK', 'photo_width': 450, 'photo_height': 600, 'face_height_ratio': 0.7},
    {'name': 'Finland', 'code': 'FI', 'photo_width': 500, 'photo_height': 653, 'face_height_ratio': 0.724},
    {'name': 'Canada', 'code': 'CA', 'photo_width': 420, 'photo_height': 540, 'face_height_ratio': 0.7},
    {'name': 'Australia', 'code': 'AU', 'photo_width': 450, 'photo_height': 600, 'face_height_ratio': 0.7},
    {'name': 'Germany', 'code': 'DE', 'photo_width': 450, 'photo_height': 600, 'face_height_ratio': 0.7},
]

for country_data in countries_data:
    Country.objects.get_or_create(**country_data)

exit()
```

**Download YapaLab YOLO-face model:**
```bash
python -c "
import requests
import os
print('Downloading YapaLab YOLO-face model...')
model_url = 'https://github.com/YapaLab/yolo-face/releases/download/v0.0.0/yolov8n-face.pt'
response = requests.get(model_url, timeout=60)
os.makedirs('/tmp', exist_ok=True)
with open('/tmp/yolov8n-face.pt', 'wb') as f:
    f.write(response.content)
print('✓ YapaLab YOLO-face model downloaded to /tmp/yolov8n-face.pt')
print(f'✓ Model size: {len(response.content) / (1024*1024):.1f} MB')
"

# Start the Django development server
python manage.py runserver
```

**Backend will be available at: http://localhost:8000**

## Frontend Setup (React + TypeScript + Tailwind CSS)

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm start
   ```

**Frontend will be available at: http://localhost:3000**

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin

## 🎯 System Features

### Face Detection Methods (in priority order)
1. **YapaLab YOLO-face** - State-of-the-art face detection (primary)
2. **OpenCV Haar Cascade** - Reliable fallback method
3. **YOLO Person Detection** - Final fallback with head estimation

### Country Support
- **Finland** - Complete compliance with official requirements (500×653px, max 250KB)
- **USA** - Standard passport dimensions (600×600px)
- **UK** - UK passport specifications (450×600px)
- **Canada, Australia, Germany** - Standard international formats
- Easily extensible for additional countries

### AI Processing Pipeline
1. **Background Removal** - Using rembg AI model
2. **Face Detection** - Multi-method cascade for reliability
3. **Head Positioning** - Intelligent scaling and centering
4. **Image Enhancement** - Sharpness and contrast optimization
5. **Format Compliance** - Country-specific dimensions and file size limits

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True

# Database (optional - defaults to SQLite)
# DATABASE_URL=mysql://user:password@localhost/dbname

# File Upload Settings
MAX_FILE_SIZE=10485760  # 10MB in bytes
```

### Advanced Configuration (ai_tools/settings.py)

```python
PASSPORT_PHOTO_SETTINGS = {
    # Basic Settings
    'TEMP_STORAGE_HOURS': 24,
    'MAX_FILE_SIZE': 10485760,  # 10MB
    'ALLOWED_FORMATS': ['JPEG', 'JPG', 'PNG', 'WEBP'],
    'OUTPUT_QUALITY': 95,
    'OUTPUT_DPI': 300,
    
    # Background Removal Configuration
    'BACKGROUND_REMOVAL_MODEL': 'u2net-human-seg',  # Options: 'u2net' (default), 'birefnet-portrait' (best quality, slow), 'u2netp' (fast), 'u2net-human-seg' (optimized for humans)
    
    # Face Detection Configuration
    'YOLO_FACE_MODEL_PATH': '/tmp/yolov8n-face.pt',  # YapaLab model location
    
    # Head Expansion Ratios (adjustable for different results)
    'HEAD_EXPANSION': {
        'YOLO_FACE': 1.4,    # For YapaLab YOLO-face (1.2-1.5 recommended)
        'OPENCV_HAAR': 1.3,  # For OpenCV Haar Cascade
        'YOLO_PERSON': 0.28, # Head ratio for person detection
    },
    
    # Detection Confidence Thresholds
    'FACE_DETECTION_CONFIDENCE': {
        'YOLO_FACE': 0.3,    # Lower = more permissive
        'OPENCV_HAAR': 0.5,
        'YOLO_PERSON': 0.5,
    },
}
```

## 🔧 Fine-tuning Configuration

### Background Removal Models

The `BACKGROUND_REMOVAL_MODEL` setting controls which AI model is used for background removal:

- **u2net**: Default model, fast general-purpose background removal
- **u2net-human-seg**: Optimized for human segmentation, **good balance of speed and quality** (default)
- **u2netp**: Lighter/faster version of u2net
- **birefnet-portrait**: Best quality for portraits but very slow (30-60s per image)

**For passport photos, `u2net-human-seg` provides the best balance of speed and quality for human subjects.**

### Head Expansion Ratios

The `HEAD_EXPANSION.YOLO_FACE` setting controls how much the detected face area is expanded to include the full head:

- **1.2**: Tighter crop, focus on facial features
- **1.3**: Balanced, good for most use cases  
- **1.4**: More conservative, shows more forehead/hair (default)
- **1.5**: Maximum expansion, includes neck/shoulders

### Testing Different Settings

```python
# In Django shell (python manage.py shell)
from django.conf import settings

# Test background removal model
settings.PASSPORT_PHOTO_SETTINGS['BACKGROUND_REMOVAL_MODEL'] = 'u2net-human-seg'

# Test head expansion ratio
settings.PASSPORT_PHOTO_SETTINGS['HEAD_EXPANSION']['YOLO_FACE'] = 1.3

# Process your test images and compare results
```

## 🛠️ Model Management

### YapaLab YOLO-face Model

**Default Location**: `/tmp/yolov8n-face.pt`  
**Size**: ~6MB  
**Source**: https://github.com/YapaLab/yolo-face

**Alternative Models** (more accurate but larger):
- `yolov8s-face.pt` (~22MB)
- `yolov8m-face.pt` (~52MB)
- `yolov8l-face.pt` (~87MB)

### Updating Model Location

```python
# In settings.py
PASSPORT_PHOTO_SETTINGS = {
    'YOLO_FACE_MODEL_PATH': '/path/to/your/model.pt',
    # ... other settings
}
```

## 🇫🇮 Finnish Passport Photo Requirements

This system implements complete compliance with Finnish Police Office requirements:

- **Exact Dimensions**: 500×653 pixels (no deviation allowed)
- **Head Size**: 445-500 pixels from crown to chin
- **Top Margin**: 56-84 pixels above crown
- **Bottom Margin**: 96-124 pixels below chin
- **Max File Size**: 250 kilobytes
- **Format**: JPEG only
- **Background**: Plain white or light colored

### Finnish Processing Features

1. **Automatic File Size Optimization** - Reduces JPEG quality to meet 250KB limit
2. **Precise Head Positioning** - Centers head at optimal position for Finnish requirements
3. **Dimension Enforcement** - Outputs exactly 500×653 pixels
4. **Quality Balance** - Maintains visual quality while meeting size constraints

## 📊 API Endpoints

### Countries
- `GET /api/v1/countries/` - List all supported countries

### Photo Processing
- `POST /api/v1/upload/` - Upload photo for processing
- `GET /api/v1/job/{job_id}/` - Check processing status

### Example API Usage

```javascript
// Upload photo
const formData = new FormData();
formData.append('photo', file);
formData.append('country_id', countryId);

const response = await fetch('/api/v1/upload/', {
    method: 'POST',
    body: formData
});

const result = await response.json();
console.log('Job ID:', result.job_id);

// Check status
const statusResponse = await fetch(`/api/v1/job/${result.job_id}/`);
const status = await statusResponse.json();
```

## Features Included

### Backend (Django)
- ✅ Django 5.2.5 with Python 3.11
- ✅ MySQL 8.0 database configuration
- ✅ REST API with Django REST Framework
- ✅ File upload handling with validation
- ✅ Background removal using rembg
- ✅ Face detection using YOLO
- ✅ Asynchronous photo processing
- ✅ Country-specific photo specifications
- ✅ Temporary file cleanup (24-hour expiration)

### Frontend (React + TypeScript + Tailwind CSS)
- ✅ React 18 with TypeScript
- ✅ Tailwind CSS for styling
- ✅ Drag-and-drop file upload
- ✅ Country selection with specifications preview
- ✅ Real-time processing status updates
- ✅ Download functionality for processed photos
- ✅ Responsive design
- ✅ Error handling and user feedback

## Next Steps for Production

1. **Security:**
   - Set strong Django SECRET_KEY
   - Configure CORS properly
   - Add rate limiting
   - Implement user authentication (if needed)

2. **Performance:**
   - Set up Redis for caching
   - Use Celery for background tasks
   - Configure CDN for media files
   - Optimize AI models for production

3. **Deployment:**
   - Set up Docker containers
   - Configure reverse proxy (nginx)
   - Set up monitoring and logging
   - Configure backup strategy

4. **AI Models:**
   - Download and optimize YOLO face detection model
   - Fine-tune background removal for passport photos
   - Add image enhancement capabilities

## Troubleshooting

### Common Issues

1. **Head edges appear blurred/soft:**
   - **Cause**: Default u2net model can create soft edges around hair and face contours
   - **Solution**: Switch to `birefnet-portrait` model in settings:
     ```python
     PASSPORT_PHOTO_SETTINGS = {
         'BACKGROUND_REMOVAL_MODEL': 'birefnet-portrait',
         # ... other settings
     }
     ```
   - **Note**: First use will be slower as the model downloads (~973MB)

2. **AI Models not downloading:**
   - First run might be slow as models download automatically
   - Ensure internet connection for model downloads
   - BiRefNet models are large (up to 1GB) - allow time for download

3. **MySQL connection issues:**
   - Verify MySQL is running
   - Check database credentials in .env
   - Ensure database exists

4. **CORS issues:**
   - Check CORS_ALLOWED_ORIGINS in Django settings
   - Ensure frontend URL is included

5. **File upload issues:**
   - Check file size limits (10MB max)
   - Verify MEDIA_ROOT permissions
   - Ensure supported file formats (JPEG, PNG, WEBP)

6. **Background removal taking too long:**
   - BiRefNet models are more accurate but slower than u2net
   - For faster processing, use `u2netp` or default `u2net`
   - Consider reducing image size before processing for development