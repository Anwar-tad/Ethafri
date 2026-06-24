# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/urls.py
# 📝 ለውጥ፦ Master CEO Agent URL Mapping — Clean & Consolidated
# ✅ የተፈቱ ችግሮች፦ View function name mismatches, Redundant API endpoints
# 📅 ቀን፦ 2026-06-23
# ============================================================

from django.urls import path
from . import views

urlpatterns = [
    # 🏠 1. የገበያ ቦታው ዋና ክፍሎች (Core Marketplace)
    path('', views.home, name='home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('post/', views.post_product, name='post_product'),
    
    # 🔐 2. የተጠቃሚዎች ማንነት ማረጋገጫ (Authentication)
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # 🧠 3. የኤጀንቱ የሥራ መቆጣጠሪያ (Master CEO Dashboard)
    # የባለቤቱ ዋና የዕድገት ዳሽቦርድ
    path('growth-dashboard/', views.admin_growth_dashboard, name='growth_dashboard'),
    
    # የባለቤት ቀጥተኛ ትዕዛዝ መስጫ (Executive Overrides)
    path('owner-directive/', views.owner_directive_view, name='owner_directive'),
    
    # ኤጀንቱን በእጅ በሃይል ማስነሻ (Manual Evolution Trigger)
    path('trigger-evolution/', views.trigger_evolution, name='trigger_evolution'),
    
    # 📊 4. የኤጀንት ሁኔታ እና ጤና (Agent Health & Stats)
    # የኤጀንቱ ዝርዝር ሁኔታ (Memory, Predictions, Logs)
    path('agent-status/', views.agent_status_dashboard, name='agent_status'),
    
    # 🌐 5. ባለብዙ-ጣቢያ አስተዳደር (Multi-Site Management)
    path('sites/', views.sites_dashboard, name='sites_dashboard'),
    path('sites/<int:site_id>/', views.site_detail, name='site_detail'),
    
    # 📱 6. የማርኬቲንግ እና የንግድ ዕድገት (Growth & Marketing)
    path('marketing/', views.marketing_dashboard, name='marketing_dashboard'),
    path('marketing/create/', views.create_marketing_campaign, name='create_marketing_campaign'),
    
    # ⚡ 7. የኤጀንት ኤፒአይዎች (Automation & Webhooks)
    # ለሪል-ታይም ዳሽቦርድ የሚሆን ዳታ መመለሻ
    path('api/v1/agent-stats/', views.advanced_stats_api, name='advanced_stats_api'),
    
    # የውጭ ክሮን (External Cron) Webhook Gateway
    path('evolve-now-secret-123/', views.trigger_autonomous_evolution, name='trigger_autonomous_evolution'),
]