# EthAfri/marketplace/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('post/', views.post_product, name='post_product'),
    
    # ⚠️ አዲሱ የእቃ ዝርዝር ገጽ አድራሻ
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    
    path('success/', views.post_success, name='post_success'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('owner-directive/', views.owner_directive_view, name='owner_directive'),
    path('evolve-now-secret-123/', views.trigger_evolution, name='trigger_evolution'),
    path('growth-dashboard/', views.admin_growth_dashboard, name='growth_dashboard'),
]