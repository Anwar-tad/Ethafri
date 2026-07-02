from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from typing import Dict, List, Optional, Union, Any
import logging
import json
import hashlib
import os

logger = logging.getLogger(__name__)

class AIUtils:
    """
    Core utility class for AI-driven operations within EthAfri Django ecosystem.
    Consolidates AI utilities, caching, and performance optimizations.
    """
    
    # Cache keys
    CACHE_PREFIX = "ai_utils_"
    DEFAULT_CACHE_TIMEOUT = 3600  # 1 hour
    
    @staticmethod
    def generate_cache_key(prefix: str, *args) -> str:
        """Generate a consistent cache key from variable arguments."""
        key_str = ':'.join(str(arg) for arg in args)
        return f"{AIUtils.CACHE_PREFIX}{prefix}:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    @staticmethod
    def get_cached(key: str, default=None, timeout: Optional[int] = None) -> Any:
        """Retrieve cached data with optional fallback."""
        cache_key = AIUtils.generate_cache_key(key)
        return cache.get(cache_key, default)
    
    @staticmethod
    def set_cached(key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Set cached data with optional timeout override."""
        cache_key = AIUtils.generate_cache_key(key)
        timeout = timeout or AIUtils.DEFAULT_CACHE_TIMEOUT
        cache.set(cache_key, value, timeout=timeout)
        return True
    
    @staticmethod
    def clear_cache(key: str = None) -> int:
        """Clear cache by optional key prefix or entire AIUtils cache."""
        if key:
            pattern = f"{AIUtils.CACHE_PREFIX}{key}*"
            keys = cache.keys(pattern)
            for k in keys:
                cache.delete(k)
            return len(keys)
        else:
            keys = cache.keys(f"{AIUtils.CACHE_PREFIX}*")
            for k in keys:
                cache.delete(k)
            return len(keys)
    
    @staticmethod
    def sanitize_input(data: Union[str, Dict, List]) -> Union[str, Dict, List]:
        """Sanitize user input to prevent XSS and injection."""
        if isinstance(data, str):
            return data.replace('<', '&lt;').replace('>', '&gt;')
        elif isinstance(data, dict):
            return {k: AIUtils.sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [AIUtils.sanitize_input(item) for item in data]
        return data
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format using RFC 5322 compliant regex."""
        import re
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2}$"
        return re.match(pattern, email) is not None
    
    @staticmethod
    def get_ai_model_version() -> str:
        """Return current AI model version from settings."""
        return getattr(settings, 'AI_MODEL_VERSION', '2026.07.02')
    
    @staticmethod
    def is_ai_feature_enabled(feature_name: str) -> bool:
        """Check if a specific AI feature is enabled in settings."""
        enabled_features = getattr(settings, 'AI_ENABLED_FEATURES', [])
        return feature_name in enabled_features
    
    @staticmethod
    def log_ai_activity(activity_type: str, metadata: Dict[str, Any], user_id: Optional[int] = None):
        """Log AI activity for analytics and debugging."""
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'activity_type': activity_type,
            'metadata': metadata,
            'user_id': user_id,
            'model_version': AIUtils.get_ai_model_version()
        }
        logger.info(json.dumps(log_entry))
    
    @staticmethod
    def get_ai_config(config_key: str, default=None) -> Any:
        """Retrieve AI configuration from settings or environment."""
        config_path = f"AI_CONFIG_{config_key.upper()}"
        return getattr(settings, config_path, os.getenv(config_path, default))
    
    @staticmethod
    def generate_ai_response_schema(response_type: str, schema_version: str = "1.0") -> Dict[str, Any]:
        """Generate a standardized response schema for AI outputs."""
        return {
            "schema_version": schema_version,
            "response_type": response_type,
            "generated_at": timezone.now().isoformat(),
            "status": "success",
            "data": None
        }
    
    @staticmethod
    def load_ai_model(model_name: str) -> Any:
        """Load AI model from cache or filesystem with fallback."""
        cache_key = AIUtils.generate_cache_key("model", model_name)
        model = AIUtils.get_cached(cache_key)
        
        if model is not None:
            return model
        
        # Fallback to model loading logic
        model_path = os.path.join(settings.BASE_DIR, 'ai_models', f"{model_name}.pkl")
        if os.path.exists(model_path):
            try:
                import pickle
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                AIUtils.set_cached(cache_key, model)
                return model
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
        
        return None

# Django Template Tag for AI Utilities
from django import template

register = template.Library()

@register.simple_tag
def ai_config(config_key: str, default=None):
    """Template tag to access AI configuration."""
    return AIUtils.get_ai_config(config_key, default)

@register.simple_tag
def ai_model_version():
    """Template tag to get current AI model version."""
    return AIUtils.get_ai_model_version()

@register.simple_tag
def ai_feature_enabled(feature_name: str):
    """Template tag to check if AI feature is enabled."""
    return AIUtils.is_ai_feature_enabled(feature_name)
