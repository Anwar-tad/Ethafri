# 📄 ፋይል፦ EthAfri/core/routing.py (ወይም ማዕከላዊው የ ASGI ራውቲንግ ፋይል)
from django.urls import re_path
from marketplace.consumers import AgentStatusConsumer # የ Consumer ፋይልህን ስም አረጋግጥ

websocket_urlpatterns = [
    # የ Regex ማጣቀሻው ከመስመሩ ጋር መገጠሙን አረጋግጥ
    re_path(r'^ws/agent-status/$', AgentStatusConsumer.as_asgi()),
]

