# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/routing.py
# 📝 ዓላማ፦ WebSocket Routing for Real-time Dashboard Updates (v10.16)
# ✅ የተፈቱ ችግሮች፦ Dynamic ASGI consumer routing, multi-tenant workspace updates connection pathing
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

from django.urls import re_path
from . import consumers

# የዳሽቦርዱን የሪል-ታይም መረጃ ስርጭት ከአስገቢው ጋር ማገናኘት [1, 2]
websocket_urlpatterns = [
    re_path(r'^ws/agent-status/$', consumers.AgentStatusConsumer.as_asgi()),
]