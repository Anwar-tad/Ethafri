# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/urls.py
# 📝 ስሪት፦ v10.17 (Master CEO Agent URL Mapping - Complete & Aligned Edition)
# ✅ የተፈቱ ችግሮች፦ Integrated frictionless token-based login routing, dynamic GSC indexer endpoint, and Ajax A/B test variant converters.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

from django.urls import path
from . import views

urlpatterns = [
    # ============================================================
    # 🏠 1. የገበያ ቦታው ዋና ክፍሎች (Core Marketplace Views)
    # ============================================================
    path('', views.home, name='home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('post/', views.post_product, name='post_product'),
    path('success/', views.post_success, name='post_success'),
    
    # ============================================================
    # 🔐 2. የተጠቃሚዎች ማንነት ማረጋገጫ (Authentication)
    # ============================================================
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # 🚪 ከውዝግብ የጸዳ ፈጣን የ ghost ተጠቃሚ መግቢያ (Frictionless Onboarding Token Link Handler) [1]
    path('api/login-token/', views.magic_login_token_view, name='magic_login_token'),
    
    # ============================================================
    # 🧠 3. የኤጀንቱ የሥራ መቆጣጠሪያ (Master CEO Command Center)
    # ============================================================
    # የባለቤቱ ዋና የዕድገት ዳሽቦርድ
    path('growth-dashboard/', views.admin_growth_dashboard, name='growth_dashboard'),
    
    # የባለቤት ቀጥተኛ ትዕዛዝ መስጫ (Executive Overrides)
    path('owner-directive/', views.owner_directive_view, name='owner_directive'),
    
    # ኤጀንቱን በእጅ በሃይል ማስነሻ (Manual UI Evolution Trigger)
    path('trigger-evolution/', views.trigger_evolution, name='trigger_evolution'),
    
    # 📊 4. የኤጀንት ሁኔታ እና ጤና (Agent Health & Status)
    path('agent-status/', views.agent_status_dashboard, name='agent_status'),
    
    # 🌐 5. ባለብዙ-ጣቢያ አስተዳደር (Multi-Site Management)
    path('sites/', views.sites_dashboard, name='sites_dashboard'),
    path('sites/<int:site_id>/', views.site_detail, name='site_detail'),
    
    # 📱 6. የማርኬቲንግ እና የንግድ ዕድገት (Growth & Marketing)
    path('marketing/', views.marketing_dashboard, name='marketing_dashboard'),
    path('marketing/create/', views.create_marketing_campaign, name='create_marketing_campaign'),
    
    # 🧠 7. የእቅድ እና ስራዎች ዕዝ ማዕከል (Autonomous Backlog Orchestrator)
    path('backlog/', views.manage_backlog_view, name='manage_backlog'),
    
    # ============================================================
    # ⚡ 8. የኤጀንት ኤፒአይዎች እና ዌብሁኮች (Automation & Webhooks)
    # ============================================================
    # ለሪል-ታይም ዳሽቦርድ የሚሆን ዳታ መመለሻ
    path('api/advanced-stats/', views.advanced_stats_api, name='advanced_stats_api'),
    
    # 🤖 ኤጀንቱን በኤፒአይ በኩል በራስ-ገዝ ማስነሻ
    path('api/agent/run/', views.trigger_autonomous_evolution, name='api_trigger_evolution'),
    
    # 🤖 የኤጀንት ሁኔታ በ JSON መልክ
    path('api/agent/status/', views.advanced_stats_api, name='api_agent_status'),
    
    # የውጭ ክሮን (External Cron) Webhook Gateway
    path('evolve-now-secret-123/', views.trigger_autonomous_evolution, name='trigger_autonomous_evolution'),
    
    # የዳሽቦርድ Purge እና Autopilot ኤፒአይዎች
    path('api/agent/purge-db/', views.purge_database_view, name='api_purge_database'),
    path('api/agent/toggle-autopilot/', views.toggle_autopilot_view, name='api_toggle_autopilot'),
    
    # 🔴 አዲስ የተጨመሩ የ A/B ሙከራ እና የ GSC API ኢንዴክሰር አድራሻዎች [1]
    path('api/ab-test/<int:test_id>/view/', views.record_ab_view_api, name='api_record_ab_view'),
    path('api/ab-test/<int:test_id>/conversion/', views.record_ab_conversion_api, name='api_record_ab_conversion'),
    path('api/agent/gsc-index/', views.google_search_console_index_view, name='api_gsc_index'),
    # 📡 9. የይዘት አሰሳ መቆጣጠሪያ አድራሻ (Harvester Orchestrator)
    path('harvester/', views.harvester_orchestrator_view, name='harvester_orchestrator'),
]