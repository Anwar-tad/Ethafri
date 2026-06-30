# ============================================================
# 📁 ፋይል፦ EthAfri/purge_fake_data.py
# 📝 ዓላማ፦ Safe Database Tables Drop — CASCADE Reset for Fresh Start (v1.1)
# ✅ የተፈቱ ችግሮች፦ Dynamic PostgreSQL/SQLite CASCADE drop and fresh django migrate bootstrapping, unblocks all migration deadlocks permanently
# ============================================================

import os
import django

# 1. Django ቅንብርን ማግኘት
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

def purge_database_tables():
    print("🧹 Dropping all marketplace database tables with CASCADE...")
    
    marketplace_tables = [
        "marketplace_producttranslation", "marketplace_translationqueue",
        "marketplace_product", "marketplace_sellerprofile", "marketplace_notificationqueue",
        "marketplace_aiprojectbacklog", "marketplace_securitylog", "marketplace_agenterrorlog",
        "marketplace_aievolutionlog", "marketplace_vectormemory", "marketplace_selfhealinglog",
        "marketplace_category", "marketplace_siteregistry", "marketplace_usersearch", 
        "marketplace_agenttask", "marketplace_predictionlog", "marketplace_abtest", "marketplace_externalapi"
    ]
    
    try:
        with connection.cursor() as cursor:
            # 1. ሁሉንም የገበያ ሰንጠረዦች በ CASCADE ማጥፋት
            for table in marketplace_tables:
                if connection.vendor == 'sqlite':
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}";')
                else:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
            
            # 2. django_migrations መዝገብን ከ app 'marketplace' ማጽዳት
            cursor.execute("DELETE FROM django_migrations WHERE app='marketplace';")
            
        print("✅ All tables and migration records dropped successfully from DB!")
        print("🛠️ Running clean migrations from scratch (0001_initial)...")
        call_command('migrate', interactive=False)
        print("🎉 Fresh migrations applied successfully! Database is completely clean and ready.")
    except Exception as e:
        print(f"❌ Failed to drop database tables: {e}")

if __name__ == "__main__":
    purge_database_tables()