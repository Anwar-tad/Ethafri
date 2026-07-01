# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/routing.py
# 📝 ዓላማ፦ WebSocket Routing for Real-time Dashboard Updates (v1.1 - Complete)
# ✅ የተፈቱ ችግሮች፦ Dynamic ASGI consumer routing, multi-tenant workspace updates connection pathing
# 📅 ቀን፦ Wednesday, July 01, 2026
# ============================================================

from django.urls import re_path
from . import consumers

# የዳሽቦርዱን የሪል-ታይም መረጃ ስርጭት ከአስገቢው ጋር ማገናኘት [1.1.2, 3.1.2]
websocket_urlpatterns = [
    re_path(r'^ws/agent-status/$', consumers.AgentStatusConsumer.as_asgi()),
]