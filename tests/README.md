# Test Suite Organization

This directory contains all tests for the Passport Photo Service, organized by test type for better maintainability.

## Directory Structure

```
tests/
├── integration/          # End-to-end integration tests
├── performance/          # Performance and benchmarking tests  
├── debug/               # Debug and development utilities
└── README.md           # This file
```

## Test Categories

### Integration Tests (`integration/`)
End-to-end tests that verify complete workflows:

- `e2e_test.py` - Main E2E test suite for core functionality
- `test_birefnet_e2e.py` - BiRefNet-Portrait workflow testing
- `test_semi_auto.py` - Semi-automatic processing workflow

**Usage:**
```bash
cd backend && source venv/bin/activate
python ../tests/integration/e2e_test.py
```

### Performance Tests (`performance/`)
Benchmarking and performance analysis:

- `test_birefnet.py` - Compare background removal model performance
- `test_birefnet_subsequent.py` - Test subsequent call performance
- `test_rembg_gpu.py` - GPU vs CPU performance comparison

**Usage:**
```bash
cd backend && source venv/bin/activate
python ../tests/performance/test_birefnet.py
```

### Debug Utilities (`debug/`)
Development and debugging tools:

- `debug_face_detection.py` - Face detection debugging with visual output
- `debug_face_detection_old.py` - Legacy debug script

**Usage:**
```bash
cd backend && source venv/bin/activate
python ../tests/debug/debug_face_detection.py
```

## Running Tests

### Prerequisites
1. Start the Django development server:
```bash
cd backend && source venv/bin/activate && python manage.py runserver
```

2. Ensure test images are available in `tmp/` directory

### Test Images
Tests expect these files in the project root `tmp/` directory:
- `tmp/test.png` - Standard test image
- `tmp/test2.jpg` - High-resolution test image

### Environment
- All tests use relative paths for portability
- Django settings are configured automatically
- GPU tests gracefully fall back to CPU if CUDA unavailable

## Development Notes

- All paths are relative to project root for security/privacy
- Tests are self-contained and don't require external dependencies beyond requirements.txt
- Visual debug outputs are saved to `tmp/` directory for inspection
- Performance tests provide timing and quality metrics for optimization