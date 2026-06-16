import os
import django

# 1. Django Setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

def create_ethafri_admin():
    # እነዚህን መረጃዎች እንደፈለክ መቀየር ትችላለህ
    username = 'Anwar'
    email = 'ilvuma11@gmail.com'
    password = 'projectreyhan2026' # ጠንካራ ፓስወርድ

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f"✅ EthAfri Admin '{username}' created successfully!")
    else:
        print(f"ℹ️ Admin '{username}' already exists. Skipping...")

if __name__ == "__main__":
    create_ethafri_admin()