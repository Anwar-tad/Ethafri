# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/urls.py
# 📝 ለውጥ፦ Advanced Agent Features — New URLs added
# 📅 ቀን፦ 2026-06-21
# ============================================================

from django.urls import path
from . import views

urlpatterns = [
    # 🏠 ዋና ገጽ እና ምርት መፈለጊያ
    path('', views.home, name='home'),
    
    # 📦 ምርት መለጠፊያ እና የስኬት ገጽ
    path('post/', views.post_product, name='post_product'),
    path('success/', views.post_success, name='post_success'),
    
    # 🔍 ነጠላ ምርት በዝርዝር ማሳያ አድራሻ
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    
    # 🔐 የተጠቃሚዎች ማንነት ማረጋገጫ
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # 🧠 የባለቤት ዕዝ ማዕከል
    path('growth-dashboard/', views.admin_growth_dashboard, name='growth_dashboard'),
    
    # 👑 የባለቤት መመሪያ ገጽ
    path('owner-directive/', views.owner_directive_view, name='owner_directive'),
    
    # ⚙️ የዕድገት መቀስቀሻ በእጅ ማዘዣ
    path('trigger-evolution/', views.trigger_evolution, name='trigger_evolution'),
    
    # 🌐 ውጫዊ ጥሪ ተቀብሎ የዕድገት ሞተሩን የሚያስነሳ
    path('evolve-now-secret-123/', views.trigger_autonomous_evolution, name='trigger_autonomous_evolution'),
    
    # ============================================================
    # 🌐 Multi-Site ዩአርኤሎች
    # ============================================================
    path('sites/', views.sites_dashboard, name='sites_dashboard'),
    path('sites/<int:site_id>/', views.site_detail, name='site_detail'),
    
    # ============================================================
    # 📱 የማርኬቲንግ ዩአርኤሎች
    # ============================================================
    path('marketing/', views.marketing_dashboard, name='marketing_dashboard'),
    path('marketing/create/', views.create_marketing_campaign, name='create_marketing_campaign'),
    
    # ============================================================
    # 🆕 የላቁ የኤጀንት ባህሪያት (Advanced Agent Features)
    # ============================================================
    
    # 📊 የኤጀንት ሁኔታ ዳሽቦርድ
    path('agent-status/', views.agent_status_dashboard, name='agent_status'),
    
    # 📊 የላቁ ስታቲስቲክስ ኤፒአይ (Advanced Stats API)
    path('api/advanced-stats/', views.advanced_stats_api, name='advanced_stats_api'),
    
    # 🤖 ኤጀንቱን በእጅ ማስነሳት (API)
    path('api/agent/run/', views.trigger_evolution, name='api_trigger_evolution'),
    
    # 🤖 የኤጀንት ሁኔታ (API)
    path('api/agent/status/', views.agent_status_dashboard, name='api_agent_status'),
]