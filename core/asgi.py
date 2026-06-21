# ============================================================
# 📁 ፋይል፦ EthAfri/core/asgi.py
# 📝 ለውጥ፦ ASGI configuration for WebSocket support
# 📅 ቀን፦ 2026-06-22
# ============================================================

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Django ASGI application
django_asgi_app = get_asgi_application()

# Import consumers (ደህንነት ባለው መንገድ)
try:
    from marketplace import consumers
    websocket_urlpatterns = [
        path('ws/agent-status/', consumers.AgentStatusConsumer.as_asgi()),
    ]
except ImportError:
    # ከሌለ ባዶ ይሁን
    websocket_urlpatterns = []

# Application routing
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})