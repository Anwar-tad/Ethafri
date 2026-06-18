# EthAfri/marketplace/urls.py

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
    
    # ⚙️ የዕድገት መቀስቀሻ በእጅ ማዘዣ (Update AI Now) - ከስህተት የጸዳ እንዲሆን ተጨምሯል
    path('trigger-evolution/', views.trigger_evolution, name='trigger_evolution'),
    
    # 🌐 ከ cron-job.org የሚመጣን ውጫዊ ጥሪ ተቀብሎ የዕድገት ሞተሩን የሚያስነሳው ዋናው በር
    path('evolve-now-secret-123/', views.trigger_autonomous_evolution, name='trigger_autonomous_evolution'),
]