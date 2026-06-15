from django.urls import path
from . import views

urlpatterns = [
    # ዋና ገጽ (እቃዎችን የሚያሳይ እና ፍለጋን የሚያስተናግድ)
    path('', views.home, name='home'),
    
    # እቃ መለጥፊያ ገጽ (በ AI የሚታገዝ)
    path('post/', views.post_product, name='post_product'),
    
    # የዕድገት ዴሽቦርድ (ለአንተ ለባለቤቱ ብቻ፡ AI ገበያውን መርምሮ ሪፖርት የሚያቀርብበት)
    path('growth-dashboard/', views.admin_growth_dashboard, name='growth_dashboard'),
    
    # እቃው በተሳካ ሁኔታ ሲለጠፍ የሚታይ ገጽ
    path('success/', views.post_success, name='post_success'),
    path('evolve-now-secret-123/', views.trigger_evolution, name='trigger_evolution'),
]