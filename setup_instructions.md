# AI Tools Platform - Setup Instructions

## Prerequisites

- Python 3.11+
- Node.js 16+ and npm
- MySQL 8.0
- Git

## Backend Setup (Django)

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Set up MySQL database:**
   ```sql
   CREATE DATABASE ai_tools_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

6. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

8. **Load sample countries data:**
   ```bash
   python manage.py shell
   ```
   Then run:
   ```python
   from passport_photo.models import Country
   
   countries_data = [
       {'name': 'United States', 'code': 'US', 'photo_width': 600, 'photo_height': 600, 'face_height_ratio': 0.7},
       {'name': 'United Kingdom', 'code': 'UK', 'photo_width': 450, 'photo_height': 600, 'face_height_ratio': 0.7},
       {'name': 'Canada', 'code': 'CA', 'photo_width': 420, 'photo_height': 540, 'face_height_ratio': 0.7},
       {'name': 'Australia', 'code': 'AU', 'photo_width': 450, 'photo_height': 600, 'face_height_ratio': 0.7},
       {'name': 'Germany', 'code': 'DE', 'photo_width': 450, 'photo_height': 600, 'face_height_ratio': 0.7},
       {'name': 'France', 'code': 'FR', 'photo_width': 450, 'photo_height': 600, 'face_height_ratio': 0.7},
   ]
   
   for country_data in countries_data:
       Country.objects.get_or_create(**country_data)
   
   exit()
   ```

9. **Start development server:**
   ```bash
   python manage.py runserver
   ```

Backend will be available at: http://localhost:8000

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

Frontend will be available at: http://localhost:3000

## API Endpoints

- `GET /api/v1/countries/` - List all countries
- `POST /api/v1/upload/` - Upload photo for processing
- `GET /api/v1/job/{job_id}/` - Get processing job status

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

1. **AI Models not downloading:**
   - First run might be slow as models download automatically
   - Ensure internet connection for model downloads

2. **MySQL connection issues:**
   - Verify MySQL is running
   - Check database credentials in .env
   - Ensure database exists

3. **CORS issues:**
   - Check CORS_ALLOWED_ORIGINS in Django settings
   - Ensure frontend URL is included

4. **File upload issues:**
   - Check file size limits (10MB max)
   - Verify MEDIA_ROOT permissions
   - Ensure supported file formats (JPEG, PNG, WEBP)