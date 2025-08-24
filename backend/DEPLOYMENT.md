# Passport Photo Service - Deployment Guide

## Requirements

### GPU-Accelerated Deployment (Recommended)

For optimal performance with GPU acceleration:

```bash
# Install GPU dependencies first
pip install onnxruntime-gpu torch torchvision

# Install remaining requirements
pip install -r requirements.txt

# Alternative: Install all at once (may show dependency warnings but works)
pip install -r requirements.txt
```

**Note**: You may see a dependency warning about `onnxruntime` not being installed. This is expected since `onnxruntime-gpu` provides the same functionality and the system will work correctly.

**Prerequisites:**
- NVIDIA GPU with CUDA support
- CUDA Toolkit 11.8 or later
- cuDNN 8.6 or later

**Performance:**
- Background removal: ~2.2s per image
- Best quality with BiRefNet-Portrait model
- Recommended for production environments

### CPU-Only Deployment

For environments without GPU support:

```bash
pip install -r requirements-cpu.txt
```

**Performance:**
- Background removal: ~4-6s per image
- Good quality with automatic CPU fallback
- Suitable for development or low-volume environments

## GPU vs CPU Performance

| Feature | GPU (RTX 3090) | CPU Only |
|---------|----------------|-----------|
| Background Removal | ~2.2s | ~4-6s |
| Model Loading | ~2.6s (one-time) | ~1s (one-time) |
| Quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Memory Usage | ~8GB VRAM | ~4GB RAM |

## Configuration

The system automatically detects GPU availability and falls back to CPU if needed:

- **GPU Available**: Uses CUDAExecutionProvider + CPUExecutionProvider
- **CPU Only**: Uses CPUExecutionProvider only

## Models Used

### Background Removal
- **Primary**: BiRefNet-Portrait (best quality for portraits)
- **Size**: ~973MB download (one-time)
- **Optimization**: GPU-accelerated ONNX runtime

### Face Detection  
- **Primary**: YapaLab YOLO-face model
- **Fallback**: OpenCV Haar Cascade → YOLO person detection
- **Size**: ~6MB download (one-time)

## Deployment Notes

1. **First Run**: Models download automatically to `~/.u2net/` directory
2. **Server Restart**: Model sessions recreated (~2-3s startup time)
3. **Memory**: GPU deployment requires sufficient VRAM (8GB+ recommended)
4. **Storage**: ~1GB for all models combined

## Environment Variables

Optional configuration in `.env`:

```bash
# Background removal model (optional)
BACKGROUND_REMOVAL_MODEL=birefnet-portrait

# YOLO face model path (optional) 
YOLO_FACE_MODEL_PATH=/tmp/yolov8n-face.pt
```

## Health Check

Test the deployment:

```bash
python manage.py shell
>>> from passport_photo.services import PassportPhotoProcessor
>>> processor = PassportPhotoProcessor()
>>> # Should show GPU detection and model loading
```