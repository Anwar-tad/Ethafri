#EthAfri/marketplace/urls.py


from django.urls import path
from . import views

urlpatterns = [
    # ዋና ገጽ (እቃዎችን እና የ AI ውጤቶችን የሚያሳይ)
    path('', views.home, name='home'),
    
    # እቃ መለጠፊያ እና ስኬት ገጽ
    path('post/', views.post_product, name='post_product'),
    path('success/', views.post_success, name='post_success'),
    
    # የተጠቃሚዎች መለያ (Authentication)
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # የ AI ራስ-ገዝ ዕድገት መቀስቀሻ (ለ Cron-job የሚሆን)
    path('evolve-now-secret-123/', views.trigger_evolution, name='trigger_evolution'),
    
    # የዕድገት መቆጣጠሪያ ዴሽቦርድ (ለአስተዳዳሪው ብቻ)
    path('growth-dashboard/', views.admin_growth_dashboard, name='growth_dashboard'),
]