#!/usr/bin/env python
# ============================================================
# 📁 ፋይል፦ EthAfri/create_admin.py
# 📝 ለውጥ፦ የተሻሻለ — አድሚን አካውንት ራስ-ሰር መፍጠሪያ (Clean/Bug-free)
# 📅 ቀን፦ 2026-06-20
# ============================================================

import os
import django

# 1. Django Setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

def main():
    """
    የEthAfri አድሚን አካውንት ይፈጥራል (ከሌለ)
    በመጀመሪያ ከአካባቢ ተለዋዋጮች ለመውሰድ ይሞክራል፤ ካልተገኘ ወደ ነባሪ እሴት ይተካል
    """
    username = os.environ.get('ADMIN_USERNAME', 'Anwar')
    email = os.environ.get('ADMIN_EMAIL', 'ilvuma11@gmail.com')
    password = os.environ.get('ADMIN_PASSWORD', 'projectreyhan2026')

    if not username or not email or not password:
        print("❌ Error: Admin credentials cannot be empty.")
        return

    try:
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            print(f"✅ EthAfri Admin '{username}' created successfully!")
            print(f"📧 Email: {email}")
            print(f"🔑 Password: [HIDDEN]")
        else:
            print(f"ℹ️ Admin '{username}' already exists. Skipping...")
    except Exception as e:
        print(f"❌ Error creating admin: {e}")

if __name__ == "__main__":
    main()