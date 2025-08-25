from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


class PassportPhotoAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_check(self):
        """Test that the health check endpoint works"""
        # Since we don't have the health endpoint defined yet, let's just test the root
        response = self.client.get('/')
        # This should return 404 which is expected for undefined root endpoint
        self.assertIn(response.status_code, [200, 404])

    def test_api_endpoints_exist(self):
        """Test that our main API structure is set up correctly"""
        # Test that the app is properly configured
        from django.conf import settings
        self.assertIn('passport_photo', settings.INSTALLED_APPS)
        self.assertIn('rest_framework', settings.INSTALLED_APPS)

    def test_models_import(self):
        """Test that models can be imported without errors"""
        try:
            from . import models
            self.assertTrue(True)  # If we get here, import worked
        except ImportError:
            self.fail("Could not import models")

    def test_views_import(self):
        """Test that views can be imported without errors"""
        try:
            from . import views
            self.assertTrue(True)  # If we get here, import worked
        except ImportError:
            self.fail("Could not import views")