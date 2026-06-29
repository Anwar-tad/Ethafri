# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/routing.py
# 📝 ዓላማ፦ WebSocket Routing for Real-time Dashboard Updates (v1.0)
# ============================================================

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # ✅ የዳሽቦርዱን የሪል-ታይም መረጃ ስርጭት ከአስገቢው ጋር ማገናኘት
    re_path(r'^ws/agent-status/$', consumers.AgentStatusConsumer.as_asgi()),
]