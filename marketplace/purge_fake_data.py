# ============================================================
# 📁 ፋይል፦ EthAfri/purge_fake_data.py
# 📝 ዓላማ፦ Safe Database Tables Drop — CASCADE Reset for Fresh Start (v10.17)
# ✅ የተፈቱ ችግሮች፦ Dynamic model schema discovery, automatic settings detection, fresh migrations, dynamic DB table scan, and primary site auto-registration.
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

import os
import sys
import django

# 1. የ Settings አቅጣጫን በራስ-ሰር መለየት (Cross-Deployment Safety)
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Django መጫኛን በደህንነት ማስጀመር
django.setup()

from django.db import connection, connections, transaction # 🛡️ connections እዚህ ተጨምሯል
from django.core.management import call_command
from django.apps import apps

def get_marketplace_tables():
    """
    የእቅድ ማሳደጊያ (Self-Evolution) አዳዲስ ሞዴሎችን ቢጨምር እንኳ ስህተት እንዳይፈጠር
    ሰንጠረዦቹን በሙሉ ከጃንጎ ሬጅስትሪ በዳይናሚክ መንገድ ፈልጎ ያወጣል
    """
    try:
        app_config = apps.get_app_config('marketplace')
        tables = [model._meta.db_table for model in app_config.get_models()]
        return tables
    except Exception as e:
        print(f"⚠️ Registry Scan Warning: App config scan failed: {e}. Falling back to default list...")
        # የሬጅስትሪ ፍተሻው ካልሰራ ወደ ነባሪው ዝርዝር መመለስ (Fallback)
        return [
            "marketplace_producttranslation", "marketplace_translationqueue",
            "marketplace_product", "marketplace_sellerprofile", "marketplace_notificationqueue",
            "marketplace_aiprojectbacklog", "marketplace_securitylog", "marketplace_agenterrorlog",
            "marketplace_aievolutionlog", "marketplace_vectormemory", "marketplace_selfhealinglog",
            "marketplace_category", "marketplace_siteregistry", "marketplace_usersearch", 
            "marketplace_agenttask", "marketplace_predictionlog", "marketplace_abtest", "marketplace_externalapi"
        ]

def purge_database_tables():
    print("🧹 Discovery: Detecting all active database tables in marketplace app...")
    marketplace_tables = get_marketplace_tables()
    
    print(f"🧹 Dropping {len(marketplace_tables)} tables with CASCADE...")
    
    try:
        with connection.cursor() as cursor:
            # 1. ሁሉንም የገበያ ሰንጠረዦች በ CASCADE ማጥፋት (sqlite እና postgresql ለይቶ)
            for table in marketplace_tables:
                if connection.vendor == 'sqlite':
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}";')
                else:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
            
            # 2. django_migrations መዝገብን ከ app 'marketplace' ማጽዳት
            try:
                cursor.execute("DELETE FROM django_migrations WHERE app='marketplace';")
            except Exception as mig_err:
                print(f"⚠️ Migrations Table Notice: Skipped migrations record delete: {mig_err}")
            
        print("✅ All discovered tables and migration records dropped successfully!")
        print("🛠️ Running clean migrations from scratch (0001_initial)...")
        call_command('migrate', interactive=False)
        print("🎉 Fresh migrations applied successfully!")
        
        # 3. የ "primary" ሳይት ምዝገባን በራስ-ሰር መፍጠር (Auto-Registration Boost)
        print("🌱 Seeding: Auto-registering fresh 'primary' site to unblock agent loop...")
        SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')
        
        with transaction.atomic():
            SiteRegistry.objects.get_or_create(
                name="primary",
                defaults={
                    'display_name': 'EthAfri Primary',
                    'niche': 'general',
                    'target_market': 'Global',
                    'is_active': True,
                    'build_phase': 0
                }
            )
        print("🎉 'primary' site registered successfully! System is fully ready for next loop.")
        
    except Exception as e:
        print(f"❌ Failed to purge database and bootstrap system: {e}")
    finally:
        # 🧹 connections ን በደህንነት መዝጋት
        try:
            connections.close_all()
        except Exception:
            pass

if __name__ == "__main__":
    purge_database_tables()