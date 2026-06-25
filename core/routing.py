# 📄 ፋይል፦ EthAfri/marketplace/routing.py (ወይም core/routing.py)
from django.urls import re_path
from . import consumers  # የ Consumer ፋይልህን ስም አረጋግጥ

websocket_urlpatterns = [
    # መጨረሻው ላይ / መኖሩን እና የ Consumer ስም ትክክል መሆኑን አረጋግጥ
    re_path(r'^ws/agent-status/$', consumers.AgentStatusConsumer.as_asgi()),
]
