# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/core/asgi.py
# 📝 ዓላማ፦ ASGI Configuration for real-time WebSocket Channels (v1.3 - Complete)
# ✅ የተፈቱ ችግሮች፦ Resolved AppRegistryNotReady by calling get_asgi_application() first, handled lazy websocket consumers import safely.
# 📅 ቀን፦ Wednesday, July 01, 2026
# ============================================================

import os
import logging
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# ⚠️ AppRegistryNotReady ስህተትን ለመከላከል get_asgi_application() ከላይ መኖር አለበት [1, 1.1.2]
django_asgi_app = get_asgi_application()

websocket_urlpatterns = []
try:
    from marketplace import consumers
    websocket_urlpatterns = [
        path('ws/agent-status/', consumers.AgentStatusConsumer.as_asgi()),
    ]
except ImportError as ie:
    # 🔴 [ZERO PASS]: በስህተት ተቆርጦ የነበረው ባዶ ሎጂክ በአስተማማኝ ሎገር ተተክቷል [1]
    logger.error("ASGI Scaffolding: Failed to import marketplace consumers. WebSocket disabled: %s", ie)

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})