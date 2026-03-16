from .models import AppConfig, AppConfigKeys, AppPlatforms
from .utils import compare_versions
from django.db import models
import logging

logger = logging.getLogger(__name__)

class AppConfigService:
    @staticmethod
    def check_version(platform: str, current_version: str) -> dict:
        platform = platform.lower()
        logger.info(f"Checking version for platform: {platform}, current_version: {current_version}")
        
        # Define keys based on platform
        if platform == AppPlatforms.ANDROID:
            min_key = AppConfigKeys.MOBILE_APP_MINIMUM_VERSION_ANDROID
            latest_key = AppConfigKeys.MOBILE_APP_LATEST_VERSION_ANDROID
            store_url_key = AppConfigKeys.MOBILE_APP_STORE_URL_ANDROID
            force_threshold_key = AppConfigKeys.MOBILE_APP_FORCE_UPDATE_THRESHOLD_ANDROID
            critical_key = AppConfigKeys.MOBILE_APP_CRITICAL_VERSION_ANDROID
        else: # ios
            min_key = AppConfigKeys.MOBILE_APP_MINIMUM_VERSION_IOS
            latest_key = AppConfigKeys.MOBILE_APP_LATEST_VERSION_IOS
            store_url_key = AppConfigKeys.MOBILE_APP_STORE_URL_IOS
            force_threshold_key = AppConfigKeys.MOBILE_APP_FORCE_UPDATE_THRESHOLD_IOS
            critical_key = AppConfigKeys.MOBILE_APP_CRITICAL_VERSION_IOS
            
        update_message_key = AppConfigKeys.MOBILE_APP_UPDATE_MESSAGE
        
        config_keys = [min_key, latest_key, store_url_key, force_threshold_key, critical_key, update_message_key]
        
        # Query configs - handle null OR empty platform field for common configs
        configs_qs = AppConfig.objects.filter(
            config_key__in=config_keys, 
            is_active=True
        ).filter(
            models.Q(platform=platform) | 
            models.Q(platform__isnull=True) | 
            models.Q(platform="")
        )
        
        configs_dict = {ac.config_key: ac.config_value for ac in configs_qs}
        logger.info(f"Found configs: {list(configs_dict.keys())}")
        
        minimum_version = configs_dict.get(min_key)
        latest_version = configs_dict.get(latest_key)
        force_threshold = configs_dict.get(force_threshold_key)
        critical_version = configs_dict.get(critical_key)
        update_message = configs_dict.get(update_message_key, "Update available")
        store_url = configs_dict.get(store_url_key)
        
        result = {
            "is_update_available": False,
            "update_type": "none",
            "is_force_update": False,
            "is_critical_update": False,
            "is_optional_update": False,
            "update_message": None,
            "latest_version": latest_version,
            "minimum_version": minimum_version,
            "store_url": store_url
        }
        
        # Evaluation Logic
        try:
            if critical_version and compare_versions(current_version, critical_version) < 0:
                result.update({"update_type": "critical", "is_critical_update": True, "is_force_update": True, "is_update_available": True})
            elif force_threshold and compare_versions(current_version, force_threshold) < 0:
                result.update({"update_type": "force", "is_force_update": True, "is_update_available": True})
            elif latest_version and compare_versions(current_version, latest_version) < 0:
                result.update({"update_type": "optional", "is_optional_update": True, "is_update_available": True})
                
            if result["is_update_available"]:
                result["update_message"] = update_message
            
            logger.info(f"Version check result: {result['update_type']} (available: {result['is_update_available']})")
        except Exception as e:
            logger.error(f"Error evaluating versions: {e}")
            # Don't re-throw here, return what we have (none update) to avoid 500
            
        return result

    @staticmethod
    def get_all_configs(platform=None, is_active=None):
        query = AppConfig.objects.all()
        if platform:
            query = query.filter(platform=platform)
        if is_active is not None:
            query = query.filter(is_active=is_active)
        return query

    @staticmethod
    def create_config(data, user):
        data['created_by'] = user
        return AppConfig.objects.create(**data)

    @staticmethod
    def update_config(config_id, data, user):
        try:
            config = AppConfig.objects.get(id=config_id)
            for attr, value in data.items():
                setattr(config, attr, value)
            config.updated_by = user
            config.save()
            return config
        except AppConfig.DoesNotExist:
            return None
