# ============================================================
# 📁 ፋይል፦ EthAfri/core/asgi.py
# 📝 ለውጥ፦ ASGI configuration for WebSocket support
# 📅 ቀን፦ 2026-06-21
# ============================================================

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Django ASGI application
django_asgi_app = get_asgi_application()

# Import consumers
from marketplace import consumers

# WebSocket URL patterns
websocket_urlpatterns = [
    path('ws/agent-status/', consumers.AgentStatusConsumer.as_asgi()),
]

# Application routing
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

