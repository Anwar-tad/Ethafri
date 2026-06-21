# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/urls.py
# 📝 ለውጥ፦ Multi-Site Dashboard + Marketing Dashboard + Site Detail URLs
# 📅 ቀን፦ 2026-06-20
# ============================================================

from django.urls import path
from . import views

urlpatterns = [
    # 🏠 ዋና ገጽ እና ምርት መፈለጊያ
    path('', views.home, name='home'),
    
    # 📦 ምርት መለጠፊያ እና የስኬት ገጽ
    path('post/', views.post_product, name='post_product'),
    path('success/', views.post_success, name='post_success'),
    
    # 🔍 ነጠላ ምርት በዝርዝር ማሳያ አድራሻ (Product Detail View)
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    
    # 🔐 የተጠቃሚዎች ማንነት ማረጋገጫ (Authentication System)
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # 🧠 የባለቤት ዕዝ ማዕከል (Control & Growth Dashboard)
    path('growth-dashboard/', views.admin_growth_dashboard, name='growth_dashboard'),
    
    # 👑 የባለቤት መመሪያ ገጽ (Owner Directive Panel)
    path('owner-directive/', views.owner_directive_view, name='owner_directive'),
    
    # ⚙️ የዕድገት መቀስቀሻ በእጅ ማዘዣ (Update AI Now)
    path('trigger-evolution/', views.trigger_evolution, name='trigger_evolution'),
    
    # 🌐 ከ cron-job.org የሚመጣን ውጫዊ ጥሪ ተቀብሎ የዕድገት ሞተሩን የሚያስነሳው ዋናው በር
    path('evolve-now-secret-123/', views.trigger_autonomous_evolution, name='trigger_autonomous_evolution'),
    
    # ============================================================
    # 🌐 አዲስ Multi-Site ዩአርኤሎች
    # ============================================================
    
    # 📊 ሁሉንም ጣቢያዎች የሚያሳይ ዳሽቦርድ
    path('sites/', views.sites_dashboard, name='sites_dashboard'),
    
    # 📋 የአንድ የተወሰነ ጣቢያ ዝርዝር ገጽ
    path('sites/<int:site_id>/', views.site_detail, name='site_detail'),
    
    # 📱 የማርኬቲንግ ዳሽቦርድ
    path('marketing/', views.marketing_dashboard, name='marketing_dashboard'),
    
    # ✏️ አዲስ ማርኬቲንግ ካምፔን መፍጠሪያ
    path('marketing/create/', views.create_marketing_campaign, name='create_marketing_campaign'),
    path('agent-status/', views.agent_status_dashboard, name='agent_status'),
]