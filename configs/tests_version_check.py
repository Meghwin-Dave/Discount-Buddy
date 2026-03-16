from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from .models import AppConfig, AppConfigKeys, AppPlatforms
from django.contrib.auth import get_user_model

User = get_user_model()

class VersionCheckTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='password')
        
        # Create some default configs
        AppConfig.objects.create(
            config_key=AppConfigKeys.MOBILE_APP_MINIMUM_VERSION_ANDROID,
            config_value="1.0.0",
            platform=AppPlatforms.ANDROID,
            created_by=self.user
        )
        AppConfig.objects.create(
            config_key=AppConfigKeys.MOBILE_APP_LATEST_VERSION_ANDROID,
            config_value="1.2.0",
            platform=AppPlatforms.ANDROID,
            created_by=self.user
        )
        AppConfig.objects.create(
            config_key=AppConfigKeys.MOBILE_APP_UPDATE_MESSAGE,
            config_value="Please update your app",
            platform=None, # Common
            created_by=self.user
        )

    def test_version_check_no_update(self):
        url = '/api/app/version/check'
        data = {'platform': 'android', 'version': '1.2.0'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_update_available'])
        self.assertEqual(response.data['update_type'], 'none')

    def test_version_check_optional_update(self):
        url = '/api/app/version/check'
        data = {'platform': 'android', 'version': '1.1.0'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_update_available'])
        self.assertEqual(response.data['update_type'], 'optional')
        self.assertEqual(response.data['update_message'], "Please update your app")

    def test_version_check_empty_platform_fallback(self):
        # Create a config with empty string platform instead of NULL
        AppConfig.objects.create(
            config_key=AppConfigKeys.MOBILE_APP_LATEST_VERSION_IOS,
            config_value="1.0.0",
            platform="",
            created_by=self.user
        )
        
        url = '/api/app/version/check'
        data = {'platform': 'ios', 'version': '0.9.0'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_update_available'])
        # It should find the config even with empty string platform
        self.assertEqual(response.data['latest_version'], "1.0.0")

    def test_invalid_platform(self):
        url = '/api/app/version/check'
        data = {'platform': 'windows', 'version': '1.0.0'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
