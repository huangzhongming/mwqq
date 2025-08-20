# Passport Photo System - Test Suite

## Overview

This test suite provides comprehensive end-to-end testing for the passport photo processing system, including API endpoints, photo processing, and result verification.

## Test Scripts

### `e2e_test.py` - Main E2E Test Suite

**Usage:**
```bash
# Full end-to-end test (upload → process → download)
python tests/e2e_test.py

# Test API endpoints only (fast, no processing)
python tests/e2e_test.py --api-only

# Verify existing processed results
python tests/e2e_test.py --verify-only

# Run without usage instructions
python tests/e2e_test.py --no-instructions
```

**What it tests:**
- ✅ Server connectivity
- ✅ Countries API endpoint
- ✅ Photo upload functionality  
- ✅ Job status polling
- ✅ Result download and verification
- ✅ Image dimensions and quality

## Test Modes

### 1. Full E2E Test (Default)
- Tests complete workflow from upload to download
- May timeout if background processing hangs
- Best for verifying end-to-end functionality

### 2. API-Only Test (`--api-only`)
- Tests all API endpoints without waiting for processing
- Fast and reliable
- Good for CI/CD pipelines

### 3. Verification Mode (`--verify-only`)  
- Checks existing processed photos
- Verifies web access and file quality
- Useful when processing is known to be working

## Prerequisites

1. **Backend server running:**
   ```bash
   cd backend
   source venv/bin/activate
   python manage.py runserver
   ```

2. **Test image available:**
   - Default: `/Users/zhongminghuang/github/mwqq/tmp/wy_small.jpg`
   - Update `self.test_image` in script if different location

3. **Python dependencies:**
   - `requests` - HTTP client
   - `PIL` (optional) - Image dimension checking

## Expected Results

### Successful Test Output:
```
🚀 Full E2E Test Mode
==============================
✅ PASS Server Connectivity: Django server and API accessible
✅ PASS Countries API: Found 7 countries including Finland
✅ PASS Test Image: Image file found (108542 bytes)
✅ PASS Photo Upload: Upload successful, Job ID: abc123...
✅ PASS Job Processing: Processing completed in 15s
✅ PASS Result Download: Downloaded 90,297 bytes, 500×653 pixels

📊 TEST SUMMARY
==================================================
Tests passed: 6/6
🎉 ALL TESTS PASSED!
```

### Common Issues:

1. **Server Not Running:**
   ```
   ❌ FAIL Server Connectivity: Cannot connect to server on localhost:8000
   ```
   **Fix:** Start Django server

2. **Processing Timeout:**
   ```
   ❌ FAIL Job Processing: Timeout after 90 seconds
   ```
   **Fix:** Use `--verify-only` to check existing results

3. **Test Image Not Found:**
   ```
   ❌ FAIL Test Image: Test image file not found
   ```
   **Fix:** Update image path or copy test image to expected location

## Output Files

Test results are saved to `/tmp/` with timestamps:
- `/tmp/e2e_result_20250820_143052.jpg` - Downloaded test result
- `/tmp/verified_passport_20250820_143105.jpg` - Verified existing result

## Integration with Development

### Daily Development Testing:
```bash
# Quick API health check
python tests/e2e_test.py --api-only

# Verify system is producing good results  
python tests/e2e_test.py --verify-only
```

### CI/CD Integration:
```bash
# Non-interactive test for automated pipelines
python tests/e2e_test.py --api-only --no-instructions
echo $?  # Exit code: 0 = success, 1 = failure
```

### Manual Quality Verification:
```bash
# Full test with result download for manual inspection
python tests/e2e_test.py
# Check the downloaded file in /tmp/ for quality
```

## Troubleshooting

### Server Issues:
- Ensure Django server is running on port 8000
- Check for port conflicts: `lsof -i :8000`
- Verify CORS settings allow test requests

### Processing Issues:  
- Background removal models may hang on first use
- Use existing results verification instead
- Check server logs for processing errors

### File Access Issues:
- Ensure test image exists and is readable
- Check `/tmp/` directory permissions for output files
- Verify media directory permissions for processed photos

## Extending the Tests

### Adding New Test Cases:
```python
def test_new_feature(self):
    """Test description"""
    # Test implementation
    self.log_result("New Feature", success, "Test message")
    return success
```

### Custom Configuration:
```python
# Update these class variables for your setup
self.base_url = "http://localhost:8000"
self.test_image = "/path/to/your/test/image.jpg"
```

### Different Country Testing:
```python
# Test with different countries
us = next((c for c in countries if c.get('code') == 'US'), None)
# Expected dimensions: 600×600 for US passport
```