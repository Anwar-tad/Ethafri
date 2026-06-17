# EthAfri/marketplace/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # 🏠 ዋና ገጽ እና ምርት መፈለጊያ
    path('', views.home, name='home'),
    
    # 📦 ምርት መለጠፊያ እና የስኬት ገጽ (የእንግዳ ተጠቃሚ 5 ገደብ መቆጣጠሪያን ጨምሮ)
    path('post/', views.post_product, name='post_product'),
    path('success/', views.post_success, name='post_success'),
    
    # 🔍 ነጠላ ምርት በዝርዝር ማሳያ አድራሻ (Product Detail View)
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    
    # 🔐 የተጠቃሚዎች ማንነት ማረጋገጫ (Authentication System)
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # 🧠 የ AI ራስ-ገዝ አስተዳደር እና የባለቤት መመሪያዎች (Control & Growth Dashboard)
    path('owner-directive/', views.owner_directive_view, name='owner_directive'),
    path('growth-dashboard/', views.admin_growth_dashboard, name='growth_dashboard'),
    
    # 🚦 የ 5 ደቂቃ ራስ-ሰር የዕድገት እና የኮድ/ዳታቤዝ ጥገና መቀስቀሻ (Core Evolution Endpoint)
    path('evolve-now-secret-123/', views.trigger_evolution, name='trigger_evolution'),
]
